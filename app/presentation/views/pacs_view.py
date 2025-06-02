import os
import subprocess
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import QThread
from app.presentation.controllers.pacs_controller import PacsController, StudiesWorker
from app.presentation.widgets.study_list_widget import StudyListWidget, QueueListWidget
from app.presentation.widgets.metadata_widget import MetadataWidget, ResultWidget
from app.services.notification_service import NotificationService
from app.presentation.styles.style_manager import load_style
from app.config.settings import Settings


class PacsView(QWidget):
    def __init__(self, pacs_controller: PacsController):
        super().__init__()
        self._pacs_controller = pacs_controller
        self._notification_service = NotificationService()
        self._settings = Settings()
        self.last_generated_pdf_path = None
        self.setWindowTitle("PACS Viewer")
        self.setGeometry(100, 100, 1600, 800)
        self._setup_ui()
        load_style(self)
        self._load_studies()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Studies list
        main_layout.addWidget(QLabel("Available Studies:"))
        self.study_list = StudyListWidget()
        self.study_list.study_selected.connect(self._on_study_selected)
        main_layout.addWidget(self.study_list)

        # Bottom section with metadata and queue
        bottom_layout = QHBoxLayout()

        # Left column - Metadata
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("Study Metadata:"))
        self.metadata_widget = MetadataWidget()
        left_col.addWidget(self.metadata_widget)

        # Right column - Queue
        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("Studies ready for upload:"))
        self.queue_list = QueueListWidget()
        right_col.addWidget(self.queue_list)

        bottom_layout.addLayout(left_col)
        bottom_layout.addLayout(right_col)
        main_layout.addLayout(bottom_layout)

        # Results section
        main_layout.addWidget(QLabel("Examination Results:"))
        self.result_widget = ResultWidget()
        main_layout.addWidget(self.result_widget)

        # PDF buttons
        pdf_button_row = QHBoxLayout()
        pdf_button_row.addStretch()

        self.preview_button = QPushButton("Preview PDF")
        self.preview_button.setObjectName("PreviewButton")
        self.preview_button.clicked.connect(self._preview_pdf)

        self.print_button = QPushButton("Print")
        self.print_button.setObjectName("PrintButton")
        self.print_button.clicked.connect(self._print_pdf)

        pdf_button_row.addWidget(self.preview_button)
        pdf_button_row.addWidget(self.print_button)
        main_layout.addLayout(pdf_button_row)

        # Main action buttons
        main_layout.addLayout(self._setup_action_buttons())

    def _setup_action_buttons(self):
        button_layout = QHBoxLayout()

        self.generate_pdf_button = QPushButton("Generate PDF")
        self.generate_pdf_button.setObjectName("GeneratePDFButton")
        self.generate_pdf_button.clicked.connect(self._export_pdf)

        self.send_button = QPushButton("Send to PACS")
        self.send_button.setObjectName("SendPACSButton")
        self.send_button.clicked.connect(self._send_to_pacs)

        self.queue_button = QPushButton("Load Study")
        self.queue_button.setObjectName("QueueButton")
        self.queue_button.clicked.connect(self._queue_studies)

        button_layout.addWidget(self.generate_pdf_button)
        button_layout.addWidget(self.queue_button)
        button_layout.addWidget(self.send_button)

        return button_layout

    def _load_studies(self):
        """Load studies from PACS in background thread"""
        self.study_list.set_loading(True)

        self.study_thread = QThread()
        self.worker = StudiesWorker(self._pacs_controller)
        self.worker.moveToThread(self.study_thread)

        self.study_thread.started.connect(self.worker.run)
        self.worker.studies_loaded.connect(self._on_studies_loaded)
        self.worker.error_occurred.connect(self._on_studies_error)

        self.worker.studies_loaded.connect(self.study_thread.quit)
        self.worker.studies_loaded.connect(self.worker.deleteLater)
        self.worker.error_occurred.connect(self.study_thread.quit)
        self.worker.error_occurred.connect(self.worker.deleteLater)
        self.study_thread.finished.connect(self.study_thread.deleteLater)

        self.study_thread.start()

    def _on_studies_loaded(self, study_ids):
        """Handle successful studies loading"""
        self.study_list.set_loading(False)

        for study_id in study_ids:
            try:
                metadata = self._pacs_controller.get_study_metadata(study_id)
                display_text = f"{metadata['Patient Name']} - {metadata['Study Date']} - {metadata['Description']}"
                self.study_list.add_study(study_id, display_text)
            except Exception as e:
                self._notification_service.show_error(self, "Error", f"Error loading metadata: {e}")

    def _on_studies_error(self, error_message):
        """Handle studies loading error"""
        self.study_list.set_loading(False)
        self._notification_service.show_error(self, "Error", f"Error loading studies:\n{error_message}")

    def _on_study_selected(self, study_id: str):
        """Handle study selection"""
        try:
            metadata = self._pacs_controller.get_study_metadata(study_id)
            self.metadata_widget.display_metadata(metadata)
        except Exception as e:
            self._notification_service.show_error(self, "Error", f"Error loading metadata:\n{e}")

    def _export_pdf(self):
        """Export study results to PDF"""
        study_id = self.study_list.get_selected_study_id()
        if not study_id:
            self._notification_service.show_warning(self, "Warning", "Please select a study.")
            return

        result_text = self.result_widget.get_result_text()
        if not result_text:
            self._notification_service.show_warning(self, "Warning", "Please enter examination results.")
            return

        success = self._pacs_controller.export_pdf(study_id, result_text, self)
        if success:
            self.last_generated_pdf_path = self._pacs_controller._last_generated_pdf_path

    def _preview_pdf(self):
        """Preview PDF before saving"""
        study_id = self.study_list.get_selected_study_id()
        if not study_id:
            self._notification_service.show_warning(self, "Warning", "Please select a study.")
            return

        result_text = self.result_widget.get_result_text()
        self._pacs_controller.preview_pdf(study_id, result_text, self)

    def _print_pdf(self):
        """Print the last generated PDF"""
        if not self.last_generated_pdf_path or not os.path.exists(self.last_generated_pdf_path):
            self._notification_service.show_warning(self, "Warning", "No PDF to print. Generate a PDF first.")
            return

        try:
            if sys.platform.startswith("linux"):
                subprocess.run(["lp", self.last_generated_pdf_path])
            elif sys.platform == "win32":
                os.startfile(self.last_generated_pdf_path, "print")
            else:
                self._notification_service.show_info(self, "Info", "Printing not supported on this platform")
        except Exception as e:
            self._notification_service.show_error(self, "Error", f"Error printing PDF: {e}")

    def _queue_studies(self):
        """Add study instances to upload queue"""
        study_id = self.study_list.get_selected_study_id()
        if not study_id:
            self._notification_service.show_warning(self, "Warning", "Please select a study.")
            return

        try:
            instances = self._pacs_controller.get_study_instances(study_id)
            instance_ids = [instance["ID"] for instance in instances]

            if not instance_ids:
                self._notification_service.show_warning(self, "Warning", "No DICOM files in study.")
                return

            metadata = self._pacs_controller.get_study_metadata(study_id)
            display_text = f"{metadata['Patient Name']} - {metadata['Study Date']} - {metadata['Description']}"

            added_count = 0
            for idx, instance_id in enumerate(instance_ids):
                try:
                    # Verify instance can be retrieved
                    self._pacs_controller._pacs_service.get_dicom_file(instance_id)

                    item_text = f"{display_text} (Instance #{idx + 1})"
                    self.queue_list.add_instance(instance_id, item_text)
                    added_count += 1

                except Exception as e:
                    self._notification_service.show_warning(self, "Warning", f"Error with instance {instance_id}: {e}")

            self._notification_service.show_info(self, "Info", f"{added_count} files added to queue.")

        except Exception as e:
            self._notification_service.show_error(self, "Error", f"Error adding files to queue: {e}")

    def _send_to_pacs(self):
        """Send queued studies to target PACS"""
        instance_ids = self.queue_list.get_all_instance_ids()

        success = self._pacs_controller.send_to_pacs(
            instance_ids,
            self._settings.PACS_URL_2,
            self
        )

        if success:
            self.queue_list.clear_queue()