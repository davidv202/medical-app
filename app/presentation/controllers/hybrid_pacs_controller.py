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


class HybridPacsController:
    """
    Enhanced PACS controller that handles both remote PACS and local DICOM files
    """

    def __init__(self, hybrid_pacs_service: IPacsService, pdf_service: IPdfService):
        self._pacs_service = hybrid_pacs_service  # This should be HybridPacsService
        self._pdf_service = pdf_service
        self._notification_service = NotificationService()
        self._settings = Settings()
        self._last_generated_pdf_path: Optional[str] = None

    def load_studies(self) -> List[str]:
        """Load studies from both PACS and local files"""
        try:
            return self._pacs_service.get_all_studies()
        except PacsConnectionError as e:
            raise e

    def get_study_metadata(self, study_id: str) -> Dict[str, Any]:
        """Get study metadata from appropriate source"""
        try:
            return self._pacs_service.get_study_metadata(study_id)
        except PacsDataError as e:
            raise e

    def get_study_instances(self, study_id: str) -> List[Dict[str, Any]]:
        """Get study instances from appropriate source"""
        try:
            return self._pacs_service.get_study_instances(study_id)
        except PacsDataError as e:
            raise e

    def export_pdf(self, study_id: str, result_text: str, parent_widget, current_user) -> bool:
        """Export PDF with examination results"""
        try:
            metadata = self.get_study_metadata(study_id)

            patient = re.sub(r'\W+', '_', metadata["Patient Name"])
            study_date = metadata["Study Date"].replace("-", "")
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{patient}_{study_date}_{timestamp}.pdf"

            doctor_name = current_user.get_full_name() if current_user else None

            pdf_path = self._pdf_service.generate_pdf(result_text, metadata, filename, doctor_name)
            self._last_generated_pdf_path = pdf_path

            # Save examination result to study
            self._save_examination_result_to_study(study_id, result_text)

            self._notification_service.show_info(parent_widget, "Succes", f"Fisier PDF salvat: {filename}")
            return True

        except (PacsDataError, PdfGenerationError) as e:
            self._notification_service.show_error(parent_widget, "Eroare", str(e))
            return False

    def preview_pdf(self, study_id: str, result_text: str, parent_widget, current_user) -> bool:
        """Preview PDF with examination results"""
        try:
            if not result_text.strip():
                self._notification_service.show_warning(parent_widget, "Atentie", "Completeaza rezultatul explorarii.")
                return False

            metadata = self.get_study_metadata(study_id)
            doctor_name = current_user.get_full_name() if current_user else None
            preview_path = self._pdf_service.preview_pdf(result_text, metadata, doctor_name)

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
        """Add study to queue with enhanced local file support"""
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

            # Save examination result to study
            self._save_examination_result_to_study(study_id, examination_result)

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
        """Send queued studies to PACS with enhanced local file support"""
        try:
            if not queued_studies:
                self._notification_service.show_warning(parent_widget, "Atenție", "Nu sunt studii în queue.")
                return False

            # Confirm send operation
            study_count = len(queued_studies)
            studies_with_results = sum(1 for qs in queued_studies if qs.examination_result.strip())
            local_studies_count = sum(1 for qs in queued_studies if self._is_local_study(qs.study_id))
            pacs_studies_count = study_count - local_studies_count

            confirm_message = f"Trimiți {study_count} studii la PACS?\n\n"
            confirm_message += f"• {studies_with_results} studii cu rezultate explorări\n"
            confirm_message += f"• {study_count - studies_with_results} studii fără rezultate\n"
            if local_studies_count > 0:
                confirm_message += f"• {local_studies_count} studii locale (din computer)\n"
            if pacs_studies_count > 0:
                confirm_message += f"• {pacs_studies_count} studii PACS (remote)\n"
            confirm_message += f"\nTarget PACS: {target_url}\n"
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
                    study_type = "LOCAL" if self._is_local_study(queued_study.study_id) else "PACS"
                    print(f"Sending {study_type} study {i + 1}/{study_count}: {queued_study.patient_name}")

                    success = self._send_study_to_target_pacs(
                        queued_study.study_id,
                        target_url,
                        target_auth,
                        queued_study.examination_result if queued_study.examination_result.strip() else None
                    )

                    if success:
                        success_count += 1
                        print(f"✓ Successfully sent {study_type} study: {queued_study.patient_name}")
                    else:
                        failed_studies.append(f"{queued_study.patient_name} ({queued_study.study_date}) [{study_type}]")
                        print(f"✗ Failed to send {study_type} study: {queued_study.patient_name}")

                except Exception as e:
                    study_type = "LOCAL" if self._is_local_study(queued_study.study_id) else "PACS"
                    failed_studies.append(
                        f"{queued_study.patient_name} ({queued_study.study_date}) [{study_type}] - {str(e)}")
                    print(f"✗ Error sending {study_type} study {queued_study.patient_name}: {e}")

            # Show results
            if success_count == study_count:
                message = f"Toate {study_count} studiile au fost trimise cu succes la PACS.\n"
                message += f"Rezultatele explorărilor au fost incluse în metadata DICOM."
                if local_studies_count > 0:
                    message += f"\n\n✨ {local_studies_count} studii locale au fost încărcate cu succes în PACS!"

                self._notification_service.show_info(parent_widget, "Succes complet", message)
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
        """Send study to target PACS with enhanced local file support"""
        try:
            study_type = "LOCAL" if self._is_local_study(study_id) else "PACS"
            print(f"Sending {study_type} study {study_id} to {target_url}")
            print(f"Using authentication: {target_auth[0]}:***")
            print(f"Examination result length: {len(examination_result) if examination_result else 0} characters")

            # Use hybrid PACS service to send study (handles both local and PACS)
            success = self._pacs_service.send_study_to_pacs(
                study_id,
                target_url,
                target_auth,
                examination_result
            )

            if success:
                print(f"✓ {study_type} study {study_id} sent successfully")
            else:
                print(f"✗ Failed to send {study_type} study {study_id}")

            return success

        except Exception as e:
            print(f"Error sending study {study_id}: {e}")
            return False

    def get_examination_result_from_study(self, study_id: str) -> str:
        """Get examination result from study (works for both local and PACS)"""
        try:
            # Use the hybrid service method that handles both local and PACS studies
            if hasattr(self._pacs_service, 'get_examination_result_from_study'):
                return self._pacs_service.get_examination_result_from_study(study_id)

            # Fallback to instance-based method
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
        """Validate study for queue (enhanced for local files)"""
        try:
            if not study_id:
                return False, None

            metadata = self.get_study_metadata(study_id)

            # Check if study has instances
            instances = self.get_study_instances(study_id)
            if not instances:
                study_type = "local" if self._is_local_study(study_id) else "PACS"
                self._notification_service.show_warning(
                    parent_widget,
                    "Atenție",
                    f"Studiul {study_type} selectat nu conține fișiere DICOM."
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

    # Local file management methods
    def load_local_dicom_file(self, file_path: str, parent_widget) -> bool:
        """Load a local DICOM file"""
        try:
            if hasattr(self._pacs_service, 'load_local_dicom_file'):
                result = self._pacs_service.load_local_dicom_file(file_path)
                study_id = result.get("study_id")
                metadata = result.get("metadata", {})
                patient_name = metadata.get("Patient Name", "Unknown")

                self._notification_service.show_info(
                    parent_widget,
                    "File Loaded",
                    f"Local DICOM file loaded successfully:\n{patient_name}"
                )
                return True
            else:
                self._notification_service.show_error(
                    parent_widget,
                    "Error",
                    "Local file support not available in current PACS service"
                )
                return False

        except Exception as e:
            self._notification_service.show_error(
                parent_widget,
                "Error",
                f"Error loading local DICOM file: {e}"
            )
            return False

    def load_local_dicom_folder(self, folder_path: str, parent_widget) -> bool:
        """Load DICOM files from folder"""
        try:
            if hasattr(self._pacs_service, 'load_local_dicom_folder'):
                studies = self._pacs_service.load_local_dicom_folder(folder_path)
                study_count = len(studies)
                total_files = sum(study.get("file_count", 0) for study in studies)

                self._notification_service.show_info(
                    parent_widget,
                    "Folder Loaded",
                    f"Loaded {study_count} studies ({total_files} files) from folder"
                )
                return True
            else:
                self._notification_service.show_error(
                    parent_widget,
                    "Error",
                    "Local folder support not available in current PACS service"
                )
                return False

        except Exception as e:
            self._notification_service.show_error(
                parent_widget,
                "Error",
                f"Error loading DICOM folder: {e}"
            )
            return False

    def clear_local_studies(self, parent_widget) -> bool:
        """Clear all local studies"""
        try:
            if hasattr(self._pacs_service, 'get_local_studies_count'):
                count = self._pacs_service.get_local_studies_count()
                if count == 0:
                    self._notification_service.show_info(
                        parent_widget,
                        "Info",
                        "No local studies to clear."
                    )
                    return True

                if self._notification_service.ask_confirmation(
                        parent_widget,
                        "Clear Local Studies",
                        f"Are you sure you want to clear all {count} local studies?\n\n"
                        "This will only remove them from memory, not delete the original files."
                ):
                    self._pacs_service.clear_local_studies()
                    self._notification_service.show_info(
                        parent_widget,
                        "Cleared",
                        "All local studies have been cleared."
                    )
                    return True
            return False

        except Exception as e:
            self._notification_service.show_error(
                parent_widget,
                "Error",
                f"Error clearing local studies: {e}"
            )
            return False

    def get_local_studies_count(self) -> int:
        """Get count of loaded local studies"""
        try:
            if hasattr(self._pacs_service, 'get_local_studies_count'):
                return self._pacs_service.get_local_studies_count()
            return 0
        except:
            return 0

    def _is_local_study(self, study_id: str) -> bool:
        """Check if study ID belongs to a local study"""
        return study_id.startswith("local_")

    def _save_examination_result_to_study(self, study_id: str, examination_result: str):
        """Save examination result to study"""
        try:
            if hasattr(self._pacs_service, 'add_examination_result_to_study'):
                self._pacs_service.add_examination_result_to_study(study_id, examination_result)
        except Exception as e:
            print(f"Warning: Could not save examination result to study {study_id}: {e}")


class StudiesWorker(QObject):
    """Enhanced worker for loading studies from both PACS and local files"""
    studies_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, pacs_controller):
        super().__init__()
        self._pacs_controller = pacs_controller

    def run(self):
        try:
            studies = self._pacs_controller.load_studies()
            self.studies_loaded.emit(studies)
        except Exception as e:
            self.error_occurred.emit(str(e))


class QueueSenderWorker(QObject):
    """Enhanced worker for sending queued studies (local and PACS) in background"""
    progress_updated = pyqtSignal(int, str)  # progress, current_study
    sending_completed = pyqtSignal(bool, str)  # success, message

    def __init__(self, pacs_controller, queued_studies: List, target_url: str):
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
            local_studies_sent = 0
            pacs_studies_sent = 0

            for i, queued_study in enumerate(self._queued_studies):
                # Emit progress
                progress = int((i / total_studies) * 100)
                study_type = "LOCAL" if self._pacs_controller._is_local_study(queued_study.study_id) else "PACS"
                self.progress_updated.emit(progress, f"[{study_type}] {queued_study.patient_name}")

                try:
                    success = self._pacs_controller._send_study_to_target_pacs(
                        queued_study.study_id,
                        self._target_url,
                        target_auth,
                        queued_study.examination_result if queued_study.examination_result.strip() else None
                    )

                    if success:
                        success_count += 1
                        if self._pacs_controller._is_local_study(queued_study.study_id):
                            local_studies_sent += 1
                        else:
                            pacs_studies_sent += 1
                    else:
                        failed_studies.append(f"{queued_study.patient_name} [{study_type}]")

                except Exception as e:
                    failed_studies.append(f"{queued_study.patient_name} [{study_type}] - {str(e)}")

            # Final progress
            self.progress_updated.emit(100, "Finalizat")

            # Build completion message
            if success_count == total_studies:
                message = f"Toate {total_studies} studiile au fost trimise cu succes!"
                if local_studies_sent > 0:
                    message += f"\n✨ {local_studies_sent} studii locale încărcate în PACS"
                if pacs_studies_sent > 0:
                    message += f"\n📡 {pacs_studies_sent} studii PACS transferate"
                self.sending_completed.emit(True, message)
            elif success_count > 0:
                message = f"Trimise: {success_count}/{total_studies} studii."
                if local_studies_sent > 0:
                    message += f"\n✨ {local_studies_sent} studii locale încărcate"
                if pacs_studies_sent > 0:
                    message += f"\n📡 {pacs_studies_sent} studii PACS transferate"
                message += f"\nEșecuri: {', '.join(failed_studies[:3])}"
                self.sending_completed.emit(True, message)
            else:
                message = f"Niciun studiu nu a putut fi trimis.\nErori: {', '.join(failed_studies[:3])}"
                self.sending_completed.emit(False, message)

        except Exception as e:
            self.sending_completed.emit(False, f"Eroare critică: {str(e)}")