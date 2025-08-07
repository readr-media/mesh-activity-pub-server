from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.activitypub import Actor
from app.core.activitypub.utils import generate_key_pair, create_actor_object
from app.core.config import settings

router = APIRouter()

class ActorCreate(BaseModel):
    username: str
    display_name: str = None
    summary: str = None
    icon_url: str = None

class ActorResponse(BaseModel):
    id: int
    username: str
    display_name: str = None
    summary: str = None
    icon_url: str = None
    is_local: bool
    created_at: str

@router.get("/", response_model=List[ActorResponse])
async def list_actors(db: AsyncSession = Depends(get_db)):
    """列出所有 Actor"""
    result = await db.execute(select(Actor))
    actors = result.scalars().all()
    
    return [
        ActorResponse(
            id=actor.id,
            username=actor.username,
            display_name=actor.display_name,
            summary=actor.summary,
            icon_url=actor.icon_url,
            is_local=actor.is_local,
            created_at=actor.created_at.isoformat()
        )
        for actor in actors
    ]

@router.post("/", response_model=ActorResponse)
async def create_actor(
    actor_data: ActorCreate,
    db: AsyncSession = Depends(get_db)
):
    """建立新 Actor"""
    # 檢查使用者名稱是否已存在
    result = await db.execute(
        select(Actor).where(Actor.username == actor_data.username)
    )
    existing_actor = result.scalar_one_or_none()
    
    if existing_actor:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # 生成金鑰對
    public_key, private_key = generate_key_pair()
    
    # 建立 Actor
    actor = Actor(
        username=actor_data.username,
        domain=settings.ACTIVITYPUB_DOMAIN,
        display_name=actor_data.display_name,
        summary=actor_data.summary,
        icon_url=actor_data.icon_url,
        inbox_url=f"/users/{actor_data.username}/inbox",
        outbox_url=f"/users/{actor_data.username}/outbox",
        followers_url=f"/users/{actor_data.username}/followers",
        following_url=f"/users/{actor_data.username}/following",
        public_key_pem=public_key,
        private_key_pem=private_key,
        is_local=True
    )
    
    db.add(actor)
    await db.commit()
    await db.refresh(actor)
    
    return ActorResponse(
        id=actor.id,
        username=actor.username,
        display_name=actor.display_name,
        summary=actor.summary,
        icon_url=actor.icon_url,
        is_local=actor.is_local,
        created_at=actor.created_at.isoformat()
    )

@router.get("/{username}")
async def get_actor(username: str, db: AsyncSession = Depends(get_db)):
    """取得特定 Actor 資訊"""
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    return create_actor_object(actor)
