from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ILocalFileService(ABC):

    @abstractmethod
    def load_dicom_file(self, file_path: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def load_dicom_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_study_metadata_from_file(self, file_path: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_local_study_instances(self, study_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_local_dicom_file(self, instance_id: str) -> bytes:
        pass

    @abstractmethod
    def add_examination_result_to_local_study(self, study_id: str, examination_result: str) -> bool:
        pass

    @abstractmethod
    def get_examination_result_from_local_study(self, study_id: str) -> str:
        pass