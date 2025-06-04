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
from app.config.settings import Settings


class PacsController:
    def __init__(self, pacs_service: IPacsService, pdf_service: IPdfService):
        self._pacs_service = pacs_service
        self._pdf_service = pdf_service
        self._notification_service = NotificationService()
        self._settings = Settings()
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

    def add_study_to_queue(self, study_id: str, examination_result: str, parent_widget) -> bool:
        try:
            if not study_id:
                self._notification_service.show_warning(parent_widget, "Atenție", "Nu este selectat niciun studiu.")
                return False

            if not examination_result.strip():
                proceed = self._notification_service.ask_confirmation(
                    parent_widget,
                    "Confirmare",
                    "Rezultatul explorării este gol. Dorești să adaugi studiul în queue fără rezultat?"
                )
                if not proceed:
                    return False

            # Get study metadata
            metadata = self.get_study_metadata(study_id)
            patient_name = metadata.get("Patient Name", "Unknown")
            study_date = metadata.get("Study Date", "Unknown")
            description = metadata.get("Description", "Unknown")

            return True, {
                'study_id': study_id,
                'patient_name': patient_name,
                'study_date': study_date,
                'description': description,
                'examination_result': examination_result.strip()
            }

        except Exception as e:
            self._notification_service.show_error(parent_widget, "Eroare", f"Eroare la adăugarea în queue: {e}")
            return False, None

    def send_queued_studies_to_pacs(self, queued_studies: List, target_url: str, parent_widget) -> bool:
        try:
            if not queued_studies:
                self._notification_service.show_warning(parent_widget, "Atenție", "Nu sunt studii în queue.")
                return False

            # Confirm send operation
            study_count = len(queued_studies)
            studies_with_results = sum(1 for qs in queued_studies if qs.examination_result.strip())

            confirm_message = f"Trimiți {study_count} studii la PACS?\n\n"
            confirm_message += f"• {studies_with_results} studii cu rezultate explorări\n"
            confirm_message += f"• {study_count - studies_with_results} studii fără rezultate\n\n"
            confirm_message += f"Target PACS: {target_url}\n"
            confirm_message += "Toate rezultatele vor fi incluse în metadata DICOM."

            if not self._notification_service.ask_confirmation(parent_widget, "Confirmare trimitere", confirm_message):
                return False

            # Debug authentication
            target_auth = self._settings.PACS_AUTH_2 if target_url == self._settings.PACS_URL_2 else self._settings.PACS_AUTH
            print(f"Debug: Sending to {target_url} with auth {target_auth[0]}:***")

            # Send studies
            success_count = 0
            failed_studies = []

            for i, queued_study in enumerate(queued_studies):
                try:
                    # Update progress
                    print(f"Sending study {i + 1}/{study_count}: {queued_study.patient_name}")

                    success = self._send_study_to_target_pacs(
                        queued_study.study_id,
                        target_url,
                        target_auth,
                        queued_study.examination_result if queued_study.examination_result.strip() else None
                    )

                    if success:
                        success_count += 1
                        print(f"✓ Successfully sent: {queued_study.patient_name}")
                    else:
                        failed_studies.append(f"{queued_study.patient_name} ({queued_study.study_date})")
                        print(f"✗ Failed to send: {queued_study.patient_name}")

                except Exception as e:
                    failed_studies.append(f"{queued_study.patient_name} ({queued_study.study_date}) - {str(e)}")
                    print(f"✗ Error sending {queued_study.patient_name}: {e}")

            # Show results
            if success_count == study_count:
                self._notification_service.show_info(
                    parent_widget,
                    "Succes complet",
                    f"Toate {study_count} studiile au fost trimise cu succes la PACS.\n"
                    f"Rezultatele explorărilor au fost incluse în metadata DICOM."
                )
                return True
            elif success_count > 0:
                message = f"Trimise cu succes: {success_count}/{study_count} studii.\n\n"
                if failed_studies:
                    message += "Studii cu erori:\n" + "\n".join(failed_studies[:5])
                    if len(failed_studies) > 5:
                        message += f"\n... și încă {len(failed_studies) - 5} studii"

                self._notification_service.show_warning(parent_widget, "Succes parțial", message)
                return True
            else:
                message = "Niciun studiu nu a putut fi trimis la PACS.\n\n"
                if failed_studies:
                    message += "Erori:\n" + "\n".join(failed_studies[:3])

                self._notification_service.show_error(parent_widget, "Eșec complet", message)
                return False

        except Exception as e:
            self._notification_service.show_error(parent_widget, "Eroare", f"Eroare la trimiterea studiilor: {e}")
            return False

    def _send_study_to_target_pacs(self, study_id: str, target_url: str, target_auth: tuple,
                                   examination_result: str = None) -> bool:
        """
        Send entire study to target PACS with specific authentication and examination result.
        """
        try:
            print(f"Sending entire study {study_id} to {target_url}")
            print(f"Using authentication: {target_auth[0]}:***")
            print(f"Examination result length: {len(examination_result) if examination_result else 0} characters")

            # Use PACS service to send entire study
            success = self._pacs_service.send_study_to_pacs(
                study_id,
                target_url,
                target_auth,
                examination_result
            )

            if success:
                print(f"✓ Study {study_id} sent successfully")
            else:
                print(f"✗ Failed to send study {study_id}")

            return success

        except Exception as e:
            print(f"Error sending study {study_id}: {e}")
            return False

    def get_examination_result_from_study(self, study_id: str) -> str:
        try:
            instances = self.get_study_instances(study_id)

            for instance in instances:
                instance_id = instance.get("ID")
                if instance_id:
                    result = self._pacs_service.get_examination_result_from_dicom(instance_id)
                    if result:
                        return result

            return ""

        except Exception as e:
            print(f"Error getting examination result from study {study_id}: {e}")
            return ""

    def validate_study_for_queue(self, study_id: str, parent_widget) -> tuple[bool, Optional[Dict[str, Any]]]:
        try:
            if not study_id:
                return False, None

            metadata = self.get_study_metadata(study_id)

            # Check if study has instances
            instances = self.get_study_instances(study_id)
            if not instances:
                self._notification_service.show_warning(
                    parent_widget,
                    "Atenție",
                    "Studiul selectat nu conține fișiere DICOM."
                )
                return False, None

            return True, metadata

        except Exception as e:
            self._notification_service.show_error(
                parent_widget,
                "Eroare",
                f"Eroare la validarea studiului: {e}"
            )
            return False, None


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


class QueueSenderWorker(QObject):
    """Worker for sending queued studies in background"""
    progress_updated = pyqtSignal(int, str)  # progress, current_study
    sending_completed = pyqtSignal(bool, str)  # success, message

    def __init__(self, pacs_controller: PacsController, queued_studies: List, target_url: str):
        super().__init__()
        self._pacs_controller = pacs_controller
        self._queued_studies = queued_studies
        self._target_url = target_url

    def run(self):
        try:
            # Get target authentication
            settings = Settings()
            target_auth = settings.PACS_AUTH_2 if self._target_url == settings.PACS_URL_2 else settings.PACS_AUTH

            success_count = 0
            failed_studies = []
            total_studies = len(self._queued_studies)

            for i, queued_study in enumerate(self._queued_studies):
                # Emit progress
                progress = int((i / total_studies) * 100)
                self.progress_updated.emit(progress, f"{queued_study.patient_name}")

                try:
                    success = self._pacs_controller._send_study_to_target_pacs(
                        queued_study.study_id,
                        self._target_url,
                        target_auth,
                        queued_study.examination_result if queued_study.examination_result.strip() else None
                    )

                    if success:
                        success_count += 1
                    else:
                        failed_studies.append(queued_study.patient_name)

                except Exception as e:
                    failed_studies.append(f"{queued_study.patient_name} - {str(e)}")

            # Final progress
            self.progress_updated.emit(100, "Finalizat")

            # Emit completion
            if success_count == total_studies:
                self.sending_completed.emit(True, f"Toate {total_studies} studiile au fost trimise cu succes!")
            elif success_count > 0:
                message = f"Trimise: {success_count}/{total_studies} studii.\nEșecuri: {', '.join(failed_studies[:3])}"
                self.sending_completed.emit(True, message)
            else:
                message = f"Niciun studiu nu a putut fi trimis.\nErori: {', '.join(failed_studies[:3])}"
                self.sending_completed.emit(False, message)

        except Exception as e:
            self.sending_completed.emit(False, f"Eroare critică: {str(e)}")