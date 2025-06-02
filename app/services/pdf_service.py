import os
from typing import Dict, Any
from datetime import datetime
from app.core.interfaces.pdf_interface import IPdfService
from app.infrastructure.pdf_generator import PdfGenerator
from app.core.exceptions.pdf_exceptions import PdfGenerationError


class PdfService(IPdfService):
    def __init__(self, pdf_generator: PdfGenerator, output_dir: str = "generated_pdfs"):
        self._pdf_generator = pdf_generator
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_pdf(self, content: str, metadata: Dict[str, Any], output_path: str) -> str:
        try:
            full_path = os.path.join(self._output_dir, output_path)
            self._pdf_generator.create_pdf(content, metadata, full_path)
            return full_path
        except Exception as e:
            raise PdfGenerationError(f"Nu am putut genera fisierul PDF: {e}")

    def preview_pdf(self, content: str, metadata: Dict[str, Any]) -> str:
        try:
            preview_dir = os.path.join("tmp_pdfs", "preview")
            os.makedirs(preview_dir, exist_ok=True)

            filename = f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            preview_path = os.path.join(preview_dir, filename)

            self._pdf_generator.create_pdf(content, metadata, preview_path)
            return preview_path
        except Exception as e:
            raise PdfGenerationError(f"Nu am putut genera fisierul PDF pentru previzualizare: {e}")