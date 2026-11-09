from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend import config
from backend.db import repository
from backend.errors import (
    APIError,
    AUTH_UNAVAILABLE,
    NOT_INVITED,
    UNAUTHORIZED,
)

_bearer = HTTPBearer(auto_error=False)
_jwks_client: jwt.PyJWKClient | None = None


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    role: str | None
    token: str


def auth_required() -> bool:
    return config.DATABASE_BACKEND == "supabase"


def _jwks() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not config.SUPABASE_URL:
            raise APIError(
                503,
                AUTH_UNAVAILABLE,
                "Supabase auth is not configured. Set SUPABASE_URL.",
            )
        _jwks_client = jwt.PyJWKClient(config.SUPABASE_JWKS_URL, cache_keys=True)
    return _jwks_client


def verify_token(token: str) -> CurrentUser:
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError as exc:
        raise APIError(401, UNAUTHORIZED, "Your session is invalid or expired.") from exc

    if algorithm == "HS256" and config.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                config.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError as exc:
            raise APIError(
                401, UNAUTHORIZED, "Your session is invalid or expired."
            ) from exc
    else:
        try:
            signing_key = _jwks().get_signing_key_from_jwt(token)
        except APIError:
            raise
        except Exception as exc:
            raise APIError(
                503,
                AUTH_UNAVAILABLE,
                "Could not reach the Supabase authentication service.",
            ) from exc

        try:
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError as exc:
            raise APIError(
                401, UNAUTHORIZED, "Your session is invalid or expired."
            ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise APIError(401, UNAUTHORIZED, "Your session is missing a user id.")
    return CurrentUser(
        id=str(user_id),
        email=payload.get("email"),
        role=payload.get("role"),
        token=token,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser | None:
    if not auth_required():
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(401, UNAUTHORIZED, "Sign in to continue.")
    user = verify_token(credentials.credentials)
    if not repository.is_allowed_user(user.email, user.token):
        raise APIError(
            403,
            NOT_INVITED,
            "This Google account has not been invited to BankSense.",
        )
    return user
