from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.core.entities.patient import Patient
from app.core.interfaces.pacs_interface import IPacsService
from app.core.exceptions.pacs_exceptions import PacsConnectionError, PacsDataError


class PatientService:
    def __init__(self, pacs_service: IPacsService):
        self._pacs_service = pacs_service
        self._patients_cache: Dict[str, Patient] = {}
        self._last_sync_time: Optional[str] = None

    def get_all_patients(self) -> List[Patient]:
        """Get all patients extracted from PACS studies"""
        try:
            print("📊 PatientService: Extracting patients from PACS studies...")

            # Get all studies from PACS
            study_ids = self._pacs_service.get_all_studies()
            print(f"📊 Found {len(study_ids)} studies in PACS")

            # Group studies by patient
            patients_data = defaultdict(list)

            for study_id in study_ids:
                try:
                    metadata = self._pacs_service.get_study_metadata(study_id)

                    # Extract patient identifier (use Patient ID if available, else Patient Name)
                    patient_id = metadata.get("Patient ID", "").strip()
                    patient_name = metadata.get("Patient Name", "Unknown").strip()

                    # Use Patient ID if available, otherwise use Patient Name as identifier
                    identifier = patient_id if patient_id and patient_id != "N/A" else patient_name

                    if identifier and identifier != "Unknown":
                        patients_data[identifier].append({
                            'study_id': study_id,
                            'metadata': metadata
                        })

                except Exception as e:
                    print(f"Warning: Could not extract patient from study {study_id}: {e}")
                    continue

            # Convert to Patient objects
            patients = []
            for patient_identifier, studies in patients_data.items():
                try:
                    patient = self._create_patient_from_studies(patient_identifier, studies)
                    patients.append(patient)
                except Exception as e:
                    print(f"Warning: Could not create patient {patient_identifier}: {e}")
                    continue

            # Update cache
            self._patients_cache = {p.patient_id: p for p in patients}

            print(f"📊 Extracted {len(patients)} unique patients from PACS")
            return patients

        except Exception as e:
            raise PacsConnectionError(f"Could not extract patients from PACS: {e}")

    def search_patients(self, query: str) -> List[Patient]:
        """Search patients by name or ID"""
        if not query.strip():
            return self.get_all_patients()

        query_lower = query.lower().strip()
        all_patients = self.get_all_patients()

        filtered_patients = []
        for patient in all_patients:
            # Search in name
            if query_lower in patient.get_formatted_name().lower():
                filtered_patients.append(patient)
                continue

            # Search in patient ID
            if query_lower in patient.patient_id.lower():
                filtered_patients.append(patient)
                continue

        return filtered_patients

    def get_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        """Get specific patient by ID"""
        if patient_id in self._patients_cache:
            return self._patients_cache[patient_id]

        # If not in cache, try to find in all patients
        all_patients = self.get_all_patients()
        for patient in all_patients:
            if patient.patient_id == patient_id:
                return patient

        return None

    def get_patient_studies(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all studies for a specific patient"""
        try:
            patient_studies = []
            study_ids = self._pacs_service.get_all_studies()

            for study_id in study_ids:
                try:
                    metadata = self._pacs_service.get_study_metadata(study_id)

                    # Check if this study belongs to the patient
                    study_patient_id = metadata.get("Patient ID", "").strip()
                    study_patient_name = metadata.get("Patient Name", "").strip()

                    # Match by Patient ID or Patient Name
                    study_identifier = study_patient_id if study_patient_id and study_patient_id != "N/A" else study_patient_name

                    if study_identifier == patient_id:
                        patient_studies.append({
                            'study_id': study_id,
                            'metadata': metadata,
                            'patient_name': study_patient_name,
                            'study_date': metadata.get("Study Date", "Unknown"),
                            'description': metadata.get("Description", "Unknown"),
                            'display_text': f"{study_patient_name} - {metadata.get('Study Date', 'Unknown')} - {metadata.get('Description', 'Unknown')}"
                        })

                except Exception as e:
                    print(f"Warning: Could not process study {study_id} for patient {patient_id}: {e}")
                    continue

            # Sort by study date (newest first)
            patient_studies.sort(key=lambda x: x['metadata'].get('Study Date', ''), reverse=True)

            return patient_studies

        except Exception as e:
            raise PacsDataError(f"Could not get studies for patient {patient_id}: {e}")

    def get_patients_statistics(self) -> Dict[str, Any]:
        """Get statistics about patients"""
        try:
            patients = self.get_all_patients()

            total_patients = len(patients)
            total_studies = sum(p.studies_count for p in patients)

            # Gender distribution
            gender_stats = {"M": 0, "F": 0, "Unknown": 0}
            for patient in patients:
                gender = patient.sex if patient.sex in ["M", "F"] else "Unknown"
                gender_stats[gender] += 1

            # Age groups (approximate)
            age_groups = {"0-18": 0, "19-40": 0, "41-65": 0, "65+": 0, "Unknown": 0}
            for patient in patients:
                age = patient.get_age()
                if age is None:
                    age_groups["Unknown"] += 1
                elif age <= 18:
                    age_groups["0-18"] += 1
                elif age <= 40:
                    age_groups["19-40"] += 1
                elif age <= 65:
                    age_groups["41-65"] += 1
                else:
                    age_groups["65+"] += 1

            return {
                "total_patients": total_patients,
                "total_studies": total_studies,
                "average_studies_per_patient": total_studies / total_patients if total_patients > 0 else 0,
                "gender_distribution": gender_stats,
                "age_distribution": age_groups,
                "last_sync": self._last_sync_time
            }

        except Exception as e:
            print(f"Error getting patient statistics: {e}")
            return {
                "total_patients": 0,
                "total_studies": 0,
                "average_studies_per_patient": 0,
                "gender_distribution": {"M": 0, "F": 0, "Unknown": 0},
                "age_distribution": {"0-18": 0, "19-40": 0, "41-65": 0, "65+": 0, "Unknown": 0},
                "last_sync": None
            }

    def refresh_patients(self) -> bool:
        """Refresh patients data from PACS"""
        try:
            self._patients_cache.clear()
            self.get_all_patients()
            return True
        except Exception as e:
            print(f"Error refreshing patients: {e}")
            return False

    def _create_patient_from_studies(self, patient_identifier: str, studies: List[Dict[str, Any]]) -> Patient:
        """Create Patient object from list of studies"""
        if not studies:
            raise ValueError("No studies provided for patient")

        # Use the first study as primary source for patient data
        primary_study = studies[0]['metadata']

        # Extract patient data
        patient_name = primary_study.get("Patient Name", "Unknown")
        birth_date = primary_study.get("Patient Birth Date", "")
        sex = primary_study.get("Patient Sex", "")

        # Clean up birth date
        if birth_date and birth_date != "N/A":
            # Convert DICOM date format YYYYMMDD to YYYY-MM-DD
            if len(birth_date) == 8 and birth_date.isdigit():
                birth_date = f"{birth_date[:4]}-{birth_date[4:6]}-{birth_date[6:8]}"
        else:
            birth_date = None

        # Clean up sex
        if sex == "N/A" or not sex:
            sex = None

        # Find latest study date
        study_dates = []
        for study in studies:
            study_date = study['metadata'].get("Study Date", "")
            if study_date and study_date != "N/A":
                study_dates.append(study_date)

        last_study_date = max(study_dates) if study_dates else None

        return Patient(
            patient_id=patient_identifier,
            name=patient_name,
            birth_date=birth_date,
            sex=sex,
            studies_count=len(studies),
            last_study_date=last_study_date,
            pacs_source="PACS"
        )