from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import json

from app.core.database import get_db
from app.models.activitypub import Actor, InboxItem
from app.core.activitypub.processor import process_activity

inbox_router = APIRouter()

@inbox_router.post("/{username}/inbox")
async def receive_activity(
    username: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """接收 ActivityPub 活動"""
    # 查詢本地 Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 讀取請求內容
    try:
        activity_data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # 驗證簽名（TODO: 實作簽名驗證）
    # await verify_signature(request, activity_data)
    
    # 儲存到收件匣
    inbox_item = InboxItem(
        activity_id=activity_data.get("id"),
        actor_id=activity_data.get("actor"),
        activity_data=activity_data,
        is_processed=False
    )
    
    db.add(inbox_item)
    await db.commit()
    
    # 非同步處理活動
    try:
        await process_activity(activity_data, db)
        inbox_item.is_processed = True
        await db.commit()
    except Exception as e:
        # 記錄錯誤但不要讓請求失敗
        print(f"Error processing activity: {e}")
    
    return {"status": "accepted"}
