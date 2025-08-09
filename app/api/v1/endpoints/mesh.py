from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.graphql_client import GraphQLClient
from app.core.activitypub.mesh_utils import (
    create_pick_activity, create_comment_activity,
    create_like_pick_activity, create_announce_pick_activity
)
from app.core.activitypub.federation import federate_activity
from app.core.config import settings

router = APIRouter()

# Pydantic 模型
class PickCreate(BaseModel):
    story_id: str
    objective: Optional[str] = None
    kind: str = "share"
    paywall: bool = False

class CommentCreate(BaseModel):
    content: str
    pick_id: Optional[str] = None
    parent_id: Optional[str] = None
    story_id: Optional[str] = None

class ActivityPubSettingsUpdate(BaseModel):
    activitypub_enabled: bool
    activitypub_auto_follow: Optional[bool] = None
    activitypub_public_posts: Optional[bool] = None
    activitypub_federation_enabled: Optional[bool] = None

class ActivityPubSettingsResponse(BaseModel):
    id: str
    activitypub_enabled: bool
    activitypub_auto_follow: bool
    activitypub_public_posts: bool
    activitypub_federation_enabled: bool

class PickResponse(BaseModel):
    id: str
    story_id: str
    objective: Optional[str]
    kind: str
    picked_date: Optional[datetime]
    story: dict
    actor: dict

class CommentResponse(BaseModel):
    id: str
    content: str
    published_date: Optional[datetime]
    actor: dict
    pick: Optional[dict]
    parent: Optional[dict]

class MemberResponse(BaseModel):
    id: str
    name: str
    nickname: Optional[str]
    avatar: Optional[str]
    intro: Optional[str]
    is_active: bool
    verified: bool
    follower_count: int
    following_count: int
    pick_count: int
    comment_count: int
    activitypub_enabled: bool = False
    activitypub_auto_follow: bool = True
    activitypub_public_posts: bool = True
    activitypub_federation_enabled: bool = True

@router.get("/members/{member_id}", response_model=MemberResponse)
async def get_member(
    member_id: str,
):
    """取得 Member 資訊"""
    # 透過 GraphQL 取得 Member 資訊
    gql_client = GraphQLClient()
    member_data = await gql_client.get_member(member_id)
    
    if not member_data:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 檢查本地是否有對應的 Actor（改為透過 GraphQL）
    username = member_data.get("nickname") or member_data.get("name", "").lower().replace(" ", "_")
    actor = await gql_client.get_actor_by_username(username)
    
    # 如果沒有本地 Actor，建立一個
    if not actor:
        actor_data = {
            "username": username,
            "domain": settings.ACTIVITYPUB_DOMAIN,
            "display_name": member_data.get("name", ""),
            "summary": member_data.get("intro", ""),
            "icon_url": member_data.get("avatar", ""),
            "inbox_url": f"/users/{username}/inbox",
            "outbox_url": f"/users/{username}/outbox",
            "followers_url": f"/users/{username}/followers",
            "following_url": f"/users/{username}/following",
            "public_key_pem": "",  # TODO: 生成金鑰
            "private_key_pem": "",  # TODO: 生成金鑰
            "is_local": True,
            "mesh_member": {"connect": {"id": member_id}},
        }
        actor = await gql_client.create_actor(actor_data)
    
    return MemberResponse(
        id=member_data["id"],
        name=member_data["name"],
        nickname=member_data.get("nickname"),
        avatar=member_data.get("avatar"),
        intro=member_data.get("intro"),
        is_active=member_data.get("is_active", True),
        verified=member_data.get("verified", False),
        follower_count=member_data.get("followerCount", 0),
        following_count=member_data.get("followingCount", 0),
        pick_count=member_data.get("pickCount", 0),
        comment_count=member_data.get("commentCount", 0),
        activitypub_enabled=member_data.get("activitypub_enabled", False),
        activitypub_auto_follow=member_data.get("activitypub_auto_follow", True),
        activitypub_public_posts=member_data.get("activitypub_public_posts", True),
        activitypub_federation_enabled=member_data.get("activitypub_federation_enabled", True)
    )

@router.post("/picks", response_model=PickResponse)
async def create_pick(
    pick_data: PickCreate,
    member_id: str,
    background_tasks: BackgroundTasks,
):
    """建立新的 Pick（分享文章）"""
    # 先建立 GraphQL client 並取得 Member 資訊
    gql_client = GraphQLClient()
    member_data = await gql_client.get_member(member_id)
    if not member_data:
        raise HTTPException(status_code=404, detail="Member not found")

    # 查詢或建立 Actor（改為透過 GraphQL）
    username = member_data.get("nickname") or member_data.get("name", "").lower().replace(" ", "_")
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        # 如果沒有本地 Actor，建立一個
        actor_data = {
            "username": username,
            "domain": settings.ACTIVITYPUB_DOMAIN,
            "display_name": member_data.get("name", ""),
            "summary": member_data.get("intro", ""),
            "icon_url": member_data.get("avatar", ""),
            "inbox_url": f"/users/{username}/inbox",
            "outbox_url": f"/users/{username}/outbox",
            "followers_url": f"/users/{username}/followers",
            "following_url": f"/users/{username}/following",
            "public_key_pem": "",  # TODO: 生成金鑰
            "private_key_pem": "",  # TODO: 生成金鑰
            "is_local": True,
            "mesh_member": {"connect": {"id": member_id}},
        }
        actor = await gql_client.create_actor(actor_data)
    
    # 透過 GraphQL 取得 Story 資訊
    story_data = await gql_client.get_story(pick_data.story_id)
    
    if not story_data:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # 不再建立本地 Story 記錄，由 Mesh 端維護
    
    # 透過 GraphQL 建立 Pick
    pick_input = {
        "storyId": pick_data.story_id,
        "objective": pick_data.objective,
        "kind": pick_data.kind,
        "paywall": pick_data.paywall,
        "pickedDate": datetime.utcnow().isoformat(),
        "memberId": member_id
    }
    
    mesh_pick = await gql_client.create_pick(pick_input)
    
    if not mesh_pick:
        raise HTTPException(status_code=500, detail="Failed to create pick in Mesh")
    
    # 不再建立本地 Pick 記錄，由 Mesh 端維護
    
    # 檢查 ActivityPub 設定（改為從 GraphQL 取得）
    if actor.get("activitypub_enabled") and actor.get("activitypub_federation_enabled"):
        # 建立 ActivityPub 活動
        activity = create_pick_activity(mesh_pick, actor, story_data)
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    return PickResponse(
        id=f"pick_{mesh_pick['id']}",
        story_id=pick_data.story_id,
        objective=pick_data.objective,
        kind=pick_data.kind,
        picked_date=datetime.utcnow(),
        story={
            "id": story_data["id"],
            "title": story_data["title"],
            "url": story_data["url"],
            "image_url": story_data.get("image")
        },
        actor={
            "id": actor.get("id"),
            "username": actor.get("username"),
            "display_name": actor.get("display_name"),
            "nickname": actor.get("nickname")
        }
    )

@router.post("/comments", response_model=CommentResponse)
async def create_comment(
    comment_data: CommentCreate,
    member_id: str,
    background_tasks: BackgroundTasks,
):
    """建立新的 Comment"""
    # 查詢 Actor（改為透過 GraphQL）
    username = member_data.get("nickname") or member_data.get("name", "").lower().replace(" ", "_")
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 透過 GraphQL 建立 Comment
    comment_input = {
        "content": comment_data.content,
        "publishedDate": datetime.utcnow().isoformat(),
        "memberId": member_id
    }
    
    if comment_data.pick_id:
        comment_input["pickId"] = comment_data.pick_id
    if comment_data.parent_id:
        comment_input["parentId"] = comment_data.parent_id
    if comment_data.story_id:
        comment_input["storyId"] = comment_data.story_id
    
    mesh_comment = await gql_client.create_comment(comment_input)
    
    if not mesh_comment:
        raise HTTPException(status_code=500, detail="Failed to create comment in Mesh")
    
    # 不再建立本地 Comment 記錄，由 Mesh 端維護
    
    # 檢查 ActivityPub 設定（改為從 GraphQL 取得）
    if actor.get("activitypub_enabled") and actor.get("activitypub_federation_enabled"):
        # 建立 ActivityPub 活動
        activity = create_comment_activity(mesh_comment, actor, None)  # TODO: 取得 pick 資訊
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    return CommentResponse(
        id=f"comment_{mesh_comment['id']}",
        content=comment_data.content,
        published_date=datetime.utcnow(),
        actor={
            "id": actor.get("id"),
            "username": actor.get("username"),
            "display_name": actor.get("display_name"),
            "nickname": actor.get("nickname")
        },
        pick=None,  # TODO: 從 GraphQL 取得 pick 資訊
        parent=None  # TODO: 從 GraphQL 取得 parent 資訊
    )

@router.get("/picks/{pick_id}/comments", response_model=List[CommentResponse])
async def get_pick_comments(
    pick_id: str,
    limit: int = 20,
    offset: int = 0,
):
    """取得 Pick 的評論列表"""
    # 不再查詢本地 Pick，由 Mesh 端維護
    
    # 透過 GraphQL 取得評論
    gql_client = GraphQLClient()
    comments_data = await gql_client.get_pick_comments(pick_id, limit, offset)
    
    # 簡單快取避免 N+1：memberId -> actor
    actor_cache: dict = {}
    comments = []
    for comment_data in comments_data:
        # 查詢對應的 Actor（改為透過 GraphQL）
        member_id = comment_data["member"]["id"]
        actor = actor_cache.get(member_id)
        if actor is None:
            member_data = await gql_client.get_member(member_id)
            username = (member_data or {}).get("nickname") or (member_data or {}).get("name", "").lower().replace(" ", "_")
            actor = await gql_client.get_actor_by_username(username) if username else None
            if actor:
                actor_cache[member_id] = actor
        
        if actor:
            comments.append(CommentResponse(
                id=f"comment_{comment_data['id']}",
                content=comment_data["content"],
                published_date=datetime.fromisoformat(comment_data["published_date"].replace("Z", "+00:00")) if comment_data.get("published_date") else None,
                actor={
                    "id": actor.get("id"),
                    "username": actor.get("username"),
                    "display_name": actor.get("display_name"),
                    "nickname": actor.get("nickname")
                },
                pick={
                    "id": pick_id,
                    "objective": "分享的文章"  # TODO: 從 GraphQL 取得 pick 資訊
                },
                parent={
                    "id": f"comment_{comment_data['parent']['id']}",
                    "content": comment_data["parent"]["content"]
                } if comment_data.get("parent") else None
            ))
    
    return comments

@router.post("/picks/{pick_id}/like")
async def like_pick(
    pick_id: str,
    member_id: str,
    background_tasks: BackgroundTasks,
):
    """對 Pick 按讚"""
    # 查詢 Actor（改為透過 GraphQL）
    member_data = await gql_client.get_member(member_id)
    username = member_data.get("nickname") or member_data.get("name", "").lower().replace(" ", "_")
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 不再查詢本地 Pick，由 Mesh 端維護
    
    # 檢查 ActivityPub 設定（改為從 GraphQL 取得）
    if actor.get("activitypub_enabled") and actor.get("activitypub_federation_enabled"):
        # 建立 ActivityPub 活動
        activity = create_like_pick_activity({"id": pick_id}, actor)
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    # Keystone 目前未支援 Pick 的 like 關聯，僅送出 ActivityPub Like
    return {"status": "liked"}

@router.post("/picks/{pick_id}/announce")
async def announce_pick(
    pick_id: str,
    member_id: str,
    background_tasks: BackgroundTasks,
):
    """轉發 Pick（類似 Facebook 的分享）"""
    # 查詢 Actor（改為透過 GraphQL）
    member_data = await gql_client.get_member(member_id)
    username = member_data.get("nickname") or member_data.get("name", "").lower().replace(" ", "_")
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 不再查詢本地 Pick，由 Mesh 端維護
    
    # 檢查 ActivityPub 設定（改為從 GraphQL 取得）
    if actor.get("activitypub_enabled") and actor.get("activitypub_federation_enabled"):
        # 建立 ActivityPub 活動
        activity = create_announce_pick_activity({"id": pick_id}, actor)
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    return {"status": "announced", "pick_id": pick_id}

@router.get("/members/{member_id}/picks", response_model=List[PickResponse])
async def get_member_picks(
    member_id: str,
    limit: int = 20,
    offset: int = 0,
):
    """取得 Member 的 Picks"""
    # 透過 GraphQL 取得 Member 的 Picks
    gql_client = GraphQLClient()
    # 預先取得對應 Actor，避免 N+1
    member_data = await gql_client.get_member(member_id)
    username = (member_data or {}).get("nickname") or (member_data or {}).get("name", "").lower().replace(" ", "_")
    actor = await gql_client.get_actor_by_username(username) if username else None
    picks_data = await gql_client.get_member_picks(member_id, limit, offset)
    
    picks = []
    for pick_data in picks_data:
        # 查詢對應的 Actor（改為透過 GraphQL）
        if actor:
            picks.append(PickResponse(
                id=f"pick_{pick_data['id']}",
                story_id=pick_data["story"]["id"],
                objective=pick_data.get("objective"),
                kind=pick_data.get("kind", "share"),
                picked_date=datetime.fromisoformat(pick_data["picked_date"].replace("Z", "+00:00")) if pick_data.get("picked_date") else None,
                story={
                    "id": pick_data["story"]["id"],
                    "title": pick_data["story"]["title"],
                    "url": pick_data["story"]["url"],
                    "image_url": pick_data["story"].get("image")
                },
                actor={
                    "id": actor.get("id"),
                    "username": actor.get("username"),
                    "display_name": actor.get("display_name"),
                    "nickname": actor.get("nickname")
                }
            ))
    
    return picks

@router.get("/members/{member_id}/activitypub-settings", response_model=ActivityPubSettingsResponse)
async def get_member_activitypub_settings(
    member_id: str,
):
    """取得 Member 的 ActivityPub 設定"""
    # 透過 GraphQL 取得 Member 資訊
    gql_client = GraphQLClient()
    member_data = await gql_client.get_member(member_id)
    
    if not member_data:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return ActivityPubSettingsResponse(
        id=member_data["id"],
        activitypub_enabled=member_data.get("activitypub_enabled", False),
        activitypub_auto_follow=member_data.get("activitypub_auto_follow", True),
        activitypub_public_posts=member_data.get("activitypub_public_posts", True),
        activitypub_federation_enabled=member_data.get("activitypub_federation_enabled", True)
    )

@router.put("/members/{member_id}/activitypub-settings", response_model=ActivityPubSettingsResponse)
async def update_member_activitypub_settings(
    member_id: str,
    settings_data: ActivityPubSettingsUpdate,
):
    """更新 Member 的 ActivityPub 設定"""
    # 透過 GraphQL 更新 Member 的 ActivityPub 設定
    gql_client = GraphQLClient()
    result = await gql_client.update_member_activitypub_settings(
        member_id=member_id,
        activitypub_enabled=settings_data.activitypub_enabled,
        activitypub_auto_follow=settings_data.activitypub_auto_follow,
        activitypub_public_posts=settings_data.activitypub_public_posts,
        activitypub_federation_enabled=settings_data.activitypub_federation_enabled
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update ActivityPub settings")
    
    # 不再同步更新本地 Actor，由 GraphQL 統一管理
    
    return ActivityPubSettingsResponse(
        id=result["id"],
        activitypub_enabled=result["activitypub_enabled"],
        activitypub_auto_follow=result["activitypub_auto_follow"],
        activitypub_public_posts=result["activitypub_public_posts"],
        activitypub_federation_enabled=result["activitypub_federation_enabled"]
    )
