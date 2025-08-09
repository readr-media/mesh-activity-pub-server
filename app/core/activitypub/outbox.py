from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.core.graphql_client import GraphQLClient
from app.core.config import settings
from app.core.activitypub.federation import is_public_activity

outbox_router = APIRouter()

# 保留路由容器，以後若有需要擴充專用 API 可再啟用；
# 目前 /users/{username}/outbox 由 actor_router 提供，避免路由重疊
