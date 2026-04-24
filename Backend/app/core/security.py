from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.domain import AuthenticatedUser


@dataclass(slots=True)
class Auth0Verifier:
    """Validates Auth0 access tokens against the tenant JWKS endpoint."""

    domain: str
    audience: str
    role_claim: str

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}/"

    @property
    def jwks_url(self) -> str:
        return f"https://{self.domain}/.well-known/jwks.json"

    def verify(self, token: str) -> AuthenticatedUser:
        """Validate signature, issuer, audience, and expiration using Auth0 JWKS."""

        client = PyJWKClient(self.jwks_url)
        signing_key = client.get_signing_key_from_jwt(token)
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
        )

        raw_roles = claims.get(self.role_claim, [])
        if not isinstance(raw_roles, list):
            raw_roles = []
        roles = [role.strip() for role in raw_roles if isinstance(role, str) and role.strip()]
        subject = str(claims.get("sub", ""))
        if not subject:
            raise InvalidTokenError("Token is missing the subject claim")

        return AuthenticatedUser(sub=subject, roles=roles, claims=claims)
