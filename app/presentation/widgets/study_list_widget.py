from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon
from typing import Dict, List, Tuple


class SearchableStudyListWidget(QWidget):
    """Enhanced study list widget with search functionality"""
    study_selected = pyqtSignal(str)  # study_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_studies: List[Tuple[str, str]] = []  # (study_id, display_text)
        self.filtered_studies: Dict[str, str] = {}  # display_text -> study_id

        # Search delay timer to avoid searching on every keystroke
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Search section
        search_layout = QHBoxLayout()

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Caută studii (nume pacient, dată, descriere)...")
        self.search_input.setObjectName("SearchInput")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._perform_search)

        # Clear search button
        self.clear_button = QPushButton("✕")
        self.clear_button.setObjectName("ClearSearchButton")
        self.clear_button.setMaximumWidth(30)
        self.clear_button.setToolTip("Șterge căutarea")
        self.clear_button.clicked.connect(self._clear_search)
        self.clear_button.setVisible(False)  # Hidden initially

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.clear_button)

        layout.addLayout(search_layout)

        # Results info
        self.results_label = QLabel()
        self.results_label.setObjectName("ResultsLabel")
        self.results_label.setVisible(False)
        layout.addWidget(self.results_label)

        # Study list - FIXED: Add proper height constraint for scroll
        self.study_list = QListWidget()
        self.study_list.setObjectName("StudyList")
        self.study_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.study_list.itemClicked.connect(self._on_item_clicked)

        # KEY FIX: Set fixed height to enable scrolling
        self.study_list.setFixedHeight(200)

        # FORCE scrollbars to be visible when needed
        self.study_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.study_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        layout.addWidget(self.study_list)

    def _on_search_text_changed(self, text: str):
        """Handle search text change with debouncing"""
        # Show/hide clear button
        self.clear_button.setVisible(bool(text.strip()))

        # Stop any pending search and start new timer
        self.search_timer.stop()
        if text.strip():
            self.search_timer.start(300)  # 300ms delay
        else:
            self._clear_search()

    def _perform_search(self):
        """Perform the actual search"""
        search_text = self.search_input.text().strip().lower()

        if not search_text:
            self._show_all_studies()
            return

        # Filter studies based on search text
        filtered = []
        for study_id, display_text in self.all_studies:
            if search_text in display_text.lower():
                filtered.append((study_id, display_text))

        self._display_filtered_studies(filtered, search_text)

    def _display_filtered_studies(self, filtered_studies: List[Tuple[str, str]], search_text: str):
        """Display filtered studies in the list"""
        self.study_list.clear()
        self.filtered_studies.clear()

        for study_id, display_text in filtered_studies:
            self.filtered_studies[display_text] = study_id

            # Highlight search terms (simple approach)
            highlighted_text = self._highlight_search_terms(display_text, search_text)
            item = QListWidgetItem(highlighted_text)
            item.setData(Qt.ItemDataRole.UserRole, study_id)
            self.study_list.addItem(item)

        # Update results info
        total_studies = len(self.all_studies)
        found_studies = len(filtered_studies)

        if found_studies == 0:
            self.results_label.setText(f"Nu s-au găsit studii pentru '{search_text}'")
            self.results_label.setStyleSheet("color: #dc2626; font-weight: 500;")
        else:
            self.results_label.setText(f"Găsite {found_studies} din {total_studies} studii")
            self.results_label.setStyleSheet("color: #059669; font-weight: 500;")

        self.results_label.setVisible(True)

    def _highlight_search_terms(self, text: str, search_term: str) -> str:
        """Simple text highlighting (you could enhance this with HTML formatting)"""
        # For now, just return the original text
        # In a more advanced implementation, you could use HTML formatting
        return text

    def _show_all_studies(self):
        """Show all studies (no filtering)"""
        self.study_list.clear()
        self.filtered_studies.clear()

        for study_id, display_text in self.all_studies:
            self.filtered_studies[display_text] = study_id
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, study_id)
            self.study_list.addItem(item)

        self.results_label.setVisible(False)

    def _clear_search(self):
        """Clear search and show all studies"""
        self.search_input.clear()
        self.clear_button.setVisible(False)
        self._show_all_studies()

    def add_study(self, study_id: str, display_text: str):
        """Add a study to the list"""
        self.all_studies.append((study_id, display_text))

        # If no search is active, add to visible list
        if not self.search_input.text().strip():
            self.filtered_studies[display_text] = study_id
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, study_id)
            self.study_list.addItem(item)

    def clear_studies(self):
        """Clear all studies"""
        self.all_studies.clear()
        self.study_list.clear()
        self.filtered_studies.clear()
        self.search_input.clear()
        self.clear_button.setVisible(False)
        self.results_label.setVisible(False)

    def set_loading(self, is_loading: bool):
        """Show/hide loading state"""
        if is_loading:
            self.clear_studies()
            self.study_list.addItem("Se încarcă studiile...")
            self.search_input.setEnabled(False)
        else:
            # Remove loading item if it exists
            for i in range(self.study_list.count()):
                item = self.study_list.item(i)
                if item and item.text() == "Se încarcă studiile...":
                    self.study_list.takeItem(i)
                    break
            self.search_input.setEnabled(True)

    def get_selected_study_id(self) -> str:
        """Get the currently selected study ID"""
        current_item = self.study_list.currentItem()
        if current_item:
            # Try to get from UserRole data first
            study_id = current_item.data(Qt.ItemDataRole.UserRole)
            if study_id:
                return study_id

            # Fallback to text-based lookup
            if current_item.text() in self.filtered_studies:
                return self.filtered_studies[current_item.text()]
        return ""

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click"""
        study_id = item.data(Qt.ItemDataRole.UserRole)
        if study_id:
            self.study_selected.emit(study_id)
        else:
            # Fallback for text-based lookup
            if item.text() in self.filtered_studies:
                study_id = self.filtered_studies[item.text()]
                self.study_selected.emit(study_id)

    def focus_search(self):
        """Set focus to search input"""
        self.search_input.setFocus()

    def get_search_text(self) -> str:
        """Get current search text"""
        return self.search_input.text().strip()

    def set_search_text(self, text: str):
        """Set search text programmatically"""
        self.search_input.setText(text)


class QueueListWidget(QListWidget):
    """Custom widget for displaying queued studies"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QueueList")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # FIXED: Add proper height and scroll for queue too
        self.setMaximumHeight(120)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def add_instance(self, instance_id: str, display_text: str):
        """Add an instance to the queue"""
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, instance_id)
        self.addItem(item)

    def get_all_instance_ids(self) -> List[str]:
        """Get all instance IDs in the queue"""
        instance_ids = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                instance_id = item.data(Qt.ItemDataRole.UserRole)
                if instance_id:
                    instance_ids.append(instance_id)
        return instance_ids

    def clear_queue(self):
        """Clear the queue"""
        self.clear()