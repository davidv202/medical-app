import re
from typing import Optional


class Validators:
    @staticmethod
    def validate_username(username: str) -> Optional[str]:
        if not username:
            return "Username is required"
        if len(username) < 3:
            return "Username must be at least 3 characters long"
        if len(username) > 50:
            return "Username must be less than 50 characters"
        return None

    @staticmethod
    def validate_password(password: str) -> Optional[str]:
        if not password:
            return "Password is required"
        if len(password) < 6:
            return "Password must be at least 6 characters long"
        return None
