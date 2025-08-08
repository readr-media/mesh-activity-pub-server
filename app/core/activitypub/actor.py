from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import json

from app.core.database import get_db
from app.core.graphql_client import GraphQLClient
from app.core.config import settings
from app.core.activitypub.utils import generate_actor_id, create_actor_object

actor_router = APIRouter()

@actor_router.get("/{username}")
async def get_actor(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get Actor information（改為透過 GraphQL）"""
    # Query Actor via GraphQL
    gql_client = GraphQLClient()
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # Create Actor object from GraphQL data
    actor_object = create_actor_object(actor)
    
    return actor_object

@actor_router.get("/{username}/followers")
async def get_followers(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get followers list（改為透過 GraphQL）"""
    # Query Actor via GraphQL
    gql_client = GraphQLClient()
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # TODO: 透過 GraphQL 取得追蹤者列表
    # 目前先回傳空列表，待實作 GraphQL 追蹤者查詢
    followers = []
    
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
    """Get following list（改為透過 GraphQL）"""
    # Query Actor via GraphQL
    gql_client = GraphQLClient()
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    # TODO: 透過 GraphQL 取得追蹤中列表
    # 目前先回傳空列表，待實作 GraphQL 追蹤中查詢
    following = []
    
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
    """Get outbox（改為透過 GraphQL）"""
    # Query Actor via GraphQL
    gql_client = GraphQLClient()
    actor = await gql_client.get_actor_by_username(username)
    
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    
    return {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{settings.ACTIVITYPUB_PROTOCOL}://{settings.ACTIVITYPUB_DOMAIN}/users/{username}/outbox",
        "type": "OrderedCollection",
        "totalItems": 0,  # TODO: Implement activity count
        "orderedItems": []  # TODO: Implement activity list
    }
