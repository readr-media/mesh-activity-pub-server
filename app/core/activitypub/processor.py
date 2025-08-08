from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

from app.core.activitypub.utils import generate_actor_id
from app.core.activitypub.mesh_utils import parse_mesh_pick_from_activity, parse_mesh_comment_from_activity
from app.core.activitypub.mesh_sync import mesh_sync_manager
from app.core.graphql_client import GraphQLClient

async def process_activity(activity_data: Dict[str, Any], db: AsyncSession):
    """Process ActivityPub activity"""
    activity_type = activity_data.get("type")
    
    if activity_type == "Follow":
        await process_follow(activity_data, db)
    elif activity_type == "Accept":
        await process_accept(activity_data, db)
    elif activity_type == "Reject":
        await process_reject(activity_data, db)
    elif activity_type == "Create":
        await process_create(activity_data, db)
    elif activity_type == "Like":
        await process_like(activity_data, db)
    elif activity_type == "Announce":
        await process_announce(activity_data, db)
    else:
        # Log unknown activity type
        print(f"Unknown activity type: {activity_type}")

async def process_follow(activity_data: Dict[str, Any], db: AsyncSession):
    """Process Follow activity"""
    # 改為由 mesh_sync_manager 透過 GraphQL 建立追蹤關係
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_accept(activity_data: Dict[str, Any], db: AsyncSession):
    """處理 Accept 活動"""
    # 不再更新本地 Follow 記錄；僅記錄 Activity 以避免重複處理
    try:
        gql = GraphQLClient()
        await gql.create_activity({
            "activity_id": activity_data.get("id"),
            "activity_type": "Accept",
            "object_data": activity_data.get("object"),
            "target_data": activity_data.get("target"),
            "is_public": True,
        })
    except Exception:
        pass

async def process_reject(activity_data: Dict[str, Any], db: AsyncSession):
    """處理 Reject 活動"""
    # 不再刪除本地 Follow 記錄；僅記錄 Activity 以避免重複處理
    try:
        gql = GraphQLClient()
        await gql.create_activity({
            "activity_id": activity_data.get("id"),
            "activity_type": "Reject",
            "object_data": activity_data.get("object"),
            "target_data": activity_data.get("target"),
            "is_public": True,
        })
    except Exception:
        pass

async def process_create(activity_data: Dict[str, Any], db: AsyncSession):
    """處理 Create 活動"""
    object_data = activity_data.get("object", {})
    object_type = object_data.get("type")
    
    if object_type == "Note":
        # 檢查是否是 Mesh Pick 或 Comment
        if await is_mesh_pick(object_data):
            await process_mesh_pick(activity_data, db)
        elif await is_mesh_comment(object_data):
            await process_mesh_comment(activity_data, db)
        else:
            # 一般 Note
            await process_note(activity_data, db)
    elif object_type == "Article":
        await process_article(activity_data, db)

async def is_mesh_pick(object_data: Dict[str, Any]) -> bool:
    """檢查是否為 Mesh Pick"""
    # 檢查是否有 attachment 且包含 Link
    attachments = object_data.get("attachment", [])
    for attachment in attachments:
        if attachment.get("type") == "Link" and attachment.get("href"):
            return True
    return False

async def is_mesh_comment(object_data: Dict[str, Any]) -> bool:
    """檢查是否為 Mesh Comment"""
    # 檢查是否有 inReplyTo 且指向 Pick
    in_reply_to = object_data.get("inReplyTo")
    if in_reply_to and "picks" in in_reply_to:
        return True
    return False

async def process_mesh_pick(activity_data: Dict[str, Any], db: AsyncSession):
    """Process Mesh Pick activity"""
    # 直接同步到 Mesh（GraphQL），不再落地本地 DB
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_mesh_comment(activity_data: Dict[str, Any], db: AsyncSession):
    """Process Mesh Comment activity"""
    # 直接同步到 Mesh（GraphQL），不再落地本地 DB
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_note(activity_data: Dict[str, Any], db: AsyncSession):
    """處理一般 Note 活動"""
    object_data = activity_data.get("object", {})
    
    # Note 不再落地 DB，改為依內容轉換至 Mesh（Pick/Comment）
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_article(activity_data: Dict[str, Any], db: AsyncSession):
    """處理 Article 活動"""
    object_data = activity_data.get("object", {})
    
    # Story 不再落地 DB，由 Mesh 端維護
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_like(activity_data: Dict[str, Any], db: AsyncSession):
    """Process Like activity"""
    # TODO: Implement Like processing logic
    # This needs to handle based on the liked object type (Pick, Comment, Note)
    # Sync to Mesh system
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_announce(activity_data: Dict[str, Any], db: AsyncSession):
    """Process Announce activity"""
    # TODO: Implement Announce processing logic
    # This is usually repost/share functionality
    # Sync to Mesh system
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

# 本檔案不再提供本地 ORM 的 get_or_create 實作，交由 mesh_sync 與 GraphQL 處理

def extract_username_from_actor_id(actor_id: str) -> str:
    """從 Actor ID 中提取使用者名稱"""
    if not actor_id:
        return ""
    
    # 格式: https://domain.com/users/username
    parts = actor_id.split("/")
    return parts[-1] if parts else ""

def extract_domain_from_actor_id(actor_id: str) -> str:
    """從 Actor ID 中提取域名"""
    if not actor_id:
        return ""
    
    # 格式: https://domain.com/users/username
    from urllib.parse import urlparse
    parsed = urlparse(actor_id)
    return parsed.netloc

def extract_actor_id_from_activity(activity_data: Dict[str, Any]) -> int:
    """從活動中提取 Actor ID"""
    # TODO: 實作 Actor ID 提取邏輯
    return 1

def is_public_activity(activity_data: Dict[str, Any]) -> bool:
    """檢查活動是否為公開"""
    to = activity_data.get("to", [])
    cc = activity_data.get("cc", [])
    
    public_uris = [
        "https://www.w3.org/ns/activitystreams#Public",
        "as:Public",
        "Public"
    ]
    
    return any(uri in to or uri in cc for uri in public_uris)
