import httpx
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.activitypub import Actor, Follow, FederationInstance, FederationConnection
from app.core.config import settings
from app.core.activitypub.federation_discovery import FederationDiscovery

async def federate_activity(activity: Dict[str, Any], db: AsyncSession = None):
    """Send activity to federation network"""
    if not settings.FEDERATION_ENABLED:
        return
    
    if not db:
        return
    
    # Get all approved federation instances
    discovery = FederationDiscovery(db)
    approved_instances = await discovery.get_approved_instances()
    
    # Send to all approved instances in parallel
    tasks = []
    for instance in approved_instances:
        if instance.is_active and not instance.is_blocked:
            task = send_activity_to_instance(activity, instance, db)
            tasks.append(task)
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def send_activity_to_instance(activity: Dict[str, Any], instance: FederationInstance, db: AsyncSession):
    """Send activity to federation instance"""
    try:
        # Check instance settings
        if not instance.auto_announce:
            return
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                instance.inbox_url,
                json=activity,
                headers={
                    "Content-Type": "application/activity+json",
                    "User-Agent": f"READr-Mesh-ActivityPub/1.0"
                }
            )
            
            # Log connection
            connection = FederationConnection(
                instance_id=instance.id,
                connection_type="activity",
                direction="outbound",
                source_actor=activity.get("actor"),
                target_actor=activity.get("object", {}).get("actor") if isinstance(activity.get("object"), dict) else None,
                activity_id=activity.get("id"),
                status="success" if response.status_code in [200, 202] else "failed",
                error_message=None if response.status_code in [200, 202] else f"HTTP {response.status_code}",
                processed_at=asyncio.get_event_loop().time()
            )
            
            db.add(connection)
            await db.commit()
            
            if response.status_code in [200, 202]:
                print(f"Successfully sent activity to {instance.domain}")
            else:
                print(f"Failed to send activity to {instance.domain}: {response.status_code}")
                
    except Exception as e:
        print(f"Error sending activity to {instance.domain}: {e}")
        
        # Log error connection
        connection = FederationConnection(
            instance_id=instance.id,
            connection_type="activity",
            direction="outbound",
            source_actor=activity.get("actor"),
            target_actor=activity.get("object", {}).get("actor") if isinstance(activity.get("object"), dict) else None,
            activity_id=activity.get("id"),
            status="failed",
            error_message=str(e),
            processed_at=asyncio.get_event_loop().time()
        )
        
        db.add(connection)
        await db.commit()

async def get_followers_for_activity(activity: Dict[str, Any], db: AsyncSession) -> List[Actor]:
    """Get followers list for activity"""
    if not db:
        return []
    
    # Extract Actor ID from activity
    actor_id = activity.get("actor")
    if not actor_id:
        return []
    
    # Parse Actor ID to get username
    username = extract_username_from_actor_id(actor_id)
    
    # Query local Actor
    result = await db.execute(
        select(Actor).where(Actor.username == username)
    )
    local_actor = result.scalar_one_or_none()
    
    if not local_actor:
        return []
    
    # Query all accepted followers
    result = await db.execute(
        select(Follow).where(
            Follow.following_id == local_actor.id,
            Follow.is_accepted == True
        ).options(selectinload(Follow.follower))
    )
    follows = result.scalars().all()
    
    # Filter external followers
    external_followers = []
    for follow in follows:
        if not follow.follower.is_local:
            external_followers.append(follow.follower)
    
    return external_followers

async def send_activity_to_inbox(activity: Dict[str, Any], follower: Actor):
    """發送活動到追蹤者的收件匣（保留向後相容性）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                follower.inbox_url,
                json=activity,
                headers={
                    "Content-Type": "application/activity+json",
                    "User-Agent": f"READr-Mesh-ActivityPub/1.0"
                }
            )
            
            if response.status_code in [200, 202]:
                print(f"Successfully sent activity to {follower.inbox_url}")
            else:
                print(f"Failed to send activity to {follower.inbox_url}: {response.status_code}")
                
    except Exception as e:
        print(f"Error sending activity to {follower.inbox_url}: {e}")

def extract_username_from_actor_id(actor_id: str) -> str:
    """從 Actor ID 中提取使用者名稱"""
    if not actor_id:
        return ""
    
    # 格式: https://domain.com/users/username
    parts = actor_id.split("/")
    return parts[-1] if parts else ""

def is_public_activity(activity: Dict[str, Any]) -> bool:
    """檢查活動是否為公開"""
    to = activity.get("to", [])
    cc = activity.get("cc", [])
    
    public_uris = [
        "https://www.w3.org/ns/activitystreams#Public",
        "as:Public",
        "Public"
    ]
    
    # 檢查 to 欄位
    for uri in public_uris:
        if uri in to:
            return True
    
    # 檢查 cc 欄位
    for uri in public_uris:
        if uri in cc:
            return True
    
    return False

async def discover_actor(actor_id: str) -> Optional[Dict[str, Any]]:
    """發現遠端 Actor"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                actor_id,
                headers={
                    "Accept": "application/activity+json",
                    "User-Agent": f"READr-Mesh-ActivityPub/1.0"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to discover actor {actor_id}: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"Error discovering actor {actor_id}: {e}")
        return None

async def verify_actor_signature(signature: str, actor_id: str, data: str) -> bool:
    """驗證 Actor 簽名"""
    # TODO: 實作簽名驗證
    return True
