from fastapi import APIRouter
from app.core.activitypub.actor import actor_router
from app.core.activitypub.inbox import inbox_router
from app.core.activitypub.outbox import outbox_router
from app.core.activitypub.webfinger import webfinger_router
from app.core.activitypub.nodeinfo import nodeinfo_router

activitypub_router = APIRouter()

# 包含所有 ActivityPub 相關路由
activitypub_router.include_router(actor_router, prefix="/users")
activitypub_router.include_router(inbox_router, prefix="/inbox")
activitypub_router.include_router(outbox_router, prefix="/outbox")
activitypub_router.include_router(webfinger_router, prefix="/webfinger")
activitypub_router.include_router(nodeinfo_router, prefix="/nodeinfo")
