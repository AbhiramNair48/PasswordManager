import base64
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

__all__ = [
    "generate_salt",
    "derive_key",
    "encrypt",
    "decrypt",
    "verify_master_password",
    "InvalidToken",
]

_PBKDF2_ITERATIONS = 480_000
_SENTINEL = "vault-ok"


def generate_salt() -> bytes:
    return os.urandom(16)


def derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def encrypt(plaintext: str, key: bytes) -> str:
    return Fernet(key).encrypt(plaintext.encode()).decode()


def decrypt(token: str, key: bytes) -> str:
    return Fernet(key).decrypt(token.encode()).decode()


def make_verification_token(key: bytes) -> str:
    return encrypt(_SENTINEL, key)


def verify_master_password(stored_token: str, key: bytes) -> bool:
    try:
        return decrypt(stored_token, key) == _SENTINEL
    except InvalidToken:
        return False
