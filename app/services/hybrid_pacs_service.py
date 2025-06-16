from typing import List, Dict, Any, Optional
from app.core.interfaces.pacs_interface import IPacsService
from app.services.local_file_service import LocalFileService
from app.services.pacs_service import PacsService
from app.core.exceptions.pacs_exceptions import PacsDataError


class HybridPacsService(IPacsService):
    def __init__(self, pacs_service: PacsService, local_file_service: LocalFileService):
        self._pacs_service = pacs_service
        self._local_file_service = local_file_service

    def get_all_studies(self) -> List[str]:
        studies = []

        # Get PACS studies
        try:
            pacs_studies = self._pacs_service.get_all_studies()
            studies.extend(pacs_studies)
        except Exception as e:
            print(f"Warning: Could not load PACS studies: {e}")

        # Get local studies
        try:
            local_studies = self._local_file_service.get_all_local_studies()
            studies.extend(local_studies)
        except Exception as e:
            print(f"Warning: Could not load local studies: {e}")

        return studies

    def get_study_metadata(self, study_id: str) -> Dict[str, Any]:
        if self._is_local_study(study_id):
            return self._local_file_service.get_local_study_metadata(study_id)
        else:
            return self._pacs_service.get_study_metadata(study_id)

    def get_study_instances(self, study_id: str) -> List[Dict[str, Any]]:
        if self._is_local_study(study_id):
            return self._local_file_service.get_local_study_instances(study_id)
        else:
            return self._pacs_service.get_study_instances(study_id)

    def get_dicom_file(self, instance_id: str) -> bytes:
        if self._is_local_instance(instance_id):
            return self._local_file_service.get_local_dicom_file(instance_id)
        else:
            return self._pacs_service.get_dicom_file(instance_id)

    def send_study_to_pacs(self, study_id: str, target_url: str, target_auth: tuple,
                           examination_result: str = None) -> bool:
        if self._is_local_study(study_id):
            return self._send_local_study_to_pacs(study_id, target_url, target_auth, examination_result)
        else:
            return self._pacs_service.send_study_to_pacs(study_id, target_url, target_auth, examination_result)

    def get_examination_result_from_dicom(self, instance_id: str) -> str:
        if self._is_local_instance(instance_id):
            # For local instances, we need to get the study ID first
            study_id = self._get_study_id_for_local_instance(instance_id)
            if study_id:
                return self._local_file_service.get_examination_result_from_local_study(study_id)
            return ""
        else:
            return self._pacs_service.get_examination_result_from_dicom(instance_id)

    # Local file management methods
    def load_local_dicom_file(self, file_path: str) -> Dict[str, Any]:
        return self._local_file_service.load_dicom_file(file_path)

    def load_local_dicom_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        return self._local_file_service.load_dicom_folder(folder_path)

    def clear_local_studies(self):
        self._local_file_service.clear_local_studies()

    def remove_local_study(self, study_id: str) -> bool:
        if self._is_local_study(study_id):
            return self._local_file_service.remove_local_study(study_id)
        return False

    def get_local_studies_count(self) -> int:
        return len(self._local_file_service.get_all_local_studies())

    # Helper methods
    def _is_local_study(self, study_id: str) -> bool:
        return study_id.startswith("local_")

    def _is_local_instance(self, instance_id: str) -> bool:
        return instance_id.startswith("local_")

    def _get_study_id_for_local_instance(self, instance_id: str) -> Optional[str]:
        for study_id in self._local_file_service.get_all_local_studies():
            instances = self._local_file_service.get_local_study_instances(study_id)
            for instance in instances:
                if instance.get("ID") == instance_id:
                    return study_id
        return None

    def _send_local_study_to_pacs(self, study_id: str, target_url: str, target_auth: tuple,
                                  examination_result: str = None) -> bool:
        try:
            instances = self._local_file_service.get_local_study_instances(study_id)

            if not instances:
                raise PacsDataError(f"No instances found in local study {study_id}")

            success_count = 0
            total_instances = len(instances)

            print(f"📤 Sending local study {study_id} with {total_instances} instances...")

            for instance in instances:
                instance_id = instance.get("ID")
                if not instance_id:
                    continue

                try:
                    print(f"🔄 Processing local instance {instance_id}...")

                    # Get local DICOM file content
                    dicom_data = self._local_file_service.get_local_dicom_file(instance_id)
                    print(f"  📥 Retrieved local DICOM data: {len(dicom_data)} bytes")

                    # Add examination result if provided
                    if examination_result:
                        print(f"  📝 Adding examination result: {len(examination_result)} chars")
                        # Use the same method as PACS service to add examination result
                        modified_dicom_data = self._pacs_service._add_examination_result_to_dicom(
                            dicom_data, examination_result
                        )
                        print(f"  📝 Modified DICOM data: {len(modified_dicom_data)} bytes")
                    else:
                        modified_dicom_data = dicom_data
                        print(f"  📝 No examination result, using original data")

                    # Send to target PACS using the existing HTTP client
                    print(f"  📤 Sending to {target_url}/instances...")
                    response = self._pacs_service._http_client.post(
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
                        print(f"  ✓ Local instance {instance_id} sent successfully")
                    else:
                        print(f"  ✗ Failed to send local instance {instance_id}")
                        print(f"    Status: {response.status_code}")
                        print(
                            f"    Response: {response.text[:500] if hasattr(response, 'text') else 'No response text'}")

                except Exception as e:
                    print(f"  ✗ Error sending local instance {instance_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"📊 Final result: {success_count}/{total_instances} local instances sent")
            return success_count == total_instances

        except Exception as e:
            print(f"❌ Error sending local study: {e}")
            import traceback
            traceback.print_exc()
            return False