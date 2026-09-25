from fastapi import APIRouter

from app.api.routes import analytics, auth, focus, me, notifications, parties, quests, realtime, system

api_router = APIRouter(prefix="/api")
for module in (auth, me, quests, focus, parties, analytics, notifications, realtime, system):
    api_router.include_router(module.router)
