from abc import ABC, abstractmethod
from typing import Dict, Any


class IPdfService(ABC):
    @abstractmethod
    def generate_pdf(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        pass

    @abstractmethod
    def preview_pdf(self, content: str, metadata: Dict[str, Any]) -> str:
        pass