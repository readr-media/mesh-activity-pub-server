#!/usr/bin/env python3
"""
測試帳號發現和映射功能的腳本
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# 測試配置
BASE_URL = "http://localhost:8000"
MEMBER_ID = "test_member_123"

async def test_account_mapping():
    """測試帳號發現和映射功能"""
    async with httpx.AsyncClient() as client:
        print("🧪 開始測試帳號發現和映射功能...")
        
        # 1. 測試自動發現帳號
        print("\n1. 測試自動發現帳號...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/account-mapping/discover",
                json={
                    "method": "auto",
                    "query": "test@example.com"
                },
                params={"member_id": MEMBER_ID}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 自動發現成功")
                print(f"   - 發現的帳號: {result['username']}@{result['domain']}")
                print(f"   - 信心分數: {result['confidence_score']}")
            else:
                print(f"❌ 自動發現失敗: {response.status_code}")
                print(f"   - 錯誤: {response.text}")
                
        except Exception as e:
            print(f"❌ 自動發現時發生錯誤: {e}")
        
        # 2. 測試透過使用者名稱發現
        print("\n2. 測試透過使用者名稱發現...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/account-mapping/discover",
                json={
                    "method": "username",
                    "query": "admin",
                    "domain": "mastodon.social"
                },
                params={"member_id": MEMBER_ID}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 使用者名稱發現成功")
                print(f"   - 發現的帳號: {result['username']}@{result['domain']}")
                print(f"   - 顯示名稱: {result.get('display_name', 'N/A')}")
                
                # 儲存發現的帳號資訊用於後續測試
                discovered_actor_id = result['actor_id']
            else:
                print(f"❌ 使用者名稱發現失敗: {response.status_code}")
                print(f"   - 錯誤: {response.text}")
                discovered_actor_id = None
                
        except Exception as e:
            print(f"❌ 使用者名稱發現時發生錯誤: {e}")
            discovered_actor_id = None
        
        # 3. 測試建立帳號映射
        if discovered_actor_id:
            print("\n3. 測試建立帳號映射...")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/account-mapping/mappings",
                    json={
                        "remote_actor_id": discovered_actor_id,
                        "verification_method": "manual"
                    },
                    params={"member_id": MEMBER_ID}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 帳號映射建立成功")
                    print(f"   - 映射 ID: {result['id']}")
                    print(f"   - 遠端帳號: {result['remote_username']}@{result['remote_domain']}")
                    print(f"   - 已驗證: {result['is_verified']}")
                    
                    mapping_id = result['id']
                else:
                    print(f"❌ 帳號映射建立失敗: {response.status_code}")
                    print(f"   - 錯誤: {response.text}")
                    mapping_id = None
                    
            except Exception as e:
                print(f"❌ 建立帳號映射時發生錯誤: {e}")
                mapping_id = None
        else:
            print("\n3. 跳過建立帳號映射（未發現帳號）")
            mapping_id = None
        
        # 4. 測試取得帳號映射列表
        print("\n4. 測試取得帳號映射列表...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/account-mapping/mappings",
                params={"member_id": MEMBER_ID}
            )
            
            if response.status_code == 200:
                mappings = response.json()
                print(f"✅ 取得帳號映射列表成功")
                print(f"   - 映射數量: {len(mappings)}")
                for mapping in mappings:
                    print(f"   - {mapping['remote_username']}@{mapping['remote_domain']} (ID: {mapping['id']})")
            else:
                print(f"❌ 取得帳號映射列表失敗: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 取得帳號映射列表時發生錯誤: {e}")
        
        # 5. 測試更新帳號映射設定
        if mapping_id:
            print("\n5. 測試更新帳號映射設定...")
            try:
                response = await client.put(
                    f"{BASE_URL}/api/v1/account-mapping/mappings/{mapping_id}",
                    json={
                        "sync_posts": True,
                        "sync_follows": False,
                        "sync_likes": True,
                        "sync_announces": True
                    },
                    params={"member_id": MEMBER_ID}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 帳號映射設定更新成功")
                    print(f"   - 同步貼文: {result['sync_posts']}")
                    print(f"   - 同步追蹤: {result['sync_follows']}")
                    print(f"   - 同步按讚: {result['sync_likes']}")
                    print(f"   - 同步轉發: {result['sync_announces']}")
                else:
                    print(f"❌ 帳號映射設定更新失敗: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 更新帳號映射設定時發生錯誤: {e}")
        
        # 6. 測試同步帳號內容
        if mapping_id:
            print("\n6. 測試同步帳號內容...")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/account-mapping/mappings/{mapping_id}/sync",
                    json={
                        "sync_type": "posts",
                        "max_items": 10
                    },
                    params={"member_id": MEMBER_ID}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 同步任務建立成功")
                    print(f"   - 任務 ID: {result['id']}")
                    print(f"   - 同步類型: {result['sync_type']}")
                    print(f"   - 狀態: {result['status']}")
                    
                    sync_task_id = result['id']
                else:
                    print(f"❌ 同步任務建立失敗: {response.status_code}")
                    print(f"   - 錯誤: {response.text}")
                    sync_task_id = None
                    
            except Exception as e:
                print(f"❌ 建立同步任務時發生錯誤: {e}")
                sync_task_id = None
        else:
            print("\n6. 跳過同步帳號內容（無映射 ID）")
            sync_task_id = None
        
        # 7. 測試取得同步任務狀態
        if sync_task_id:
            print("\n7. 測試取得同步任務狀態...")
            try:
                response = await client.get(
                    f"{BASE_URL}/api/v1/account-mapping/sync-tasks/{sync_task_id}",
                    params={"member_id": MEMBER_ID}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 取得同步任務狀態成功")
                    print(f"   - 進度: {result['progress']}%")
                    print(f"   - 已處理: {result['items_processed']}")
                    print(f"   - 已同步: {result['items_synced']}")
                    print(f"   - 失敗: {result['items_failed']}")
                else:
                    print(f"❌ 取得同步任務狀態失敗: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 取得同步任務狀態時發生錯誤: {e}")
        
        # 8. 測試取得發現記錄
        print("\n8. 測試取得發現記錄...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/account-mapping/discoveries",
                params={"member_id": MEMBER_ID, "limit": 10}
            )
            
            if response.status_code == 200:
                discoveries = response.json()
                print(f"✅ 取得發現記錄成功")
                print(f"   - 記錄數量: {len(discoveries)}")
                for discovery in discoveries[:3]:  # 只顯示前3個
                    print(f"   - {discovery['discovery_method']}: {discovery['search_query']} (成功: {discovery['is_successful']})")
            else:
                print(f"❌ 取得發現記錄失敗: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 取得發現記錄時發生錯誤: {e}")
        
        # 9. 測試驗證帳號映射
        if mapping_id:
            print("\n9. 測試驗證帳號映射...")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/account-mapping/mappings/{mapping_id}/verify",
                    params={"member_id": MEMBER_ID}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 帳號映射驗證成功")
                    print(f"   - 訊息: {result['message']}")
                else:
                    print(f"❌ 帳號映射驗證失敗: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 驗證帳號映射時發生錯誤: {e}")
        
        # 10. 測試刪除帳號映射（清理測試資料）
        if mapping_id:
            print("\n10. 測試刪除帳號映射...")
            try:
                response = await client.delete(
                    f"{BASE_URL}/api/v1/account-mapping/mappings/{mapping_id}",
                    params={"member_id": MEMBER_ID}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 帳號映射刪除成功")
                    print(f"   - 訊息: {result['message']}")
                else:
                    print(f"❌ 帳號映射刪除失敗: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 刪除帳號映射時發生錯誤: {e}")
        
        print("\n🎉 帳號發現和映射功能測試完成！")

if __name__ == "__main__":
    asyncio.run(test_account_mapping())
