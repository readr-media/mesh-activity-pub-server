#!/usr/bin/env python3
"""
測試聯邦網站發現功能的腳本
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# 測試配置
BASE_URL = "http://localhost:8000"

# 一些知名的聯邦網站用於測試
TEST_INSTANCES = [
    "mastodon.social",
    "mastodon.online", 
    "mstdn.jp",
    "pawoo.net",
    "pleroma.site"
]

async def test_federation_discovery():
    """測試聯邦網站發現功能"""
    async with httpx.AsyncClient() as client:
        print("🧪 開始測試聯邦網站發現功能...")
        
        # 1. 測試手動發現聯邦實例
        print("\n1. 測試手動發現聯邦實例...")
        for domain in TEST_INSTANCES[:2]:  # 只測試前兩個
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/federation/discover",
                    json={"domain": domain}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 成功發現實例: {domain}")
                    print(f"   - 發現狀態: {result['discovered']}")
                    if result.get('instance_data'):
                        print(f"   - 軟體: {result['instance_data'].get('software', 'Unknown')}")
                        print(f"   - 版本: {result['instance_data'].get('version', 'Unknown')}")
                        print(f"   - 使用者數: {result['instance_data'].get('user_count', 0)}")
                else:
                    print(f"❌ 發現實例失敗: {domain} - {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 發現實例時發生錯誤: {domain} - {e}")
        
        # 2. 取得聯邦實例列表
        print("\n2. 取得聯邦實例列表...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/federation/instances?limit=10")
            if response.status_code == 200:
                instances = response.json()
                print(f"✅ 成功取得 {len(instances)} 個聯邦實例")
                for instance in instances[:3]:  # 只顯示前3個
                    print(f"   - {instance['domain']} ({instance['software']})")
            else:
                print(f"❌ 取得實例列表失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ 取得實例列表時發生錯誤: {e}")
        
        # 3. 取得聯邦統計資訊
        print("\n3. 取得聯邦統計資訊...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/federation/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ 聯邦統計資訊:")
                print(f"   - 總實例數: {stats['total_instances']}")
                print(f"   - 活躍實例數: {stats['active_instances']}")
                print(f"   - 已核准實例數: {stats['approved_instances']}")
                print(f"   - 被封鎖實例數: {stats['blocked_instances']}")
                print(f"   - 發現率: {stats['discovery_rate']:.2%}")
            else:
                print(f"❌ 取得統計資訊失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ 取得統計資訊時發生錯誤: {e}")
        
        # 4. 測試手動建立聯邦實例
        print("\n4. 測試手動建立聯邦實例...")
        test_instance = {
            "domain": "test.example.com",
            "name": "Test Instance",
            "description": "This is a test instance",
            "software": "TestSoftware",
            "version": "1.0.0",
            "auto_follow": False,
            "auto_announce": True,
            "max_followers": 500,
            "max_following": 500
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/federation/instances",
                json=test_instance
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 成功建立測試實例: {result['domain']}")
                print(f"   - ID: {result['id']}")
                print(f"   - 名稱: {result['name']}")
                print(f"   - 軟體: {result['software']}")
                
                # 5. 測試更新實例設定
                print("\n5. 測試更新實例設定...")
                update_data = {
                    "is_approved": True,
                    "auto_follow": True,
                    "description": "Updated test instance"
                }
                
                response = await client.put(
                    f"{BASE_URL}/api/v1/federation/instances/{test_instance['domain']}",
                    json=update_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 成功更新實例設定")
                    print(f"   - 已核准: {result['is_approved']}")
                    print(f"   - 自動追蹤: {result['auto_follow']}")
                    print(f"   - 描述: {result['description']}")
                else:
                    print(f"❌ 更新實例設定失敗: {response.status_code}")
                
                # 6. 測試核准實例
                print("\n6. 測試核准實例...")
                response = await client.post(
                    f"{BASE_URL}/api/v1/federation/instances/{test_instance['domain']}/approve"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {result['message']}")
                else:
                    print(f"❌ 核准實例失敗: {response.status_code}")
                
                # 7. 測試連接
                print("\n7. 測試實例連接...")
                response = await client.post(
                    f"{BASE_URL}/api/v1/federation/instances/{test_instance['domain']}/test"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 連接測試完成")
                    print(f"   - 連接成功: {result['connection_successful']}")
                    print(f"   - 最後測試: {result['last_test']}")
                else:
                    print(f"❌ 連接測試失敗: {response.status_code}")
                
                # 8. 清理測試實例
                print("\n8. 清理測試實例...")
                response = await client.delete(
                    f"{BASE_URL}/api/v1/federation/instances/{test_instance['domain']}"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {result['message']}")
                else:
                    print(f"❌ 刪除實例失敗: {response.status_code}")
                    
            else:
                print(f"❌ 建立測試實例失敗: {response.status_code}")
                print(f"   - 錯誤: {response.text}")
                
        except Exception as e:
            print(f"❌ 測試實例操作時發生錯誤: {e}")
        
        # 9. 測試自動發現
        print("\n9. 測試自動發現...")
        try:
            response = await client.post(f"{BASE_URL}/api/v1/federation/discover/auto")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result['message']}")
            else:
                print(f"❌ 自動發現失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ 自動發現時發生錯誤: {e}")
        
        # 10. 測試連接測試
        print("\n10. 測試所有連接...")
        try:
            response = await client.post(f"{BASE_URL}/api/v1/federation/test-all")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result['message']}")
            else:
                print(f"❌ 連接測試失敗: {response.status_code}")
        except Exception as e:
            print(f"❌ 連接測試時發生錯誤: {e}")
        
        print("\n🎉 聯邦網站發現功能測試完成！")

if __name__ == "__main__":
    asyncio.run(test_federation_discovery())
