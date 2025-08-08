"""
聯邦網站管理 API 端點
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.graphql_client import GraphQLClient
from app.core.activitypub.federation_discovery import FederationDiscovery, FederationManager

router = APIRouter()

# Pydantic 模型
class FederationInstanceCreate(BaseModel):
    domain: str
    name: Optional[str] = None
    description: Optional[str] = None
    software: Optional[str] = None
    version: Optional[str] = None
    auto_follow: bool = False
    auto_announce: bool = True
    max_followers: int = 1000
    max_following: int = 1000

class FederationInstanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    is_blocked: Optional[bool] = None
    auto_follow: Optional[bool] = None
    auto_announce: Optional[bool] = None
    max_followers: Optional[int] = None
    max_following: Optional[int] = None

class FederationInstanceResponse(BaseModel):
    id: int
    domain: str
    name: Optional[str]
    description: Optional[str]
    software: Optional[str]
    version: Optional[str]
    is_active: bool
    is_approved: bool
    is_blocked: bool
    last_seen: Optional[datetime]
    last_successful_connection: Optional[datetime]
    user_count: int
    post_count: int
    connection_count: int
    error_count: int
    auto_follow: bool
    auto_announce: bool
    max_followers: int
    max_following: int
    created_at: datetime
    updated_at: Optional[datetime]

class FederationStatsResponse(BaseModel):
    total_instances: int
    active_instances: int
    approved_instances: int
    blocked_instances: int
    discovery_rate: float

class DiscoveryRequest(BaseModel):
    domain: str

class DiscoveryResponse(BaseModel):
    domain: str
    discovered: bool
    instance_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

@router.get("/instances", response_model=List[FederationInstanceResponse])
async def get_federation_instances(
    limit: int = 100,
    offset: int = 0,
    approved_only: bool = False,
    active_only: bool = True,
):
    """取得聯邦實例列表"""
    gql = GraphQLClient()
    instances = await gql.list_federation_instances(limit, offset, approved_only, active_only)
    
    return [
        FederationInstanceResponse(
            id=int(instance['id']) if isinstance(instance.get('id'), str) and instance['id'].isdigit() else instance.get('id', 0),
            domain=instance['domain'],
            name=instance.get('name'),
            description=instance.get('description'),
            software=instance.get('software'),
            version=instance.get('version'),
            is_active=instance.get('is_active', True),
            is_approved=instance.get('is_approved', False),
            is_blocked=instance.get('is_blocked', False),
            last_seen=instance.get('last_seen'),
            last_successful_connection=instance.get('last_successful_connection'),
            user_count=instance.get('user_count', 0),
            post_count=instance.get('post_count', 0),
            connection_count=instance.get('connection_count', 0),
            error_count=instance.get('error_count', 0),
            auto_follow=instance.get('auto_follow', False),
            auto_announce=instance.get('auto_announce', True),
            max_followers=instance.get('max_followers', 0),
            max_following=instance.get('max_following', 0),
            created_at=instance.get('created_at'),
            updated_at=instance.get('updated_at')
        )
        for instance in instances
    ]

@router.get("/instances/{domain}", response_model=FederationInstanceResponse)
async def get_federation_instance(domain: str):
    """取得特定聯邦實例資訊"""
    gql = GraphQLClient()
    instance = await gql.get_federation_instance(domain)
    if not instance:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    return FederationInstanceResponse(
        id=int(instance['id']) if isinstance(instance.get('id'), str) and instance['id'].isdigit() else instance.get('id', 0),
        domain=instance['domain'],
        name=instance.get('name'),
        description=instance.get('description'),
        software=instance.get('software'),
        version=instance.get('version'),
        is_active=instance.get('is_active', True),
        is_approved=instance.get('is_approved', False),
        is_blocked=instance.get('is_blocked', False),
        last_seen=instance.get('last_seen'),
        last_successful_connection=instance.get('last_successful_connection'),
        user_count=instance.get('user_count', 0),
        post_count=instance.get('post_count', 0),
        connection_count=instance.get('connection_count', 0),
        error_count=instance.get('error_count', 0),
        auto_follow=instance.get('auto_follow', False),
        auto_announce=instance.get('auto_announce', True),
        max_followers=instance.get('max_followers', 0),
        max_following=instance.get('max_following', 0),
        created_at=instance.get('created_at'),
        updated_at=instance.get('updated_at')
    )

@router.post("/instances", response_model=FederationInstanceResponse)
async def create_federation_instance(
    instance_data: FederationInstanceCreate,
):
    """手動建立聯邦實例"""
    gql = GraphQLClient()
    exists = await gql.get_federation_instance(instance_data.domain)
    if exists:
        raise HTTPException(status_code=400, detail="Federation instance already exists")

    created = await gql.create_federation_instance({
        "domain": instance_data.domain,
        "name": instance_data.name or instance_data.domain,
        "description": instance_data.description,
        "software": instance_data.software,
        "version": instance_data.version,
        "auto_follow": instance_data.auto_follow,
        "auto_announce": instance_data.auto_announce,
        "max_followers": instance_data.max_followers,
        "max_following": instance_data.max_following,
        "is_active": True,
    })
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create instance")
    inst = await gql.get_federation_instance(instance_data.domain)
    return FederationInstanceResponse(
        id=int(inst['id']) if isinstance(inst.get('id'), str) and inst['id'].isdigit() else inst.get('id', 0),
        domain=inst['domain'],
        name=inst.get('name'),
        description=inst.get('description'),
        software=inst.get('software'),
        version=inst.get('version'),
        is_active=inst.get('is_active', True),
        is_approved=inst.get('is_approved', False),
        is_blocked=inst.get('is_blocked', False),
        last_seen=inst.get('last_seen'),
        last_successful_connection=inst.get('last_successful_connection'),
        user_count=inst.get('user_count', 0),
        post_count=inst.get('post_count', 0),
        connection_count=inst.get('connection_count', 0),
        error_count=inst.get('error_count', 0),
        auto_follow=inst.get('auto_follow', False),
        auto_announce=inst.get('auto_announce', True),
        max_followers=inst.get('max_followers', 0),
        max_following=inst.get('max_following', 0),
        created_at=inst.get('created_at'),
        updated_at=inst.get('updated_at')
    )

@router.put("/instances/{domain}", response_model=FederationInstanceResponse)
async def update_federation_instance(
    domain: str,
    update_data: FederationInstanceUpdate,
):
    """更新聯邦實例設定"""
    gql = GraphQLClient()
    instance = await gql.get_federation_instance(domain)
    if not instance:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    update_dict = update_data.dict(exclude_unset=True)
    ok = await gql.update_federation_instance(instance.get('id'), update_dict)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update instance")
    inst = await gql.get_federation_instance(domain)
    return FederationInstanceResponse(
        id=int(inst['id']) if isinstance(inst.get('id'), str) and inst['id'].isdigit() else inst.get('id', 0),
        domain=inst['domain'],
        name=inst.get('name'),
        description=inst.get('description'),
        software=inst.get('software'),
        version=inst.get('version'),
        is_active=inst.get('is_active', True),
        is_approved=inst.get('is_approved', False),
        is_blocked=inst.get('is_blocked', False),
        last_seen=inst.get('last_seen'),
        last_successful_connection=inst.get('last_successful_connection'),
        user_count=inst.get('user_count', 0),
        post_count=inst.get('post_count', 0),
        connection_count=inst.get('connection_count', 0),
        error_count=inst.get('error_count', 0),
        auto_follow=inst.get('auto_follow', False),
        auto_announce=inst.get('auto_announce', True),
        max_followers=inst.get('max_followers', 0),
        max_following=inst.get('max_following', 0),
        created_at=inst.get('created_at'),
        updated_at=inst.get('updated_at')
    )

@router.post("/instances/{domain}/approve")
async def approve_federation_instance(domain: str):
    """核准聯邦實例"""
    manager = FederationManager(None)
    success = await manager.approve_instance(domain)
    
    if not success:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    return {"message": f"Federation instance {domain} approved successfully"}

@router.post("/instances/{domain}/block")
async def block_federation_instance(domain: str):
    """封鎖聯邦實例"""
    manager = FederationManager(None)
    success = await manager.block_instance(domain)
    
    if not success:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    return {"message": f"Federation instance {domain} blocked successfully"}

@router.post("/instances/{domain}/test")
async def test_federation_instance(domain: str):
    """測試聯邦實例連接"""
    gql = GraphQLClient()
    instance = await gql.get_federation_instance(domain)
    if not instance:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    discovery = FederationDiscovery(None)
    success = await discovery.test_connection(instance)
    
    return {
        "domain": domain,
        "connection_successful": success,
        "last_test": datetime.utcnow()
    }

@router.post("/discover", response_model=DiscoveryResponse)
async def discover_federation_instance(request: DiscoveryRequest):
    """發現新的聯邦實例"""
    discovery = FederationDiscovery(None)
    
    try:
        instance_data = await discovery.discover_instance(request.domain)
        
        if instance_data:
            instance = await discovery.save_instance(instance_data)
            return DiscoveryResponse(
                domain=request.domain,
                discovered=True,
                instance_data={
                    "id": instance.id,
                    "name": instance.name,
                    "software": instance.software,
                    "version": instance.version,
                    "user_count": instance.user_count,
                    "post_count": instance.post_count
                }
            )
        else:
            return DiscoveryResponse(
                domain=request.domain,
                discovered=False,
                error_message="Failed to discover instance"
            )
            
    except Exception as e:
        return DiscoveryResponse(
            domain=request.domain,
            discovered=False,
            error_message=str(e)
        )

@router.post("/discover/auto")
async def auto_discover_instances(background_tasks: BackgroundTasks):
    """自動發現新的聯邦實例"""
    manager = FederationManager(None)
    
    # 在背景執行自動發現
    background_tasks.add_task(manager.auto_discover_instances)
    
    return {"message": "Auto-discovery started in background"}

@router.get("/stats", response_model=FederationStatsResponse)
async def get_federation_stats():
    """取得聯邦統計資訊"""
    manager = FederationManager(None)
    stats = await manager.get_federation_stats()
    
    return FederationStatsResponse(**stats)

@router.post("/test-all")
async def test_all_connections(background_tasks: BackgroundTasks):
    """測試所有聯邦實例的連接"""
    manager = FederationManager(None)
    
    # 在背景執行連接測試
    background_tasks.add_task(manager.test_all_connections)
    
    return {"message": "Connection testing started in background"}

@router.delete("/instances/{domain}")
async def delete_federation_instance(domain: str):
    """刪除聯邦實例"""
    gql = GraphQLClient()
    inst = await gql.get_federation_instance(domain)
    if not inst:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    ok = await gql.delete_federation_instance(inst.get('id'))
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete instance")
    return {"message": f"Federation instance {domain} deleted successfully"}

@router.post("/cleanup")
async def cleanup_old_instances(days: int = 30):
    """清理舊的無效實例"""
    discovery = FederationDiscovery(None)
    count = await discovery.cleanup_old_instances(days)
    
    return {"message": f"Cleaned up {count} old instances"}
