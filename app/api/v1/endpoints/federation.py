"""
聯邦網站管理 API 端點
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.activitypub import FederationInstance, FederationConnection, FederationActivity
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
    db: AsyncSession = Depends(get_db)
):
    """取得聯邦實例列表"""
    query = select(FederationInstance)
    
    if approved_only:
        query = query.where(FederationInstance.is_approved == True)
    
    if active_only:
        query = query.where(FederationInstance.is_active == True)
    
    query = query.order_by(FederationInstance.last_seen.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    instances = result.scalars().all()
    
    return [
        FederationInstanceResponse(
            id=instance.id,
            domain=instance.domain,
            name=instance.name,
            description=instance.description,
            software=instance.software,
            version=instance.version,
            is_active=instance.is_active,
            is_approved=instance.is_approved,
            is_blocked=instance.is_blocked,
            last_seen=instance.last_seen,
            last_successful_connection=instance.last_successful_connection,
            user_count=instance.user_count,
            post_count=instance.post_count,
            connection_count=instance.connection_count,
            error_count=instance.error_count,
            auto_follow=instance.auto_follow,
            auto_announce=instance.auto_announce,
            max_followers=instance.max_followers,
            max_following=instance.max_following,
            created_at=instance.created_at,
            updated_at=instance.updated_at
        )
        for instance in instances
    ]

@router.get("/instances/{domain}", response_model=FederationInstanceResponse)
async def get_federation_instance(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """取得特定聯邦實例資訊"""
    result = await db.execute(
        select(FederationInstance).where(FederationInstance.domain == domain)
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    return FederationInstanceResponse(
        id=instance.id,
        domain=instance.domain,
        name=instance.name,
        description=instance.description,
        software=instance.software,
        version=instance.version,
        is_active=instance.is_active,
        is_approved=instance.is_approved,
        is_blocked=instance.is_blocked,
        last_seen=instance.last_seen,
        last_successful_connection=instance.last_successful_connection,
        user_count=instance.user_count,
        post_count=instance.post_count,
        connection_count=instance.connection_count,
        error_count=instance.error_count,
        auto_follow=instance.auto_follow,
        auto_announce=instance.auto_announce,
        max_followers=instance.max_followers,
        max_following=instance.max_following,
        created_at=instance.created_at,
        updated_at=instance.updated_at
    )

@router.post("/instances", response_model=FederationInstanceResponse)
async def create_federation_instance(
    instance_data: FederationInstanceCreate,
    db: AsyncSession = Depends(get_db)
):
    """手動建立聯邦實例"""
    # 檢查是否已存在
    result = await db.execute(
        select(FederationInstance).where(FederationInstance.domain == instance_data.domain)
    )
    existing_instance = result.scalar_one_or_none()
    
    if existing_instance:
        raise HTTPException(status_code=400, detail="Federation instance already exists")
    
    # 建立新實例
    instance = FederationInstance(
        domain=instance_data.domain,
        name=instance_data.name or instance_data.domain,
        description=instance_data.description,
        software=instance_data.software,
        version=instance_data.version,
        auto_follow=instance_data.auto_follow,
        auto_announce=instance_data.auto_announce,
        max_followers=instance_data.max_followers,
        max_following=instance_data.max_following,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_seen=datetime.utcnow()
    )
    
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    
    return FederationInstanceResponse(
        id=instance.id,
        domain=instance.domain,
        name=instance.name,
        description=instance.description,
        software=instance.software,
        version=instance.version,
        is_active=instance.is_active,
        is_approved=instance.is_approved,
        is_blocked=instance.is_blocked,
        last_seen=instance.last_seen,
        last_successful_connection=instance.last_successful_connection,
        user_count=instance.user_count,
        post_count=instance.post_count,
        connection_count=instance.connection_count,
        error_count=instance.error_count,
        auto_follow=instance.auto_follow,
        auto_announce=instance.auto_announce,
        max_followers=instance.max_followers,
        max_following=instance.max_following,
        created_at=instance.created_at,
        updated_at=instance.updated_at
    )

@router.put("/instances/{domain}", response_model=FederationInstanceResponse)
async def update_federation_instance(
    domain: str,
    update_data: FederationInstanceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新聯邦實例設定"""
    result = await db.execute(
        select(FederationInstance).where(FederationInstance.domain == domain)
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    # 更新欄位
    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(instance, key, value)
    
    instance.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(instance)
    
    return FederationInstanceResponse(
        id=instance.id,
        domain=instance.domain,
        name=instance.name,
        description=instance.description,
        software=instance.software,
        version=instance.version,
        is_active=instance.is_active,
        is_approved=instance.is_approved,
        is_blocked=instance.is_blocked,
        last_seen=instance.last_seen,
        last_successful_connection=instance.last_successful_connection,
        user_count=instance.user_count,
        post_count=instance.post_count,
        connection_count=instance.connection_count,
        error_count=instance.error_count,
        auto_follow=instance.auto_follow,
        auto_announce=instance.auto_announce,
        max_followers=instance.max_followers,
        max_following=instance.max_following,
        created_at=instance.created_at,
        updated_at=instance.updated_at
    )

@router.post("/instances/{domain}/approve")
async def approve_federation_instance(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """核准聯邦實例"""
    manager = FederationManager(db)
    success = await manager.approve_instance(domain)
    
    if not success:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    return {"message": f"Federation instance {domain} approved successfully"}

@router.post("/instances/{domain}/block")
async def block_federation_instance(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """封鎖聯邦實例"""
    manager = FederationManager(db)
    success = await manager.block_instance(domain)
    
    if not success:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    return {"message": f"Federation instance {domain} blocked successfully"}

@router.post("/instances/{domain}/test")
async def test_federation_instance(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """測試聯邦實例連接"""
    result = await db.execute(
        select(FederationInstance).where(FederationInstance.domain == domain)
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    discovery = FederationDiscovery(db)
    success = await discovery.test_connection(instance)
    
    return {
        "domain": domain,
        "connection_successful": success,
        "last_test": datetime.utcnow()
    }

@router.post("/discover", response_model=DiscoveryResponse)
async def discover_federation_instance(
    request: DiscoveryRequest,
    db: AsyncSession = Depends(get_db)
):
    """發現新的聯邦實例"""
    discovery = FederationDiscovery(db)
    
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
async def auto_discover_instances(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """自動發現新的聯邦實例"""
    manager = FederationManager(db)
    
    # 在背景執行自動發現
    background_tasks.add_task(manager.auto_discover_instances)
    
    return {"message": "Auto-discovery started in background"}

@router.get("/stats", response_model=FederationStatsResponse)
async def get_federation_stats(
    db: AsyncSession = Depends(get_db)
):
    """取得聯邦統計資訊"""
    manager = FederationManager(db)
    stats = await manager.get_federation_stats()
    
    return FederationStatsResponse(**stats)

@router.post("/test-all")
async def test_all_connections(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """測試所有聯邦實例的連接"""
    manager = FederationManager(db)
    
    # 在背景執行連接測試
    background_tasks.add_task(manager.test_all_connections)
    
    return {"message": "Connection testing started in background"}

@router.delete("/instances/{domain}")
async def delete_federation_instance(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """刪除聯邦實例"""
    result = await db.execute(
        select(FederationInstance).where(FederationInstance.domain == domain)
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Federation instance not found")
    
    await db.delete(instance)
    await db.commit()
    
    return {"message": f"Federation instance {domain} deleted successfully"}

@router.post("/cleanup")
async def cleanup_old_instances(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """清理舊的無效實例"""
    discovery = FederationDiscovery(db)
    count = await discovery.cleanup_old_instances(days)
    
    return {"message": f"Cleaned up {count} old instances"}
