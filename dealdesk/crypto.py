"""Encrypt OAuth tokens at rest.

We hold credentials to people's livelihoods. Tokens never touch the database
in plaintext.
"""
from cryptography.fernet import Fernet
from flask import current_app


def _fernet() -> Fernet:
    key = current_app.config["TOKEN_ENCRYPTION_KEY"]
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set; see .env.example")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().decrypt(value.encode()).decode()
