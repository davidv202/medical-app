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
from app.services.local_file_service import LocalFileService
from app.services.hybrid_pacs_service import HybridPacsService
from app.services.pdf_service import PdfService

# Controllers
from app.presentation.controllers.auth_controller import AuthController
from app.presentation.controllers.hybrid_pacs_controller import HybridPacsController


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
    def get_local_file_service(cls) -> LocalFileService:
        settings = Settings()
        cache_dir = getattr(settings, 'LOCAL_STUDIES_CACHE_DIR', 'local_studies_cache')
        return cls._get_or_create('local_file_service', lambda: LocalFileService(cache_dir))

    @classmethod
    def get_hybrid_pacs_service(cls) -> HybridPacsService:
        pacs_service = cls.get_pacs_service()
        local_file_service = cls.get_local_file_service()
        return cls._get_or_create('hybrid_pacs_service', lambda: HybridPacsService(
            pacs_service, local_file_service
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
    def get_pacs_controller(cls) -> HybridPacsController:
        hybrid_pacs_service = cls.get_hybrid_pacs_service()
        pdf_service = cls.get_pdf_service()
        return cls._get_or_create('hybrid_pacs_controller', lambda: HybridPacsController(
            hybrid_pacs_service, pdf_service
        ))

    # Backward compatibility methods
    @classmethod
    def get_hybrid_pacs_controller(cls) -> HybridPacsController:
        return cls.get_pacs_controller()

    @classmethod
    def reset_instances(cls):
        cls._instances.clear()

    @classmethod
    def get_service_info(cls) -> dict:
        info = {
            'loaded_services': list(cls._instances.keys()),
            'local_file_support': 'local_file_service' in cls._instances,
            'hybrid_pacs_support': 'hybrid_pacs_service' in cls._instances,
            'pdf_support': 'pdf_service' in cls._instances
        }

        # Check if pydicom is available
        try:
            import pydicom
            info['pydicom_available'] = True
            info['pydicom_version'] = getattr(pydicom, '__version__', 'unknown')
        except ImportError:
            info['pydicom_available'] = False
            info['pydicom_version'] = None

        return info