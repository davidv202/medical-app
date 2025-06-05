from abc import ABC, abstractmethod
from typing import Dict, Any


class IPdfService(ABC):
    @abstractmethod
    def generate_pdf(self, content: str, metadata: Dict[str, Any], output_path: str, doctor_name: str = None) -> str:
        """Generează un PDF cu conținutul și metadatele date"""
        pass

    @abstractmethod
    def preview_pdf(self, content: str, metadata: Dict[str, Any], doctor_name: str = None) -> str:
        """Generează un PDF pentru previzualizare"""
        pass

    def generate_preview_html(self, content: str, metadata: Dict[str, Any], doctor_name: str = None) -> str:
        """Generează HTML pentru previzualizare în browser (opțional)"""
        pass