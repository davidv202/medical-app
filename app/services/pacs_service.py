from io import BytesIO

import pydicom
from typing import List, Dict, Any
from app.core.interfaces.pacs_interface import IPacsService
from app.infrastructure.http_client import HttpClient
from app.core.exceptions.pacs_exceptions import PacsConnectionError, PacsDataError


class PacsService(IPacsService):
    def __init__(self, http_client: HttpClient, pacs_url: str, pacs_auth: tuple):
        self._http_client = http_client

        if pacs_url and pacs_auth:
            self._pacs_url = pacs_url
            self._pacs_auth = pacs_auth
        else:
            from app.config.settings import Settings
            self._pacs_url, self._pacs_auth = Settings.get_pacs_config()

        from app.di.container import Container
        self._anonymizer = Container.get_dicom_anonymizer_service()

    def get_all_studies(self) -> List[str]:
        try:
            response = self._http_client.get(f"{self._pacs_url}/studies", auth=self._pacs_auth)
            return response.json()
        except Exception as e:
            raise PacsConnectionError(f"Nu am putut incarca studiile: {e}")

    def get_study_metadata(self, study_id: str) -> Dict[str, Any]:
        try:
            response = self._http_client.get(f"{self._pacs_url}/studies/{study_id}", auth=self._pacs_auth)
            data = response.json()

            return {
                # Date Pacient - ESENȚIALE
                "Patient Name": data.get('PatientMainDicomTags', {}).get('PatientName', 'N/A'),
                "Patient ID": data.get('PatientMainDicomTags', {}).get('PatientID', 'N/A'),
                "Patient Birth Date": data.get('PatientMainDicomTags', {}).get('PatientBirthDate', 'N/A'),
                "Patient Sex": data.get('PatientMainDicomTags', {}).get('PatientSex', 'N/A'),
                "Patient Age": data.get('PatientMainDicomTags', {}).get('PatientAge', 'N/A'),

                # Date Studiu - CRITICE
                "Study Date": data.get('MainDicomTags', {}).get('StudyDate', 'N/A'),
                "Study Time": data.get('MainDicomTags', {}).get('StudyTime', 'N/A'),
                "Description": data.get('MainDicomTags', {}).get('StudyDescription', 'N/A'),
                "Study Instance UID": data.get('MainDicomTags', {}).get('StudyInstanceUID', 'N/A'),
                "Referring Physician": data.get('MainDicomTags', {}).get('ReferringPhysicianName', 'N/A'),
                "Study ID": data.get('MainDicomTags', {}).get('StudyID', 'N/A'),
                "Accession Number": data.get('MainDicomTags', {}).get('AccessionNumber', 'N/A'),
                "Referring Physician Name": data.get('MainDicomTags', {}).get('ReferringPhysicianName', 'N/A'),
                "Radipharmaceutical"

                # Date Echipament
                "Institution Name": data.get('MainDicomTags', {}).get('InstitutionName', 'N/A'),
                "Modality": data.get('MainDicomTags', {}).get('Modality', 'N/A'),

                # Date Serie (primul disponibil)
                "Series Description": data.get('SeriesMainDicomTags', {}).get('SeriesDescription', 'N/A'),
                "Body Part Examined": data.get('SeriesMainDicomTags', {}).get('BodyPartExamined', 'N/A'),

                # Status
                "Series Status": data.get('SeriesMainDicomTags', {}).get('Status', 'Available')
            }
        except Exception as e:
            raise PacsDataError(f"Nu am putut incarca metadatele din studiul {study_id}: {e}")

    def get_study_instances(self, study_id: str) -> List[Dict[str, Any]]:
        try:
            response = self._http_client.get(f"{self._pacs_url}/studies/{study_id}/instances", auth=self._pacs_auth)
            return response.json()
        except Exception as e:
            raise PacsDataError(f"Nu am putut accesa instantele studiului {study_id}: {e}")

    def get_dicom_file(self, instance_id: str) -> bytes:
        try:
            response = self._http_client.get(f"{self._pacs_url}/instances/{instance_id}/file", auth=self._pacs_auth)
            return response.content
        except Exception as e:
            raise PacsDataError(f"Nu am putut accesa fisierul DICOM pentru instanta {instance_id}: {e}")

    def send_study_to_pacs(self, study_id: str, target_url: str, target_auth: tuple,
                           examination_result: str = None, anonymize: bool = False) -> bool:

        try:
            instances = self.get_study_instances(study_id)

            if not instances:
                raise PacsDataError(f"No instances found in study {study_id}")

            existing_study_id = self._find_existing_study_in_target(study_id, target_url, target_auth)

            if existing_study_id:
                print(f"Study exists in target PACS (ID: {existing_study_id}) - UPDATING with new result")

                delete_success = self._delete_existing_study(existing_study_id, target_url, target_auth)

                if not delete_success:
                    print(f"Failed to delete existing study, aborting update")
                    return False

                print(f"Recreating study with new examination result...")
                return self._create_new_study(study_id, target_url, target_auth, examination_result, anonymize)
            else:
                print(f"Study does not exist in target PACS - CREATING new")
                return self._create_new_study(study_id, target_url, target_auth, examination_result, anonymize)

        except Exception as e:
            raise PacsConnectionError(f"Nu am putut procesa studiul în PACS: {e}")

    def _find_existing_study_in_target(self, source_study_id: str, target_url: str, target_auth: tuple) -> str:

        try:
            # Get Study Instance UID from source
            source_metadata = self.get_study_metadata(source_study_id)
            study_instance_uid = source_metadata.get("Study Instance UID")

            if not study_instance_uid:
                return None

            print(f"Looking for study with UID: {study_instance_uid}")

            # Search in target PACS
            response = self._http_client.get(f"{target_url}/studies", auth=target_auth)
            target_studies = response.json()

            for target_study_id in target_studies:
                try:
                    response = self._http_client.get(f"{target_url}/studies/{target_study_id}", auth=target_auth)
                    target_metadata = response.json()

                    target_uid = target_metadata.get('MainDicomTags', {}).get('StudyInstanceUID')

                    if target_uid == study_instance_uid:
                        print(f"✅ Found existing study: {target_study_id}")
                        return target_study_id

                except Exception as e:
                    continue

            print(f"Study not found in target PACS")
            return None

        except Exception as e:
            print(f"Error searching for existing study: {e}")
            return None

    def _create_new_study(self, study_id: str, target_url: str, target_auth: tuple, examination_result: str, anonymize: bool = False) -> bool:

        try:
            instances = self.get_study_instances(study_id)
            success_count = 0
            total_instances = len(instances)

            print(f"Creating new study with {total_instances} instances...")

            for instance in instances:
                instance_id = instance.get("ID")
                if not instance_id:
                    continue

                try:
                    print(f"Processing instance {instance_id}...")

                    # Get original DICOM
                    dicom_data = self.get_dicom_file(instance_id)
                    print(f"Retrieved DICOM data: {len(dicom_data)} bytes")

                    if anonymize:
                        print(f"Anonymizing PACS DICOM data...")
                        dicom_data = self._anonymizer.anonymize_dicom(dicom_data)
                        print(f"DICOM anonymized: {len(dicom_data)} bytes")

                    # Add examination result if provided
                    if examination_result:
                        print(f"Adding examination result: {len(examination_result)} chars")
                        modified_dicom_data = self.add_examination_result_to_dicom(
                            dicom_data, examination_result
                        )
                        print(f"Modified DICOM data: {len(modified_dicom_data)} bytes")
                    else:
                        modified_dicom_data = dicom_data
                        print(f"No examination result, using original data")

                    # Send to target PACS
                    print(f"Sending to {target_url}/instances...")
                    response = self._http_client.post(
                        f"{target_url}/instances",
                        data=modified_dicom_data,
                        auth=target_auth,
                        headers={"Content-Type": "application/dicom"}
                    )

                    print(f"Response status: {response.status_code}")
                    if hasattr(response, 'text') and response.text:
                        print(f"Response text: {response.text[:200]}...")

                    if response.status_code == 200:
                        success_count += 1
                        print(f"Instance {instance_id} sent successfully")
                    else:
                        print(f"Failed to send instance {instance_id}")
                        print(f"Status: {response.status_code}")
                        print(
                            f"Response: {response.text[:500] if hasattr(response, 'text') else 'No response text'}")

                except Exception as e:
                    print(f"Error sending instance {instance_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"Final result: {success_count}/{total_instances} instances sent")
            return success_count == total_instances

        except Exception as e:
            print(f"Error creating new study: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _delete_existing_study(self, target_study_id: str, target_url: str, target_auth: tuple) -> bool:

        try:
            print(f"Deleting existing study {target_study_id}...")
            delete_response = self._http_client.delete(f"{target_url}/studies/{target_study_id}", auth=target_auth)

            print(f"Delete response status: {delete_response.status_code}")

            if delete_response.status_code == 200:
                print(f"Existing study deleted successfully")
                return True
            else:
                print(f"Failed to delete existing study: {delete_response.status_code}")
                if hasattr(delete_response, 'text'):
                    print(f"Response: {delete_response.text[:200]}...")
                return False

        except Exception as e:
            print(f"Error deleting existing study: {e}")
            return False

    def add_examination_result_to_dicom(self, dicom_data: bytes, examination_result: str) -> bytes:
        try:
            dicom_dataset = pydicom.dcmread(BytesIO(dicom_data))

            # PRINCIPAL: Image Comments (0020,4000) - Funcționează pe toate instanțele DICOM
            if len(examination_result) <= 10240:
                dicom_dataset.ImageComments = examination_result
                print(f"Added to ImageComments: {len(examination_result)} chars")
            else:
                # Pentru texte lungi, trunchiază și adaugă notificare
                truncated_text = examination_result[:10200] + "\n\n[TRUNCATED - See private tags]"
                dicom_dataset.ImageComments = truncated_text
                print(f"Added truncated to ImageComments: {len(truncated_text)} chars")

            dicom_dataset.add_new(0x77770010, 'LO', 'MEDICAL_APP_RESULT')

            if len(examination_result) <= 65534:  # Limita pentru un tag LT
                dicom_dataset.add_new(0x77771001, 'LT', examination_result)
                print(f"Added complete result to private tag: {len(examination_result)} chars")
            else:
                # Împarte textul în segmente de max 65000 caractere
                chunk_size = 65000
                chunks = [examination_result[i:i + chunk_size] for i in range(0, len(examination_result), chunk_size)]

                for i, chunk in enumerate(chunks[:10]):  # Maxim 10 chunks
                    tag_element = 0x1001 + i  # 0x77771001, 0x77771002, etc.
                    dicom_dataset.add_new(0x7777, tag_element, 'LT', chunk)
                    print(f"Added chunk {i + 1} to private tag 7777,{tag_element:04X}: {len(chunk)} chars")

                dicom_dataset.add_new(0x77770020, 'IS', str(len(chunks)))

            try:
                if not hasattr(dicom_dataset, 'StudyComments'):
                    study_comment = f"EXAMINATION RESULT: {examination_result[:200]}"
                    dicom_dataset.add_new(0x0032, 0x4000, 'LT', study_comment)
                    print(f"Added to StudyComments: {len(study_comment)} chars")
            except:
                pass

            # Salvează
            output_buffer = BytesIO()
            dicom_dataset.save_as(output_buffer, write_like_original=False)

            final_size = len(output_buffer.getvalue())
            print(f"Final DICOM size: {final_size} bytes (original: {len(dicom_data)})")

            return output_buffer.getvalue()

        except Exception as e:
            print(f"Error adding examination result to DICOM: {e}")
            import traceback
            traceback.print_exc()
            return dicom_data

    def get_examination_result_from_dicom(self, instance_id: str) -> str:
        try:
            dicom_data = self.get_dicom_file(instance_id)
            dicom_dataset = pydicom.dcmread(BytesIO(dicom_data))

            # PRIORITATE 1: Tag-urile noastre private (textul complet)
            if (0x7777, 0x0010) in dicom_dataset:
                print(f"Found our private tags in instance {instance_id}")

                # Verifică dacă avem un singur tag sau multiple chunks
                if (0x7777, 0x0020) in dicom_dataset:  # Tag pentru numărul de chunks
                    try:
                        num_chunks = int(str(dicom_dataset[0x7777, 0x0020].value))
                        print(f"Found {num_chunks} chunks")

                        result_parts = []
                        for i in range(num_chunks):
                            tag_element = 0x1001 + i
                            if (0x7777, tag_element) in dicom_dataset:
                                chunk = str(dicom_dataset[0x7777, tag_element].value)
                                result_parts.append(chunk)
                                print(f"Read chunk {i + 1}: {len(chunk)} chars")

                        if result_parts:
                            complete_result = ''.join(result_parts)
                            print(f"Reconstructed complete result: {len(complete_result)} chars")
                            return complete_result
                    except:
                        pass

                # Fallback la tag-ul simplu
                if (0x7777, 0x1001) in dicom_dataset:
                    private_result = str(dicom_dataset[0x7777, 0x1001].value)
                    print(f"Found private tag result: {len(private_result)} chars")
                    return private_result

            # PRIORITATE 2: Image Comments (disponibil peste tot)
            if hasattr(dicom_dataset, 'ImageComments'):
                image_comments = str(dicom_dataset.ImageComments)
                print(f"Found ImageComments: {len(image_comments)} chars")
                return image_comments

            # PRIORITATE 3: Study Comments (dacă există)
            if (0x0032, 0x4000) in dicom_dataset:
                study_comments = str(dicom_dataset[0x0032, 0x4000].value)
                if "EXAMINATION RESULT:" in study_comments:
                    result = study_comments.replace("EXAMINATION RESULT: ", "")
                    print(f"Found StudyComments result: {len(result)} chars")
                    return result

            print(f"No examination result found in instance {instance_id}")
            return ""

        except ImportError:
            print("Warning: pydicom not available for reading DICOM metadata")
            return ""
        except Exception as e:
            print(f"Warning: Failed to read examination result from DICOM {instance_id}: {e}")
            return ""