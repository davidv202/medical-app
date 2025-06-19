from typing import Optional, List

from sqlalchemy.exc import SQLAlchemyError

from app.database.models import PacsUrl
from app.repositories.base_repository import BaseRepository


class PacsUrlRepository(BaseRepository[PacsUrl]):

    def find_by_id(self, entity_id: int) -> Optional[PacsUrl]:
        session = self._get_session()
        try:
            return session.query(PacsUrl).filter_by(id=entity_id).first()
        finally:
            session.close()

    def create(self, entity: PacsUrl) -> PacsUrl:
        session = self._get_session()
        try:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update(self, entity: PacsUrl) -> PacsUrl:
        session = self._get_session()
        try:
            session.merge(entity)
            session.commit()
            return entity
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete(self, entity_id: int) -> bool:
        session = self._get_session()
        try:
            pacs_url = session.query(PacsUrl).filter_by(id=entity_id).first()
            if not pacs_url:
                return False
            session.delete(pacs_url)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def find_all(self) -> List[PacsUrl]:
        session = self._get_session()
        try:
            return session.query(PacsUrl).all()
        finally:
            session.close()

    def find_all_active(self) -> List[PacsUrl]:
        session = self._get_session()
        try:
            return session.query(PacsUrl).filter_by(is_active=True).all()
        finally:
            session.close()

    def find_primary(self) -> Optional[PacsUrl]:
        session = self._get_session()
        try:
            return session.query(PacsUrl).filter_by(is_primary=True, is_active=True).first()
        finally:
            session.close()

    def set_primary(self, pacs_id: int) -> bool:
        session = self._get_session()
        try:
            # First, unset all primary flags
            session.query(PacsUrl).update({PacsUrl.is_primary: False})

            # Then set the new primary
            pacs_url = session.query(PacsUrl).filter_by(id=pacs_id).first()
            if not pacs_url:
                return False

            pacs_url.is_primary = True
            pacs_url.is_active = True  # Ensure primary is also active
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()