# CI/CD 流程文檔

## 概述

本專案已整合完整的 CI/CD 流程，包含自動化測試、建置和部署。所有測試都使用 mock data 來確保測試的可靠性和一致性。

## CI/CD 架構

### 工作流程

1. **測試階段** (`test`)
   - 執行 ActivityPub 功能測試
   - 使用 mock data 確保測試一致性
   - 生成詳細測試報告

2. **建置階段** (`build`)
   - 建置 Docker 映像
   - 測試 Docker 容器
   - 推送到 Container Registry

3. **部署階段** (`deploy`)
   - 部署到 Google Cloud Run
   - 執行部署後測試
   - 驗證服務可用性

## Mock Data 策略

### 為什麼需要 Mock Data？

1. **測試一致性**: 確保每次測試都使用相同的資料
2. **隔離性**: 測試不依賴外部服務
3. **速度**: 避免網路延遲和外部 API 調用
4. **可靠性**: 避免因外部服務故障導致的測試失敗

### Mock Data 配置

```python
# test_config.py
TEST_MOCK_DATA = {
    "members": {
        "test": {
            "id": "test-member-id",
            "nickname": "test",
            "name": "Test User",
            "email": "test@example.com"
        }
    },
    "actors": {
        "test": {
            "id": "test-actor-id",
            "username": "test",
            "domain": "activity.readr.tw",
            "display_name": "Test User",
            "is_local": True
        }
    }
}
```

### 環境變數配置

```bash
# CI/CD 環境變數
GRAPHQL_MOCK=true
ACTIVITYPUB_DOMAIN=localhost:8000
SECRET_KEY=test-secret-key-for-ci-cd
REDIS_URL=redis://localhost:6379
```

## 測試策略

### 測試類型

1. **健康檢查測試**
   - 驗證服務基本功能
   - 檢查關鍵端點可用性

2. **ActivityPub 標準測試**
   - NodeInfo 發現
   - WebFinger 協議
   - Actor 資訊
   - Inbox/Outbox 功能

3. **API 功能測試**
   - REST API 端點
   - 資料驗證
   - 錯誤處理

4. **整合測試**
   - 端到端功能測試
   - 資料流程驗證

### 測試執行

```bash
# 本地測試
./test_activitypub.sh --full

# CI/CD 測試
python ci_test.py

# 快速測試
make test-quick
```

## CI/CD 配置

### Google Cloud Build

```yaml
# cloudbuild.yaml
steps:
  # 步驟 1: 安裝依賴和執行測試
  - name: 'gcr.io/cloud-builders/python'
    entrypoint: bash
    args:
      - -c
      - |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
        # 設定測試環境變數
        export GRAPHQL_MOCK=true
        export ACTIVITYPUB_DOMAIN=localhost:8000
        export SECRET_KEY=test-secret-key-for-ci-cd
        
        # 執行測試
        python ci_test.py
```

### 測試報告

每次測試都會生成詳細的 JSON 報告：

```json
{
  "ci_cd": true,
  "timestamp": "2024-01-01T00:00:00Z",
  "duration": 5.23,
  "total_tests": 14,
  "successful_tests": 14,
  "failed_tests": 0,
  "success_rate": 100.0,
  "all_passed": true,
  "results": [...]
}
```

## 部署流程

### 自動部署

1. **觸發條件**: 推送到 `main` 分支觸發 Cloud Build
2. **測試**: 執行 ActivityPub 功能測試
3. **建置**: 自動建置 Docker 映像
4. **容器測試**: 測試 Docker 容器功能
5. **部署**: 部署到 Google Cloud Run
6. **部署後驗證**: 執行部署後測試

### 手動部署

```bash
# 本地建置
make build

# 部署到 Cloud Run
./deploy.sh deploy --project-id YOUR_PROJECT_ID

# 或使用 Cloud Build
gcloud builds submit --config cloudbuild.yaml .
```

## 監控和警報

### 測試監控

- 每次提交都會觸發 Cloud Build
- 測試失敗會阻止後續步驟
- 測試報告會保存在 `test-results/` 目錄

### 部署監控

- 部署後自動執行健康檢查
- 驗證關鍵端點可用性
- 監控服務響應時間
- Cloud Build 日誌提供詳細的執行資訊

## 故障排除

### 常見問題

1. **測試失敗**
   ```bash
   # 檢查服務狀態
   make status
   
   # 重新執行測試
   make test-full
   ```

2. **部署失敗**
   ```bash
   # 檢查 GCP 認證
   gcloud auth list
   
   # 檢查專案設定
   gcloud config get-value project
   ```

3. **Mock Data 問題**
   ```bash
   # 檢查環境變數
   echo $GRAPHQL_MOCK
   
   # 重新設定測試環境
   python -c "from test_config import setup_test_environment; setup_test_environment()"
   ```

### 調試技巧

1. **本地重現 CI 問題**
   ```bash
   # 使用相同的環境變數
   export GRAPHQL_MOCK=true
   export ACTIVITYPUB_DOMAIN=localhost:8000
   
   # 執行 CI 測試
   python ci_test.py
   ```

2. **檢查測試報告**
   ```bash
   # 查看最新的測試報告
   ls -la ci_activitypub_test_report_*.json
   
   # 分析測試結果
   python -c "import json; print(json.dumps(json.load(open('ci_activitypub_test_report_*.json')), indent=2))"
   ```

## 最佳實踐

### 開發流程

1. **本地測試**: 提交前先在本地執行測試
2. **小步提交**: 每次提交都包含可測試的變更
3. **測試覆蓋**: 新功能必須包含相應的測試

### Mock Data 管理

1. **一致性**: 確保 mock data 與實際資料結構一致
2. **更新**: 當 API 變更時及時更新 mock data
3. **文檔**: 保持 mock data 的文檔更新

### 部署策略

1. **藍綠部署**: 使用 Cloud Run 的版本管理
2. **回滾機制**: 保留前一個穩定版本
3. **監控**: 部署後立即監控關鍵指標

## 總結

本 CI/CD 流程提供了：

- ✅ 完整的自動化測試
- ✅ 可靠的 mock data 策略
- ✅ 詳細的測試報告
- ✅ 自動化部署流程
- ✅ 部署後驗證
- ✅ 故障排除指南

這確保了程式碼品質和部署的可靠性，同時提供了良好的開發體驗。
