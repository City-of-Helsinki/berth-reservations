from typing import Optional


def is_valid_email(email: Optional[str]) -> bool:
    return email and "@example.com" not in email
