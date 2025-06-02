from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from app.presentation.styles.style_manager import load_style


class PatientsView(QWidget):
    """Simple patients view - can be expanded later"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Patients Management")
        self._setup_ui()
        load_style(self)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Patients Management")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        content = QLabel("Patient management features will be implemented here.")
        content.setWordWrap(True)
        layout.addWidget(content)

        layout.addStretch()