import httpx
import asyncio
from typing import Dict, Any, List, Optional
"""Federation helpers (no local ORM dependency)"""
from app.core.config import settings
from app.core.activitypub.federation_discovery import FederationDiscovery

async def federate_activity(activity: Dict[str, Any], db=None):
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

async def send_activity_to_instance(activity: Dict[str, Any], instance: Dict[str, Any], db=None):
    """Send activity to federation instance"""
    try:
        # Check instance settings
        if not (instance.get("auto_announce", True)):
            return
        
        transport = httpx.AsyncHTTPTransport(retries=2)
        async with httpx.AsyncClient(timeout=30.0, transport=transport) as client:
            response = await client.post(
                (instance.get("inbox_url") or f"https://{instance.get('domain')}/inbox"),
                json=activity,
                headers={
                    "Content-Type": "application/activity+json",
                    "User-Agent": f"READr-Mesh-ActivityPub/1.0"
                }
            )
            
            if response.status_code in [200, 202]:
                print(f"Successfully sent activity to {instance.get('domain')}")
            else:
                print(f"Failed to send activity to {instance.get('domain')}: {response.status_code}")
                
    except Exception as e:
        print(f"Error sending activity to {instance.get('domain')}: {e}")

async def get_followers_for_activity(activity: Dict[str, Any], db=None) -> List[Dict[str, Any]]:
    """Get followers list for activity（改為透過 GraphQL）"""
    if not db:
        return []
    
    # Extract Actor ID from activity
    actor_id = activity.get("actor")
    if not actor_id:
        return []
    
    # Parse Actor ID to get username
    username = extract_username_from_actor_id(actor_id)
    
    # 改為透過 GraphQL 取得 Actor 與追蹤者
    from app.core.graphql_client import GraphQLClient
    gql = GraphQLClient()
    actor = await gql.get_actor_by_username(username)
    
    if not actor:
        return []
    
    # TODO: 透過 GraphQL 取得追蹤者列表
    # 目前先回傳空列表，待實作 GraphQL 追蹤者查詢
    return []

async def send_activity_to_inbox(activity: Dict[str, Any], follower: Dict[str, Any]):
    """發送活動到追蹤者的收件匣（保留向後相容性）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                follower.get("inbox_url", ""),
                json=activity,
                headers={
                    "Content-Type": "application/activity+json",
                    "User-Agent": f"READr-Mesh-ActivityPub/1.0"
                }
            )
            
            if response.status_code in [200, 202]:
                print(f"Successfully sent activity to {follower.get('inbox_url', '')}")
            else:
                print(f"Failed to send activity to {follower.get('inbox_url', '')}: {response.status_code}")
                
    except Exception as e:
        print(f"Error sending activity to {follower.get('inbox_url', '')}: {e}")

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
