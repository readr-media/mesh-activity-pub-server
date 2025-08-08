# ActivityPub 功能測試指南

本文件說明如何測試 ActivityPub 服務的各項功能。

## 快速測試

### 使用自動化測試腳本

我們提供了兩個測試腳本來簡化測試流程：

#### 1. Shell 腳本（推薦）

```bash
# 完整測試流程（啟動服務 + 執行測試 + 停止服務）
./test_activitypub.sh --full

# 僅啟動服務
./test_activitypub.sh --start

# 僅執行測試（假設服務已運行）
./test_activitypub.sh --test

# 停止服務
./test_activitypub.sh --kill

# 顯示幫助
./test_activitypub.sh --help
```

#### 2. Python 測試腳本

```bash
# 測試本地服務
python3 test_activitypub.py

# 測試其他服務
python3 test_activitypub.py http://other-server:8000
```

## 手動測試

如果您想要手動測試特定功能，可以使用以下命令：

### 1. 啟動服務

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 基本端點測試

```bash
# 根端點
curl -X GET "http://localhost:8000/"

# 健康檢查
curl -X GET "http://localhost:8000/api/v1/health/"
```

### 3. ActivityPub 標準端點測試

```bash
# NodeInfo 發現
curl -X GET "http://localhost:8000/.well-known/nodeinfo"

# NodeInfo 2.0
curl -X GET "http://localhost:8000/.well-known/nodeinfo/2.0"

# Actor 資訊
curl -X GET "http://localhost:8000/.well-known/users/test" \
  -H "Accept: application/activity+json"

# WebFinger（會失敗，因為域名不匹配）
curl -X GET "http://localhost:8000/.well-known/webfinger?resource=acct:test@activity.readr.tw"

# Inbox
curl -X POST "http://localhost:8000/.well-known/inbox/test/inbox" \
  -H "Content-Type: application/activity+json" \
  -d '{"type":"Follow","actor":"https://example.com/users/test","object":"http://localhost:8000/users/test"}'
```

### 4. API 端點測試

```bash
# Actors API
curl -X GET "http://localhost:8000/api/v1/actors/"

# Mesh API
curl -X GET "http://localhost:8000/api/v1/mesh/members/test"

# Federation API
curl -X GET "http://localhost:8000/api/v1/federation/instances"

# Account Mapping API
curl -X GET "http://localhost:8000/api/v1/account-mapping/mappings?member_id=test"
```

## 測試結果

### 預期成功的測試

✅ **基本端點**
- 根端點 (`GET /`)
- 健康檢查 (`GET /api/v1/health/`)

✅ **ActivityPub 標準端點**
- NodeInfo 發現 (`GET /.well-known/nodeinfo`)
- NodeInfo 2.0 (`GET /.well-known/nodeinfo/2.0`)
- Actor 資訊 (`GET /.well-known/users/{username}`)
- Inbox (`POST /.well-known/inbox/{username}/inbox`)

✅ **API 端點**
- Actors API (`GET /api/v1/actors/`)
- Mesh API (`GET /api/v1/mesh/members/{member_id}`)
- Federation API (`GET /api/v1/federation/instances`)
- Account Mapping API (`GET /api/v1/account-mapping/mappings`)

### 預期失敗的測試

❌ **WebFinger**
- 原因：域名不匹配設定中的 `activity.readr.tw`
- 解決：在生產環境中使用正確的域名

❌ **未實作的端點**
- Actor 創建 (`POST /api/v1/actors/`)
- Pick 創建 (`POST /api/v1/mesh/picks`)
- Federation 發現 (`POST /api/v1/federation/discover`)
- 原因：這些功能尚未實作

## 測試報告

測試腳本會生成詳細的測試報告，包含：

- 測試摘要（總數、成功數、失敗數、成功率）
- 每個測試的詳細結果
- 錯誤訊息和響應內容
- 執行時間統計

報告文件會保存為 `activitypub_test_report_YYYYMMDD_HHMMSS.json`

## 故障排除

### 常見問題

1. **服務啟動失敗**
   ```bash
   # 檢查端口是否被佔用
   lsof -ti:8000
   
   # 清理舊進程
   pkill -f uvicorn
   ```

2. **Python 版本問題**
   ```bash
   # 使用系統 Python
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

3. **依賴套件問題**
   ```bash
   # 重新安裝依賴
   pip install -r requirements.txt --force-reinstall
   ```

4. **架構相容性問題**
   ```bash
   # 重新安裝 pydantic
   pip uninstall pydantic pydantic-core -y
   pip install pydantic
   ```

### 調試模式

```bash
# 啟動服務並顯示詳細日誌
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

# 測試特定端點
curl -v -X GET "http://localhost:8000/api/v1/health/"
```

## 持續整合

這些測試腳本可以輕鬆整合到 CI/CD 流程中：

```yaml
# GitHub Actions 範例
- name: Test ActivityPub
  run: |
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    sleep 10
    python3 test_activitypub.py
```

## 擴展測試

要添加新的測試，請修改 `test_activitypub.py` 文件：

1. 在 `ActivityPubTester` 類中添加新的測試方法
2. 在 `run_all_tests` 方法中調用新測試
3. 更新測試報告格式（如需要）

範例：
```python
async def test_new_feature(self) -> List[Dict[str, Any]]:
    """測試新功能"""
    results = []
    results.append(await self.test_endpoint("GET", f"{self.base_url}/api/v1/new-feature"))
    return results
```
