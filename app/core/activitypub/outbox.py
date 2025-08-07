from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List

from app.core.database import get_db
from app.models.activitypub import Actor, Activity
from app.core.activitypub.utils import create_activity_object
from app.core.config import settings
from app.core.activitypub.federation import is_public_activity

outbox_router = APIRouter()

@outbox_router.get("/{username}/outbox")
async def get_outbox(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """取得發件匣"""
    # 查詢 Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 查詢活動（TODO: 實作分頁）
    result = await db.execute(
        select(Activity).where(Activity.actor_id == actor.id).order_by(Activity.created_at.desc())
    )
    activities = result.scalars().all()
    
    # 建立活動列表
    activity_list = []
    for activity in activities:
        activity_obj = {
            "id": activity.activity_id,
            "type": activity.activity_type,
            "actor": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}",
            "object": activity.object_data,
            "published": activity.created_at.isoformat() + "Z"
        }
        
        if activity.target_data:
            activity_obj["target"] = activity.target_data
        
        if activity.to:
            activity_obj["to"] = activity.to
        
        if activity.cc:
            activity_obj["cc"] = activity.cc
        
        activity_list.append(activity_obj)
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}/outbox",
        "type": "OrderedCollection",
        "totalItems": len(activity_list),
        "orderedItems": activity_list
    }

@outbox_router.post("/{username}/outbox")
async def create_activity(
    username: str,
    activity_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """建立新活動"""
    # 查詢 Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 驗證活動資料
    activity_type = activity_data.get("type")
    if not activity_type:
        raise HTTPException(status_code=400, detail="Activity type is required")
    
    # 儲存活動
    activity = Activity(
        activity_id=activity_data.get("id"),
        actor_id=actor.id,
        activity_type=activity_type,
        object_data=activity_data.get("object", {}),
        target_data=activity_data.get("target"),
        to=activity_data.get("to"),
        cc=activity_data.get("cc"),
        is_local=True,
        is_public=is_public_activity(activity_data)
    )
    
    db.add(activity)
    await db.commit()
    
    # 發送到其他實例（TODO: 實作聯邦發送）
    # await federate_activity(activity_data)
    
    return {"status": "created", "id": activity.activity_id}
