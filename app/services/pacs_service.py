from io import BytesIO

import pydicom
from typing import List, Dict, Any
from app.core.interfaces.pacs_interface import IPacsService
from app.infrastructure.http_client import HttpClient
from app.core.exceptions.pacs_exceptions import PacsConnectionError, PacsDataError


class PacsService(IPacsService):
    def __init__(self, http_client: HttpClient, pacs_url: str, pacs_auth: tuple):
        self._http_client = http_client
        self._pacs_url = pacs_url
        self._pacs_auth = pacs_auth

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
                "Patient Name": data.get('PatientMainDicomTags', {}).get('PatientName', 'N/A'),
                "Patient Birth Date": data.get('PatientMainDicomTags', {}).get('PatientBirthDate', 'N/A'),
                "Patient Sex": data.get('PatientMainDicomTags', {}).get('PatientSex', 'N/A'),
                "Study Date": data.get('MainDicomTags', {}).get('StudyDate', 'N/A'),
                "Study Instance UID": data.get('MainDicomTags', {}).get('StudyInstanceUID', 'N/A'),
                "Description": data.get('MainDicomTags', {}).get('StudyDescription', 'N/A'),
                "Series Status": data.get('SeriesMainDicomTags', {}).get('Status', 'N/A')
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

    def send_to_pacs(self, data: bytes, target_url: str) -> bool:
        try:
            response = self._http_client.post(
                f"{target_url}/instances",
                data=data,
                headers={"Content-Type": "application/dicom"}
            )
            return response.status_code == 200
        except Exception as e:
            raise PacsConnectionError(f"Nu am putut trimite datele la PACS: {e}")

    def send_study_to_pacs(self, study_id: str, target_url: str, target_auth: tuple,
                           examination_result: str = None) -> bool:
        """
        Smart send: Create if new, Update if exists.
        """
        try:
            instances = self.get_study_instances(study_id)

            if not instances:
                raise PacsDataError(f"No instances found in study {study_id}")

            # VERIFICĂ dacă studiul există deja în target PACS
            existing_study_id = self._find_existing_study_in_target(study_id, target_url, target_auth)

            if existing_study_id:
                print(f"📝 Study exists in target PACS (ID: {existing_study_id}) - UPDATING with new result")

                # 1. Șterge studiul existent
                delete_success = self._delete_existing_study(existing_study_id, target_url, target_auth)

                if not delete_success:
                    print(f"❌ Failed to delete existing study, aborting update")
                    return False

                # 2. Recreează cu rezultatul nou
                print(f"🔄 Recreating study with new examination result...")
                return self._create_new_study(study_id, target_url, target_auth, examination_result)
            else:
                print(f"✨ Study does not exist in target PACS - CREATING new")
                return self._create_new_study(study_id, target_url, target_auth, examination_result)

        except Exception as e:
            raise PacsConnectionError(f"Nu am putut procesa studiul în PACS: {e}")

    def _find_existing_study_in_target(self, source_study_id: str, target_url: str, target_auth: tuple) -> str:
        """
        Find if study already exists in target PACS. Returns target study ID if found.
        """
        try:
            # Get Study Instance UID from source
            source_metadata = self.get_study_metadata(source_study_id)
            study_instance_uid = source_metadata.get("Study Instance UID")

            if not study_instance_uid:
                return None

            print(f"🔍 Looking for study with UID: {study_instance_uid}")

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

            print(f"❌ Study not found in target PACS")
            return None

        except Exception as e:
            print(f"Error searching for existing study: {e}")
            return None

    def _update_existing_study(self, target_study_id: str, target_url: str, target_auth: tuple,
                               examination_result: str) -> bool:
        """
        Update existing study in target PACS with new examination result.
        """
        try:
            print(f"🔄 Updating study {target_study_id} with new result...")

            # For now, let's simplify - just delete and let the caller recreate
            print(f"🗑️ Deleting existing study {target_study_id}...")
            delete_response = self._http_client.delete(f"{target_url}/studies/{target_study_id}", auth=target_auth)

            print(f"🗑️ Delete response status: {delete_response.status_code}")
            if hasattr(delete_response, 'text'):
                print(f"🗑️ Delete response: {delete_response.text[:200]}...")

            if delete_response.status_code == 200:
                print(f"✅ Existing study deleted successfully")
                return True  # Let the main function handle recreation
            else:
                print(f"❌ Failed to delete existing study: {delete_response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error updating existing study: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _create_new_study(self, study_id: str, target_url: str, target_auth: tuple, examination_result: str) -> bool:
        """
        Create new study in target PACS.
        """
        try:
            instances = self.get_study_instances(study_id)
            success_count = 0
            total_instances = len(instances)

            print(f"📤 Creating new study with {total_instances} instances...")

            for instance in instances:
                instance_id = instance.get("ID")
                if not instance_id:
                    continue

                try:
                    print(f"🔄 Processing instance {instance_id}...")

                    # Get original DICOM
                    dicom_data = self.get_dicom_file(instance_id)
                    print(f"  📥 Retrieved DICOM data: {len(dicom_data)} bytes")

                    # Add examination result if provided
                    if examination_result:
                        print(f"  📝 Adding examination result: {len(examination_result)} chars")
                        modified_dicom_data = self._add_examination_result_to_dicom(
                            dicom_data, examination_result
                        )
                        print(f"  📝 Modified DICOM data: {len(modified_dicom_data)} bytes")
                    else:
                        modified_dicom_data = dicom_data
                        print(f"  📝 No examination result, using original data")

                    # Send to target PACS
                    print(f"  📤 Sending to {target_url}/instances...")
                    response = self._http_client.post(
                        f"{target_url}/instances",
                        data=modified_dicom_data,
                        auth=target_auth,
                        headers={"Content-Type": "application/dicom"}
                    )

                    print(f"  📨 Response status: {response.status_code}")
                    if hasattr(response, 'text') and response.text:
                        print(f"  📨 Response text: {response.text[:200]}...")

                    if response.status_code == 200:
                        success_count += 1
                        print(f"  ✓ Instance {instance_id} sent successfully")
                    else:
                        print(f"  ✗ Failed to send instance {instance_id}")
                        print(f"    Status: {response.status_code}")
                        print(
                            f"    Response: {response.text[:500] if hasattr(response, 'text') else 'No response text'}")

                except Exception as e:
                    print(f"  ✗ Error sending instance {instance_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"📊 Final result: {success_count}/{total_instances} instances sent")
            return success_count == total_instances

        except Exception as e:
            print(f"❌ Error creating new study: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _delete_existing_study(self, target_study_id: str, target_url: str, target_auth: tuple) -> bool:
        """
        Delete existing study from target PACS.
        """
        try:
            print(f"🗑️ Deleting existing study {target_study_id}...")
            delete_response = self._http_client.delete(f"{target_url}/studies/{target_study_id}", auth=target_auth)

            print(f"🗑️ Delete response status: {delete_response.status_code}")

            if delete_response.status_code == 200:
                print(f"✅ Existing study deleted successfully")
                return True
            else:
                print(f"❌ Failed to delete existing study: {delete_response.status_code}")
                if hasattr(delete_response, 'text'):
                    print(f"❌ Response: {delete_response.text[:200]}...")
                return False

        except Exception as e:
            print(f"❌ Error deleting existing study: {e}")
            return False

    def _add_examination_result_to_dicom(self, dicom_data: bytes, examination_result: str) -> bytes:
        try:
            dicom_dataset = pydicom.dcmread(BytesIO(dicom_data))

            # Adaugă în Image Comments (vizibil ca "Image Comments")
            dicom_dataset.ImageComments = examination_result[:10240]

            # Adaugă tag-uri private pentru backup
            dicom_dataset.add_new(0x77770010, 'LO', 'MEDICAL_APP_RESULT')
            dicom_dataset.add_new(0x77771001, 'LT', examination_result)

            # Salvează
            output_buffer = BytesIO()
            dicom_dataset.save_as(output_buffer, write_like_original=False)
            return output_buffer.getvalue()

        except Exception as e:
            print(f"Error: {e}")
            return dicom_data

    def get_examination_result_from_dicom(self, instance_id: str) -> str:
        try:
            dicom_data = self.get_dicom_file(instance_id)
            dicom_dataset = pydicom.dcmread(BytesIO(dicom_data))

            # Try to get examination result from our private tag first
            if 0x77771001 in dicom_dataset:
                return str(dicom_dataset[0x77771001].value)

            # Fallback to Image Comments
            if hasattr(dicom_dataset, 'ImageComments'):
                return str(dicom_dataset.ImageComments)

            return ""

        except ImportError:
            print("Warning: pydicom not available for reading DICOM metadata")
            return ""
        except Exception as e:
            print(f"Warning: Failed to read examination result from DICOM: {e}")
            return ""