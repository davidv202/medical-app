import os
import subprocess
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from app.presentation.controllers.pacs_controller import PacsController, StudiesWorker
from app.presentation.widgets.study_list_widget import SearchableStudyListWidget, QueueListWidget
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
        self._setup_shortcuts()
        load_style(self)
        self._load_studies()

    def _setup_ui(self):
        # Main layout with better spacing
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Compact header
        header_layout = QHBoxLayout()
        studies_label = QLabel("📋 Available Studies")
        studies_label.setObjectName("SectionTitle")

        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.setMaximumWidth(100)
        self.refresh_button.setMaximumHeight(30)
        self.refresh_button.clicked.connect(self._load_studies)

        header_layout.addWidget(studies_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        main_layout.addLayout(header_layout)

        # Study list
        self.study_list = SearchableStudyListWidget()
        self.study_list.study_selected.connect(self._on_study_selected)
        self.study_list.setMaximumHeight(250)
        main_layout.addWidget(self.study_list)

        # Horizontal layout for metadata and queue
        middle_layout = QHBoxLayout()

        # Left: Metadata (compact)
        left_col = QVBoxLayout()
        metadata_label = QLabel("📊 Metadata")
        metadata_label.setObjectName("SectionTitle")
        left_col.addWidget(metadata_label)

        self.metadata_widget = MetadataWidget()
        self.metadata_widget.setMaximumHeight(150)  # Limit height
        left_col.addWidget(self.metadata_widget)

        # Right: Queue (compact)
        right_col = QVBoxLayout()
        queue_label = QLabel("📤 Queue")
        queue_label.setObjectName("SectionTitle")
        right_col.addWidget(queue_label)

        self.queue_list = QueueListWidget()
        self.queue_list.setMaximumHeight(120)  # Limit height
        right_col.addWidget(self.queue_list)

        middle_layout.addLayout(left_col)
        middle_layout.addLayout(right_col)
        main_layout.addLayout(middle_layout)

        # Results section (compact)
        results_label = QLabel("📝 Results")
        results_label.setObjectName("SectionTitle")
        main_layout.addWidget(results_label)

        self.result_widget = ResultWidget()
        self.result_widget.setMaximumHeight(100)  # Limit height
        main_layout.addWidget(self.result_widget)

        # Compact button layout - single row
        button_layout = QHBoxLayout()

        self.preview_button = QPushButton("👁️ Preview")
        self.preview_button.setObjectName("PreviewButton")
        self.preview_button.setMaximumHeight(35)
        self.preview_button.clicked.connect(self._preview_pdf)

        self.generate_pdf_button = QPushButton("💾 Generate PDF")
        self.generate_pdf_button.setObjectName("GeneratePDFButton")
        self.generate_pdf_button.setMaximumHeight(35)
        self.generate_pdf_button.clicked.connect(self._export_pdf)

        self.print_button = QPushButton("🖨️ Print")
        self.print_button.setObjectName("PrintButton")
        self.print_button.setMaximumHeight(35)
        self.print_button.clicked.connect(self._print_pdf)

        self.queue_button = QPushButton("➕ Load Study")
        self.queue_button.setObjectName("QueueButton")
        self.queue_button.setMaximumHeight(35)
        self.queue_button.clicked.connect(self._queue_studies)

        self.send_button = QPushButton("🚀 Send to PACS")
        self.send_button.setObjectName("SendPACSButton")
        self.send_button.setMaximumHeight(35)
        self.send_button.clicked.connect(self._send_to_pacs)

        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.generate_pdf_button)
        button_layout.addWidget(self.print_button)
        button_layout.addWidget(self.queue_button)
        button_layout.addWidget(self.send_button)

        main_layout.addLayout(button_layout)

        # Shortcuts info (compact)
        shortcuts_label = QLabel("💡 Ctrl+F (Search) • F5 (Refresh) • Esc (Clear)")
        shortcuts_label.setStyleSheet("color: #6b7280; font-size: 10px; font-style: italic;")
        shortcuts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcuts_label.setMaximumHeight(20)
        main_layout.addWidget(shortcuts_label)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for improved usability"""
        # Ctrl+F to focus search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.study_list.focus_search)

        # Escape to clear search
        clear_shortcut = QShortcut(QKeySequence("Escape"), self)
        clear_shortcut.activated.connect(self._clear_search_if_focused)

        # F5 to refresh
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._load_studies)

        # Ctrl+G to generate PDF quickly
        generate_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        generate_shortcut.activated.connect(self._export_pdf)

        # Ctrl+P to preview
        preview_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        preview_shortcut.activated.connect(self._preview_pdf)

    def _clear_search_if_focused(self):
        """Clear search only if search input has focus"""
        if hasattr(self.study_list, 'search_input') and self.study_list.search_input.hasFocus():
            self.study_list._clear_search()

    def _load_studies(self):
        """Load studies from PACS in background thread"""
        self.study_list.set_loading(True)
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("⏳ Loading...")

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
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("🔄 Refresh")

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
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("🔄 Refresh")
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