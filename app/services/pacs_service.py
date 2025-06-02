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