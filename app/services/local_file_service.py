import os
import json
import uuid
from typing import List, Dict, Any, Tuple
from datetime import datetime
import pydicom

from app.core.interfaces.local_file_interface import ILocalFileService
from app.core.exceptions.pacs_exceptions import PacsDataError


class LocalFileService(ILocalFileService):

    def __init__(self, cache_dir: str = "local_studies_cache"):
        self.cache_dir = cache_dir
        self.local_studies: Dict[str, Dict[str, Any]] = {}  # study_id -> study_data
        self.study_instances: Dict[str, List[Dict[str, Any]]] = {}  # study_id -> instances
        self.instance_files: Dict[str, str] = {}  # instance_id -> file_path
        self.examination_results: Dict[str, str] = {}  # study_id -> examination_result

        os.makedirs(cache_dir, exist_ok=True)

        self._load_cache()

    def load_dicom_file(self, file_path: str) -> Dict[str, Any]:

        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            dataset = pydicom.dcmread(file_path)

            metadata = self._extract_metadata_from_dataset(dataset)

            study_instance_uid = getattr(dataset, 'StudyInstanceUID', str(uuid.uuid4()))
            study_id = f"local_{abs(hash(study_instance_uid)) % 1000000}"

            instance_id = f"local_{abs(hash(getattr(dataset, 'SOPInstanceUID', str(uuid.uuid4())))) % 1000000}"

            self.local_studies[study_id] = metadata
            self.instance_files[instance_id] = file_path

            if study_id not in self.study_instances:
                self.study_instances[study_id] = []

            instance_data = {
                "ID": instance_id,
                "StudyID": study_id,
                "FilePath": file_path,
                "SOPInstanceUID": getattr(dataset, 'SOPInstanceUID', instance_id),
                "SeriesInstanceUID": getattr(dataset, 'SeriesInstanceUID', str(uuid.uuid4())),
                "InstanceNumber": getattr(dataset, 'InstanceNumber', 1)
            }

            if not any(inst["ID"] == instance_id for inst in self.study_instances[study_id]):
                self.study_instances[study_id].append(instance_data)

            self._save_cache()

            return {
                "study_id": study_id,
                "metadata": metadata,
                "instance_id": instance_id
            }

        except Exception as e:
            raise PacsDataError(f"Error loading DICOM file {file_path}: {e}")

    def load_dicom_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(folder_path):
            raise PacsDataError(f"Folder not found: {folder_path}")

        loaded_studies = []
        study_files = {}  # study_id -> list of files

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)

                if self._is_dicom_file(file_path):
                    try:
                        result = self.load_dicom_file(file_path)
                        study_id = result["study_id"]

                        if study_id not in study_files:
                            study_files[study_id] = []
                            loaded_studies.append({
                                "study_id": study_id,
                                "metadata": result["metadata"],
                                "file_count": 0
                            })

                        study_files[study_id].append(file_path)

                    except Exception as e:
                        print(f"Warning: Could not load {file_path}: {e}")
                        continue

        for study_data in loaded_studies:
            study_id = study_data["study_id"]
            study_data["file_count"] = len(study_files.get(study_id, []))

        return loaded_studies

    def get_study_metadata_from_file(self, file_path: str) -> Dict[str, Any]:
        result = self.load_dicom_file(file_path)
        return result["metadata"]

    def get_local_study_instances(self, study_id: str) -> List[Dict[str, Any]]:
        return self.study_instances.get(study_id, [])

    def get_local_dicom_file(self, instance_id: str) -> bytes:
        file_path = self.instance_files.get(instance_id)
        if not file_path or not os.path.exists(file_path):
            raise PacsDataError(f"Local DICOM file not found for instance {instance_id}")

        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise PacsDataError(f"Error reading local DICOM file: {e}")

    def add_examination_result_to_local_study(self, study_id: str, examination_result: str) -> bool:
        try:
            self.examination_results[study_id] = examination_result
            self._save_cache()
            return True
        except Exception as e:
            print(f"Error saving examination result: {e}")
            return False

    def get_examination_result_from_local_study(self, study_id: str) -> str:
        return self.examination_results.get(study_id, "")

    def get_all_local_studies(self) -> List[str]:
        return list(self.local_studies.keys())

    def get_local_study_metadata(self, study_id: str) -> Dict[str, Any]:
        if study_id not in self.local_studies:
            raise PacsDataError(f"Local study {study_id} not found")
        return self.local_studies[study_id]

    def clear_local_studies(self):
        self.local_studies.clear()
        self.study_instances.clear()
        self.instance_files.clear()
        self.examination_results.clear()
        self._save_cache()

    def remove_local_study(self, study_id: str) -> bool:
        try:
            if study_id in self.local_studies:
                del self.local_studies[study_id]
            if study_id in self.study_instances:
                # Clean up instance files
                for instance in self.study_instances[study_id]:
                    instance_id = instance.get("ID")
                    if instance_id in self.instance_files:
                        del self.instance_files[instance_id]
                del self.study_instances[study_id]
            if study_id in self.examination_results:
                del self.examination_results[study_id]

            self._save_cache()
            return True
        except Exception as e:
            print(f"Error removing local study: {e}")
            return False

    def send_local_study_to_pacs(self, study_id: str, target_url: str, target_auth: Tuple[str, str],
                                 examination_result: str = None, dicom_modifier_callback=None) -> bool:
        try:
            print(f"📤 LocalFileService: Sending local study {study_id} to {target_url}")

            # Verifică că studiul există
            if study_id not in self.local_studies:
                raise PacsDataError(f"Local study {study_id} not found")

            # Obține instanțele studiului
            instances = self.get_local_study_instances(study_id)
            if not instances:
                raise PacsDataError(f"No instances found in local study {study_id}")

            success_count = 0
            total_instances = len(instances)

            print(f"   📄 Found {total_instances} instances in local study")

            # Importă requests pentru HTTP
            import requests
            from requests.auth import HTTPBasicAuth

            for i, instance in enumerate(instances):
                instance_id = instance.get("ID")
                if not instance_id:
                    print(f"   ⚠️ Instance {i + 1} has no ID, skipping")
                    continue

                try:
                    print(f"   🔄 Processing local instance {i + 1}/{total_instances}: {instance_id}")

                    # Citește fișierul DICOM local
                    dicom_data = self.get_local_dicom_file(instance_id)
                    print(f"      📥 Read local DICOM: {len(dicom_data)} bytes")

                    # Aplică modificarea DICOM (ex: adăugarea rezultatului) prin callback
                    if dicom_modifier_callback and examination_result:
                        print(f"      📝 Applying DICOM modifications via callback...")
                        modified_dicom_data = dicom_modifier_callback(dicom_data, examination_result)
                        print(f"      📝 Modified DICOM: {len(modified_dicom_data)} bytes")
                    else:
                        modified_dicom_data = dicom_data
                        print(f"      📝 No modifications, using original data")

                    # Trimite la target PACS
                    print(f"      📤 Sending to {target_url}/instances...")
                    response = requests.post(
                        f"{target_url}/instances",
                        data=modified_dicom_data,
                        auth=HTTPBasicAuth(*target_auth),
                        headers={"Content-Type": "application/dicom"},
                        timeout=30
                    )

                    print(f"      📨 Response: {response.status_code}")

                    if response.status_code == 200:
                        success_count += 1
                        print(f"      ✅ Local instance sent successfully")
                    else:
                        print(f"      ❌ Failed to send local instance")
                        print(f"         Status: {response.status_code}")
                        if hasattr(response, 'text'):
                            print(f"         Response: {response.text[:200]}...")

                except Exception as e:
                    print(f"      ❌ Error sending local instance {instance_id}: {e}")
                    continue

            # Rezultat final
            print(f"   📊 Final result: {success_count}/{total_instances} local instances sent")

            success = success_count == total_instances

            if success:
                print(f"   ✅ All local instances sent successfully!")
            else:
                print(f"   ⚠️ Partial success: {success_count}/{total_instances} instances sent")

            return success

        except Exception as e:
            print(f"❌ LocalFileService: Error sending local study {study_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_examination_result_from_local_dicom_file(self, instance_id: str) -> str:
        try:
            file_path = self.instance_files.get(instance_id)
            if not file_path or not os.path.exists(file_path):
                # Fallback la cache-ul local
                return self.examination_results.get(self._get_study_id_for_instance(instance_id), "")

            from io import BytesIO

            with open(file_path, 'rb') as f:
                dicom_data = f.read()

            dicom_dataset = pydicom.dcmread(BytesIO(dicom_data))

            # PRIORITATE 1: Tag-urile noastre private cu reconstrucție chunks
            if (0x7777, 0x0010) in dicom_dataset:
                identifier = str(dicom_dataset[0x7777, 0x0010].value)
                if identifier == "MEDICAL_APP_RESULT":
                    print(f"  📖 Found our private tags in local file")

                    # Verifică chunks multiple
                    if (0x7777, 0x0020) in dicom_dataset:
                        try:
                            num_chunks = int(str(dicom_dataset[0x7777, 0x0020].value))
                            print(f"  📖 Found {num_chunks} chunks in local file")

                            result_parts = []
                            for i in range(num_chunks):
                                tag_element = 0x1001 + i
                                if (0x7777, tag_element) in dicom_dataset:
                                    chunk = str(dicom_dataset[0x7777, tag_element].value)
                                    result_parts.append(chunk)

                            if result_parts:
                                complete_result = ''.join(result_parts)
                                print(
                                    f"  📖 Reconstructed complete result from local file: {len(complete_result)} chars")
                                return complete_result
                        except:
                            pass

                    # Fallback la tag simplu
                    if (0x7777, 0x1001) in dicom_dataset:
                        private_result = str(dicom_dataset[0x7777, 0x1001].value)
                        print(f"  📖 Found private tag result in local file: {len(private_result)} chars")
                        return private_result

            # PRIORITATE 2: Image Comments
            if hasattr(dicom_dataset, 'ImageComments'):
                image_comments = str(dicom_dataset.ImageComments)
                print(f"  📖 Found ImageComments in local file: {len(image_comments)} chars")
                return image_comments

            # PRIORITATE 3: Fallback la cache-ul nostru local
            study_id = self._get_study_id_for_instance(instance_id)
            if study_id and study_id in self.examination_results:
                cached_result = self.examination_results[study_id]
                print(f"  📖 Using cached result for local study: {len(cached_result)} chars")
                return cached_result

            return ""

        except ImportError:
            print("Warning: pydicom not available - using cached result")
            # Fallback la cache-ul local
            study_id = self._get_study_id_for_instance(instance_id)
            return self.examination_results.get(study_id, "")
        except Exception as e:
            print(f"Error reading examination result from local DICOM: {e}")
            # Fallback la cache-ul local
            study_id = self._get_study_id_for_instance(instance_id)
            return self.examination_results.get(study_id, "")

    def _get_study_id_for_instance(self, instance_id: str) -> str:
        """Helper method to find study_id for a given instance_id"""
        for study_id, instances in self.study_instances.items():
            for instance in instances:
                if instance.get("ID") == instance_id:
                    return study_id
        return ""

    def _extract_metadata_from_dataset(self, dataset) -> Dict[str, Any]:
        try:
            return {
                "Patient Name": str(getattr(dataset, 'PatientName', 'Unknown')).replace('^', ' '),
                "Patient Birth Date": self._format_date(getattr(dataset, 'PatientBirthDate', '')),
                "Patient Sex": str(getattr(dataset, 'PatientSex', 'Unknown')),
                "Study Date": self._format_date(getattr(dataset, 'StudyDate', '')),
                "Study Instance UID": str(getattr(dataset, 'StudyInstanceUID', 'Unknown')),
                "Description": str(getattr(dataset, 'StudyDescription', 'Local DICOM Study')),
                "Series Status": "LOCAL",
                "Source": "Local File"
            }
        except Exception as e:
            print(f"Warning: Error extracting metadata: {e}")
            return {
                "Patient Name": "Unknown",
                "Patient Birth Date": "Unknown",
                "Patient Sex": "Unknown",
                "Study Date": datetime.now().strftime("%Y-%m-%d"),
                "Study Instance UID": "Unknown",
                "Description": "Local DICOM Study",
                "Series Status": "LOCAL",
                "Source": "Local File"
            }

    def _format_date(self, date_str: str) -> str:
        if not date_str or len(date_str) < 8:
            return "Unknown"

        try:
            # DICOM date format: YYYYMMDD
            if len(date_str) >= 8:
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return f"{year}-{month}-{day}"
        except:
            pass

        return date_str

    def _is_dicom_file(self, file_path: str) -> bool:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.dcm', '.dicom']:
                return True

            with open(file_path, 'rb') as f:
                header = f.read(132)
                if len(header) >= 132 and header[128:132] == b'DICM':
                    return True

                f.seek(0)
                try:
                    pydicom.dcmread(f, stop_before_pixels=True)
                    return True
                except:
                    return False

        except Exception:
            return False

        return False

    def _save_cache(self):
        try:
            cache_file = os.path.join(self.cache_dir, "local_studies_cache.json")
            cache_data = {
                "local_studies": self.local_studies,
                "study_instances": self.study_instances,
                "instance_files": self.instance_files,
                "examination_results": self.examination_results,
                "last_updated": datetime.now().isoformat()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def _load_cache(self):
        try:
            cache_file = os.path.join(self.cache_dir, "local_studies_cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                self.local_studies = cache_data.get("local_studies", {})
                self.study_instances = cache_data.get("study_instances", {})
                self.instance_files = cache_data.get("instance_files", {})
                self.examination_results = cache_data.get("examination_results", {})

        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
            self.local_studies = {}
            self.study_instances = {}
            self.instance_files = {}
            self.examination_results = {}