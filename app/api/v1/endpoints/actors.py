from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

from app.core.activitypub.utils import generate_key_pair, create_actor_object
from app.core.config import settings
from app.core.graphql_client import GraphQLClient

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
async def list_actors():
    """列出所有 Actor"""
    # 目前僅提供單筆查詢使用，列表可後續擴充 GraphQL query
    return []

@router.post("/", response_model=ActorResponse)
async def create_actor(actor_data: ActorCreate):
    """建立新 Actor"""
    gql = GraphQLClient()
    existing = await gql.get_actor_by_username(actor_data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # 生成金鑰對
    public_key, private_key = generate_key_pair()
    
    data = {
        "username": actor_data.username,
        "domain": settings.ACTIVITYPUB_DOMAIN,
        "display_name": actor_data.display_name,
        "summary": actor_data.summary,
        "icon_url": actor_data.icon_url,
        "inbox_url": f"/users/{actor_data.username}/inbox",
        "outbox_url": f"/users/{actor_data.username}/outbox",
        "followers_url": f"/users/{actor_data.username}/followers",
        "following_url": f"/users/{actor_data.username}/following",
        "public_key_pem": public_key,
        "private_key_pem": private_key,
        "is_local": True,
    }
    created = await gql.create_actor(data)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create actor")
    # GraphQL 目前不回 created_at，先返回基本欄位
    return ActorResponse(
        id=-1,
        username=data["username"],
        display_name=data.get("display_name"),
        summary=data.get("summary"),
        icon_url=data.get("icon_url"),
        is_local=True,
        created_at=""
    )

@router.get("/{username}")
async def get_actor(username: str):
    """取得特定 Actor 資訊"""
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    # 構造最小 Actor 物件以回傳 AP 文件
    from types import SimpleNamespace
    actor_ns = SimpleNamespace(
        username=actor["username"],
        display_name=actor.get("display_name"),
        summary=actor.get("summary"),
        icon_url=actor.get("icon_url"),
        public_key_pem=actor.get("public_key_pem", ""),
    )
    return create_actor_object(actor_ns)
