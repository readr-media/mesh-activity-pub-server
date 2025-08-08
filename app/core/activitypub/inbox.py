from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import json

from app.core.activitypub.processor import process_activity
from app.core.graphql_client import GraphQLClient

inbox_router = APIRouter()

@inbox_router.post("/{username}/inbox")
async def receive_activity(username: str, request: Request):
    """接收 ActivityPub 活動"""
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 讀取請求內容
    try:
        activity_data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # 驗證簽名（TODO: 實作簽名驗證）
    # await verify_signature(request, activity_data)
    
    # 儲存到收件匣（GraphQL）
    created = await gql.create_inbox_item({
        "activity_id": activity_data.get("id"),
        "actor_id": activity_data.get("actor"),
        "activity_data": activity_data,
        "is_processed": False,
    })
    
    # 非同步處理活動
    try:
        # 處理活動（後續也會全面改為 GQL，現階段先維持傳入 None 作為 db 佔位）
        await process_activity(activity_data, None)
        if created and created.get("id"):
            await gql.update_inbox_item_processed(created["id"], True)
    except Exception as e:
        # 記錄錯誤但不要讓請求失敗
        print(f"Error processing activity: {e}")
    
    return {"status": "accepted"}
