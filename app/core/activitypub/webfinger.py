from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import re

from app.core.database import get_db
from app.models.activitypub import Actor
from app.core.config import settings

webfinger_router = APIRouter()

async def handle_webfinger(resource: str) -> Dict[str, Any]:
    """處理 WebFinger 請求"""
    # 解析資源 URI
    # 格式: acct:username@domain
    match = re.match(r'^acct:([^@]+)@(.+)$', resource)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid resource format")
    
    username, domain = match.groups()
    
    # 檢查域名是否匹配
    if domain != settings.ACTIVITYPUB_DOMAIN:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # 查詢 Actor
    async with AsyncSession() as db:
        result = await db.execute(
            select(Actor).where(Actor.username == username)
        )
        actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 建立 WebFinger 回應
    actor_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}"
    
    return {
        "subject": resource,
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": actor_id
            },
            {
                "rel": "http://webfinger.net/rel/profile-page",
                "type": "text/html",
                "href": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}"
            },
            {
                "rel": "http://schemas.google.com/g/2010#updates-from",
                "type": "application/atom+xml",
                "href": f"{actor_id}/outbox"
            }
        ]
    }
