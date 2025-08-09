from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import re

from app.core.config import settings
from app.core.graphql_client import GraphQLClient
from app.core.activitypub.utils import create_actor_object

from fastapi.responses import ORJSONResponse, RedirectResponse
webfinger_router = APIRouter()

async def handle_webfinger(resource: str, db=None) -> Dict[str, Any]:
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
    
    # 透過 GraphQL 查詢 Actor
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
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

# 兼容測試腳本：/.well-known/users/{username}
@webfinger_router.get("/users/{username}")
async def compat_users(username: str):
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    # 直接以 dict 形式呼叫工具函式，並加上快取
    data = create_actor_object(actor)
    return ORJSONResponse(data, headers={"Cache-Control": "public, max-age=300"})

# 兼容測試腳本：/.well-known/inbox/{username}/inbox
@webfinger_router.post("/inbox/{username}/inbox")
async def compat_inbox(username: str, request: Request):
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        activity_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    created = await gql.create_inbox_item({
        "activity_id": activity_data.get("id"),
        "actor_id": activity_data.get("actor"),
        "activity_data": activity_data,
        "is_processed": False,
    })
    # 非同步處理（不阻塞回應）
    try:
        from app.core.activitypub.processor import process_activity
        await process_activity(activity_data, None)
        if created and created.get("id"):
            await gql.update_inbox_item_processed(created["id"], True)
    except Exception as e:
        print(f"Compat inbox process error: {e}")
    return {"status": "accepted"}
