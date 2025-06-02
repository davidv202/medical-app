import re
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtCore import pyqtSignal, QObject

from app.core.interfaces.pacs_interface import IPacsService
from app.core.interfaces.pdf_interface import IPdfService
from app.services.notification_service import NotificationService
from app.core.exceptions.pacs_exceptions import PacsConnectionError, PacsDataError
from app.core.exceptions.pdf_exceptions import PdfGenerationError


class PacsController:
    def __init__(self, pacs_service: IPacsService, pdf_service: IPdfService):
        self._pacs_service = pacs_service
        self._pdf_service = pdf_service
        self._notification_service = NotificationService()
        self._last_generated_pdf_path: Optional[str] = None

    def load_studies(self) -> List[str]:
        try:
            return self._pacs_service.get_all_studies()
        except PacsConnectionError as e:
            raise e

    def get_study_metadata(self, study_id: str) -> Dict[str, Any]:
        try:
            return self._pacs_service.get_study_metadata(study_id)
        except PacsDataError as e:
            raise e

    def get_study_instances(self, study_id: str) -> List[Dict[str, Any]]:
        try:
            return self._pacs_service.get_study_instances(study_id)
        except PacsDataError as e:
            raise e

    def export_pdf(self, study_id: str, result_text: str, parent_widget) -> bool:
        try:
            metadata = self.get_study_metadata(study_id)

            patient = re.sub(r'\W+', '_', metadata["Patient Name"])
            study_date = metadata["Study Date"].replace("-", "")
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{patient}_{study_date}_{timestamp}.pdf"

            pdf_path = self._pdf_service.generate_pdf(result_text, metadata, filename)
            self._last_generated_pdf_path = pdf_path

            self._notification_service.show_info(parent_widget, "Succes", f"Fisier PDF salvat: {filename}")
            return True

        except (PacsDataError, PdfGenerationError) as e:
            self._notification_service.show_error(parent_widget, "Eroare", str(e))
            return False

    def preview_pdf(self, study_id: str, result_text: str, parent_widget) -> bool:
        try:
            if not result_text.strip():
                self._notification_service.show_warning(parent_widget, "Atentie", "Completeaza rezultatul explorarii.")
                return False

            metadata = self.get_study_metadata(study_id)
            preview_path = self._pdf_service.preview_pdf(result_text, metadata)

            import sys
            import subprocess
            if sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", preview_path])
            elif sys.platform == "win32":
                os.startfile(preview_path)

            return True

        except (PacsDataError, PdfGenerationError) as e:
            self._notification_service.show_error(parent_widget, "Eroare", str(e))
            return False

    def send_to_pacs(self, instance_ids: List[str], target_url: str, parent_widget) -> bool:
        try:
            if not instance_ids:
                self._notification_service.show_warning(parent_widget, "Atentie", "Nu sunt studii in coada.")
                return False

            success_count = 0
            for instance_id in instance_ids:
                try:
                    dicom_data = self._pacs_service.get_dicom_file(instance_id)
                    if self._pacs_service.send_to_pacs(dicom_data, target_url):
                        success_count += 1
                except Exception as e:
                    self._notification_service.show_warning(
                        parent_widget, "Atentie", f"Eroare la isntanta {instance_id}: {e}"
                    )

            self._notification_service.show_info(
                parent_widget, "Info", f"Fisiere trimise: {success_count}/{len(instance_ids)}."
            )
            return success_count > 0

        except Exception as e:
            self._notification_service.show_error(parent_widget, "Eroare", f"Eroare la trimiterea fisierelor: {e}")
            return False


class StudiesWorker(QObject):
    studies_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, pacs_controller: PacsController):
        super().__init__()
        self._pacs_controller = pacs_controller

    def run(self):
        try:
            studies = self._pacs_controller.load_studies()
            self.studies_loaded.emit(studies)
        except Exception as e:
            self.error_occurred.emit(str(e))