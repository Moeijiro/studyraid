from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import Session
from app.core.config import get_settings
from app.engine.progression import total_xp_for_level, xp_to_next

router = APIRouter(prefix="/system", tags=["system"])

DEMO_EMAIL = "maks@studyraid.dev"
DEMO_PASSWORD = "raid-demo-2026"  # noqa: S105 - public demo account, shown only with DEMO_MODE


@router.get("/health")
async def health(session: Session) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/info")
async def info() -> dict[str, Any]:
    settings = get_settings()
    return {
        "name": "StudyRaid",
        "registration": settings.allow_registration,
        "demo": {"email": DEMO_EMAIL, "password": DEMO_PASSWORD} if settings.demo_mode else None,
        "level_curve": [{"level": lv, "total_xp": total_xp_for_level(lv), "to_next": xp_to_next(lv)} for lv in range(1, 31)],
    }
