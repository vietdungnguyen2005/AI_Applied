import base64
import hashlib
import re
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Request
from sqlalchemy import BigInteger, String, Uuid, insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from vmarket_ai.database import Base
from vmarket_ai.gateway.wire import GatewayError, strict_json, validate


class Nonce(Base):
    __tablename__ = "request_nonces"
    kid: Mapped[str] = mapped_column(String(32), primary_key=True)
    nonce: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    expires_at: Mapped[int] = mapped_column(BigInteger)


def digest(method: str, path: str, body: bytes) -> str:
    lines = [
        "vmarket-ai-request:v1",
        method,
        path,
        "application/json",
        *([""] * 7),
        hashlib.sha256(body).hexdigest(),
    ]
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def decode(value: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError
    result = base64.b64decode(value + "=" * ((-len(value)) % 4), altchars=b"-_", validate=True)
    if base64.urlsafe_b64encode(result).decode().rstrip("=") != value:
        raise ValueError
    return result


class ContextVerifier:
    def __init__(self, engine: Engine, keys: dict[str, str]) -> None:
        self.engine, self.keys = engine, keys

    async def verify(self, request: Request, operation: str) -> dict[str, Any]:
        try:
            values = {}
            for name in (b"x-ai-context", b"x-ai-signature"):
                parts = [v for k, v in request.scope["headers"] if k.lower() == name]
                if len(parts) != 1:
                    raise ValueError
                values[name] = parts[0].decode("ascii")
            encoded, signature = values[b"x-ai-context"], values[b"x-ai-signature"]
            if not 1 <= len(encoded) <= 4096 or len(signature) != 86:
                raise ValueError
            claims = strict_json(decode(encoded))
            validate("SignedContext", claims)
            key = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(self.keys[claims["kid"]], validate=True)
            )
            key.verify(decode(signature), b"vmarket-ai-context:v1." + encoded.encode())
            now = time.time()
            deadline = datetime.fromisoformat(
                claims["deadline_at"].replace("Z", "+00:00")
            ).timestamp()
            if not (
                0 <= now - claims["issued_at"] <= 30
                and claims["issued_at"] <= claims["expires_at"] <= claims["issued_at"] + 30
                and now < claims["expires_at"] <= deadline
                and now < deadline
            ):
                raise ValueError
            if request.url.query or request.scope.get("raw_path") != request.url.path.encode():
                raise ValueError
            if request.headers.get("content-type") != "application/json":
                raise ValueError
            if any(
                k.lower().startswith((b"x-source-", b"x-doc-")) or k.lower() == b"x-vendor-code"
                for k, v in request.scope["headers"]
            ):
                raise ValueError
            if any(
                k.lower()
                in {
                    b"cookie",
                    b"authorization",
                    b"x-csrf-token",
                    b"x-v-market-bff-secret",
                    b"x-v-market-ops-secret",
                }
                for k, v in request.scope["headers"]
            ):
                raise ValueError
            if claims["request_digest"] != digest(
                request.method, request.url.path, await request.body()
            ):
                raise ValueError
            if claims["request_id"] != request.state.request_id or claims["operation"] != operation:
                raise ValueError
            with self.engine.begin() as c:
                c.execute(
                    insert(Nonce).values(
                        kid=claims["kid"],
                        nonce=UUID(claims["nonce"]),
                        expires_at=claims["expires_at"],
                    )
                )
            return dict(claims)
        except IntegrityError:
            raise GatewayError("CONTEXT_REPLAY", 409) from None
        except SQLAlchemyError:
            raise GatewayError("DEPENDENCY_UNAVAILABLE", 503) from None
        except (ValueError, KeyError, TypeError, InvalidSignature, GatewayError):
            raise GatewayError("CONTEXT_INVALID", 401) from None
