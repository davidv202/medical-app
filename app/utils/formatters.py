import re
from datetime import datetime
from typing import Dict, Any


class Formatters:
    @staticmethod
    def format_filename(patient_name: str, study_date: str, timestamp: str = None) -> str:
        """Format a safe filename for PDF generation"""
        safe_name = re.sub(r'\W+', '_', patient_name)
        safe_date = study_date.replace("-", "")

        if timestamp is None:
            timestamp = datetime.now().strftime("%H%M%S")

        return f"{safe_name}_{safe_date}_{timestamp}.pdf"

    @staticmethod
    def format_study_display_text(patient_name: str, study_date: str, description: str) -> str:
        """Format study information for display in lists"""
        return f"{patient_name} - {study_date} - {description}"

    @staticmethod
    def format_metadata_display(metadata: Dict[str, Any]) -> str:
        """Format metadata for display in text widgets"""
        formatted_items = []
        display_names = {
            "Patient Name": "Nume pacient",
            "Patient Birth Date": "Data nasterii",
            "Patient Sex": "Sex",
            "Study Date": "Data efectuarii studiului",
            "Description": "Descriere",
            "Study Instance UID": "ID Instanta",
            "Series Status": "Status serie"
        }

        for key, value in metadata.items():
            display_name = display_names.get(key, key)
            formatted_items.append(f"{display_name}: {value}")

        return "\n".join(formatted_items)

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Basic HTML sanitization for PDF generation"""
        return text.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')