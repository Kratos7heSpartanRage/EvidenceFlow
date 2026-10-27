"""Health check endpoint checking database connectivity."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db, utc_now

router = APIRouter(tags=["Health"])


@router.get("/health", summary="System Health and Database Connectivity")
def get_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1")).scalar()
        db_status = "connected"
    except SQLAlchemyError:
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "version": "0.1.0",
        "time": utc_now().isoformat(),
    }
