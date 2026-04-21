"""
Keycloak JWT verification untuk E-Ticket backend.
Menggantikan local auth (username/password Oracle) dengan validasi JWT dari Keycloak.
"""

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.config import get_settings

settings = get_settings()

KEYCLOAK_URL  = settings.KEYCLOAK_URL
REALM         = settings.KEYCLOAK_REALM
CLIENT_ID     = settings.KEYCLOAK_CLIENT_ID
ISSUER        = f"{KEYCLOAK_URL}/realms/{REALM}"
CERTS_URL     = f"{ISSUER}/protocol/openid-connect/certs"

_jwks_cache = None


class KeycloakUser(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[str] = []


def _fetch_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        try:
            resp = httpx.get(CERTS_URL, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
        except Exception as e:
            raise HTTPException(503, f"Tidak bisa mengambil Keycloak public keys: {e}")
    return _jwks_cache


def _clear_jwks_cache():
    global _jwks_cache
    _jwks_cache = None


def verify_token(token: str) -> KeycloakUser:
    """
    Verifikasi Keycloak JWT token.
    Mendukung key rotation: otomatis clear cache dan retry saat JWTError.
    """
    def _decode(jwks):
        return jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience="account",
            issuer=ISSUER,
            options={"verify_exp": True, "verify_iss": True, "verify_aud": True},
        )

    try:
        payload = _decode(_fetch_jwks())
    except JWTError:
        _clear_jwks_cache()
        try:
            payload = _decode(_fetch_jwks())
        except JWTError as e:
            raise HTTPException(
                401,
                f"Token tidak valid: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    client_roles = (
        payload.get("resource_access", {})
        .get(CLIENT_ID, {})
        .get("roles", [])
    )

    return KeycloakUser(
        id=payload["sub"],
        username=payload.get("preferred_username", ""),
        email=payload.get("email"),
        name=payload.get("name"),
        first_name=payload.get("given_name"),
        last_name=payload.get("family_name"),
        roles=client_roles,
    )
