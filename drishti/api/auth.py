"""API-key authentication. Keys are shown once at creation and stored only as salted hashes.

On Cloud Run you can instead put the service behind Identity-Aware Proxy / IAM and set
`DRISHTI_AUTH=iam`, which trusts the `X-Goog-Authenticated-User-Email` header added by IAP
(only safe when the service is not publicly invokable).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select

from drishti.config import get_settings
from drishti.db.models import ApiKey
from drishti.db.session import session_scope


def hash_key(key: str) -> str:
    pepper = get_settings().api_key_pepper
    return hashlib.sha256(f"{pepper}:{key}".encode()).hexdigest()


def create_key(name: str, role: str = "analyst") -> str:
    key = "dk_" + secrets.token_urlsafe(32)
    with session_scope() as db:
        db.add(ApiKey(name=name, key_hash=hash_key(key), role=role))
    return key


class Principal:
    def __init__(self, name: str, role: str):
        self.name, self.role = name, role


async def require_key(request: Request, x_api_key: str | None = Header(default=None)) -> Principal:
    if os.getenv("DRISHTI_AUTH") == "iam":
        email = request.headers.get("x-goog-authenticated-user-email", "")
        if not email:
            raise HTTPException(401, "missing IAP identity")
        return Principal(email.split(":")[-1], "analyst")
    if not x_api_key:
        raise HTTPException(401, "missing X-API-Key")
    digest = hash_key(x_api_key)
    with session_scope() as db:
        row = db.scalar(select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.revoked == 0))
        if row is None or not hmac.compare_digest(row.key_hash, digest):
            raise HTTPException(401, "invalid API key")
        return Principal(row.name, row.role)


def require_admin(p: Principal = Depends(require_key)) -> Principal:
    if p.role != "admin":
        raise HTTPException(403, "admin role required")
    return p


if __name__ == "__main__":  # python -m drishti.api.auth <name> [role]
    import sys

    from drishti.db.session import init_db

    init_db()
    print(create_key(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "analyst"))
