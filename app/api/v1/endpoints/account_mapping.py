"""
帳號發現和映射 API 端點
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.activitypub import AccountMapping, AccountDiscovery, AccountSyncTask
from app.core.activitypub.account_discovery import (
    AccountDiscoveryService, AccountMappingService, AccountSyncService
)

router = APIRouter()

# Pydantic 模型
class AccountDiscoveryRequest(BaseModel):
    method: str  # username, email, profile_url, auto
    query: str  # 搜尋查詢
    domain: Optional[str] = None  # 域名（用於 username 方法）

class AccountDiscoveryResponse(BaseModel):
    discovery_id: int
    actor_id: str
    username: str
    domain: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    summary: Optional[str]
    confidence_score: float

class AccountMappingCreate(BaseModel):
    remote_actor_id: str
    verification_method: str = "manual"

class AccountMappingUpdate(BaseModel):
    sync_enabled: Optional[bool] = None
    sync_posts: Optional[bool] = None
    sync_follows: Optional[bool] = None
    sync_likes: Optional[bool] = None
    sync_announces: Optional[bool] = None

class AccountMappingResponse(BaseModel):
    id: int
    mesh_member_id: str
    remote_actor_id: str
    remote_username: str
    remote_domain: str
    remote_display_name: Optional[str]
    remote_avatar_url: Optional[str]
    remote_summary: Optional[str]
    is_verified: bool
    verification_method: Optional[str]
    verification_date: Optional[datetime]
    sync_enabled: bool
    sync_posts: bool
    sync_follows: bool
    sync_likes: bool
    sync_announces: bool
    last_sync_at: Optional[datetime]
    sync_error_count: int
    remote_follower_count: int
    remote_following_count: int
    remote_post_count: int
    created_at: datetime
    updated_at: Optional[datetime]

class AccountSyncRequest(BaseModel):
    sync_type: str = "posts"  # posts, follows, likes, announces, profile
    since_date: Optional[datetime] = None
    max_items: int = 100

class AccountSyncResponse(BaseModel):
    id: int
    mapping_id: int
    sync_type: str
    status: str
    progress: int
    items_processed: int
    items_synced: int
    items_failed: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

@router.post("/discover", response_model=AccountDiscoveryResponse)
async def discover_account(
    request: AccountDiscoveryRequest,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """發現帳號"""
    discovery_service = AccountDiscoveryService(db)
    
    try:
        if request.method == "username":
            if not request.domain:
                raise HTTPException(status_code=400, detail="Domain is required for username discovery")
            
            # 解析使用者名稱和域名
            if '@' in request.query:
                username, domain = request.query.split('@', 1)
            else:
                username = request.query
                domain = request.domain
            
            result = await discovery_service.discover_account_by_username(
                member_id, username, domain
            )
            
        elif request.method == "email":
            result = await discovery_service.discover_account_by_email(
                member_id, request.query
            )
            
        elif request.method == "profile_url":
            result = await discovery_service.discover_account_by_profile_url(
                member_id, request.query
            )
            
        elif request.method == "auto":
            results = await discovery_service.auto_discover_accounts(member_id)
            if results:
                result = results[0]  # 返回第一個發現的結果
            else:
                result = None
        else:
            raise HTTPException(status_code=400, detail="Invalid discovery method")
        
        if not result:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return AccountDiscoveryResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

@router.get("/discoveries", response_model=List[Dict[str, Any]])
async def get_account_discoveries(
    member_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """取得帳號發現記錄"""
    result = await db.execute(
        select(AccountDiscovery)
        .where(AccountDiscovery.mesh_member_id == member_id)
        .order_by(AccountDiscovery.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    discoveries = result.scalars().all()
    
    return [
        {
            "id": discovery.id,
            "discovery_method": discovery.discovery_method,
            "search_query": discovery.search_query,
            "discovered_actor_id": discovery.discovered_actor_id,
            "discovered_username": discovery.discovered_username,
            "discovered_domain": discovery.discovered_domain,
            "is_successful": discovery.is_successful,
            "confidence_score": discovery.confidence_score,
            "match_reason": discovery.match_reason,
            "created_at": discovery.created_at
        }
        for discovery in discoveries
    ]

@router.post("/mappings", response_model=AccountMappingResponse)
async def create_account_mapping(
    request: AccountMappingCreate,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """建立帳號映射"""
    mapping_service = AccountMappingService(db)
    
    try:
        mapping = await mapping_service.create_account_mapping(
            member_id, request.remote_actor_id, request.verification_method
        )
        
        if not mapping:
            raise HTTPException(status_code=400, detail="Failed to create account mapping")
        
        return AccountMappingResponse(
            id=mapping.id,
            mesh_member_id=mapping.mesh_member_id,
            remote_actor_id=mapping.remote_actor_id,
            remote_username=mapping.remote_username,
            remote_domain=mapping.remote_domain,
            remote_display_name=mapping.remote_display_name,
            remote_avatar_url=mapping.remote_avatar_url,
            remote_summary=mapping.remote_summary,
            is_verified=mapping.is_verified,
            verification_method=mapping.verification_method,
            verification_date=mapping.verification_date,
            sync_enabled=mapping.sync_enabled,
            sync_posts=mapping.sync_posts,
            sync_follows=mapping.sync_follows,
            sync_likes=mapping.sync_likes,
            sync_announces=mapping.sync_announces,
            last_sync_at=mapping.last_sync_at,
            sync_error_count=mapping.sync_error_count,
            remote_follower_count=mapping.remote_follower_count,
            remote_following_count=mapping.remote_following_count,
            remote_post_count=mapping.remote_post_count,
            created_at=mapping.created_at,
            updated_at=mapping.updated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create mapping: {str(e)}")

@router.get("/mappings", response_model=List[AccountMappingResponse])
async def get_account_mappings(
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """取得帳號映射列表"""
    mapping_service = AccountMappingService(db)
    mappings = await mapping_service.get_account_mappings(member_id)
    
    return [
        AccountMappingResponse(
            id=mapping.id,
            mesh_member_id=mapping.mesh_member_id,
            remote_actor_id=mapping.remote_actor_id,
            remote_username=mapping.remote_username,
            remote_domain=mapping.remote_domain,
            remote_display_name=mapping.remote_display_name,
            remote_avatar_url=mapping.remote_avatar_url,
            remote_summary=mapping.remote_summary,
            is_verified=mapping.is_verified,
            verification_method=mapping.verification_method,
            verification_date=mapping.verification_date,
            sync_enabled=mapping.sync_enabled,
            sync_posts=mapping.sync_posts,
            sync_follows=mapping.sync_follows,
            sync_likes=mapping.sync_likes,
            sync_announces=mapping.sync_announces,
            last_sync_at=mapping.last_sync_at,
            sync_error_count=mapping.sync_error_count,
            remote_follower_count=mapping.remote_follower_count,
            remote_following_count=mapping.remote_following_count,
            remote_post_count=mapping.remote_post_count,
            created_at=mapping.created_at,
            updated_at=mapping.updated_at
        )
        for mapping in mappings
    ]

@router.get("/mappings/{mapping_id}", response_model=AccountMappingResponse)
async def get_account_mapping(
    mapping_id: int,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """取得特定帳號映射"""
    result = await db.execute(
        select(AccountMapping).where(
            AccountMapping.id == mapping_id,
            AccountMapping.mesh_member_id == member_id
        )
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    return AccountMappingResponse(
        id=mapping.id,
        mesh_member_id=mapping.mesh_member_id,
        remote_actor_id=mapping.remote_actor_id,
        remote_username=mapping.remote_username,
        remote_domain=mapping.remote_domain,
        remote_display_name=mapping.remote_display_name,
        remote_avatar_url=mapping.remote_avatar_url,
        remote_summary=mapping.remote_summary,
        is_verified=mapping.is_verified,
        verification_method=mapping.verification_method,
        verification_date=mapping.verification_date,
        sync_enabled=mapping.sync_enabled,
        sync_posts=mapping.sync_posts,
        sync_follows=mapping.sync_follows,
        sync_likes=mapping.sync_likes,
        sync_announces=mapping.sync_announces,
        last_sync_at=mapping.last_sync_at,
        sync_error_count=mapping.sync_error_count,
        remote_follower_count=mapping.remote_follower_count,
        remote_following_count=mapping.remote_following_count,
        remote_post_count=mapping.remote_post_count,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at
    )

@router.put("/mappings/{mapping_id}", response_model=AccountMappingResponse)
async def update_account_mapping(
    mapping_id: int,
    request: AccountMappingUpdate,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """更新帳號映射設定"""
    mapping_service = AccountMappingService(db)
    
    # 檢查映射是否屬於該 Member
    result = await db.execute(
        select(AccountMapping).where(
            AccountMapping.id == mapping_id,
            AccountMapping.mesh_member_id == member_id
        )
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    # 更新同步設定
    sync_settings = request.dict(exclude_unset=True)
    success = await mapping_service.update_mapping_sync_settings(mapping_id, sync_settings)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update mapping settings")
    
    # 重新取得更新後的映射
    result = await db.execute(
        select(AccountMapping).where(AccountMapping.id == mapping_id)
    )
    updated_mapping = result.scalar_one_or_none()
    
    return AccountMappingResponse(
        id=updated_mapping.id,
        mesh_member_id=updated_mapping.mesh_member_id,
        remote_actor_id=updated_mapping.remote_actor_id,
        remote_username=updated_mapping.remote_username,
        remote_domain=updated_mapping.remote_domain,
        remote_display_name=updated_mapping.remote_display_name,
        remote_avatar_url=updated_mapping.remote_avatar_url,
        remote_summary=updated_mapping.remote_summary,
        is_verified=updated_mapping.is_verified,
        verification_method=updated_mapping.verification_method,
        verification_date=updated_mapping.verification_date,
        sync_enabled=updated_mapping.sync_enabled,
        sync_posts=updated_mapping.sync_posts,
        sync_follows=updated_mapping.sync_follows,
        sync_likes=updated_mapping.sync_likes,
        sync_announces=updated_mapping.sync_announces,
        last_sync_at=updated_mapping.last_sync_at,
        sync_error_count=updated_mapping.sync_error_count,
        remote_follower_count=updated_mapping.remote_follower_count,
        remote_following_count=updated_mapping.remote_following_count,
        remote_post_count=updated_mapping.remote_post_count,
        created_at=updated_mapping.created_at,
        updated_at=updated_mapping.updated_at
    )

@router.post("/mappings/{mapping_id}/verify")
async def verify_account_mapping(
    mapping_id: int,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """驗證帳號映射"""
    mapping_service = AccountMappingService(db)
    
    # 檢查映射是否屬於該 Member
    result = await db.execute(
        select(AccountMapping).where(
            AccountMapping.id == mapping_id,
            AccountMapping.mesh_member_id == member_id
        )
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    success = await mapping_service.verify_account_mapping(mapping_id, "manual")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to verify account mapping")
    
    return {"message": "Account mapping verified successfully"}

@router.delete("/mappings/{mapping_id}")
async def delete_account_mapping(
    mapping_id: int,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """刪除帳號映射"""
    mapping_service = AccountMappingService(db)
    
    # 檢查映射是否屬於該 Member
    result = await db.execute(
        select(AccountMapping).where(
            AccountMapping.id == mapping_id,
            AccountMapping.mesh_member_id == member_id
        )
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    success = await mapping_service.delete_account_mapping(mapping_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete account mapping")
    
    return {"message": "Account mapping deleted successfully"}

@router.post("/mappings/{mapping_id}/sync", response_model=AccountSyncResponse)
async def sync_account_content(
    mapping_id: int,
    request: AccountSyncRequest,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """同步帳號內容"""
    # 檢查映射是否屬於該 Member
    result = await db.execute(
        select(AccountMapping).where(
            AccountMapping.id == mapping_id,
            AccountMapping.mesh_member_id == member_id
        )
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    sync_service = AccountSyncService(db)
    
    try:
        sync_task = await sync_service.sync_account_content(
            mapping_id, request.sync_type, request.since_date, request.max_items
        )
        
        return AccountSyncResponse(
            id=sync_task.id,
            mapping_id=sync_task.mapping_id,
            sync_type=sync_task.sync_type,
            status=sync_task.status,
            progress=sync_task.progress,
            items_processed=sync_task.items_processed,
            items_synced=sync_task.items_synced,
            items_failed=sync_task.items_failed,
            created_at=sync_task.created_at,
            started_at=sync_task.started_at,
            completed_at=sync_task.completed_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")

@router.get("/mappings/{mapping_id}/sync-tasks", response_model=List[AccountSyncResponse])
async def get_sync_tasks(
    mapping_id: int,
    member_id: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """取得同步任務列表"""
    # 檢查映射是否屬於該 Member
    result = await db.execute(
        select(AccountMapping).where(
            AccountMapping.id == mapping_id,
            AccountMapping.mesh_member_id == member_id
        )
    )
    mapping = result.scalar_one_or_none()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    result = await db.execute(
        select(AccountSyncTask)
        .where(AccountSyncTask.mapping_id == mapping_id)
        .order_by(AccountSyncTask.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    sync_tasks = result.scalars().all()
    
    return [
        AccountSyncResponse(
            id=task.id,
            mapping_id=task.mapping_id,
            sync_type=task.sync_type,
            status=task.status,
            progress=task.progress,
            items_processed=task.items_processed,
            items_synced=task.items_synced,
            items_failed=task.items_failed,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at
        )
        for task in sync_tasks
    ]

@router.get("/sync-tasks/{task_id}", response_model=AccountSyncResponse)
async def get_sync_task(
    task_id: int,
    member_id: str,
    db: AsyncSession = Depends(get_db)
):
    """取得特定同步任務"""
    result = await db.execute(
        select(AccountSyncTask)
        .join(AccountMapping, AccountSyncTask.mapping_id == AccountMapping.id)
        .where(
            AccountSyncTask.id == task_id,
            AccountMapping.mesh_member_id == member_id
        )
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Sync task not found")
    
    return AccountSyncResponse(
        id=task.id,
        mapping_id=task.mapping_id,
        sync_type=task.sync_type,
        status=task.status,
        progress=task.progress,
        items_processed=task.items_processed,
        items_synced=task.items_synced,
        items_failed=task.items_failed,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at
    )
