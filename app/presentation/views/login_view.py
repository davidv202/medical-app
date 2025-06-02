from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QLabel, QHBoxLayout
)
from app.presentation.controllers.auth_controller import AuthController
from app.core.entities.user import UserRole
from app.presentation.styles.style_manager import load_style
from app.services.notification_service import NotificationService


class LoginView(QWidget):
    def __init__(self, auth_controller: AuthController):
        super().__init__()
        self._auth_controller = auth_controller
        self._notification_service = NotificationService()
        self.setWindowTitle("Medical App - Login")
        self.setGeometry(100, 100, 1600, 800)
        self._setup_ui()
        load_style(self)

    def _setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addStretch()

        # Center container
        center_widget = QWidget()
        center_widget.setMaximumWidth(400)
        center_layout = QVBoxLayout(center_widget)

        # Title
        title_label = QLabel("Medical PACS System")
        title_label.setObjectName("LoginTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Conecteaza-te pentru a continua")
        subtitle_label.setObjectName("LoginSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(subtitle_label)

        center_layout.addSpacing(30)

        # Form
        form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.username_input.setObjectName("UsernameInput")
        self.username_input.setPlaceholderText("Introdu username")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("PasswordInput")
        self.password_input.setPlaceholderText("Introdu parola")

        self.username_input.returnPressed.connect(self._handle_login)
        self.password_input.returnPressed.connect(self._handle_login)

        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)

        center_layout.addLayout(form_layout)
        center_layout.addSpacing(20)

        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("LoginButton")
        self.login_button.clicked.connect(self._handle_login)
        center_layout.addWidget(self.login_button)

        # Center the form
        container_layout = QHBoxLayout()
        container_layout.addStretch()
        container_layout.addWidget(center_widget)
        container_layout.addStretch()

        main_layout.addLayout(container_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self.username_input.setFocus()

    def _handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self._notification_service.show_warning(
                self, "Atentie", "Introduceti username-ul si parola."
            )
            return

        if self._auth_controller.login(username, password, self):
            user = self._auth_controller.get_current_user()
            self._open_main_window(user.role)

    def _open_main_window(self, role: UserRole):
        from app.di.container import Container

        if role == UserRole.ADMIN:
            from app.presentation.views.admin_view import AdminView
            self.main_window = AdminView(Container.get_auth_controller())
        elif role == UserRole.DOCTOR:
            from app.presentation.views.main_view import MainView
            self.main_window = MainView(
                Container.get_auth_controller(),
                Container.get_pacs_controller()
            )
        else:
            self._notification_service.show_warning(self, "Atentie", "Rol necunoscut.")

        self.main_window.show()
        self.close()