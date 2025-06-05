import os
import subprocess
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QProgressBar, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from app.presentation.controllers.pacs_controller import PacsController, StudiesWorker, QueueSenderWorker
from app.presentation.widgets.study_list_widget import SearchableStudyListWidget, StudyQueueWidget
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
        # Scrollable container setup
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setSpacing(8)
        scroll_layout.setContentsMargins(12, 12, 12, 12)

        # Header
        header_layout = QHBoxLayout()
        studies_label = QLabel("Studii disponibile")
        studies_label.setObjectName("SectionTitle")

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setMaximumWidth(100)
        self.refresh_button.setFixedHeight(30)
        self.refresh_button.clicked.connect(self._load_studies)

        header_layout.addWidget(studies_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        scroll_layout.addLayout(header_layout)

        # Study list (no external scroll, it handles scroll internally)
        self.study_list = SearchableStudyListWidget()
        self.study_list.study_selected.connect(self._on_study_selected)
        self.study_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        scroll_layout.addWidget(self.study_list)

        # Metadata and Queue
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(12)

        # Metadata section
        left_col = QVBoxLayout()
        metadata_label = QLabel("Metadate Studiu")
        metadata_label.setObjectName("SectionTitle")
        left_col.addWidget(metadata_label)

        self.metadata_widget = MetadataWidget()
        self.metadata_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_col.addWidget(self.metadata_widget)

        # Queue section with buttons
        right_col = QVBoxLayout()
        queue_label = QLabel("Coada de studii")
        queue_label.setObjectName("SectionTitle")
        right_col.addWidget(queue_label)

        self.queue_widget = StudyQueueWidget()
        self.queue_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_col.addWidget(self.queue_widget)

        # Queue buttons (moved under queue widget)
        queue_buttons_layout = QHBoxLayout()
        queue_buttons_layout.setSpacing(8)

        self.add_to_queue_button = QPushButton("+ Adauga in coada")
        self.add_to_queue_button.setObjectName("QueueButton")
        self.add_to_queue_button.clicked.connect(self._add_study_to_queue)

        self.send_queue_button = QPushButton("Trimite")
        self.send_queue_button.setObjectName("SendPACSButton")
        self.send_queue_button.clicked.connect(self._send_queue_to_pacs)

        # Set button sizes for queue buttons
        for btn in [self.add_to_queue_button, self.send_queue_button]:
            btn.setFixedHeight(35)
            btn.setMinimumWidth(120)

        queue_buttons_layout.addWidget(self.add_to_queue_button)
        queue_buttons_layout.addWidget(self.send_queue_button)
        queue_buttons_layout.addStretch()

        right_col.addLayout(queue_buttons_layout)

        left_widget = QWidget()
        left_widget.setLayout(left_col)
        right_widget = QWidget()
        right_widget.setLayout(right_col)

        middle_layout.addWidget(left_widget, 1)
        middle_layout.addWidget(right_widget, 1)
        scroll_layout.addLayout(middle_layout)

        # Results section
        results_label = QLabel("Rezultatul explorarii")
        results_label.setObjectName("SectionTitle")
        scroll_layout.addWidget(results_label)

        self.result_widget = ResultWidget()
        self.result_widget.setMinimumHeight(200)
        self.result_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_layout.addWidget(self.result_widget)

        # PDF Buttons (aligned to the right)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.preview_button = QPushButton("Previzualizare PDF")
        self.preview_button.setObjectName("PreviewButton")
        self.preview_button.clicked.connect(self._preview_pdf)

        self.generate_pdf_button = QPushButton("Generare PDF")
        self.generate_pdf_button.setObjectName("GeneratePDFButton")
        self.generate_pdf_button.clicked.connect(self._export_pdf)

        self.print_button = QPushButton("Print")
        self.print_button.setObjectName("PrintButton")
        self.print_button.clicked.connect(self._print_pdf)

        pdf_buttons = [self.preview_button, self.generate_pdf_button, self.print_button]

        for btn in pdf_buttons:
            btn.setFixedHeight(35)
            btn.setMinimumWidth(120)

        # Add stretch to push buttons to the right
        button_layout.addStretch()
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.generate_pdf_button)
        button_layout.addWidget(self.print_button)

        scroll_layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(20)
        scroll_layout.addWidget(self.progress_bar)

        # Shortcuts info
        shortcuts_label = QLabel("💡 Ctrl+F (Cautare studiu) • F5 (Refresh) • Ctrl+Q (Adauga in coada) • Esc (Anuleaza Cautarea)")
        shortcuts_label.setStyleSheet("color: #6b7280; font-size: 10px; font-style: italic; padding: 4px;")
        shortcuts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcuts_label.setMaximumHeight(20)
        scroll_layout.addWidget(shortcuts_label)

        # Final stretch to consume space if needed
        scroll_layout.addStretch()

        # Apply scroll container
        scroll_area.setWidget(scroll_container)

        # Final layout of the widget
        final_layout = QVBoxLayout(self)
        final_layout.addWidget(scroll_area)
        self.setLayout(final_layout)

        # Update buttons state
        self._update_queue_buttons()

    def _setup_shortcuts(self):
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
        if hasattr(self.study_list, 'search_input') and self.study_list.search_input.hasFocus():
            self.study_list._clear_search()

    def _load_studies(self):
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
        self.study_list.set_loading(False)
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("🔄 Refresh")
        self._notification_service.show_error(self, "Error", f"Error loading studies:\n{error_message}")

    def _on_study_selected(self, study_id: str):
        try:
            metadata = self._pacs_controller.get_study_metadata(study_id)
            self.metadata_widget.display_metadata(metadata)
            print(self._pacs_controller.get_examination_result_from_study(study_id))
        except Exception as e:
            self._notification_service.show_error(self, "Error", f"Error loading metadata:\n{e}")

    def _export_pdf(self):
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
        study_id = self.study_list.get_selected_study_id()
        if not study_id:
            self._notification_service.show_warning(self, "Warning", "Please select a study.")
            return

        result_text = self.result_widget.get_result_text()
        self._pacs_controller.preview_pdf(study_id, result_text, self)

    def _print_pdf(self):
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

    def _add_study_to_queue(self):
        study_id = self.study_list.get_selected_study_id()
        if not study_id:
            self._notification_service.show_warning(self, "Atenție", "Selectează un studiu pentru a-l adăuga în queue.")
            return

        if self.queue_widget.is_study_in_queue(study_id):
            self._notification_service.show_warning(
                self,
                "Studiu deja în queue",
                "Acest studiu este deja în queue pentru trimitere."
            )
            return

        # Validate study
        is_valid, metadata = self._pacs_controller.validate_study_for_queue(study_id, self)
        if not is_valid:
            return

        # Get examination result
        examination_result = self.result_widget.get_result_text()

        if not examination_result.strip():
            proceed = self._notification_service.ask_confirmation(
                self,
                "Rezultat lipsă",
                "Nu există rezultat al explorării introdus.\n\n"
                "Vrei să adaugi studiul în queue fără rezultat?"
            )
            if not proceed:
                return

        # Add to queue
        patient_name = metadata.get("Patient Name", "Unknown")
        study_date = metadata.get("Study Date", "Unknown")
        description = metadata.get("Description", "Unknown")
        display_text = f"{patient_name} - {study_date} - {description}"

        success = self.queue_widget.add_study_to_queue(
            study_id,
            display_text,
            examination_result,
            patient_name,
            study_date,
            description
        )

        if success:
            message = f"Studiul '{patient_name}' a fost adăugat în queue."
            if examination_result.strip():
                message += f"\nRezultatul explorării ({len(examination_result)} caractere) a fost atașat."
            else:
                message += "\nStudiul a fost adăugat fără rezultat al explorării."

            self._notification_service.show_info(self, "Studiu adăugat", message)

            # Update queue buttons
            self._update_queue_buttons()

    def _send_queue_to_pacs(self):
        """Send all queued studies to target PACS"""
        queued_studies = self.queue_widget.get_queued_studies()

        if not queued_studies:
            self._notification_service.show_warning(self, "Queue gol", "Nu sunt studii în queue pentru trimitere.")
            return

        # Show progress and send in background
        self._show_sending_progress(queued_studies)

    def _show_sending_progress(self, queued_studies):
        """Show progress dialog while sending studies"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.send_queue_button.setEnabled(False)
        self.send_queue_button.setText("⏳ Trimitere...")

        # Create worker thread
        self.sender_thread = QThread()
        self.sender_worker = QueueSenderWorker(
            self._pacs_controller,
            queued_studies,
            self._settings.PACS_URL_2
        )
        self.sender_worker.moveToThread(self.sender_thread)

        # Connect signals
        self.sender_thread.started.connect(self.sender_worker.run)
        self.sender_worker.progress_updated.connect(self._update_sending_progress)
        self.sender_worker.sending_completed.connect(self._on_sending_completed)

        # Cleanup
        self.sender_worker.sending_completed.connect(self.sender_thread.quit)
        self.sender_worker.sending_completed.connect(self.sender_worker.deleteLater)
        self.sender_thread.finished.connect(self.sender_thread.deleteLater)

        self.sender_thread.start()

    def _update_sending_progress(self, progress: int, current_study: str):
        """Update progress bar during sending"""
        self.progress_bar.setValue(progress)
        if progress < 100:
            self.send_queue_button.setText(f"⏳ Trimitere... {current_study}")

    def _on_sending_completed(self, success: bool, message: str):
        """Handle completion of queue sending"""
        self.progress_bar.setVisible(False)
        self.send_queue_button.setEnabled(True)
        self.send_queue_button.setText("🚀 Send Queue to PACS")

        if success:
            # Clear queue on success
            self.queue_widget.clear_queue()
            self._notification_service.show_info(self, "Trimitere finalizată", message)
        else:
            self._notification_service.show_error(self, "Eroare trimitere", message)

        self._update_queue_buttons()

    def _clear_queue(self):
        """Clear the queue after confirmation"""
        if self.queue_widget.get_queue_count() == 0:
            return

        if self._notification_service.ask_confirmation(
                self,
                "Confirmă ștergerea",
                f"Sigur vrei să ștergi toate {self.queue_widget.get_queue_count()} studiile din queue?"
        ):
            self.queue_widget.clear_queue()
            self._notification_service.show_info(self, "Queue șters", "Toate studiile au fost eliminate din queue.")
            self._update_queue_buttons()

    def _update_queue_buttons(self):
        """Update queue-related buttons based on queue state"""
        queue_count = self.queue_widget.get_queue_count()
        has_studies = queue_count > 0

        self.send_queue_button.setEnabled(has_studies)

        # Update button text with count
        if has_studies:
            self.send_queue_button.setText(f"🚀 Send Queue ({queue_count}) to PACS")
        else:
            self.send_queue_button.setText("🚀 Send Queue to PACS")