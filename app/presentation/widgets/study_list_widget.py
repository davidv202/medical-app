from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import pyqtSignal, Qt
from typing import Dict, List
from app.presentation.widgets.base_widgets import BaseWidget


class StudyListWidget(QListWidget):
    """Custom widget for displaying PACS studies"""
    study_selected = pyqtSignal(str)  # study_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.studies: Dict[str, str] = {}  # display_text -> study_id
        self.setObjectName("StudyList")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.itemClicked.connect(self._on_item_clicked)

    def add_study(self, study_id: str, display_text: str):
        """Add a study to the list"""
        self.studies[display_text] = study_id
        self.addItem(display_text)

    def clear_studies(self):
        """Clear all studies"""
        self.clear()
        self.studies.clear()

    def set_loading(self, is_loading: bool):
        """Show/hide loading state"""
        if is_loading:
            self.clear_studies()
            self.addItem("Se incarca studiile...")
        else:
            # Remove loading item if it exists
            for i in range(self.count()):
                item = self.item(i)
                if item and item.text() == "Se incarca studiile...":
                    self.takeItem(i)
                    break

    def get_selected_study_id(self) -> str:
        """Get the currently selected study ID"""
        current_item = self.currentItem()
        if current_item and current_item.text() in self.studies:
            return self.studies[current_item.text()]
        return ""

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click"""
        if item.text() in self.studies:
            study_id = self.studies[item.text()]
            self.study_selected.emit(study_id)


class QueueListWidget(QListWidget):
    """Custom widget for displaying queued studies"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QueueList")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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