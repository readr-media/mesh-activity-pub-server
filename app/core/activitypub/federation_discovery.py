"""
聯邦網站發現和管理模組
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse

from app.models.activitypub import FederationInstance, FederationConnection
from app.core.graphql_client import GraphQLClient
from app.core.config import settings

class FederationDiscovery:
    """聯邦網站發現器"""
    
    def __init__(self, db: AsyncSession | None):
        self.db = db
        self.gql = GraphQLClient()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def discover_instance(self, domain: str) -> Optional[Dict[str, Any]]:
        """發現聯邦實例"""
        try:
            # 1. 嘗試取得 NodeInfo
            nodeinfo = await self._get_nodeinfo(domain)
            if nodeinfo:
                return await self._process_nodeinfo(domain, nodeinfo)
            
            # 2. 嘗試 WebFinger
            webfinger = await self._get_webfinger(domain)
            if webfinger:
                return await self._process_webfinger(domain, webfinger)
            
            # 3. 嘗試直接 ActivityPub 端點
            activitypub = await self._get_activitypub_info(domain)
            if activitypub:
                return await self._process_activitypub(domain, activitypub)
            
            return None
            
        except Exception as e:
            print(f"Error discovering instance {domain}: {e}")
            return None
    
    async def _get_nodeinfo(self, domain: str) -> Optional[Dict[str, Any]]:
        """取得 NodeInfo 資訊"""
        try:
            # 嘗試 NodeInfo 2.0
            response = await self.client.get(
                f"https://{domain}/.well-known/nodeinfo/2.0",
                headers={"Accept": "application/json"}
            )
            if response.status_code == 200:
                return response.json()
            
            # 嘗試 NodeInfo 1.0
            response = await self.client.get(
                f"https://{domain}/.well-known/nodeinfo/1.0",
                headers={"Accept": "application/json"}
            )
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            print(f"Error getting NodeInfo for {domain}: {e}")
            return None
    
    async def _get_webfinger(self, domain: str) -> Optional[Dict[str, Any]]:
        """取得 WebFinger 資訊"""
        try:
            # 使用一個測試帳號來取得 WebFinger 資訊
            response = await self.client.get(
                f"https://{domain}/.well-known/webfinger",
                params={"resource": f"acct:test@{domain}"},
                headers={"Accept": "application/json"}
            )
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            print(f"Error getting WebFinger for {domain}: {e}")
            return None
    
    async def _get_activitypub_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """取得 ActivityPub 資訊"""
        try:
            # 嘗試取得實例的 Actor 資訊
            response = await self.client.get(
                f"https://{domain}/users/admin",
                headers={"Accept": "application/activity+json"}
            )
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            print(f"Error getting ActivityPub info for {domain}: {e}")
            return None
    
    async def _process_nodeinfo(self, domain: str, nodeinfo: Dict[str, Any]) -> Dict[str, Any]:
        """處理 NodeInfo 資訊"""
        metadata = nodeinfo.get("metadata", {})
        
        return {
            "domain": domain,
            "name": metadata.get("nodeName", domain),
            "description": metadata.get("nodeDescription", ""),
            "software": nodeinfo.get("software", {}).get("name", "Unknown"),
            "version": nodeinfo.get("software", {}).get("version", ""),
            "user_count": nodeinfo.get("usage", {}).get("users", {}).get("total", 0),
            "post_count": nodeinfo.get("usage", {}).get("localPosts", 0),
            "protocols": nodeinfo.get("protocols", []),
            "nodeinfo_url": f"https://{domain}/.well-known/nodeinfo/2.0",
            "webfinger_url": f"https://{domain}/.well-known/webfinger",
            "inbox_url": f"https://{domain}/inbox",
            "outbox_url": f"https://{domain}/outbox"
        }
    
    async def _process_webfinger(self, domain: str, webfinger: Dict[str, Any]) -> Dict[str, Any]:
        """處理 WebFinger 資訊"""
        return {
            "domain": domain,
            "name": domain,
            "description": "",
            "software": "Unknown",
            "version": "",
            "user_count": 0,
            "post_count": 0,
            "protocols": ["activitypub"],
            "webfinger_url": f"https://{domain}/.well-known/webfinger",
            "inbox_url": f"https://{domain}/inbox",
            "outbox_url": f"https://{domain}/outbox"
        }
    
    async def _process_activitypub(self, domain: str, activitypub: Dict[str, Any]) -> Dict[str, Any]:
        """處理 ActivityPub 資訊"""
        return {
            "domain": domain,
            "name": activitypub.get("name", domain),
            "description": activitypub.get("summary", ""),
            "software": "Unknown",
            "version": "",
            "user_count": 0,
            "post_count": 0,
            "protocols": ["activitypub"],
            "inbox_url": activitypub.get("inbox", f"https://{domain}/inbox"),
            "outbox_url": activitypub.get("outbox", f"https://{domain}/outbox")
        }
    
    async def save_instance(self, instance_data: Dict[str, Any]) -> Dict[str, Any]:
        """儲存聯邦實例（改用 GraphQL）"""
        # 先查是否存在
        existing = await self.gql.get_federation_instance(instance_data["domain"])
        data = {
            "domain": instance_data["domain"],
            "name": instance_data.get("name") or instance_data["domain"],
            "description": instance_data.get("description", ""),
            "software": instance_data.get("software"),
            "version": instance_data.get("version"),
            "user_count": instance_data.get("user_count", 0),
            "post_count": instance_data.get("post_count", 0),
            "is_active": True,
            "is_approved": False,
            "is_blocked": False,
        }
        if existing:
            await self.gql.update_federation_instance(existing.get("id"), data)
            return existing
        else:
            created = await self.gql.create_federation_instance(data)
            return created or {}
    
    async def test_connection(self, instance: FederationInstance | Dict[str, Any]) -> bool:
        """測試與聯邦實例的連接"""
        try:
            # 測試 NodeInfo 端點
            response = await self.client.get(
                f"https://{(instance.domain if isinstance(instance, FederationInstance) else instance['domain'])}/.well-known/nodeinfo/2.0",
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 200:
                # 更新連接狀態
                if isinstance(instance, dict):
                    await self.gql.update_federation_instance(instance.get("id"), {"last_successful_connection": datetime.utcnow().isoformat()})
                return True
            else:
                if isinstance(instance, dict):
                    await self.gql.update_federation_instance(instance.get("id"), {"error_count": (instance.get('error_count', 0) + 1)})
                return False
                
        except Exception as e:
            print(f"Error testing connection to {instance.domain}: {e}")
            if isinstance(instance, dict):
                await self.gql.update_federation_instance(instance.get("id"), {"error_count": (instance.get('error_count', 0) + 1)})
            return False
    
    async def discover_from_activity(self, activity: Dict[str, Any]) -> List[str]:
        """從活動中發現新的聯邦實例"""
        discovered_domains = []
        
        # 從活動的 actor 欄位發現
        if "actor" in activity:
            actor_domain = self._extract_domain_from_actor(activity["actor"])
            if actor_domain and actor_domain != settings.ACTIVITYPUB_DOMAIN:
                discovered_domains.append(actor_domain)
        
        # 從活動的 object 欄位發現
        if "object" in activity:
            object_domain = self._extract_domain_from_object(activity["object"])
            if object_domain and object_domain != settings.ACTIVITYPUB_DOMAIN:
                discovered_domains.append(object_domain)
        
        # 從活動的 target 欄位發現
        if "target" in activity:
            target_domain = self._extract_domain_from_object(activity["target"])
            if target_domain and target_domain != settings.ACTIVITYPUB_DOMAIN:
                discovered_domains.append(target_domain)
        
        return list(set(discovered_domains))
    
    def _extract_domain_from_actor(self, actor: str) -> Optional[str]:
        """從 Actor URL 中提取域名"""
        try:
            parsed = urlparse(actor)
            return parsed.netloc
        except:
            return None
    
    def _extract_domain_from_object(self, obj: Any) -> Optional[str]:
        """從物件中提取域名"""
        if isinstance(obj, str):
            return self._extract_domain_from_actor(obj)
        elif isinstance(obj, dict):
            # 檢查 id 欄位
            if "id" in obj:
                return self._extract_domain_from_actor(obj["id"])
            # 檢查 actor 欄位
            if "actor" in obj:
                return self._extract_domain_from_actor(obj["actor"])
        return None
    
    async def get_known_instances(self, limit: int = 100) -> List[Dict[str, Any]]:
        """取得已知的聯邦實例"""
        return await self.gql.list_federation_instances(limit=limit, offset=0, approved_only=False, active_only=True)
    
    async def get_approved_instances(self) -> List[Dict[str, Any]]:
        """取得已核准的聯邦實例"""
        items = await self.gql.list_federation_instances(limit=1000, offset=0, approved_only=True, active_only=True)
        return [i for i in items if not i.get("is_blocked")]
    
    async def update_instance_status(self, domain: str, **kwargs) -> bool:
        """更新實例狀態"""
        data = kwargs.copy()
        data["updated_at"] = datetime.utcnow().isoformat()
        return await self.gql.update_federation_instance_by_domain(domain, data)
    
    async def cleanup_old_instances(self, days: int = 30) -> int:
        """清理舊的無效實例"""
        # GraphQL Keystone 無法直接用日期比較刪除，改用列表過濾後逐筆刪除
        items = await self.gql.list_federation_instances(limit=1000, offset=0, approved_only=False, active_only=True)
        to_delete = [i for i in items if not i.get("is_approved") and (i.get("connection_count", 0) == 0)]
        count = 0
        for inst in to_delete:
            if await self.gql.delete_federation_instance(inst.get("id")):
                count += 1
        return count

class FederationManager:
    """聯邦管理器"""
    
    def __init__(self, db: AsyncSession | None):
        self.db = db
        self.discovery = FederationDiscovery(db)
    
    async def auto_discover_instances(self) -> List[str]:
        """自動發現新的聯邦實例"""
        discovered_domains = []
        
        # 從已知實例的活動中發現新實例
        known_instances = await self.discovery.get_known_instances()
        
        for instance in known_instances:
            try:
                # 取得實例的公開時間軸
                activities = await self._get_public_timeline(instance)
                
                for activity in activities:
                    new_domains = await self.discovery.discover_from_activity(activity)
                    discovered_domains.extend(new_domains)
                    
            except Exception as e:
                print(f"Error discovering from instance {(instance['domain'] if isinstance(instance, dict) else instance.domain)}: {e}")
        
        # 去重並發現新實例
        unique_domains = list(set(discovered_domains))
        new_instances = []
        
        for domain in unique_domains:
            # 檢查是否已存在
            existing = await self.discovery.gql.get_federation_instance(domain)
            if not existing:
                # 發現新實例
                instance_data = await self.discovery.discover_instance(domain)
                if instance_data:
                    instance = await self.discovery.save_instance(instance_data)
                    new_instances.append(instance_data["domain"])
        
        return new_instances
    
    async def _get_public_timeline(self, instance: FederationInstance | Dict[str, Any]) -> List[Dict[str, Any]]:
        """取得實例的公開時間軸"""
        try:
            response = await self.discovery.client.get(
                f"https://{(instance['domain'] if isinstance(instance, dict) else instance.domain)}/api/v1/timelines/public",
                headers={"Accept": "application/json"},
                params={"limit": 20}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            print(f"Error getting public timeline from {(instance['domain'] if isinstance(instance, dict) else instance.domain)}: {e}")
            return []
    
    async def approve_instance(self, domain: str) -> bool:
        """核准聯邦實例"""
        return await self.discovery.update_instance_status(
            domain,
            is_approved=True,
            is_blocked=False
        )
    
    async def block_instance(self, domain: str) -> bool:
        """封鎖聯邦實例"""
        return await self.discovery.update_instance_status(
            domain,
            is_approved=False,
            is_blocked=True
        )
    
    async def test_all_connections(self) -> Dict[str, bool]:
        """測試所有聯邦實例的連接"""
        instances = await self.discovery.get_known_instances()
        results = {}
        
        for instance in instances:
            success = await self.discovery.test_connection(instance)
            results[instance["domain"] if isinstance(instance, dict) else instance.domain] = success
        
        return results
    
    async def get_federation_stats(self) -> Dict[str, Any]:
        """取得聯邦統計資訊"""
        items = await self.discovery.gql.list_federation_instances(limit=1000, offset=0)
        total_instances = len(items)
        active_instances = len([i for i in items if i.get("is_active")])
        approved_instances = len([i for i in items if i.get("is_approved")])
        blocked_instances = len([i for i in items if i.get("is_blocked")])
        
        return {
            "total_instances": total_instances,
            "active_instances": active_instances,
            "approved_instances": approved_instances,
            "blocked_instances": blocked_instances,
            "discovery_rate": active_instances / total_instances if total_instances > 0 else 0
        }
