import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_is_hashed_and_verifiable():
    hashed = hash_password("StrongPass123")
    assert hashed != "StrongPass123"
    assert hashed.startswith("$argon2")
    assert verify_password("StrongPass123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_same_password_gives_different_hashes():
    assert hash_password("StrongPass123") != hash_password("StrongPass123")


def test_token_roundtrip():
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_token_is_rejected():
    assert decode_access_token(create_access_token(42, expires_minutes=-1)) is None


def test_garbage_and_tampered_tokens_are_rejected():
    assert decode_access_token("not-a-token") is None
    forged = jwt.encode(
        {"sub": "1"},
        "another-secret-key-that-is-long-enough-32b",
        algorithm=settings.algorithm,
    )
    assert decode_access_token(forged) is None
