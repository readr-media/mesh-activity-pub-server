from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.graphql_client import GraphQLClient
from app.models.activitypub import Actor, Story, Pick, Comment
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
    db: AsyncSession = Depends(get_db)
):
    """取得 Member 資訊"""
    # 透過 GraphQL 取得 Member 資訊
    gql_client = GraphQLClient()
    member_data = await gql_client.get_member(member_id)
    
    if not member_data:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 檢查本地是否有對應的 Actor
    result = await db.execute(
        select(Actor).where(Actor.mesh_member_id == member_id)
    )
    actor = result.scalar_one_or_none()
    
    # 如果沒有本地 Actor，建立一個
    if not actor:
        actor = Actor(
            username=member_data.get("nickname") or member_data.get("name", "").lower().replace(" ", "_"),
            domain=settings.ACTIVITYPUB_DOMAIN,
            display_name=member_data.get("name", ""),
            summary=member_data.get("intro", ""),
            icon_url=member_data.get("avatar", ""),
            inbox_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/inbox",
            outbox_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/outbox",
            followers_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/followers",
            following_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/following",
            public_key_pem="",  # TODO: 生成金鑰
            private_key_pem="",  # TODO: 生成金鑰
            is_local=True,
            mesh_member_id=member_id,
            nickname=member_data.get("nickname"),
            email=member_data.get("email"),
            avatar=member_data.get("avatar"),
            intro=member_data.get("intro"),
            is_active=member_data.get("is_active", True),
            verified=member_data.get("verified", False),
            language=member_data.get("language", "zh-TW")
        )
        db.add(actor)
        await db.commit()
        await db.refresh(actor)
    
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
    db: AsyncSession = Depends(get_db)
):
    """建立新的 Pick（分享文章）"""
    # 查詢或建立 Actor
    result = await db.execute(
        select(Actor).where(Actor.mesh_member_id == member_id)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        # 如果沒有本地 Actor，先取得 Member 資訊
        gql_client = GraphQLClient()
        member_data = await gql_client.get_member(member_id)
        
        if not member_data:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # 建立 Actor
        actor = Actor(
            username=member_data.get("nickname") or member_data.get("name", "").lower().replace(" ", "_"),
            domain=settings.ACTIVITYPUB_DOMAIN,
            display_name=member_data.get("name", ""),
            summary=member_data.get("intro", ""),
            icon_url=member_data.get("avatar", ""),
            inbox_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/inbox",
            outbox_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/outbox",
            followers_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/followers",
            following_url=f"/users/{member_data.get('nickname') or member_data.get('name', '').lower().replace(' ', '_')}/following",
            public_key_pem="",  # TODO: 生成金鑰
            private_key_pem="",  # TODO: 生成金鑰
            is_local=True,
            mesh_member_id=member_id,
            nickname=member_data.get("nickname"),
            email=member_data.get("email"),
            avatar=member_data.get("avatar"),
            intro=member_data.get("intro"),
            is_active=member_data.get("is_active", True),
            verified=member_data.get("verified", False),
            language=member_data.get("language", "zh-TW")
        )
        db.add(actor)
        await db.commit()
        await db.refresh(actor)
    
    # 透過 GraphQL 取得 Story 資訊
    gql_client = GraphQLClient()
    story_data = await gql_client.get_story(pick_data.story_id)
    
    if not story_data:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # 檢查 Story 是否已存在於本地資料庫
    result = await db.execute(
        select(Story).where(Story.mesh_story_id == pick_data.story_id)
    )
    story = result.scalar_one_or_none()
    
    if not story:
        # 建立新的 Story 記錄
        story = Story(
            story_id=f"story_{pick_data.story_id}",
            mesh_story_id=pick_data.story_id,
            title=story_data.get("title", ""),
            content=story_data.get("content", ""),
            url=story_data.get("url", ""),
            image_url=story_data.get("image", ""),
            published_date=datetime.fromisoformat(story_data.get("published_date")) if story_data.get("published_date") else None,
            is_active=story_data.get("is_active", True),
            state=story_data.get("state", "published")
        )
        db.add(story)
        await db.commit()
        await db.refresh(story)
    
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
    
    # 建立本地 Pick 記錄
    pick = Pick(
        pick_id=f"pick_{mesh_pick['id']}",
        mesh_pick_id=mesh_pick['id'],
        actor_id=actor.id,
        story_id=story.id,
        kind=pick_data.kind,
        objective=pick_data.objective,
        paywall=pick_data.paywall,
        picked_date=datetime.utcnow(),
        is_active=True,
        state="active"
    )
    
    db.add(pick)
    await db.commit()
    await db.refresh(pick)
    
    # 檢查 ActivityPub 設定
    if actor.activitypub_enabled and actor.activitypub_federation_enabled:
        # 建立 ActivityPub 活動
        activity = create_pick_activity(pick, actor, story)
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    return PickResponse(
        id=pick.pick_id,
        story_id=story.story_id,
        objective=pick.objective,
        kind=pick.kind,
        picked_date=pick.picked_date,
        story={
            "id": story.story_id,
            "title": story.title,
            "url": story.url,
            "image_url": story.image_url
        },
        actor={
            "id": actor.id,
            "username": actor.username,
            "display_name": actor.display_name,
            "nickname": actor.nickname
        }
    )

@router.post("/comments", response_model=CommentResponse)
async def create_comment(
    comment_data: CommentCreate,
    member_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """建立新的 Comment"""
    # 查詢 Actor
    result = await db.execute(
        select(Actor).where(Actor.mesh_member_id == member_id)
    )
    actor = result.scalar_one_or_none()
    
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
    
    # 建立本地 Comment 記錄
    comment = Comment(
        comment_id=f"comment_{mesh_comment['id']}",
        mesh_comment_id=mesh_comment['id'],
        actor_id=actor.id,
        content=comment_data.content,
        published_date=datetime.utcnow(),
        is_active=True,
        state="published"
    )
    
    # 如果是指定 Pick 的評論
    if comment_data.pick_id:
        result = await db.execute(
            select(Pick).where(Pick.mesh_pick_id == comment_data.pick_id)
        )
        pick = result.scalar_one_or_none()
        if pick:
            comment.pick_id = pick.id
    
    # 如果是回覆其他評論
    if comment_data.parent_id:
        result = await db.execute(
            select(Comment).where(Comment.mesh_comment_id == comment_data.parent_id)
        )
        parent_comment = result.scalar_one_or_none()
        if parent_comment:
            comment.parent_id = parent_comment.id
    
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    
    # 檢查 ActivityPub 設定
    if actor.activitypub_enabled and actor.activitypub_federation_enabled:
        # 建立 ActivityPub 活動
        activity = create_comment_activity(comment, actor, comment.pick)
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    return CommentResponse(
        id=comment.comment_id,
        content=comment.content,
        published_date=comment.published_date,
        actor={
            "id": actor.id,
            "username": actor.username,
            "display_name": actor.display_name,
            "nickname": actor.nickname
        },
        pick={
            "id": comment.pick.pick_id,
            "objective": comment.pick.objective
        } if comment.pick else None,
        parent={
            "id": comment.parent.comment_id,
            "content": comment.parent.content
        } if comment.parent else None
    )

@router.get("/picks/{pick_id}/comments", response_model=List[CommentResponse])
async def get_pick_comments(
    pick_id: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """取得 Pick 的評論列表"""
    # 查詢 Pick
    result = await db.execute(
        select(Pick).where(Pick.mesh_pick_id == pick_id)
    )
    pick = result.scalar_one_or_none()
    
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")
    
    # 透過 GraphQL 取得評論
    gql_client = GraphQLClient()
    comments_data = await gql_client.get_pick_comments(pick_id, limit, offset)
    
    comments = []
    for comment_data in comments_data:
        # 查詢對應的 Actor
        result = await db.execute(
            select(Actor).where(Actor.mesh_member_id == comment_data["member"]["id"])
        )
        actor = result.scalar_one_or_none()
        
        if actor:
            comments.append(CommentResponse(
                id=f"comment_{comment_data['id']}",
                content=comment_data["content"],
                published_date=datetime.fromisoformat(comment_data["published_date"]) if comment_data.get("published_date") else None,
                actor={
                    "id": actor.id,
                    "username": actor.username,
                    "display_name": actor.display_name,
                    "nickname": actor.nickname
                },
                pick={
                    "id": pick.pick_id,
                    "objective": pick.objective
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
    db: AsyncSession = Depends(get_db)
):
    """對 Pick 按讚"""
    # 查詢 Actor
    result = await db.execute(
        select(Actor).where(Actor.mesh_member_id == member_id)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 查詢 Pick
    result = await db.execute(
        select(Pick).where(Pick.mesh_pick_id == pick_id)
    )
    pick = result.scalar_one_or_none()
    
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")
    
    # 透過 GraphQL 按讚
    gql_client = GraphQLClient()
    like_result = await gql_client.like_pick(pick_id, member_id)
    
    if not like_result:
        raise HTTPException(status_code=500, detail="Failed to like pick in Mesh")
    
    # 檢查 ActivityPub 設定
    if actor.activitypub_enabled and actor.activitypub_federation_enabled:
        # 建立 ActivityPub Like 活動
        activity = create_like_pick_activity(pick, actor)
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    return {"status": "liked", "like_count": like_result.get("likeCount", 0)}

@router.post("/picks/{pick_id}/announce")
async def announce_pick(
    pick_id: str,
    member_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """轉發 Pick（類似 Facebook 的分享）"""
    # 查詢 Actor
    result = await db.execute(
        select(Actor).where(Actor.mesh_member_id == member_id)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # 查詢 Pick
    result = await db.execute(
        select(Pick).where(Pick.mesh_pick_id == pick_id)
    )
    pick = result.scalar_one_or_none()
    
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")
    
    # 檢查 ActivityPub 設定
    if actor.activitypub_enabled and actor.activitypub_federation_enabled:
        # 建立 ActivityPub Announce 活動
        activity = create_announce_pick_activity(pick, actor)
        
        # 背景任務：發送到聯邦網路
        background_tasks.add_task(federate_activity, activity)
    
    return {"status": "announced", "pick_id": pick.pick_id}

@router.get("/members/{member_id}/picks", response_model=List[PickResponse])
async def get_member_picks(
    member_id: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """取得 Member 的 Picks"""
    # 透過 GraphQL 取得 Member 的 Picks
    gql_client = GraphQLClient()
    picks_data = await gql_client.get_member_picks(member_id, limit, offset)
    
    picks = []
    for pick_data in picks_data:
        # 查詢對應的 Actor
        result = await db.execute(
            select(Actor).where(Actor.mesh_member_id == member_id)
        )
        actor = result.scalar_one_or_none()
        
        if actor:
            picks.append(PickResponse(
                id=f"pick_{pick_data['id']}",
                story_id=pick_data["story"]["id"],
                objective=pick_data.get("objective"),
                kind=pick_data.get("kind", "share"),
                picked_date=datetime.fromisoformat(pick_data["picked_date"]) if pick_data.get("picked_date") else None,
                story={
                    "id": pick_data["story"]["id"],
                    "title": pick_data["story"]["title"],
                    "url": pick_data["story"]["url"],
                    "image_url": pick_data["story"]["image"]
                },
                actor={
                    "id": actor.id,
                    "username": actor.username,
                    "display_name": actor.display_name,
                    "nickname": actor.nickname
                }
            ))
    
    return picks

@router.get("/members/{member_id}/activitypub-settings", response_model=ActivityPubSettingsResponse)
async def get_member_activitypub_settings(
    member_id: str,
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    
    # 同步更新本地 Actor 的設定
    result = await db.execute(
        select(Actor).where(Actor.mesh_member_id == member_id)
    )
    actor = result.scalar_one_or_none()
    
    if actor:
        actor.activitypub_enabled = settings_data.activitypub_enabled
        if settings_data.activitypub_auto_follow is not None:
            actor.activitypub_auto_follow = settings_data.activitypub_auto_follow
        if settings_data.activitypub_public_posts is not None:
            actor.activitypub_public_posts = settings_data.activitypub_public_posts
        if settings_data.activitypub_federation_enabled is not None:
            actor.activitypub_federation_enabled = settings_data.activitypub_federation_enabled
        
        await db.commit()
        await db.refresh(actor)
    
    return ActivityPubSettingsResponse(
        id=result["id"],
        activitypub_enabled=result["activitypub_enabled"],
        activitypub_auto_follow=result["activitypub_auto_follow"],
        activitypub_public_posts=result["activitypub_public_posts"],
        activitypub_federation_enabled=result["activitypub_federation_enabled"]
    )
