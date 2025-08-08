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
from app.core.graphql_client import GraphQLClient

class AccountDiscoveryService:
    """帳號發現服務"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
        self.gql = GraphQLClient()
    
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
        
        # 以 GQL 取得 Member 資訊（不再查本地 Actor）
        actor = await self.gql.get_member(mesh_member_id)
        
        if not actor:
            return discovered_accounts
        
        # 1. 基於電子郵件發現
        email = actor.get("email") if isinstance(actor, dict) else getattr(actor, "email", None)
        if email:
            email_result = await self.discover_account_by_email(mesh_member_id, email)
            if email_result:
                discovered_accounts.append(email_result)
        
        # 2. 基於使用者名稱搜尋知名實例
        nickname = actor.get("nickname") if isinstance(actor, dict) else getattr(actor, "nickname", None)
        username_field = actor.get("name") if isinstance(actor, dict) else getattr(actor, "username", None)
        if nickname or username_field:
            username = nickname or username_field
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
        # 改為記錄到 Keystone 的 AccountDiscovery
        data = {
            "mesh_member": {"connect": {"id": mesh_member_id}},
            "discovery_method": method,
            "search_query": f"{username}@{domain}",
            "discovered_actor_id": result.get("actor_id"),
            "discovered_username": result.get("username"),
            "discovered_domain": result.get("domain"),
            "is_successful": True,
            "confidence_score": 0.8,
            "match_reason": f"Discovered via {method}",
        }
        created = await self.gql.create_account_discovery(data)
        return {
            "discovery_id": (created or {}).get("id", ""),
            "actor_id": result.get("actor_id"),
            "username": result.get("username"),
            "domain": result.get("domain"),
            "display_name": result.get("display_name"),
            "avatar_url": result.get("avatar_url"),
            "summary": result.get("summary"),
            "confidence_score": (created or {}).get("confidence_score", 0.8),
        }
    
    async def _get_known_instances(self) -> List[FederationInstance]:
        """取得已知的聯邦實例（透過 GraphQL）"""
        from app.core.graphql_client import GraphQLClient
        gql = GraphQLClient()
        instances = await gql.list_federation_instances(limit=50, offset=0, approved_only=True, active_only=True)
        # 為了沿用既有程式碼回傳物件具有 .domain 屬性
        from types import SimpleNamespace
        return [SimpleNamespace(domain=i.get("domain")) for i in instances]

class AccountMappingService:
    """帳號映射服務"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.discovery_service = AccountDiscoveryService(db)
        self.gql = GraphQLClient()
    
    async def create_account_mapping(
        self, 
        mesh_member_id: str, 
        remote_actor_id: str,
        verification_method: str = "manual"
    ) -> Optional[AccountMapping]:
        """建立帳號映射"""
        try:
            # 檢查是否已存在映射（GQL）
            existing = await self.gql.get_account_mapping_by_member_and_remote_actor(mesh_member_id, remote_actor_id)
            if existing:
                return existing
            # 解析遠端 Actor ID
            parsed = urlparse(remote_actor_id)
            remote_domain = parsed.netloc
            path_parts = parsed.path.strip('/').split('/')
            remote_username = path_parts[-1] if path_parts else ""
            # 取得遠端 Actor 資訊（HTTP）
            actor_info = await self.discovery_service._get_actor_info(remote_actor_id)
            # 建立映射（GQL）
            data = {
                "mesh_member": {"connect": {"id": mesh_member_id}},
                "remote_actor_id": remote_actor_id,
                "remote_username": remote_username,
                "remote_domain": remote_domain,
                "remote_display_name": (actor_info or {}).get("name"),
                "remote_avatar_url": ((actor_info or {}).get("icon") or {}).get("url"),
                "remote_summary": (actor_info or {}).get("summary"),
                "is_verified": True,
                "verification_method": verification_method,
                "verification_date": datetime.utcnow().isoformat(),
            }
            created = await self.gql.create_account_mapping(data)
            return created
        except Exception as e:
            print(f"Error creating account mapping: {e}")
            return None
    
    async def get_account_mappings(self, mesh_member_id: str) -> List[AccountMapping]:
        """取得 Member 的所有帳號映射"""
        return await self.gql.get_account_mappings(mesh_member_id)
    
    async def verify_account_mapping(
        self, 
        mapping_id: int, 
        verification_method: str = "manual"
    ) -> bool:
        """驗證帳號映射"""
        try:
            mapping = await self.gql.get_account_mapping_by_id(str(mapping_id))
            if not mapping:
                return False
            data = {
                "is_verified": True,
                "verification_method": verification_method,
                "verification_date": datetime.utcnow().isoformat(),
            }
            updated = await self.gql.update_account_mapping(str(mapping_id), data)
            return bool(updated)
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
            updated = await self.gql.update_account_mapping(str(mapping_id), sync_settings)
            return bool(updated)
        except Exception as e:
            print(f"Error updating mapping sync settings: {e}")
            return False
    
    async def delete_account_mapping(self, mapping_id: int) -> bool:
        """刪除帳號映射"""
        try:
            return await self.gql.delete_account_mapping(str(mapping_id))
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
            # 建立同步任務（GQL）
            data = {
                "mapping": {"connect": {"id": str(mapping_id)}},
                "sync_type": sync_type,
                "status": "pending",
                "progress": 0,
                "since_date": since_date.isoformat() if since_date else None,
                "max_items": max_items,
                "created_at": datetime.utcnow().isoformat(),
            }
            created = await self.gql.create_account_sync_task(data)
            # 在背景執行同步
            if created:
                asyncio.create_task(self._execute_sync_task(created["id"]))
            return created  # 回傳 GQL 物件
        except Exception as e:
            print(f"Error creating sync task: {e}")
            raise
    
    async def _execute_sync_task(self, task_id: int):
        """執行同步任務"""
        try:
            # 取得任務（GQL）
            task = await self.gql.get_account_sync_task(str(task_id))
            if not task:
                return
            # 更新任務狀態 -> running
            await self.gql.update_account_sync_task(task["id"], {
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
            })
            # 取得映射資訊（GQL）
            mapping = await self.gql.get_account_mapping_by_id(task["mapping"]["id"] if isinstance(task.get("mapping"), dict) else task.get("mapping"))
            if not mapping:
                await self.gql.update_account_sync_task(task["id"], {
                    "status": "failed",
                    "error_message": "Mapping not found",
                })
                return
            # 執行同步
            if task["sync_type"] == "posts":
                await self._sync_posts(task, mapping)
            elif task["sync_type"] == "follows":
                await self._sync_follows(task, mapping)
            elif task["sync_type"] == "likes":
                await self._sync_likes(task, mapping)
            elif task["sync_type"] == "announces":
                await self._sync_announces(task, mapping)
            elif task["sync_type"] == "profile":
                await self._sync_profile(task, mapping)
            # 完成
            await self.gql.update_account_sync_task(task["id"], {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "progress": 100,
            })
        except Exception as e:
            print(f"Error executing sync task {task_id}: {e}")
            # 失敗狀態
            await self.gql.update_account_sync_task(str(task_id), {
                "status": "failed",
                "error_message": str(e),
            })
    
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
                    await self.gql.update_account_sync_task(task["id"], {
                        "progress": int((processed_count / min(len(items), task.get("max_items", len(items)))) * 100),
                        "items_processed": processed_count,
                        "items_synced": synced_count,
                    })
                
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
