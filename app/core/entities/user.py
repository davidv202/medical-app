from dataclasses import dataclass
from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"


@dataclass
class User:
    id: int
    username: str
    password: str
    role: UserRole

    def has_admin_privileges(self) -> bool:
        return self.role == UserRole.ADMIN

    def can_access_pacs(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.DOCTOR]