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
    first_name: str
    last_name: str

    def has_admin_privileges(self) -> bool:
        return self.role == UserRole.ADMIN

    def can_access_pacs(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.DOCTOR]

    def get_full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"