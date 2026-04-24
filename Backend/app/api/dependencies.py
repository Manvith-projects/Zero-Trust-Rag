from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from app.core.security import Auth0Verifier
from app.domain import AuthenticatedUser
from app.services.rag import SecureRAGService


def get_auth_verifier(request: Request) -> Auth0Verifier:
    verifier = getattr(request.app.state, "auth_verifier", None)
    if verifier is None:
        raise RuntimeError("Auth verifier is not configured")
    return verifier


def get_rag_service(request: Request) -> SecureRAGService:
    service = getattr(request.app.state, "rag_service", None)
    if service is None:
        raise RuntimeError("RAG service is not configured")
    return service


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verifier = get_auth_verifier(request)
    try:
        return verifier.verify(token)
    except Exception as exc:  # pragma: no cover - security boundary, asserted in tests
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
