from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QHBoxLayout, QLabel, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt
from app.presentation.controllers.auth_controller import AuthController
from app.core.entities.user import User, UserRole
from app.services.notification_service import NotificationService
from app.presentation.styles.style_manager import load_style
from app.utils.validators import Validators


class AdminView(QWidget):
    def __init__(self, auth_controller: AuthController):
        super().__init__()
        self._auth_controller = auth_controller
        self._notification_service = NotificationService()
        self.setWindowTitle("Admin Panel - Medical PACS System")
        self.setGeometry(100, 100, 1600, 800)
        self._setup_ui()
        load_style(self)
        self._load_users()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("")
        title_label.setObjectName("AdminTitle")

        # User info and logout
        current_user = self._auth_controller.get_current_user()
        username = current_user.username if current_user else "Unknown"

        user_info_label = QLabel(f"Logat ca: {username}")
        user_info_label.setObjectName("UserLabel")

        self.logout_button = QPushButton("Iesi din cont")
        self.logout_button.setObjectName("LogoutButton")
        self.logout_button.clicked.connect(self._handle_logout)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(user_info_label)
        header_layout.addWidget(self.logout_button)

        main_layout.addLayout(header_layout)

        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - User list
        left_widget = self._create_user_list_section()
        splitter.addWidget(left_widget)

        # Right side - User form
        right_widget = self._create_user_form_section()
        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setSizes([600, 400])

        main_layout.addWidget(splitter)

    def _create_user_list_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Section title
        section_title = QLabel("Utilizatori")
        section_title.setObjectName("SectionTitle")
        layout.addWidget(section_title)

        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(3)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Rol"])
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Set column widths
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # Connect selection change
        self.users_table.itemSelectionChanged.connect(self._on_user_selected)

        layout.addWidget(self.users_table)

        # User actions
        user_actions_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._load_users)

        self.delete_user_button = QPushButton("Sterge user")
        self.delete_user_button.clicked.connect(self._delete_user)
        self.delete_user_button.setEnabled(False)

        user_actions_layout.addWidget(self.refresh_button)
        user_actions_layout.addWidget(self.delete_user_button)
        user_actions_layout.addStretch()

        layout.addLayout(user_actions_layout)

        return widget

    def _create_user_form_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Create user form
        form_group = QGroupBox("Creeaza user")
        form_layout = QFormLayout(form_group)

        self.username_input = QLineEdit()
        self.username_input.setObjectName("UsernameInput")
        self.username_input.setPlaceholderText("Introdu username")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("PasswordInput")
        self.password_input.setPlaceholderText("Introdu parola")

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setObjectName("PasswordInput")
        self.confirm_password_input.setPlaceholderText("Confirma parola")

        self.role_input = QComboBox()
        self.role_input.addItems([role.value for role in UserRole])

        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Parola:", self.password_input)
        form_layout.addRow("Confirma parola:", self.confirm_password_input)
        form_layout.addRow("Rol:", self.role_input)

        layout.addWidget(form_group)

        # Form buttons
        form_buttons_layout = QHBoxLayout()

        self.clear_button = QPushButton("Reset")
        self.clear_button.clicked.connect(self._clear_form)

        self.create_button = QPushButton("Creaza user")
        self.create_button.setObjectName("CreateButton")
        self.create_button.clicked.connect(self._handle_create_user)

        form_buttons_layout.addWidget(self.clear_button)
        form_buttons_layout.addWidget(self.create_button)

        layout.addLayout(form_buttons_layout)

        # System info section
        info_group = QGroupBox("Informatii sistem")
        info_layout = QVBoxLayout(info_group)

        self.system_info = QTextEdit()
        self.system_info.setReadOnly(True)
        self.system_info.setMaximumHeight(200)

        info_layout.addWidget(self.system_info)
        layout.addWidget(info_group)

        layout.addStretch()

        return widget

    def _load_users(self):
        try:
            from app.di.container import Container
            user_repo = Container.get_user_repository()
            users = user_repo.find_all()

            self.users_table.setRowCount(len(users))

            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.users_table.setItem(row, 1, QTableWidgetItem(user.username))
                self.users_table.setItem(row, 2, QTableWidgetItem(user.role.value.title()))

        except Exception as e:
            self._notification_service.show_error(self, "Eroare", f"Nu s-au putut incarca conturile utilizatorilor: {e}")

    def _on_user_selected(self):
        current_row = self.users_table.currentRow()
        self.delete_user_button.setEnabled(current_row >= 0)

    def _delete_user(self):
        current_row = self.users_table.currentRow()

        if current_row >= 0:
            user_id = int(self.users_table.item(current_row, 0).text())
            username = self.users_table.item(current_row, 1).text()

            # Don't allow deleting current user
            current_user = self._auth_controller.get_current_user()
            if current_user and current_user.id == user_id:
                self._notification_service.show_warning(
                    self, "Atentie", "Nu poti sa iti stergi propriu cont."
                )
                return

            if self._notification_service.ask_confirmation(
                    self, "Confirm Delete", f"Esti sigur ca vrei sa stergi utilizatorul '{username}'?"
            ):
                try:
                    from app.di.container import Container
                    user_repo = Container.get_user_repository()

                    if user_repo.delete(user_id):
                        self._notification_service.show_info(self, "Succes", "Utilizator sters cu succes.")
                        self._load_users()
                    else:
                        self._notification_service.show_error(self, "Eroare", "Eroare la stergerea utilizatorului")

                except Exception as e:
                    self._notification_service.show_error(self, "Eroare", f"Eroare la stergerea utilizatorului: {e}")

    def _handle_create_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()
        role_value = self.role_input.currentText()

        # Validation
        username_error = Validators.validate_username(username)
        if username_error:
            self._notification_service.show_warning(self, "Validation Error", username_error)
            return

        password_error = Validators.validate_password(password)
        if password_error:
            self._notification_service.show_warning(self, "Validation Error", password_error)
            return

        if password != confirm_password:
            self._notification_service.show_warning(self, "Validation Error", "Passwords do not match")
            return

        try:
            from app.di.container import Container
            auth_service = Container.get_auth_service()
            user_repo = Container.get_user_repository()

            # Hash password and create user
            hashed_password = auth_service.hash_password(password)
            role = UserRole(role_value)

            new_user = User(
                id=0,
                username=username,
                password=hashed_password,
                role=role
            )

            created_user = user_repo.create(new_user)

            self._notification_service.show_info(self, "Succes", f"Utilizatorul '{username}' a fost creat cu succes.")
            self._clear_form()
            self._load_users()

        except Exception as e:
            self._notification_service.show_error(self, "Error", f"Failed to create user: {e}")

    def _clear_form(self):
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()
        self.role_input.setCurrentIndex(0)
        self.username_input.setFocus()

    def _handle_logout(self):
        if self._auth_controller.logout(self):
            self._open_login_window()

    def _open_login_window(self):
        from app.presentation.views.login_view import LoginView
        from app.di.container import Container

        self.login_window = LoginView(Container.get_auth_controller())
        self.login_window.show()
        self.close()