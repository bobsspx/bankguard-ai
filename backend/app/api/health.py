from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import SessionLocal


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/database")
def database_health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "connected",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )