import os


class Settings:
    # Database settings
    DB_URI = "mysql+pymysql://admin:admin@localhost:3306/medical_app"

    # Default PACS settings (fallback)
    PACS_URL = "http://localhost:8042"
    PACS_AUTH = ("orthanc", "orthanc")
    PACS_URL_2 = "http://localhost:8052"
    PACS_AUTH_2 = ("orthanc", "orthanc")

    # File paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    STYLE_PATH = os.path.join(BASE_DIR, "app", "presentation", "styles", "style.qss")
    PDF_CSS_PATH = os.path.join(BASE_DIR, "app", "presentation", "styles", "pdf_style.css")

    # PDF settings
    PDF_OUTPUT_DIR = "generated_pdfs"
    PDF_PREVIEW_DIR = "tmp_pdfs"

    # Local DICOM file settings
    LOCAL_STUDIES_CACHE_DIR = "local_studies_cache"
    SUPPORTED_DICOM_EXTENSIONS = ['.dcm', '.dicom', '.dic']

    AUTO_CLEANUP_CACHE = True  # Automatically clean up invalid cache entries
    VERIFY_DICOM_FILES = True  # Verify DICOM files before loading

    # Performance settings for local files
    BATCH_LOAD_SIZE = 50  # Number of files to process in each batch
    BACKGROUND_LOADING = True  # Load files in background threads

    # Local file validation settings
    MIN_DICOM_FILE_SIZE = 128  # Minimum file size in bytes to consider as DICOM
    MAX_DICOM_FILE_SIZE = 500 * 1024 * 1024  # Maximum file size (500MB)

    @classmethod
    def get_source_pacs_config(cls):
        """Get source PACS configuration from database settings"""
        try:
            from app.di.container import Container
            settings_service = Container.get_settings_service()
            config = settings_service.get_source_pacs_config()
            if config:
                return config
        except Exception as e:
            print(f"Warning: Could not load source PACS config from database: {e}")

        # Fallback to default
        return cls.PACS_URL, cls.PACS_AUTH

    @classmethod
    def get_target_pacs_config(cls):
        """Get target PACS configuration from database settings"""
        try:
            from app.di.container import Container
            settings_service = Container.get_settings_service()
            config = settings_service.get_target_pacs_config()
            if config:
                return config
        except Exception as e:
            print(f"Warning: Could not load target PACS config from database: {e}")

        # Fallback to secondary PACS
        return cls.PACS_URL_2, cls.PACS_AUTH_2

    @classmethod
    def get_pacs_config(cls):
        """Get primary PACS configuration (same as source)"""
        return cls.get_source_pacs_config()

    @classmethod
    def get_local_cache_path(cls) -> str:
        return os.path.join(cls.BASE_DIR, cls.LOCAL_STUDIES_CACHE_DIR)

    @classmethod
    def ensure_directories(cls):
        directories = [
            cls.PDF_OUTPUT_DIR,
            cls.PDF_PREVIEW_DIR,
            cls.LOCAL_STUDIES_CACHE_DIR,
            os.path.join(cls.PDF_PREVIEW_DIR, "preview")
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    @classmethod
    def is_supported_dicom_extension(cls, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.SUPPORTED_DICOM_EXTENSIONS

    @classmethod
    def get_app_info(cls) -> dict:
        return {
            'app_name': 'Medical PACS System with Local File Support',
            'version': '2.0.0',
            'base_dir': cls.BASE_DIR,
            'pacs_urls': [cls.PACS_URL, cls.PACS_URL_2],
            'pdf_output_dir': cls.PDF_OUTPUT_DIR,
            'local_cache_dir': cls.LOCAL_STUDIES_CACHE_DIR,
            'supported_extensions': cls.SUPPORTED_DICOM_EXTENSIONS
        }