from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

from app.models.activitypub import Actor, Follow, Note, Story, Pick, Comment
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
    actor_id = activity_data.get("actor")
    object_id = activity_data.get("object")
    
    # Parse Actor ID to get username
    username = extract_username_from_actor_id(object_id)
    
    # Query local Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    local_actor = result.scalar_one_or_none()
    
    if not local_actor:
        return
    
    # Create Follow relationship
    follow = Follow(
        follower_id=actor_id,  # External Actor ID
        following_id=local_actor.id,
        activity_id=activity_data.get("id"),
        is_accepted=False
    )
    
    db.add(follow)
    await db.commit()
    
    # Automatically accept Follow (can be adjusted based on settings)
    follow.is_accepted = True
    await db.commit()
    
    # Sync to Mesh system
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_accept(activity_data: Dict[str, Any], db: AsyncSession):
    """處理 Accept 活動"""
    # 查找對應的 Follow 活動並標記為已接受
    follow_activity_id = activity_data.get("object", {}).get("id")
    
    if follow_activity_id:
        result = await db.execute(
            select(Follow).where(Follow.activity_id == follow_activity_id)
        )
        follow = result.scalar_one_or_none()
        
        if follow:
            follow.is_accepted = True
            await db.commit()

async def process_reject(activity_data: Dict[str, Any], db: AsyncSession):
    """處理 Reject 活動"""
    # 查找對應的 Follow 活動並刪除
    follow_activity_id = activity_data.get("object", {}).get("id")
    
    if follow_activity_id:
        result = await db.execute(
            select(Follow).where(Follow.activity_id == follow_activity_id)
        )
        follow = result.scalar_one_or_none()
        
        if follow:
            await db.delete(follow)
            await db.commit()

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
    # Parse Pick data
    pick_info = parse_mesh_pick_from_activity(activity_data)
    
    # Get Actor
    actor_id = activity_data.get("actor")
    actor = await get_or_create_actor(actor_id, db)
    
    if not actor:
        return
    
    # Create or update Story
    story = await get_or_create_story(pick_info["story"], db)
    
    # 改為直接同步到 Mesh（GraphQL），本地不再落地 Pick
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)
    
    # Sync to Mesh system
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)

async def process_mesh_comment(activity_data: Dict[str, Any], db: AsyncSession):
    """Process Mesh Comment activity"""
    # Parse Comment data
    comment_info = parse_mesh_comment_from_activity(activity_data)
    
    # Get Actor
    actor_id = activity_data.get("actor")
    actor = await get_or_create_actor(actor_id, db)
    
    if not actor:
        return
    
    # 改為直接同步到 Mesh（GraphQL），本地不再落地 Comment
    await mesh_sync_manager.sync_activity_to_mesh(activity_data, db)
    
    # Sync to Mesh system
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

async def get_or_create_actor(actor_id: str, db: AsyncSession) -> Optional[Actor]:
    """取得或建立 Actor"""
    # 先查詢是否已存在
    result = await db.execute(
        select(Actor).where(Actor.username == extract_username_from_actor_id(actor_id))
    )
    actor = result.scalar_one_or_none()
    
    if actor:
        return actor
    
    # 如果不存在，嘗試發現遠端 Actor
    from app.core.activitypub.federation import discover_actor
    actor_data = await discover_actor(actor_id)
    
    if actor_data:
        # 建立新的 Actor 記錄
        actor = Actor(
            username=actor_data.get("preferredUsername", ""),
            domain=extract_domain_from_actor_id(actor_id),
            display_name=actor_data.get("name", ""),
            summary=actor_data.get("summary", ""),
            icon_url=actor_data.get("icon", {}).get("url", ""),
            inbox_url=actor_data.get("inbox", ""),
            outbox_url=actor_data.get("outbox", ""),
            followers_url=actor_data.get("followers", ""),
            following_url=actor_data.get("following", ""),
            public_key_pem=actor_data.get("publicKey", {}).get("publicKeyPem", ""),
            is_local=False
        )
        
        db.add(actor)
        await db.commit()
        await db.refresh(actor)
        
        return actor
    
    return None

async def get_or_create_story(story_info: Dict[str, Any], db: AsyncSession) -> Story:
    """取得或建立 Story"""
    # 先查詢是否已存在
    result = await db.execute(
        select(Story).where(Story.url == story_info["url"])
    )
    story = result.scalar_one_or_none()
    
    if story:
        return story
    
    # 建立新的 Story
    story = Story(
        story_id=f"story_{hash(story_info['url'])}",
        title=story_info["title"],
        content=story_info.get("content", ""),
        url=story_info["url"],
        image_url=story_info.get("image_url", ""),
        is_active=True,
        state="published"
    )
    
    db.add(story)
    await db.commit()
    await db.refresh(story)
    
    return story

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
