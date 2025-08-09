"""
帳號發現和映射 API 端點
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# 移除對本地 ORM 模型的依賴，改為純 GraphQL
from app.core.activitypub.account_discovery import (
    AccountDiscoveryService, AccountMappingService, AccountSyncService
)
from app.core.graphql_client import GraphQLClient

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
):
    """發現帳號"""
    discovery_service = AccountDiscoveryService(None)
    
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
):
    """取得帳號發現記錄"""
    gql = GraphQLClient()
    discoveries = await gql.list_account_discoveries(member_id, limit, offset)
    return discoveries

@router.post("/mappings", response_model=AccountMappingResponse)
async def create_account_mapping(
    request: AccountMappingCreate,
    member_id: str,
):
    """建立帳號映射"""
    mapping_service = AccountMappingService(None)
    
    try:
        mapping = await mapping_service.create_account_mapping(
            member_id, request.remote_actor_id, request.verification_method
        )
        
        if not mapping:
            raise HTTPException(status_code=400, detail="Failed to create account mapping")
        
        return AccountMappingResponse(
            id=int(mapping.get("id") or 0) if str(mapping.get("id", "")).isdigit() else mapping.get("id"),
            mesh_member_id=(mapping.get("mesh_member") or {}).get("id"),
            remote_actor_id=mapping.get("remote_actor_id"),
            remote_username=mapping.get("remote_username"),
            remote_domain=mapping.get("remote_domain"),
            remote_display_name=mapping.get("remote_display_name"),
            remote_avatar_url=mapping.get("remote_avatar_url"),
            remote_summary=mapping.get("remote_summary"),
            is_verified=mapping.get("is_verified", False),
            verification_method=mapping.get("verification_method"),
            verification_date=mapping.get("verification_date"),
            sync_enabled=mapping.get("sync_enabled", True),
            sync_posts=mapping.get("sync_posts", True),
            sync_follows=mapping.get("sync_follows", False),
            sync_likes=mapping.get("sync_likes", False),
            sync_announces=mapping.get("sync_announces", False),
            last_sync_at=mapping.get("last_sync_at"),
            sync_error_count=mapping.get("sync_error_count", 0),
            remote_follower_count=mapping.get("remote_follower_count", 0),
            remote_following_count=mapping.get("remote_following_count", 0),
            remote_post_count=mapping.get("remote_post_count", 0),
            created_at=mapping.get("created_at"),
            updated_at=mapping.get("updated_at")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create mapping: {str(e)}")

@router.get("/mappings", response_model=List[AccountMappingResponse])
async def get_account_mappings(
    member_id: str,
):
    """取得帳號映射列表"""
    mapping_service = AccountMappingService(None)
    mappings = await mapping_service.get_account_mappings(member_id)
    
    return [
        AccountMappingResponse(
            id=int(m.get("id") or 0) if str(m.get("id", "")).isdigit() else m.get("id"),
            mesh_member_id=(m.get("mesh_member") or {}).get("id"),
            remote_actor_id=m.get("remote_actor_id"),
            remote_username=m.get("remote_username"),
            remote_domain=m.get("remote_domain"),
            remote_display_name=m.get("remote_display_name"),
            remote_avatar_url=m.get("remote_avatar_url"),
            remote_summary=m.get("remote_summary"),
            is_verified=m.get("is_verified", False),
            verification_method=m.get("verification_method"),
            verification_date=m.get("verification_date"),
            sync_enabled=m.get("sync_enabled", True),
            sync_posts=m.get("sync_posts", True),
            sync_follows=m.get("sync_follows", False),
            sync_likes=m.get("sync_likes", False),
            sync_announces=m.get("sync_announces", False),
            last_sync_at=m.get("last_sync_at"),
            sync_error_count=m.get("sync_error_count", 0),
            remote_follower_count=m.get("remote_follower_count", 0),
            remote_following_count=m.get("remote_following_count", 0),
            remote_post_count=m.get("remote_post_count", 0),
            created_at=m.get("created_at"),
            updated_at=m.get("updated_at")
        )
        for m in mappings
    ]

@router.get("/mappings/{mapping_id}", response_model=AccountMappingResponse)
async def get_account_mapping(
    mapping_id: int,
    member_id: str,
):
    """取得特定帳號映射（透過 GraphQL）"""
    gql = GraphQLClient()
    mapping = await gql.get_account_mapping_by_id(str(mapping_id))
    if not mapping or mapping.get("mesh_member", {}).get("id") != member_id:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    return AccountMappingResponse(
        id=int(mapping.get("id") or 0) if str(mapping.get("id", "")).isdigit() else mapping.get("id"),
        mesh_member_id=mapping.get("mesh_member", {}).get("id"),
        remote_actor_id=mapping.get("remote_actor_id"),
        remote_username=mapping.get("remote_username"),
        remote_domain=mapping.get("remote_domain"),
        remote_display_name=mapping.get("remote_display_name"),
        remote_avatar_url=mapping.get("remote_avatar_url"),
        remote_summary=mapping.get("remote_summary"),
        is_verified=mapping.get("is_verified", False),
        verification_method=mapping.get("verification_method"),
        verification_date=mapping.get("verification_date"),
        sync_enabled=mapping.get("sync_enabled", True),
        sync_posts=mapping.get("sync_posts", True),
        sync_follows=mapping.get("sync_follows", False),
        sync_likes=mapping.get("sync_likes", False),
        sync_announces=mapping.get("sync_announces", False),
        last_sync_at=mapping.get("last_sync_at"),
        sync_error_count=mapping.get("sync_error_count", 0),
        remote_follower_count=mapping.get("remote_follower_count", 0),
        remote_following_count=mapping.get("remote_following_count", 0),
        remote_post_count=mapping.get("remote_post_count", 0),
        created_at=mapping.get("created_at"),
        updated_at=mapping.get("updated_at"),
    )

@router.put("/mappings/{mapping_id}", response_model=AccountMappingResponse)
async def update_account_mapping(
    mapping_id: int,
    request: AccountMappingUpdate,
    member_id: str,
):
    """更新帳號映射設定"""
    mapping_service = AccountMappingService(None)
    
    gql = GraphQLClient()
    mapping = await gql.get_account_mapping_by_id(str(mapping_id))
    if not mapping or mapping.get("mesh_member", {}).get("id") != member_id:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    # 更新同步設定
    sync_settings = request.dict(exclude_unset=True)
    success = await mapping_service.update_mapping_sync_settings(mapping_id, sync_settings)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update mapping settings")
    
    # 重新取得更新後的映射
    updated = await gql.get_account_mapping_by_id(str(mapping_id))
    
    return AccountMappingResponse(
        id=int(updated.get("id") or 0) if str(updated.get("id", "")).isdigit() else updated.get("id"),
        mesh_member_id=updated.get("mesh_member", {}).get("id"),
        remote_actor_id=updated.get("remote_actor_id"),
        remote_username=updated.get("remote_username"),
        remote_domain=updated.get("remote_domain"),
        remote_display_name=updated.get("remote_display_name"),
        remote_avatar_url=updated.get("remote_avatar_url"),
        remote_summary=updated.get("remote_summary"),
        is_verified=updated.get("is_verified", False),
        verification_method=updated.get("verification_method"),
        verification_date=updated.get("verification_date"),
        sync_enabled=updated.get("sync_enabled", True),
        sync_posts=updated.get("sync_posts", True),
        sync_follows=updated.get("sync_follows", False),
        sync_likes=updated.get("sync_likes", False),
        sync_announces=updated.get("sync_announces", False),
        last_sync_at=updated.get("last_sync_at"),
        sync_error_count=updated.get("sync_error_count", 0),
        remote_follower_count=updated.get("remote_follower_count", 0),
        remote_following_count=updated.get("remote_following_count", 0),
        remote_post_count=updated.get("remote_post_count", 0),
        created_at=updated.get("created_at"),
        updated_at=updated.get("updated_at")
    )

@router.post("/mappings/{mapping_id}/verify")
async def verify_account_mapping(
    mapping_id: int,
    member_id: str,
):
    """驗證帳號映射"""
    mapping_service = AccountMappingService(None)
    
    gql = GraphQLClient()
    mapping = await gql.get_account_mapping_by_id(str(mapping_id))
    if not mapping or mapping.get("mesh_member", {}).get("id") != member_id:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    success = await mapping_service.verify_account_mapping(mapping_id, "manual")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to verify account mapping")
    
    return {"message": "Account mapping verified successfully"}

@router.delete("/mappings/{mapping_id}")
async def delete_account_mapping(
    mapping_id: int,
    member_id: str,
):
    """刪除帳號映射"""
    mapping_service = AccountMappingService(db)
    
    gql = GraphQLClient()
    mapping = await gql.get_account_mapping_by_id(str(mapping_id))
    if not mapping or mapping.get("mesh_member", {}).get("id") != member_id:
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
):
    """同步帳號內容"""
    # 檢查映射是否屬於該 Member
    gql = GraphQLClient()
    mapping = await gql.get_account_mapping_by_id(str(mapping_id))
    if mapping and mapping.get("mesh_member", {}).get("id") != member_id:
        mapping = None
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    sync_service = AccountSyncService(None)
    
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
):
    """取得同步任務列表"""
    # 檢查映射是否屬於該 Member
    gql = GraphQLClient()
    mapping = await gql.get_account_mapping_by_id(str(mapping_id))
    if mapping and mapping.get("mesh_member", {}).get("id") != member_id:
        mapping = None
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Account mapping not found")
    
    tasks = await gql.list_account_sync_tasks(str(mapping_id), limit, offset)
    
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
        for task in tasks
    ]

@router.get("/sync-tasks/{task_id}", response_model=AccountSyncResponse)
async def get_sync_task(
    task_id: int,
    member_id: str,
):
    """取得特定同步任務"""
    gql = GraphQLClient()
    task = await gql.get_account_sync_task(str(task_id))
    if not task or task.get("mapping", {}).get("id") != str(mapping_id):
        raise HTTPException(status_code=404, detail="Sync task not found")
    return AccountSyncResponse(
        id=task.get("id"),
        mapping_id=task.get("mapping", {}).get("id"),
        sync_type=task.get("sync_type"),
        status=task.get("status"),
        progress=task.get("progress", 0),
        items_processed=task.get("items_processed", 0),
        items_synced=task.get("items_synced", 0),
        items_failed=task.get("items_failed", 0),
        created_at=task.get("created_at"),
        started_at=task.get("started_at"),
        completed_at=task.get("completed_at"),
    )
