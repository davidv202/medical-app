from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QToolBar, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtGui import QAction, QFont, QTextCharFormat
from typing import Dict, Any
from app.utils.formatters import Formatters
from app.services.notification_service import NotificationService


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


class ResultWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ResultWidget")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        indication_layout = QHBoxLayout()

        indication_layout.addWidget(QLabel("Age:"))

        self.age_input = QLineEdit()
        self.age_input.setMaximumWidth(75)
        indication_layout.addWidget(self.age_input)

        indication_layout.addWidget(QLabel("Dignosis:"))
        self.diagnostic_input = QLineEdit()
        self.diagnostic_input.setMinimumWidth(300)
        indication_layout.addWidget(self.diagnostic_input)

        self.generate_button = QPushButton("Generate Text")
        self.generate_button.setMaximumWidth(30)
        self.generate_button.setToolTip("Generate Text")
        self.generate_button.clicked.connect(self._generate_text)
        indication_layout.addWidget(self.generate_button)

        indication_layout.addStretch()
        layout.addLayout(indication_layout)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        
        self._create_format_actions()
        
        layout.addWidget(self.toolbar)
        
        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlaceholderText("Rezultatul explorării...")
        self.text_edit.currentCharFormatChanged.connect(self._update_toolbar)
        
        layout.addWidget(self.text_edit)

    def _create_format_actions(self):
        # Bold
        self.bold_action = QAction("Bold", self)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.setCheckable(True)
        self.bold_action.triggered.connect(lambda: self.text_edit.setFontWeight(
            QFont.Weight.Bold if self.bold_action.isChecked() else QFont.Weight.Normal))
        self.toolbar.addAction(self.bold_action)
        
        # Italic
        self.italic_action = QAction("Italic", self)
        self.italic_action.setShortcut("Ctrl+I") 
        self.italic_action.setCheckable(True)
        self.italic_action.triggered.connect(lambda: self.text_edit.setFontItalic(self.italic_action.isChecked()))
        self.toolbar.addAction(self.italic_action)
        
        # Underline
        self.underline_action = QAction("Underline", self)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.setCheckable(True) 
        self.underline_action.triggered.connect(lambda: self.text_edit.setFontUnderline(self.underline_action.isChecked()))
        self.toolbar.addAction(self.underline_action)

    def _update_toolbar(self, fmt):
        self.bold_action.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.italic_action.setChecked(fmt.fontItalic())
        self.underline_action.setChecked(fmt.fontUnderline())
        
    def _generate_text(self):
        varsta = self.age_input.text().strip()
        diagnostic = self.diagnostic_input.text().strip()
        
        if not varsta or not diagnostic:
            NotificationService.show_warning(self, "Date incomplete", 
                                        "Completează vârsta și diagnosticul.")
            return

        if not varsta.isdigit():
            NotificationService.show_warning(self, "Atentie",
                                             "Varsta trebuie sa fie un numar.")
            return
        
        # Folosește HTML pentru formatare
        indicatie_html = f"""<p><b><i>Indicație:</i></b> pacient în vârsta de {varsta} ani este diagnosticat cu {diagnostic}</p>

        <p><b><i>Realizare:</i></b> </p>

        <p><b><i>Rezultat:</i></b></p>

        <p><b>CONCLUZII<b><p>
        """
        
        # Setează HTML în loc de text simplu
        self.text_edit.setHtml(indicatie_html)
        
        # Poziționează cursorul după "Realizare:"
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def get_result_text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def set_result_text(self, text: str):
        self.text_edit.setPlainText(text)

    def clear_result(self):
        self.text_edit.clear()