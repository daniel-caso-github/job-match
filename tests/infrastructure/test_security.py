from __future__ import annotations

import pytest

from src.infrastructure.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("mipassword")
    assert verify_password("mipassword", hashed)


def test_verify_rejects_wrong_password():
    hashed = hash_password("correcto")
    assert not verify_password("incorrecto", hashed)


def test_hash_is_not_plaintext():
    plain = "secret"
    hashed = hash_password(plain)
    assert plain not in hashed
    assert hashed.startswith("$2b$")


def test_create_and_decode_token():
    token = create_access_token("uuid-123", "daniel-test")
    payload = decode_access_token(token)
    assert payload["sub"] == "uuid-123"
    assert payload["username"] == "daniel-test"
    assert "exp" in payload


def test_decode_rejects_tampered_token():
    import jwt as pyjwt

    token = create_access_token("uuid-123", "daniel-test")
    # Modifica el último carácter para invalidar la firma.
    bad_token = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(pyjwt.exceptions.InvalidSignatureError):
        decode_access_token(bad_token)
