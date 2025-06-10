from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ILocalFileService(ABC):
    """Interface for handling local DICOM files"""

    @abstractmethod
    def load_dicom_file(self, file_path: str) -> Dict[str, Any]:
        """Load a single DICOM file and extract metadata"""
        pass

    @abstractmethod
    def load_dicom_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        """Load all DICOM files from a folder and group by study"""
        pass

    @abstractmethod
    def get_study_metadata_from_file(self, file_path: str) -> Dict[str, Any]:
        """Extract study metadata from a DICOM file"""
        pass

    @abstractmethod
    def get_local_study_instances(self, study_id: str) -> List[Dict[str, Any]]:
        """Get instances for a local study"""
        pass

    @abstractmethod
    def get_local_dicom_file(self, instance_id: str) -> bytes:
        """Get DICOM file content from local instance"""
        pass

    @abstractmethod
    def add_examination_result_to_local_study(self, study_id: str, examination_result: str) -> bool:
        """Add examination result to local study metadata"""
        pass

    @abstractmethod
    def get_examination_result_from_local_study(self, study_id: str) -> str:
        """Get examination result from local study"""
        pass