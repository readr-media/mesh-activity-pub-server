from datetime import datetime
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.models.activitypub import Actor, Story, Pick, Comment
from app.core.activitypub.utils import generate_activity_id, create_activity_object

def create_story_object(story: Story) -> Dict[str, Any]:
    """建立 Story 物件（對應 ActivityPub 的 Article）"""
    story_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/stories/{story.story_id}"
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": story_id,
        "type": "Article",
        "name": story.title,
        "content": story.content,
        "url": story.url,
        "image": story.image_url,
        "published": story.published_date.isoformat() + "Z" if story.published_date else None,
        "updated": story.updated_at.isoformat() + "Z" if story.updated_at else None,
        "attributedTo": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/readr",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/readr/followers"]
    }

def create_pick_object(pick: Pick, actor: Actor, story: Story) -> Dict[str, Any]:
    """建立 Pick 物件（對應 ActivityPub 的 Announce + Note 組合）"""
    pick_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/picks/{pick.pick_id}"
    actor_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{actor.username}"
    story_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/stories/{story.story_id}"
    
    # 建立 Pick 物件（類似 Facebook 的分享）
    pick_object = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": pick_id,
        "type": "Note",
        "attributedTo": actor_id,
        "content": pick.objective or f"分享了這篇文章：{story.title}",
        "contentType": "text/html",
        "published": pick.picked_date.isoformat() + "Z" if pick.picked_date else pick.created_at.isoformat() + "Z",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{actor_id}/followers"],
        "attachment": [
            {
                "type": "Link",
                "href": story.url,
                "name": story.title,
                "mediaType": "text/html",
                "image": story.image_url
            }
        ],
        "tag": [
            {
                "type": "Mention",
                "href": story_id,
                "name": story.title
            }
        ]
    }
    
    return pick_object

def create_comment_object(comment: Comment, actor: Actor, pick: Optional[Pick] = None) -> Dict[str, Any]:
    """建立 Comment 物件"""
    comment_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/comments/{comment.comment_id}"
    actor_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{actor.username}"
    
    comment_object = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": comment_id,
        "type": "Note",
        "attributedTo": actor_id,
        "content": comment.content,
        "contentType": "text/html",
        "published": comment.published_date.isoformat() + "Z" if comment.published_date else comment.created_at.isoformat() + "Z",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{actor_id}/followers"]
    }
    
    # 如果是 pick 的評論，添加 inReplyTo
    if pick:
        pick_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/picks/{pick.pick_id}"
        comment_object["inReplyTo"] = pick_id
    
    # 如果是回覆其他評論
    if comment.parent_id:
        parent_comment_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/comments/{comment.parent.comment_id}"
        comment_object["inReplyTo"] = parent_comment_id
    
    return comment_object

def create_pick_activity(pick: Pick, actor: Actor, story: Story) -> Dict[str, Any]:
    """建立 Pick 活動（Create 活動）"""
    activity_id = generate_activity_id("Create", actor.username)
    actor_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{actor.username}"
    
    pick_object = create_pick_object(pick, actor, story)
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": activity_id,
        "type": "Create",
        "actor": actor_id,
        "object": pick_object,
        "published": pick.picked_date.isoformat() + "Z" if pick.picked_date else pick.created_at.isoformat() + "Z",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{actor_id}/followers"]
    }

def create_comment_activity(comment: Comment, actor: Actor, pick: Optional[Pick] = None) -> Dict[str, Any]:
    """建立 Comment 活動（Create 活動）"""
    activity_id = generate_activity_id("Create", actor.username)
    actor_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{actor.username}"
    
    comment_object = create_comment_object(comment, actor, pick)
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": activity_id,
        "type": "Create",
        "actor": actor_id,
        "object": comment_object,
        "published": comment.published_date.isoformat() + "Z" if comment.published_date else comment.created_at.isoformat() + "Z",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{actor_id}/followers"]
    }

def create_like_pick_activity(pick: Pick, actor: Actor) -> Dict[str, Any]:
    """建立對 Pick 的 Like 活動"""
    activity_id = generate_activity_id("Like", actor.username)
    actor_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{actor.username}"
    pick_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/picks/{pick.pick_id}"
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": activity_id,
        "type": "Like",
        "actor": actor_id,
        "object": pick_id,
        "published": datetime.utcnow().isoformat() + "Z",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{actor_id}/followers"]
    }

def create_announce_pick_activity(pick: Pick, actor: Actor) -> Dict[str, Any]:
    """建立對 Pick 的 Announce 活動（轉發）"""
    activity_id = generate_activity_id("Announce", actor.username)
    actor_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{actor.username}"
    pick_id = f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/picks/{pick.pick_id}"
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": activity_id,
        "type": "Announce",
        "actor": actor_id,
        "object": pick_id,
        "published": datetime.utcnow().isoformat() + "Z",
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [f"{actor_id}/followers"]
    }

def parse_mesh_pick_from_activity(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """從 ActivityPub 活動解析 Mesh Pick 資料"""
    object_data = activity_data.get("object", {})
    
    # 提取文章資訊
    story_info = {
        "title": object_data.get("name") or "分享的文章",
        "url": None,
        "image_url": None
    }
    
    # 從 attachment 中提取 URL
    attachments = object_data.get("attachment", [])
    for attachment in attachments:
        if attachment.get("type") == "Link":
            story_info["url"] = attachment.get("href")
            story_info["image_url"] = attachment.get("image")
            break
    
    # 提取 pick 資訊
    pick_info = {
        "objective": object_data.get("content"),
        "kind": "share",
        "picked_date": object_data.get("published")
    }
    
    return {
        "story": story_info,
        "pick": pick_info
    }

def parse_mesh_comment_from_activity(activity_data: Dict[str, Any]) -> Dict[str, Any]:
    """從 ActivityPub 活動解析 Mesh Comment 資料"""
    object_data = activity_data.get("object", {})
    
    comment_info = {
        "content": object_data.get("content"),
        "published_date": object_data.get("published"),
        "in_reply_to": object_data.get("inReplyTo")
    }
    
    return comment_info
