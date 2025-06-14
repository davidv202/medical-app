# app/config/settings.py - Updated with Local File Support
import os


class Settings:
    # Database settings
    DB_URI = "mysql+pymysql://admin:admin@localhost:3306/medical_app"

    # PACS settings
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

    # Local file management settings
    MAX_LOCAL_STUDIES = 1000  # Maximum number of local studies to keep in memory
    AUTO_CLEANUP_CACHE = True  # Automatically clean up invalid cache entries
    VERIFY_DICOM_FILES = True  # Verify DICOM files before loading

    # Performance settings for local files
    BATCH_LOAD_SIZE = 50  # Number of files to process in each batch
    BACKGROUND_LOADING = True  # Load files in background threads

    # Local file validation settings
    MIN_DICOM_FILE_SIZE = 128  # Minimum file size in bytes to consider as DICOM
    MAX_DICOM_FILE_SIZE = 500 * 1024 * 1024  # Maximum file size (500MB)

    @classmethod
    def get_local_cache_path(cls) -> str:
        """Get the full path for local studies cache"""
        return os.path.join(cls.BASE_DIR, cls.LOCAL_STUDIES_CACHE_DIR)

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
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
        """Check if file has supported DICOM extension"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.SUPPORTED_DICOM_EXTENSIONS

    @classmethod
    def get_app_info(cls) -> dict:
        """Get application configuration information"""
        return {
            'app_name': 'Medical PACS System with Local File Support',
            'version': '2.0.0',
            'base_dir': cls.BASE_DIR,
            'pacs_urls': [cls.PACS_URL, cls.PACS_URL_2],
            'pdf_output_dir': cls.PDF_OUTPUT_DIR,
            'local_cache_dir': cls.LOCAL_STUDIES_CACHE_DIR,
            'supported_extensions': cls.SUPPORTED_DICOM_EXTENSIONS,
            'max_local_studies': cls.MAX_LOCAL_STUDIES
        }