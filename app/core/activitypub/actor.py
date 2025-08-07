from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from typing import List, Dict, Any
import json

from app.core.database import get_db
from app.models.activitypub import Actor, Follow
from app.core.config import settings
from app.core.activitypub.utils import generate_actor_id, create_actor_object

actor_router = APIRouter()

@actor_router.get("/{username}")
async def get_actor(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get Actor information"""
    # Query Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # Create Actor object
    actor_object = create_actor_object(actor)
    
    return actor_object

@actor_router.get("/{username}/followers")
async def get_followers(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get followers list"""
    # Query Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # Query followers
    result = await db.execute(
        select(Follow).where(
            Follow.following_id == actor.id,
            Follow.is_accepted == True
        ).options(selectinload(Follow.follower))
    )
    follows = result.scalars().all()
    
    # Create followers list
    followers = []
    for follow in follows:
        follower_actor = create_actor_object(follow.follower)
        followers.append(follower_actor)
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}/followers",
        "type": "OrderedCollection",
        "totalItems": len(followers),
        "orderedItems": followers
    }

@actor_router.get("/{username}/following")
async def get_following(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get following list"""
    # Query Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # Query following
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == actor.id,
            Follow.is_accepted == True
        ).options(selectinload(Follow.following))
    )
    follows = result.scalars().all()
    
    # Create following list
    following = []
    for follow in follows:
        following_actor = create_actor_object(follow.following)
        following.append(following_actor)
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}/following",
        "type": "OrderedCollection",
        "totalItems": len(following),
        "orderedItems": following
    }

@actor_router.get("/{username}/outbox")
async def get_outbox(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get outbox"""
    # Query Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    actor = result.scalar_one_or_none()
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}/outbox",
        "type": "OrderedCollection",
        "totalItems": 0,  # TODO: Implement activity count
        "orderedItems": []  # TODO: Implement activity list
    }
