import pytest
from cryptography.fernet import InvalidToken

from password_manager.crypto import (
    decrypt,
    derive_key,
    encrypt,
    generate_salt,
    make_verification_token,
    verify_master_password,
)


def test_generate_salt_returns_16_bytes():
    salt = generate_salt()
    assert isinstance(salt, bytes)
    assert len(salt) == 16


def test_generate_salt_is_random():
    assert generate_salt() != generate_salt()


def test_derive_key_is_deterministic():
    salt = generate_salt()
    key1 = derive_key("my-password", salt)
    key2 = derive_key("my-password", salt)
    assert key1 == key2


def test_derive_key_differs_by_password():
    salt = generate_salt()
    assert derive_key("password-a", salt) != derive_key("password-b", salt)


def test_derive_key_differs_by_salt():
    assert derive_key("same-password", generate_salt()) != derive_key("same-password", generate_salt())


def test_derive_key_returns_bytes():
    key = derive_key("pw", generate_salt())
    assert isinstance(key, bytes)


def test_encrypt_decrypt_round_trip():
    key = derive_key("pw", generate_salt())
    plaintext = "super-secret-password"
    token = encrypt(plaintext, key)
    assert decrypt(token, key) == plaintext


def test_encrypt_produces_different_ciphertext_each_time():
    key = derive_key("pw", generate_salt())
    t1 = encrypt("same", key)
    t2 = encrypt("same", key)
    assert t1 != t2  # Fernet uses a random IV


def test_wrong_key_raises_invalid_token():
    key1 = derive_key("pw1", generate_salt())
    key2 = derive_key("pw2", generate_salt())
    token = encrypt("secret", key1)
    with pytest.raises(InvalidToken):
        decrypt(token, key2)


def test_verify_master_password_correct():
    key = derive_key("master", generate_salt())
    token = make_verification_token(key)
    assert verify_master_password(token, key) is True


def test_verify_master_password_wrong_key():
    key1 = derive_key("correct", generate_salt())
    key2 = derive_key("wrong", generate_salt())
    token = make_verification_token(key1)
    assert verify_master_password(token, key2) is False
