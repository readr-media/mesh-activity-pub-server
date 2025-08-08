from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.core.graphql_client import GraphQLClient
from app.core.config import settings
from app.core.activitypub.federation import is_public_activity

outbox_router = APIRouter()

@outbox_router.get("/{username}/outbox")
async def get_outbox(username: str):
    """取得發件匣"""
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    # TODO: 實作透過 Activity list 取出對應 actor 的活動清單
    activity_list: list[Dict[str, Any]] = []
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}/outbox",
        "type": "OrderedCollection",
        "totalItems": len(activity_list),
        "orderedItems": activity_list
    }

@outbox_router.post("/{username}/outbox")
async def create_activity(username: str, activity_data: Dict[str, Any]):
    """建立新活動"""
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 驗證活動資料
    activity_type = activity_data.get("type")
    if not activity_type:
        raise HTTPException(status_code=400, detail="Activity type is required")
    
    # 儲存活動（GraphQL: Activity 以及 OutboxItem）
    await gql.create_activity({
        "activity_id": activity_data.get("id"),
        "activity_type": activity_type,
        "actor": {"connect": {"id": actor["id"]}},
        "object_data": activity_data.get("object", {}),
        "target_data": activity_data.get("target"),
        "to": activity_data.get("to"),
        "cc": activity_data.get("cc"),
    })
    await gql.create_outbox_item({
        "activity_id": activity_data.get("id"),
        "actor": {"connect": {"id": actor["id"]}},
        "activity_data": activity_data,
        "is_delivered": False,
        "delivery_attempts": 0,
    })
    
    # 發送到其他實例（TODO: 實作聯邦發送）
    # await federate_activity(activity_data)
    
    return {"status": "created", "id": activity_data.get("id")}
