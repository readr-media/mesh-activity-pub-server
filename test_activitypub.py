#!/usr/bin/env python3
"""
ActivityPub 功能自動化測試腳本
測試所有 ActivityPub 相關端點和功能
"""

import asyncio
import httpx
import json
import time
import sys
import os
from typing import Dict, Any, List
from datetime import datetime

# 導入測試配置
try:
    from test_config import setup_test_environment, CI_TEST_CONFIG
    setup_test_environment()
except ImportError:
    # 如果沒有 test_config，使用預設配置
    CI_TEST_CONFIG = {
        "timeout": 30,
        "retry_count": 3,
        "health_check_endpoints": ["/", "/api/v1/health/", "/.well-known/nodeinfo"],
        "expected_status_codes": {
            "basic_endpoints": 200,
            "activitypub_endpoints": [200, 404],
            "api_endpoints": [200, 400, 500]
        }
    }

class ActivityPubTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        
    async def test_endpoint(self, method: str, url: str, expected_status: int = 200, 
                           data: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """測試單一端點"""
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            result = {
                "url": url,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response": response.text[:200] if response.text else "",
                "timestamp": datetime.now().isoformat()
            }
            
            if success:
                print(f"✅ {method} {url} - {response.status_code}")
            else:
                print(f"❌ {method} {url} - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:100]}...")
            
            return result
            
        except Exception as e:
            result = {
                "url": url,
                "method": method,
                "expected_status": expected_status,
                "actual_status": None,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ {method} {url} - Error: {e}")
            return result
    
    async def test_basic_endpoints(self) -> List[Dict[str, Any]]:
        """測試基本端點"""
        print("\n🔍 測試基本端點...")
        results = []
        
        # 根端點
        results.append(await self.test_endpoint("GET", f"{self.base_url}/"))
        
        # 健康檢查
        results.append(await self.test_endpoint("GET", f"{self.base_url}/api/v1/health/"))
        
        return results
    
    async def test_activitypub_endpoints(self) -> List[Dict[str, Any]]:
        """測試 ActivityPub 標準端點"""
        print("\n🔍 測試 ActivityPub 標準端點...")
        results = []
        
        # NodeInfo 發現
        results.append(await self.test_endpoint("GET", f"{self.base_url}/.well-known/nodeinfo"))
        
        # NodeInfo 2.0
        results.append(await self.test_endpoint("GET", f"{self.base_url}/.well-known/nodeinfo/2.0"))
        
        # Actor 資訊
        results.append(await self.test_endpoint(
            "GET", 
            f"{self.base_url}/.well-known/users/test",
            headers={"Accept": "application/activity+json"}
        ))
        
        # WebFinger (會失敗，因為域名不匹配)
        results.append(await self.test_endpoint(
            "GET", 
            f"{self.base_url}/.well-known/webfinger?resource=acct:test@activity.readr.tw",
            expected_status=404  # 預期失敗
        ))
        
        # Inbox
        activity_data = {
            "type": "Follow",
            "actor": "https://example.com/users/test",
            "object": f"{self.base_url}/users/test"
        }
        results.append(await self.test_endpoint(
            "POST",
            f"{self.base_url}/.well-known/inbox/test/inbox",
            data=activity_data,
            headers={"Content-Type": "application/activity+json"}
        ))
        
        return results
    
    async def test_api_endpoints(self) -> List[Dict[str, Any]]:
        """測試 API 端點"""
        print("\n🔍 測試 API 端點...")
        results = []
        
        # Actors API
        results.append(await self.test_endpoint("GET", f"{self.base_url}/api/v1/actors/"))
        
        # Mesh API
        results.append(await self.test_endpoint("GET", f"{self.base_url}/api/v1/mesh/members/test"))
        
        # Federation API
        results.append(await self.test_endpoint("GET", f"{self.base_url}/api/v1/federation/instances"))
        
        # Account Mapping API
        results.append(await self.test_endpoint("GET", f"{self.base_url}/api/v1/account-mapping/mappings?member_id=test"))
        
        return results
    
    async def test_actor_creation(self) -> List[Dict[str, Any]]:
        """測試 Actor 創建功能"""
        print("\n🔍 測試 Actor 創建功能...")
        results = []
        
        # 測試創建 Actor
        actor_data = {
            "username": "testuser",
            "domain": "activity.readr.tw",
            "display_name": "Test User",
            "summary": "A test user for ActivityPub",
            "is_local": True
        }
        
        # 注意：這個端點存在但會因為用戶名已存在而失敗
        results.append(await self.test_endpoint(
            "POST",
            f"{self.base_url}/api/v1/actors/",
            data=actor_data,
            expected_status=400  # 預期失敗，因為用戶名已存在
        ))
        
        return results
    
    async def test_mesh_integration(self) -> List[Dict[str, Any]]:
        """測試 Mesh 整合功能"""
        print("\n🔍 測試 Mesh 整合功能...")
        results = []
        
        # 測試創建 Pick
        pick_data = {
            "story_id": "test-story-123",
            "objective": "測試分享",
            "kind": "share",
            "paywall": False
        }
        
        # 在 GraphQL mock 或已接上 GQL 服務時應成功建立，預期 200
        results.append(await self.test_endpoint(
            "POST",
            f"{self.base_url}/api/v1/mesh/picks?member_id=test",
            data=pick_data,
            expected_status=200
        ))
        
        return results
    
    async def test_federation_discovery(self) -> List[Dict[str, Any]]:
        """測試聯邦發現功能"""
        print("\n🔍 測試聯邦發現功能...")
        results = []
        
        # 測試聯邦實例發現
        results.append(await self.test_endpoint(
            "POST",
            f"{self.base_url}/api/v1/federation/discover",
            data={"domain": "mastodon.social"},
            expected_status=200  # 預期成功，但會返回發現失敗的結果
        ))
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """執行所有測試"""
        print("🚀 開始 ActivityPub 功能測試...")
        print(f"📡 測試目標: {self.base_url}")
        print(f"⏰ 開始時間: {datetime.now().isoformat()}")
        
        start_time = time.time()
        
        # 執行所有測試
        all_results = []
        all_results.extend(await self.test_basic_endpoints())
        all_results.extend(await self.test_activitypub_endpoints())
        all_results.extend(await self.test_api_endpoints())
        all_results.extend(await self.test_actor_creation())
        all_results.extend(await self.test_mesh_integration())
        all_results.extend(await self.test_federation_discovery())
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 統計結果
        total_tests = len(all_results)
        successful_tests = sum(1 for result in all_results if result["success"])
        failed_tests = total_tests - successful_tests
        
        # 生成報告
        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "duration_seconds": duration,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat()
            },
            "results": all_results
        }
        
        # 輸出結果
        print(f"\n📊 測試結果摘要:")
        print(f"   總測試數: {total_tests}")
        print(f"   成功: {successful_tests}")
        print(f"   失敗: {failed_tests}")
        print(f"   成功率: {report['summary']['success_rate']:.1f}%")
        print(f"   耗時: {duration:.2f} 秒")
        
        if failed_tests > 0:
            print(f"\n❌ 失敗的測試:")
            for result in all_results:
                if not result["success"]:
                    print(f"   - {result['method']} {result['url']}")
                    if "error" in result:
                        print(f"     錯誤: {result['error']}")
        
        return report
    
    async def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """保存測試報告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"activitypub_test_report_{timestamp}.json"
        
        # 確保報告目錄存在
        os.makedirs("test-results", exist_ok=True)
        filepath = os.path.join("test-results", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 測試報告已保存至: {filepath}")
        return filepath
    
    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()

async def main():
    """主函數"""
    # 檢查命令行參數
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🎯 ActivityPub 測試工具")
    print(f"📍 目標服務: {base_url}")
    print(f"⏰ 開始時間: {datetime.now().isoformat()}")
    
    # 創建測試器
    tester = ActivityPubTester(base_url)
    
    try:
        # 執行測試
        report = await tester.run_all_tests()
        
        # 保存報告
        await tester.save_report(report)
        
        # 根據結果決定退出碼
        if report["summary"]["failed_tests"] == 0:
            print("\n🎉 所有測試通過！")
            sys.exit(0)
        else:
            print(f"\n⚠️  有 {report['summary']['failed_tests']} 個測試失敗")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 測試執行時發生錯誤: {e}")
        sys.exit(1)
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
