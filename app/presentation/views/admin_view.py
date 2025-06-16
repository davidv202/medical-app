from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QHBoxLayout, QLabel, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt

from app.di.container import Container
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
        self.setWindowTitle("Admin Panel")
        self.setGeometry(100, 100, 1600, 800)

        self._editing_user_id = None
        self._editing_mode = False

        self._setup_ui()
        load_style(self)
        self._setup_user_search_shortcuts()
        self._load_users()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()

        title_label = QLabel("Admin Panel - Gestiune Utilizatori")
        title_label.setObjectName("AdminTitle")

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

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = self._create_user_list_section()
        splitter.addWidget(left_widget)

        right_widget = self._create_user_form_section()
        splitter.addWidget(right_widget)

        splitter.setSizes([600, 400])

        main_layout.addWidget(splitter)

        shortcuts_info = QLabel(
            "💡 Shortcuts: Ctrl+F (Cauta) • Esc (Goleste cautarea) • F5 (Refresh) • Enter/Dublu-click (Editeaza user)")
        shortcuts_info.setStyleSheet("color: #6b7280; font-size: 10px; font-style: italic; padding: 5px;")
        shortcuts_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcuts_info.setMaximumHeight(25)
        main_layout.addWidget(shortcuts_info)

    def _create_user_list_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        section_title = QLabel("Utilizatori")
        section_title.setObjectName("SectionTitle")
        layout.addWidget(section_title)

        search_layout = QHBoxLayout()

        self.user_search_input = QLineEdit()
        self.user_search_input.setPlaceholderText("Caută utilizatori (username sau nume)...")
        self.user_search_input.setObjectName("SearchInput")
        self.user_search_input.textChanged.connect(self._filter_users)

        self.clear_user_search_button = QPushButton("✕")
        self.clear_user_search_button.setObjectName("ClearSearchButton")
        self.clear_user_search_button.setMaximumWidth(25)
        self.clear_user_search_button.setToolTip("Sterge cautarea")
        self.clear_user_search_button.clicked.connect(self._clear_user_search)
        self.clear_user_search_button.setVisible(False)

        search_layout.addWidget(self.user_search_input)
        search_layout.addWidget(self.clear_user_search_button)
        layout.addLayout(search_layout)

        self.user_results_label = QLabel()
        self.user_results_label.setVisible(False)
        self.user_results_label.setStyleSheet("color: #6b7280; font-size: 11px; padding: 2px;")
        layout.addWidget(self.user_results_label)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nume Complet", "Rol"])
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.users_table.itemSelectionChanged.connect(self._on_user_selected)
        self.users_table.itemDoubleClicked.connect(self._on_user_double_clicked)

        layout.addWidget(self.users_table)

        user_actions_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._load_users)

        self.edit_user_button = QPushButton("Modifica user")
        self.edit_user_button.setObjectName("EditButton")
        self.edit_user_button.clicked.connect(self._edit_selected_user)
        self.edit_user_button.setEnabled(False)

        self.delete_user_button = QPushButton("Sterge user")
        self.delete_user_button.clicked.connect(self._delete_user)
        self.delete_user_button.setEnabled(False)

        user_actions_layout.addWidget(self.refresh_button)
        user_actions_layout.addWidget(self.edit_user_button)
        user_actions_layout.addWidget(self.delete_user_button)
        user_actions_layout.addStretch()

        layout.addLayout(user_actions_layout)

        return widget

    def _filter_users(self, text: str):
        self.clear_user_search_button.setVisible(bool(text.strip()))

        if not text.strip():
            self._show_all_users()
            return

        visible_count = 0
        total_count = self.users_table.rowCount()

        for row in range(total_count):
            username_item = self.users_table.item(row, 1)  # Username column
            fullname_item = self.users_table.item(row, 2)  # Full name column

            username_match = text.lower() in username_item.text().lower() if username_item else False
            fullname_match = text.lower() in fullname_item.text().lower() if fullname_item else False

            if username_match or fullname_match:
                self.users_table.setRowHidden(row, False)
                visible_count += 1
            else:
                self.users_table.setRowHidden(row, True)

        if visible_count == 0:
            self.user_results_label.setText(f"Nu s-au găsit utilizatori pentru '{text}'")
            self.user_results_label.setStyleSheet("color: #dc2626; font-size: 11px; padding: 2px;")
        else:
            self.user_results_label.setText(f"Găsiți {visible_count} din {total_count} utilizatori")
            self.user_results_label.setStyleSheet("color: #059669; font-size: 11px; padding: 2px;")

        self.user_results_label.setVisible(True)

    def _show_all_users(self):
        for row in range(self.users_table.rowCount()):
            self.users_table.setRowHidden(row, False)
        self.user_results_label.setVisible(False)

    def _clear_user_search(self):
        self.user_search_input.clear()
        self.clear_user_search_button.setVisible(False)
        self._show_all_users()

    def _focus_user_search(self):
        self.user_search_input.setFocus()

    def _clear_user_search_if_focused(self):
        if self.user_search_input.hasFocus():
            self._clear_user_search()

    def _create_user_form_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.form_group = QGroupBox("Creeaza user")
        form_layout = QFormLayout(self.form_group)

        self.username_input = QLineEdit()
        self.username_input.setObjectName("UsernameInput")
        self.username_input.setPlaceholderText("Introdu username")

        self.first_name_input = QLineEdit()
        self.first_name_input.setObjectName("UsernameInput")
        self.first_name_input.setPlaceholderText("Introdu prenumele")

        self.last_name_input = QLineEdit()
        self.last_name_input.setObjectName("UsernameInput")
        self.last_name_input.setPlaceholderText("Introdu numele de familie")

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
        form_layout.addRow("Prenume:", self.first_name_input)
        form_layout.addRow("Nume familie:", self.last_name_input)
        form_layout.addRow("Parola:", self.password_input)
        form_layout.addRow("Confirma parola:", self.confirm_password_input)
        form_layout.addRow("Rol:", self.role_input)

        layout.addWidget(self.form_group)

        form_buttons_layout = QHBoxLayout()

        self.clear_button = QPushButton("Reset")
        self.clear_button.clicked.connect(self._clear_form)

        self.cancel_button = QPushButton("Anuleaza")
        self.cancel_button.setObjectName("CancelButton")
        self.cancel_button.clicked.connect(self._cancel_edit)
        self.cancel_button.setVisible(False)

        self.create_button = QPushButton("Creaza user")
        self.create_button.setObjectName("CreateButton")
        self.create_button.clicked.connect(self._handle_create_or_update_user)

        form_buttons_layout.addWidget(self.clear_button)
        form_buttons_layout.addWidget(self.cancel_button)
        form_buttons_layout.addWidget(self.create_button)

        layout.addLayout(form_buttons_layout)
        layout.addStretch()

        return widget

    def _load_users(self):
        try:
            from app.di.container import Container
            user_repo = Container.get_user_repository()
            users = user_repo.find_all()

            self.users_table.setColumnCount(4)
            self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nume Complet", "Rol"])

            self.users_table.setRowCount(len(users))

            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.users_table.setItem(row, 1, QTableWidgetItem(user.username))

                full_name = ""
                if user.first_name or user.last_name:
                    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                self.users_table.setItem(row, 2, QTableWidgetItem(full_name))

                self.users_table.setItem(row, 3, QTableWidgetItem(user.role.value.title()))

            header = self.users_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

            self._clear_user_search()

        except Exception as e:
            self._notification_service.show_error(self, "Eroare",
                                                  f"Nu s-au putut incarca conturile utilizatorilor: {e}")

    def _on_user_selected(self):
        current_row = self.users_table.currentRow()
        has_selection = current_row >= 0

        self.delete_user_button.setEnabled(has_selection)
        self.edit_user_button.setEnabled(has_selection)

    def _on_user_double_clicked(self, item):
        self._edit_selected_user()

    def _edit_selected_user(self):
        current_row = self.users_table.currentRow()
        if current_row < 0:
            return

        user_id = int(self.users_table.item(current_row, 0).text())

        try:
            user_repo = Container.get_user_repository()
            user = user_repo.find_by_id(user_id)

            if not user:
                self._notification_service.show_error(self, "Eroare", "Utilizatorul nu a fost gasit.")
                return

            self.username_input.setText(user.username)
            self.first_name_input.setText(user.first_name or "")
            self.last_name_input.setText(user.last_name or "")
            self.password_input.clear()
            self.confirm_password_input.clear()

            role_index = 0
            for i, role in enumerate(UserRole):
                if role == user.role:
                    role_index = i
                    break
            self.role_input.setCurrentIndex(role_index)

            self._editing_mode = True
            self._editing_user_id = user_id

            self.form_group.setTitle(f"Modifica user: {user.username}")
            self.create_button.setText("Actualizeaza user")
            self.cancel_button.setVisible(True)

            self.password_input.setPlaceholderText("Lasa gol pentru a pastra parola actuala")
            self.confirm_password_input.setPlaceholderText("Lasa gol pentru a pastra parola actuala")

            self.username_input.setFocus()

        except Exception as e:
            self._notification_service.show_error(self, "Eroare", f"Eroare la incarcarea datelor utilizatorului: {e}")

    def _cancel_edit(self):
        self._editing_mode = False
        self._editing_user_id = None

        self.form_group.setTitle("Creeaza user")
        self.create_button.setText("Creaza user")
        self.cancel_button.setVisible(False)

        self.password_input.setPlaceholderText("Introdu parola")
        self.confirm_password_input.setPlaceholderText("Confirma parola")

        self._clear_form()

    def _handle_create_or_update_user(self):
        if self._editing_mode:
            self._handle_update_user()
        else:
            self._handle_create_user()

    def _handle_update_user(self):
        username = self.username_input.text().strip()
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        password = self.password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()
        role_value = self.role_input.currentText()

        username_error = Validators.validate_username(username)
        if username_error:
            self._notification_service.show_warning(self, "Validation Error", username_error)
            return

        if first_name:
            first_name_error = Validators.validate_name(first_name, "Prenumele")
            if first_name_error:
                self._notification_service.show_warning(self, "Validation Error", first_name_error)
                return

        if last_name:
            last_name_error = Validators.validate_name(last_name, "Numele de familie")
            if last_name_error:
                self._notification_service.show_warning(self, "Validation Error", last_name_error)
                return

        if password:
            password_error = Validators.validate_password(password)
            if password_error:
                self._notification_service.show_warning(self, "Validation Error", password_error)
                return

            if password != confirm_password:
                self._notification_service.show_warning(self, "Validation Error", "Parolele sunt diferite.")
                return

        try:
            from app.di.container import Container
            auth_service = Container.get_auth_service()
            user_repo = Container.get_user_repository()

            # Get current user data
            current_user = user_repo.find_by_id(self._editing_user_id)
            if not current_user:
                self._notification_service.show_error(self, "Eroare", "Utilizatorul nu mai existe.")
                return

            existing_user = user_repo.find_by_username(username)
            if existing_user and existing_user.id != self._editing_user_id:
                self._notification_service.show_error(self, "Eroare",
                                                      f"Username-ul '{username}' este deja folosit de alt utilizator.")
                return

            # Prepare updated user data
            role = UserRole(role_value)

            # Use new password if provided, otherwise keep current
            if password:
                hashed_password = auth_service.hash_password(password)
            else:
                hashed_password = current_user.password

            updated_user = User(
                id=self._editing_user_id,
                username=username,
                password=hashed_password,
                role=role,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None
            )

            user_repo.update(updated_user)

            self._notification_service.show_info(self, "Succes",
                                                 f"Utilizatorul '{username}' a fost actualizat cu succes.")

            self._cancel_edit()
            self._load_users()

        except Exception as e:
            self._notification_service.show_error(self, "Error", f"Nu s-a putut actualiza utilizatorul: {e}")

    def _delete_user(self):
        current_row = self.users_table.currentRow()

        if current_row >= 0:
            user_id = int(self.users_table.item(current_row, 0).text())
            username = self.users_table.item(current_row, 1).text()

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

                        if self._editing_mode and self._editing_user_id == user_id:
                            self._cancel_edit()

                        self._load_users()
                    else:
                        self._notification_service.show_error(self, "Eroare", "Eroare la stergerea utilizatorului")

                except Exception as e:
                    self._notification_service.show_error(self, "Eroare", f"Eroare la stergerea utilizatorului: {e}")

    def _handle_create_user(self):
        username = self.username_input.text().strip()
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        password = self.password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()
        role_value = self.role_input.currentText()

        username_error = Validators.validate_username(username)
        if username_error:
            self._notification_service.show_warning(self, "Validation Error", username_error)
            return

        if first_name:
            first_name_error = Validators.validate_name(first_name, "Prenumele")
            if first_name_error:
                self._notification_service.show_warning(self, "Validation Error", first_name_error)
                return

        if last_name:
            last_name_error = Validators.validate_name(last_name, "Numele de familie")
            if last_name_error:
                self._notification_service.show_warning(self, "Validation Error", last_name_error)
                return

        password_error = Validators.validate_password(password)
        if password_error:
            self._notification_service.show_warning(self, "Validation Error", password_error)
            return

        if password != confirm_password:
            self._notification_service.show_warning(self, "Validation Error", "Parolele sunt diferite.")
            return

        try:
            from app.di.container import Container
            auth_service = Container.get_auth_service()
            user_repo = Container.get_user_repository()

            hashed_password = auth_service.hash_password(password)
            role = UserRole(role_value)

            new_user = User(
                id=0,
                username=username,
                password=hashed_password,
                role=role,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None
            )

            created_user = user_repo.create(new_user)

            self._notification_service.show_info(self, "Succes", f"Utilizatorul '{username}' a fost creat cu succes.")
            self._clear_form()
            self._load_users()

        except Exception as e:
            self._notification_service.show_error(self, "Error", f"Nu s-a putut crea utilizatorul nou: {e}")

    def _clear_form(self):
        self.username_input.clear()
        self.first_name_input.clear()
        self.last_name_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()
        self.role_input.setCurrentIndex(0)

        if not self._editing_mode:
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

    def _setup_user_search_shortcuts(self):
        # Ctrl+F to focus user search
        user_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        user_search_shortcut.activated.connect(self._focus_user_search)

        # Escape to clear user search (when focused)
        clear_user_search_shortcut = QShortcut(QKeySequence("Escape"), self)
        clear_user_search_shortcut.activated.connect(self._clear_user_search_if_focused)

        # F5 to refresh
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._load_users)

        # Enter to edit selected user
        edit_shortcut = QShortcut(QKeySequence("Return"), self)
        edit_shortcut.activated.connect(self._edit_selected_user)