from app.config.settings import Settings
from app.config.database import DatabaseConfig

# Infrastructure
from app.infrastructure.http_client import HttpClient
from app.infrastructure.pdf_generator import PdfGenerator

# Repositories
from app.repositories.user_repository import UserRepository

# Services
from app.services.auth_service import AuthService
from app.services.session_service import SessionService
from app.services.pacs_service import PacsService
from app.services.pdf_service import PdfService

# Controllers
from app.presentation.controllers.auth_controller import AuthController
from app.presentation.controllers.pacs_controller import PacsController


class Container:
    _instances = {}

    @classmethod
    def _get_or_create(cls, key: str, factory):
        if key not in cls._instances:
            cls._instances[key] = factory()
        return cls._instances[key]

    @classmethod
    def get_database_config(cls) -> DatabaseConfig:
        return cls._get_or_create('database_config', DatabaseConfig)

    @classmethod
    def get_http_client(cls) -> HttpClient:
        return cls._get_or_create('http_client', lambda: HttpClient(timeout=30))

    @classmethod
    def get_pdf_generator(cls) -> PdfGenerator:
        settings = Settings()
        return cls._get_or_create('pdf_generator', lambda: PdfGenerator(settings.PDF_CSS_PATH))

    @classmethod
    def get_user_repository(cls) -> UserRepository:
        db_config = cls.get_database_config()
        return cls._get_or_create('user_repository', lambda: UserRepository(db_config))

    @classmethod
    def get_auth_service(cls) -> AuthService:
        user_repo = cls.get_user_repository()
        return cls._get_or_create('auth_service', lambda: AuthService(user_repo))

    @classmethod
    def get_session_service(cls) -> SessionService:
        return cls._get_or_create('session_service', SessionService)

    @classmethod
    def get_pacs_service(cls) -> PacsService:
        http_client = cls.get_http_client()
        settings = Settings()
        return cls._get_or_create('pacs_service', lambda: PacsService(
            http_client, settings.PACS_URL, settings.PACS_AUTH
        ))

    @classmethod
    def get_pdf_service(cls) -> PdfService:
        pdf_generator = cls.get_pdf_generator()
        return cls._get_or_create('pdf_service', lambda: PdfService(pdf_generator))

    @classmethod
    def get_auth_controller(cls) -> AuthController:
        auth_service = cls.get_auth_service()
        session_service = cls.get_session_service()
        return cls._get_or_create('auth_controller', lambda: AuthController(auth_service, session_service))

    @classmethod
    def get_pacs_controller(cls) -> PacsController:
        pacs_service = cls.get_pacs_service()
        pdf_service = cls.get_pdf_service()
        return cls._get_or_create('pacs_controller', lambda: PacsController(pacs_service, pdf_service))