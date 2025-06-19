from typing import List, Optional, Tuple
from app.repositories.pacs_url_repository import PacsUrlRepository
from app.database.models import PacsUrl


class PacsUrlService:
    def __init__(self, pacs_url_repository: PacsUrlRepository):
        self._pacs_url_repository = pacs_url_repository

    def get_all_pacs_urls(self) -> List[PacsUrl]:
        return self._pacs_url_repository.find_all()

    def get_active_pacs_urls(self) -> List[PacsUrl]:
        return self._pacs_url_repository.find_all_active()

    def get_primary_pacs(self) -> Optional[PacsUrl]:
        return self._pacs_url_repository.find_primary()

    def get_primary_pacs_config(self) -> Tuple[str, Tuple[str, str]]:
        primary = self.get_primary_pacs()
        if primary:
            return primary.url, (primary.username, primary.password)

        # Fallback to first active PACS
        active_pacs = self.get_active_pacs_urls()
        if active_pacs:
            pacs = active_pacs[0]
            return pacs.url, (pacs.username, pacs.password)

        # Ultimate fallback to default
        return "http://localhost:8042", ("orthanc", "orthanc")

    def get_pacs_by_id(self, pacs_id: int) -> Optional[PacsUrl]:
        return self._pacs_url_repository.find_by_id(pacs_id)

    def get_pacs_config_by_id(self, pacs_id: int) -> Optional[Tuple[str, Tuple[str, str]]]:
        pacs = self.get_pacs_by_id(pacs_id)
        if pacs and pacs.is_active:
            return pacs.url, (pacs.username, pacs.password)
        return None

    def create_pacs_url(self, name: str, url: str, username: str, password: str, is_active: bool = True, is_primary: bool = False) -> PacsUrl:

        if not all([name.strip(), url.strip(), username.strip(), password.strip()]):
            raise ValueError("All fields (name, url, username, password) are required")

        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        if is_primary:
            self._unset_all_primary()

        existing_pacs = self.get_all_pacs_urls()
        if not existing_pacs:
            is_primary = True
            is_active = True

        pacs_url = PacsUrl(
            name=name.strip(),
            url=url.strip().rstrip('/'),
            username=username.strip(),
            password=password.strip(),
            is_active=is_active,
            is_primary=is_primary
        )

        return self._pacs_url_repository.create(pacs_url)

    def update_pacs_url(self, pacs_id: int, name: str, url: str, username: str,
                        password: str, is_active: bool, is_primary: bool) -> bool:

        pacs_url = self._pacs_url_repository.find_by_id(pacs_id)
        if not pacs_url:
            return False

        if not all([name.strip(), url.strip(), username.strip(), password.strip()]):
            raise ValueError("All fields (name, url, username, password) are required")

        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        if is_primary and not pacs_url.is_primary:
            self._unset_all_primary()

        if pacs_url.is_primary and not is_active:
            other_active = [p for p in self.get_active_pacs_urls() if p.id != pacs_id]
            if not other_active:
                raise ValueError("Cannot disable the primary PACS when it's the only active one")

        pacs_url.name = name.strip()
        pacs_url.url = url.strip().rstrip('/')
        pacs_url.username = username.strip()
        pacs_url.password = password.strip()
        pacs_url.is_active = is_active
        pacs_url.is_primary = is_primary

        self._pacs_url_repository.update(pacs_url)
        return True

    def delete_pacs_url(self, pacs_id: int) -> bool:
        pacs_url = self._pacs_url_repository.find_by_id(pacs_id)
        if not pacs_url:
            return False

        if pacs_url.is_primary:
            other_active = [p for p in self.get_active_pacs_urls() if p.id != pacs_id]
            if not other_active:
                raise ValueError("Cannot delete the primary PACS when it's the only active one")

        if pacs_url.is_primary:
            other_active = [p for p in self.get_active_pacs_urls() if p.id != pacs_id]
            if other_active:
                self.set_primary_pacs(other_active[0].id)

        return self._pacs_url_repository.delete(pacs_id)

    def set_primary_pacs(self, pacs_id: int) -> bool:
        pacs_url = self._pacs_url_repository.find_by_id(pacs_id)
        if not pacs_url:
            return False

        if not pacs_url.is_active:
            pacs_url.is_active = True
            self._pacs_url_repository.update(pacs_url)

        return self._pacs_url_repository.set_primary(pacs_id)

    def toggle_active_status(self, pacs_id: int) -> bool:
        pacs_url = self._pacs_url_repository.find_by_id(pacs_id)
        if not pacs_url:
            return False

        if pacs_url.is_primary and pacs_url.is_active:
            other_active = [p for p in self.get_active_pacs_urls() if p.id != pacs_id]
            if not other_active:
                raise ValueError("Cannot deactivate the primary PACS when it's the only active one")

        pacs_url.is_active = not pacs_url.is_active
        self._pacs_url_repository.update(pacs_url)
        return True

    def activate_pacs(self, pacs_id: int) -> bool:
        pacs_url = self._pacs_url_repository.find_by_id(pacs_id)
        if not pacs_url:
            return False

        pacs_url.is_active = True
        self._pacs_url_repository.update(pacs_url)
        return True

    def deactivate_pacs(self, pacs_id: int) -> bool:
        pacs_url = self._pacs_url_repository.find_by_id(pacs_id)
        if not pacs_url:
            return False

        if pacs_url.is_primary:
            other_active = [p for p in self.get_active_pacs_urls() if p.id != pacs_id]
            if not other_active:
                raise ValueError("Cannot deactivate the primary PACS when it's the only active one")

        pacs_url.is_active = False
        self._pacs_url_repository.update(pacs_url)
        return True

    def test_pacs_connection(self, pacs_id: int) -> bool:
        pacs_config = self.get_pacs_config_by_id(pacs_id)
        if not pacs_config:
            return False

        url, (username, password) = pacs_config

        try:
            from app.infrastructure.http_client import HttpClient
            client = HttpClient(timeout=10)
            response = client.get(f"{url}/system", auth=(username, password))
            return response.status_code == 200
        except Exception:
            return False

    def get_target_pacs_options(self) -> List[Tuple[int, str]]:
        active_pacs = self.get_active_pacs_urls()
        return [(pacs.id, f"{pacs.name} ({pacs.url})") for pacs in active_pacs]

    def validate_pacs_data(self, name: str, url: str, username: str, password: str) -> List[str]:
        errors = []

        if not name.strip():
            errors.append("Name is required")
        elif len(name.strip()) > 255:
            errors.append("Name must be less than 255 characters")

        if not url.strip():
            errors.append("URL is required")
        elif not url.startswith(('http://', 'https://')):
            errors.append("URL must start with http:// or https://")
        elif len(url.strip()) > 512:
            errors.append("URL must be less than 512 characters")

        if not username.strip():
            errors.append("Username is required")
        elif len(username.strip()) > 100:
            errors.append("Username must be less than 100 characters")

        if not password.strip():
            errors.append("Password is required")
        elif len(password.strip()) > 255:
            errors.append("Password must be less than 255 characters")

        return errors

    def get_pacs_statistics(self) -> dict:
        all_pacs = self.get_all_pacs_urls()
        active_pacs = self.get_active_pacs_urls()
        primary_pacs = self.get_primary_pacs()

        return {
            'total_pacs': len(all_pacs),
            'active_pacs': len(active_pacs),
            'inactive_pacs': len(all_pacs) - len(active_pacs),
            'has_primary': primary_pacs is not None,
            'primary_pacs_name': primary_pacs.name if primary_pacs else None,
            'primary_pacs_url': primary_pacs.url if primary_pacs else None
        }

    def ensure_primary_pacs_exists(self) -> bool:
        primary = self.get_primary_pacs()
        if primary:
            return True

        active_pacs = self.get_active_pacs_urls()
        if active_pacs:
            return self.set_primary_pacs(active_pacs[0].id)

        return False

    def _unset_all_primary(self):
        all_pacs = self.get_all_pacs_urls()
        for pacs in all_pacs:
            if pacs.is_primary:
                pacs.is_primary = False
                self._pacs_url_repository.update(pacs)