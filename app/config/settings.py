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