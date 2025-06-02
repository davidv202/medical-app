from PyQt6.QtWidgets import QTextEdit
from typing import Dict, Any
from app.utils.formatters import Formatters


class MetadataWidget(QTextEdit):
    """Custom widget for displaying study metadata"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("MetadataWidget")

    def display_metadata(self, metadata: Dict[str, Any]):
        """Display formatted metadata"""
        formatted_text = Formatters.format_metadata_display(metadata)
        self.setPlainText(formatted_text)

    def clear_metadata(self):
        """Clear the metadata display"""
        self.clear()


class ResultWidget(QTextEdit):
    """Custom widget for examination results input"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Rezultatul explorării...")
        self.setObjectName("ResultWidget")

    def get_result_text(self) -> str:
        """Get the examination result text"""
        return self.toPlainText().strip()

    def set_result_text(self, text: str):
        """Set the examination result text"""
        self.setPlainText(text)

    def clear_result(self):
        """Clear the result text"""
        self.clear()