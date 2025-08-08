#!/usr/bin/env python3
"""
CI/CD 專用的 ActivityPub 測試腳本
針對 CI/CD 環境優化，包含更嚴格的測試和報告
"""

import asyncio
import httpx
import json
import time
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# 導入測試配置
from test_config import setup_test_environment, CI_TEST_CONFIG

class CITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=CI_TEST_CONFIG["timeout"])
        self.test_results = []
        self.setup_test_environment()
        
    def setup_test_environment(self):
        """設定 CI/CD 測試環境"""
        setup_test_environment()
        print(f"🔧 CI/CD 測試環境已設定")
        print(f"   - 基礎 URL: {self.base_url}")
        print(f"   - 超時設定: {CI_TEST_CONFIG['timeout']} 秒")
        print(f"   - 重試次數: {CI_TEST_CONFIG['retry_count']}")
        
    async def test_endpoint_with_retry(self, method: str, url: str, expected_status: int = 200,
                                      data: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """帶重試機制的端點測試"""
        for attempt in range(CI_TEST_CONFIG["retry_count"]):
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
                    "attempt": attempt + 1,
                    "response": response.text[:200] if response.text else "",
                    "timestamp": datetime.now().isoformat()
                }
                
                if success:
                    print(f"✅ {method} {url} - {response.status_code} (attempt {attempt + 1})")
                    return result
                else:
                    print(f"⚠️  {method} {url} - Expected {expected_status}, got {response.status_code} (attempt {attempt + 1})")
                    if attempt == CI_TEST_CONFIG["retry_count"] - 1:
                        return result
                    time.sleep(1)  # 重試前等待
                    
            except Exception as e:
                print(f"❌ {method} {url} - Error: {e} (attempt {attempt + 1})")
                if attempt == CI_TEST_CONFIG["retry_count"] - 1:
                    return {
                        "url": url,
                        "method": method,
                        "expected_status": expected_status,
                        "actual_status": None,
                        "success": False,
                        "attempt": attempt + 1,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                time.sleep(1)  # 重試前等待
        
        return {"success": False, "error": "Max retries exceeded"}
    
    async def health_check(self) -> bool:
        """健康檢查 - 確保服務正常運行"""
        print("\n🏥 執行健康檢查...")
        
        for endpoint in CI_TEST_CONFIG["health_check_endpoints"]:
            result = await self.test_endpoint_with_retry("GET", f"{self.base_url}{endpoint}")
            if not result["success"]:
                print(f"❌ 健康檢查失敗: {endpoint}")
                return False
        
        print("✅ 健康檢查通過")
        return True
    
    async def test_basic_endpoints(self) -> List[Dict[str, Any]]:
        """測試基本端點"""
        print("\n🔍 測試基本端點...")
        results = []
        
        # 根端點
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/"))
        
        # 健康檢查
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/api/v1/health/"))
        
        return results
    
    async def test_activitypub_endpoints(self) -> List[Dict[str, Any]]:
        """測試 ActivityPub 標準端點"""
        print("\n🔍 測試 ActivityPub 標準端點...")
        results = []
        
        # NodeInfo 發現
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/.well-known/nodeinfo"))
        
        # NodeInfo 2.0
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/.well-known/nodeinfo/2.0"))
        
        # Actor 資訊
        results.append(await self.test_endpoint_with_retry(
            "GET", 
            f"{self.base_url}/.well-known/users/test",
            headers={"Accept": "application/activity+json"}
        ))
        
        # WebFinger (預期失敗)
        results.append(await self.test_endpoint_with_retry(
            "GET", 
            f"{self.base_url}/.well-known/webfinger?resource=acct:test@activity.readr.tw",
            expected_status=404
        ))
        
        # Inbox 測試
        inbox_data = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "actor": "https://mastodon.social/users/test",
            "object": f"{self.base_url}/.well-known/users/test"
        }
        results.append(await self.test_endpoint_with_retry(
            "POST",
            f"{self.base_url}/.well-known/inbox/test/inbox",
            data=inbox_data,
            headers={"Content-Type": "application/activity+json"}
        ))
        
        return results
    
    async def test_api_endpoints(self) -> List[Dict[str, Any]]:
        """測試 API 端點"""
        print("\n🔍 測試 API 端點...")
        results = []
        
        # 獲取 actors
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/api/v1/actors/"))
        
        # 獲取 member
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/api/v1/mesh/members/test"))
        
        # 獲取 federation instances
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/api/v1/federation/instances"))
        
        # 獲取 account mappings
        results.append(await self.test_endpoint_with_retry("GET", f"{self.base_url}/api/v1/account-mapping/mappings?member_id=test"))
        
        return results
    
    async def test_actor_creation(self) -> List[Dict[str, Any]]:
        """測試 Actor 創建"""
        print("\n🔍 測試 Actor 創建...")
        results = []
        
        # 嘗試創建已存在的 actor (預期失敗)
        actor_data = {
            "username": "test",
            "display_name": "Test User",
            "summary": "Test user"
        }
        results.append(await self.test_endpoint_with_retry(
            "POST",
            f"{self.base_url}/api/v1/actors/",
            data=actor_data,
            expected_status=400  # 預期失敗，因為已存在
        ))
        
        return results
    
    async def test_mesh_integration(self) -> List[Dict[str, Any]]:
        """測試 Mesh 整合"""
        print("\n🔍 測試 Mesh 整合...")
        results = []
        
        # 創建 pick (預期失敗，因為缺少必要資料)
        pick_data = {
            "story_id": "test-story",
            "comment": "Great story!"
        }
        results.append(await self.test_endpoint_with_retry(
            "POST",
            f"{self.base_url}/api/v1/mesh/picks?member_id=test",
            data=pick_data,
            expected_status=500  # 預期內部錯誤
        ))
        
        return results
    
    async def test_federation_discovery(self) -> List[Dict[str, Any]]:
        """測試聯邦發現"""
        print("\n🔍 測試聯邦發現...")
        results = []
        
        # 測試聯邦發現
        discovery_data = {
            "domain": "mastodon.social"
        }
        results.append(await self.test_endpoint_with_retry(
            "POST",
            f"{self.base_url}/api/v1/federation/discover",
            data=discovery_data,
            expected_status=200
        ))
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """執行所有測試"""
        print("🚀 開始 CI/CD ActivityPub 測試...")
        start_time = time.time()
        
        # 健康檢查
        if not await self.health_check():
            return {
                "success": False,
                "error": "Health check failed",
                "timestamp": datetime.now().isoformat()
            }
        
        # 執行所有測試
        all_results = []
        
        all_results.extend(await self.test_basic_endpoints())
        all_results.extend(await self.test_activitypub_endpoints())
        all_results.extend(await self.test_api_endpoints())
        all_results.extend(await self.test_actor_creation())
        all_results.extend(await self.test_mesh_integration())
        all_results.extend(await self.test_federation_discovery())
        
        # 計算結果
        total_tests = len(all_results)
        successful_tests = sum(1 for result in all_results if result.get("success", False))
        failed_tests = total_tests - successful_tests
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 生成報告
        report = {
            "ci_cd": True,
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "all_passed": failed_tests == 0,
            "results": all_results,
            "environment": {
                "base_url": self.base_url,
                "timeout": CI_TEST_CONFIG["timeout"],
                "retry_count": CI_TEST_CONFIG["retry_count"]
            }
        }
        
        # 輸出結果
        print(f"\n📊 CI/CD 測試結果:")
        print(f"   - 總測試數: {total_tests}")
        print(f"   - 成功: {successful_tests}")
        print(f"   - 失敗: {failed_tests}")
        print(f"   - 成功率: {report['success_rate']:.1f}%")
        print(f"   - 執行時間: {duration:.2f} 秒")
        
        if report["all_passed"]:
            print("🎉 所有測試通過！")
        else:
            print("⚠️  部分測試失敗")
            
        return report
    
    async def save_report(self, report: Dict[str, Any], filename: str = None) -> str:
        """保存測試報告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ci_activitypub_test_report_{timestamp}.json"
        
        # 確保報告目錄存在
        os.makedirs("test-results", exist_ok=True)
        filepath = os.path.join("test-results", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 測試報告已保存: {filepath}")
        return filepath
    
    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()

async def main():
    """主函數"""
    # 從環境變數獲取基礎 URL
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    tester = CITester(base_url)
    
    try:
        report = await tester.run_all_tests()
        
        # 保存報告
        await tester.save_report(report)
        
        # 根據結果設定退出碼
        if not report["all_passed"]:
            print("❌ CI/CD 測試失敗")
            sys.exit(1)
        else:
            print("✅ CI/CD 測試成功")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ CI/CD 測試執行錯誤: {e}")
        sys.exit(1)
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
