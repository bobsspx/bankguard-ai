import hashlib
import hmac
from datetime import datetime, timezone

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.login_rate_limit import LoginRateLimit


WINDOW_SECONDS = 300
ACCOUNT_LIMIT = 5
IP_LIMIT = 20


def reserve_login_attempt(
    db: Session, *, email: str, client_ip: str, now: datetime | None = None,
) -> int | None:
    now = now or datetime.now(timezone.utc)
    epoch = int(now.timestamp())
    window_start = epoch - epoch % WINDOW_SECONDS
    retry_after = WINDOW_SECONDS - (epoch - window_start)
    exceeded = False
    try:
        # One transaction serializes updates to each shared bucket across workers.
        for scope, value, limit in (
            ("account", email.strip().casefold(), ACCOUNT_LIMIT),
            ("ip", client_ip, IP_LIMIT),
        ):
            digest = hmac.new(
                settings.jwt_secret.encode(), f"{scope}:{value}".encode(), hashlib.sha256,
            ).hexdigest()
            attempts = db.execute(text("""
                INSERT INTO login_rate_limits (scope, key_hash, window_start, attempts)
                VALUES (:scope, :key_hash, :window_start, 1)
                ON CONFLICT (scope, key_hash, window_start)
                DO UPDATE SET attempts = login_rate_limits.attempts + 1
                RETURNING attempts
            """), {"scope": scope, "key_hash": digest, "window_start": window_start}).scalar_one()
            exceeded |= attempts > limit
        db.execute(delete(LoginRateLimit).where(LoginRateLimit.window_start < window_start))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return retry_after if exceeded else None
