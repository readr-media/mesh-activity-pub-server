"""
帳號發現和映射模組
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse
import difflib

from app.models.activitypub import (
    AccountMapping, AccountDiscovery, AccountSyncTask, 
    Actor, FederationInstance
)
from app.core.config import settings
from app.core.activitypub.federation_discovery import FederationDiscovery

class AccountDiscoveryService:
    """帳號發現服務"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def discover_account_by_username(
        self, 
        mesh_member_id: str, 
        username: str, 
        domain: str
    ) -> Optional[Dict[str, Any]]:
        """透過使用者名稱發現帳號"""
        try:
            # 1. 嘗試 WebFinger 發現
            webfinger_result = await self._discover_via_webfinger(username, domain)
            if webfinger_result:
                return await self._process_discovery_result(
                    mesh_member_id, "webfinger", username, domain, webfinger_result
                )
            
            # 2. 嘗試直接 ActivityPub 端點
            activitypub_result = await self._discover_via_activitypub(username, domain)
            if activitypub_result:
                return await self._process_discovery_result(
                    mesh_member_id, "activitypub", username, domain, activitypub_result
                )
            
            # 3. 嘗試搜尋 API
            search_result = await self._discover_via_search(username, domain)
            if search_result:
                return await self._process_discovery_result(
                    mesh_member_id, "search", username, domain, search_result
                )
            
            return None
            
        except Exception as e:
            print(f"Error discovering account {username}@{domain}: {e}")
            return None
    
    async def discover_account_by_email(
        self, 
        mesh_member_id: str, 
        email: str
    ) -> Optional[Dict[str, Any]]:
        """透過電子郵件發現帳號"""
        try:
            # 解析電子郵件
            username, domain = email.split('@')
            
            # 嘗試多種發現方法
            discovery_methods = [
                ("webfinger", self._discover_via_webfinger),
                ("activitypub", self._discover_via_activitypub),
                ("search", self._discover_via_search)
            ]
            
            for method_name, method_func in discovery_methods:
                try:
                    result = await method_func(username, domain)
                    if result:
                        return await self._process_discovery_result(
                            mesh_member_id, method_name, username, domain, result
                        )
                except Exception as e:
                    print(f"Error with {method_name} discovery: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error discovering account by email {email}: {e}")
            return None
    
    async def discover_account_by_profile_url(
        self, 
        mesh_member_id: str, 
        profile_url: str
    ) -> Optional[Dict[str, Any]]:
        """透過個人資料 URL 發現帳號"""
        try:
            # 解析 URL
            parsed = urlparse(profile_url)
            domain = parsed.netloc
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) >= 2 and path_parts[0] == 'users':
                username = path_parts[1]
                
                # 嘗試取得 Actor 資訊
                actor_result = await self._discover_via_activitypub(username, domain)
                if actor_result:
                    return await self._process_discovery_result(
                        mesh_member_id, "profile_url", username, domain, actor_result
                    )
            
            return None
            
        except Exception as e:
            print(f"Error discovering account by profile URL {profile_url}: {e}")
            return None
    
    async def auto_discover_accounts(self, mesh_member_id: str) -> List[Dict[str, Any]]:
        """自動發現帳號（基於已知資訊）"""
        discovered_accounts = []
        
        # 取得 Member 資訊
        result = await self.db.execute(
            select(Actor).where(Actor.mesh_member_id == mesh_member_id)
        )
        actor = result.scalar_one_or_none()
        
        if not actor:
            return discovered_accounts
        
        # 1. 基於電子郵件發現
        if actor.email:
            email_result = await self.discover_account_by_email(mesh_member_id, actor.email)
            if email_result:
                discovered_accounts.append(email_result)
        
        # 2. 基於使用者名稱搜尋知名實例
        if actor.nickname or actor.username:
            username = actor.nickname or actor.username
            known_instances = await self._get_known_instances()
            
            for instance in known_instances[:5]:  # 只搜尋前5個實例
                try:
                    result = await self.discover_account_by_username(
                        mesh_member_id, username, instance.domain
                    )
                    if result:
                        discovered_accounts.append(result)
                        break  # 找到一個就停止
                except Exception as e:
                    print(f"Error auto-discovering on {instance.domain}: {e}")
                    continue
        
        return discovered_accounts
    
    async def _discover_via_webfinger(self, username: str, domain: str) -> Optional[Dict[str, Any]]:
        """透過 WebFinger 發現帳號"""
        try:
            response = await self.client.get(
                f"https://{domain}/.well-known/webfinger",
                params={"resource": f"acct:{username}@{domain}"},
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 尋找 ActivityPub 相關的連結
                for link in data.get("links", []):
                    if link.get("type") == "application/activity+json":
                        actor_url = link.get("href")
                        if actor_url:
                            # 取得 Actor 資訊
                            actor_info = await self._get_actor_info(actor_url)
                            if actor_info:
                                return {
                                    "actor_id": actor_url,
                                    "username": username,
                                    "domain": domain,
                                    "display_name": actor_info.get("name"),
                                    "avatar_url": actor_info.get("icon", {}).get("url"),
                                    "summary": actor_info.get("summary")
                                }
            
            return None
            
        except Exception as e:
            print(f"Error in WebFinger discovery: {e}")
            return None
    
    async def _discover_via_activitypub(self, username: str, domain: str) -> Optional[Dict[str, Any]]:
        """透過 ActivityPub 端點發現帳號"""
        try:
            actor_url = f"https://{domain}/users/{username}"
            actor_info = await self._get_actor_info(actor_url)
            
            if actor_info:
                return {
                    "actor_id": actor_url,
                    "username": username,
                    "domain": domain,
                    "display_name": actor_info.get("name"),
                    "avatar_url": actor_info.get("icon", {}).get("url"),
                    "summary": actor_info.get("summary")
                }
            
            return None
            
        except Exception as e:
            print(f"Error in ActivityPub discovery: {e}")
            return None
    
    async def _discover_via_search(self, username: str, domain: str) -> Optional[Dict[str, Any]]:
        """透過搜尋 API 發現帳號"""
        try:
            # 嘗試 Mastodon 風格的搜尋 API
            search_urls = [
                f"https://{domain}/api/v1/accounts/search",
                f"https://{domain}/api/v2/search"
            ]
            
            for search_url in search_urls:
                try:
                    response = await self.client.get(
                        search_url,
                        params={"q": username, "limit": 5},
                        headers={"Accept": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        accounts = data.get("accounts", [])
                        
                        for account in accounts:
                            if account.get("username") == username:
                                return {
                                    "actor_id": account.get("id"),
                                    "username": account.get("username"),
                                    "domain": domain,
                                    "display_name": account.get("display_name"),
                                    "avatar_url": account.get("avatar"),
                                    "summary": account.get("note")
                                }
                
                except Exception as e:
                    print(f"Error with search URL {search_url}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error in search discovery: {e}")
            return None
    
    async def _get_actor_info(self, actor_url: str) -> Optional[Dict[str, Any]]:
        """取得 Actor 資訊"""
        try:
            response = await self.client.get(
                actor_url,
                headers={
                    "Accept": "application/activity+json",
                    "User-Agent": f"READr-Mesh-ActivityPub/1.0"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            print(f"Error getting actor info from {actor_url}: {e}")
            return None
    
    async def _process_discovery_result(
        self, 
        mesh_member_id: str, 
        method: str, 
        username: str, 
        domain: str, 
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理發現結果"""
        # 記錄發現
        discovery = AccountDiscovery(
            mesh_member_id=mesh_member_id,
            discovery_method=method,
            search_query=f"{username}@{domain}",
            discovered_actor_id=result.get("actor_id"),
            discovered_username=result.get("username"),
            discovered_domain=result.get("domain"),
            is_successful=True,
            confidence_score=0.8,  # 基礎信心分數
            match_reason=f"Discovered via {method}",
            created_at=datetime.utcnow()
        )
        
        self.db.add(discovery)
        await self.db.commit()
        
        return {
            "discovery_id": discovery.id,
            "actor_id": result.get("actor_id"),
            "username": result.get("username"),
            "domain": result.get("domain"),
            "display_name": result.get("display_name"),
            "avatar_url": result.get("avatar_url"),
            "summary": result.get("summary"),
            "confidence_score": discovery.confidence_score
        }
    
    async def _get_known_instances(self) -> List[FederationInstance]:
        """取得已知的聯邦實例"""
        result = await self.db.execute(
            select(FederationInstance)
            .where(
                FederationInstance.is_active == True,
                FederationInstance.is_approved == True
            )
            .order_by(FederationInstance.user_count.desc())
        )
        return result.scalars().all()

class AccountMappingService:
    """帳號映射服務"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.discovery_service = AccountDiscoveryService(db)
    
    async def create_account_mapping(
        self, 
        mesh_member_id: str, 
        remote_actor_id: str,
        verification_method: str = "manual"
    ) -> Optional[AccountMapping]:
        """建立帳號映射"""
        try:
            # 檢查是否已存在映射
            result = await self.db.execute(
                select(AccountMapping).where(
                    AccountMapping.mesh_member_id == mesh_member_id,
                    AccountMapping.remote_actor_id == remote_actor_id
                )
            )
            existing_mapping = result.scalar_one_or_none()
            
            if existing_mapping:
                return existing_mapping
            
            # 取得本地 Actor
            result = await self.db.execute(
                select(Actor).where(Actor.mesh_member_id == mesh_member_id)
            )
            local_actor = result.scalar_one_or_none()
            
            if not local_actor:
                raise ValueError(f"Local actor not found for member {mesh_member_id}")
            
            # 解析遠端 Actor ID
            parsed = urlparse(remote_actor_id)
            remote_domain = parsed.netloc
            path_parts = parsed.path.strip('/').split('/')
            remote_username = path_parts[-1] if path_parts else ""
            
            # 取得遠端 Actor 資訊
            actor_info = await self.discovery_service._get_actor_info(remote_actor_id)
            
            # 建立映射
            mapping = AccountMapping(
                mesh_member_id=mesh_member_id,
                local_actor_id=local_actor.id,
                remote_actor_id=remote_actor_id,
                remote_username=remote_username,
                remote_domain=remote_domain,
                remote_display_name=actor_info.get("name") if actor_info else None,
                remote_avatar_url=actor_info.get("icon", {}).get("url") if actor_info else None,
                remote_summary=actor_info.get("summary") if actor_info else None,
                is_verified=True,
                verification_method=verification_method,
                verification_date=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(mapping)
            await self.db.commit()
            await self.db.refresh(mapping)
            
            return mapping
            
        except Exception as e:
            print(f"Error creating account mapping: {e}")
            return None
    
    async def get_account_mappings(self, mesh_member_id: str) -> List[AccountMapping]:
        """取得 Member 的所有帳號映射"""
        result = await self.db.execute(
            select(AccountMapping).where(AccountMapping.mesh_member_id == mesh_member_id)
        )
        return result.scalars().all()
    
    async def verify_account_mapping(
        self, 
        mapping_id: int, 
        verification_method: str = "manual"
    ) -> bool:
        """驗證帳號映射"""
        try:
            result = await self.db.execute(
                select(AccountMapping).where(AccountMapping.id == mapping_id)
            )
            mapping = result.scalar_one_or_none()
            
            if not mapping:
                return False
            
            # 更新驗證狀態
            mapping.is_verified = True
            mapping.verification_method = verification_method
            mapping.verification_date = datetime.utcnow()
            mapping.updated_at = datetime.utcnow()
            
            await self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error verifying account mapping: {e}")
            return False
    
    async def update_mapping_sync_settings(
        self, 
        mapping_id: int, 
        sync_settings: Dict[str, bool]
    ) -> bool:
        """更新映射同步設定"""
        try:
            result = await self.db.execute(
                select(AccountMapping).where(AccountMapping.id == mapping_id)
            )
            mapping = result.scalar_one_or_none()
            
            if not mapping:
                return False
            
            # 更新設定
            for key, value in sync_settings.items():
                if hasattr(mapping, key):
                    setattr(mapping, key, value)
            
            mapping.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error updating mapping sync settings: {e}")
            return False
    
    async def delete_account_mapping(self, mapping_id: int) -> bool:
        """刪除帳號映射"""
        try:
            result = await self.db.execute(
                select(AccountMapping).where(AccountMapping.id == mapping_id)
            )
            mapping = result.scalar_one_or_none()
            
            if not mapping:
                return False
            
            await self.db.delete(mapping)
            await self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error deleting account mapping: {e}")
            return False

class AccountSyncService:
    """帳號同步服務"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def sync_account_content(
        self, 
        mapping_id: int, 
        sync_type: str = "posts",
        since_date: Optional[datetime] = None,
        max_items: int = 100
    ) -> AccountSyncTask:
        """同步帳號內容"""
        try:
            # 建立同步任務
            sync_task = AccountSyncTask(
                mapping_id=mapping_id,
                sync_type=sync_type,
                status="pending",
                progress=0,
                since_date=since_date,
                max_items=max_items,
                created_at=datetime.utcnow()
            )
            
            self.db.add(sync_task)
            await self.db.commit()
            await self.db.refresh(sync_task)
            
            # 在背景執行同步
            asyncio.create_task(self._execute_sync_task(sync_task.id))
            
            return sync_task
            
        except Exception as e:
            print(f"Error creating sync task: {e}")
            raise
    
    async def _execute_sync_task(self, task_id: int):
        """執行同步任務"""
        try:
            # 取得任務
            result = await self.db.execute(
                select(AccountSyncTask).where(AccountSyncTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return
            
            # 更新任務狀態
            task.status = "running"
            task.started_at = datetime.utcnow()
            await self.db.commit()
            
            # 取得映射資訊
            result = await self.db.execute(
                select(AccountMapping).where(AccountMapping.id == task.mapping_id)
            )
            mapping = result.scalar_one_or_none()
            
            if not mapping:
                task.status = "failed"
                task.error_message = "Mapping not found"
                await self.db.commit()
                return
            
            # 執行同步
            if task.sync_type == "posts":
                await self._sync_posts(task, mapping)
            elif task.sync_type == "follows":
                await self._sync_follows(task, mapping)
            elif task.sync_type == "likes":
                await self._sync_likes(task, mapping)
            elif task.sync_type == "announces":
                await self._sync_announces(task, mapping)
            elif task.sync_type == "profile":
                await self._sync_profile(task, mapping)
            
            # 更新任務狀態
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.progress = 100
            await self.db.commit()
            
        except Exception as e:
            print(f"Error executing sync task {task_id}: {e}")
            
            # 更新錯誤狀態
            result = await self.db.execute(
                select(AccountSyncTask).where(AccountSyncTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = "failed"
                task.error_message = str(e)
                task.retry_count += 1
                await self.db.commit()
    
    async def _sync_posts(self, task: AccountSyncTask, mapping: AccountMapping):
        """同步貼文"""
        try:
            # 取得遠端貼文
            outbox_url = f"{mapping.remote_actor_id}/outbox"
            
            response = await self.client.get(
                outbox_url,
                headers={"Accept": "application/activity+json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("orderedItems", [])
                
                processed_count = 0
                synced_count = 0
                
                for item in items[:task.max_items]:
                    processed_count += 1
                    
                    if item.get("type") == "Create" and item.get("object", {}).get("type") == "Note":
                        # 處理貼文
                        success = await self._process_post(item, mapping)
                        if success:
                            synced_count += 1
                    
                    # 更新進度
                    task.progress = int((processed_count / min(len(items), task.max_items)) * 100)
                    task.items_processed = processed_count
                    task.items_synced = synced_count
                    await self.db.commit()
                
        except Exception as e:
            print(f"Error syncing posts: {e}")
            raise
    
    async def _process_post(self, activity: Dict[str, Any], mapping: AccountMapping) -> bool:
        """處理貼文"""
        try:
            # 這裡可以實作將遠端貼文轉換為本地 Pick 的邏輯
            # 暫時只記錄處理狀態
            print(f"Processing post from {mapping.remote_actor_id}")
            return True
            
        except Exception as e:
            print(f"Error processing post: {e}")
            return False
    
    async def _sync_follows(self, task: AccountSyncTask, mapping: AccountMapping):
        """同步追蹤關係"""
        # TODO: 實作追蹤關係同步
        pass
    
    async def _sync_likes(self, task: AccountSyncTask, mapping: AccountMapping):
        """同步按讚"""
        # TODO: 實作按讚同步
        pass
    
    async def _sync_announces(self, task: AccountSyncTask, mapping: AccountMapping):
        """同步轉發"""
        # TODO: 實作轉發同步
        pass
    
    async def _sync_profile(self, task: AccountSyncTask, mapping: AccountMapping):
        """同步個人資料"""
        try:
            # 取得遠端個人資料
            response = await self.client.get(
                mapping.remote_actor_id,
                headers={"Accept": "application/activity+json"}
            )
            
            if response.status_code == 200:
                actor_data = response.json()
                
                # 更新映射資訊
                mapping.remote_display_name = actor_data.get("name")
                mapping.remote_avatar_url = actor_data.get("icon", {}).get("url")
                mapping.remote_summary = actor_data.get("summary")
                mapping.updated_at = datetime.utcnow()
                
                await self.db.commit()
                
        except Exception as e:
            print(f"Error syncing profile: {e}")
            raise
