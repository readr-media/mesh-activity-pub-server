from fastapi import APIRouter
from app.core.activitypub.actor import actor_router
from app.core.activitypub.inbox import inbox_router
from app.core.activitypub.webfinger import webfinger_router
from app.core.activitypub.nodeinfo import nodeinfo_router

# routers
users_router = APIRouter()
well_known_router = APIRouter()

# 將 users/inbox 置於站台根目錄
users_router.include_router(actor_router, prefix="/users")
users_router.include_router(inbox_router, prefix="/inbox")

# 僅在 .well-known 底下提供標準發現端點
# /.well-known 子路徑需指定前綴，避免空字串路由衝突
well_known_router.include_router(webfinger_router)
well_known_router.include_router(nodeinfo_router, prefix="/nodeinfo")
