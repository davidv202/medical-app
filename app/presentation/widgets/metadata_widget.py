from PyQt6.QtWidgets import QTextEdit
from typing import Dict, Any
from app.utils.formatters import Formatters


class MetadataWidget(QTextEdit):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("MetadataWidget")

    def display_metadata(self, metadata: Dict[str, Any]):
        formatted_text = Formatters.format_metadata_display(metadata)
        self.setPlainText(formatted_text)

    def clear_metadata(self):
        self.clear()


class ResultWidget(QTextEdit):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Rezultatul explorării...")
        self.setObjectName("ResultWidget")

    def get_result_text(self) -> str:
        return self.toPlainText().strip()

    def set_result_text(self, text: str):
        self.setPlainText(text)

    def clear_result(self):
        self.clear()