# 聯邦網站管理系統

## 概述

聯邦網站管理系統讓您可以自動發現、管理和控制與哪些 ActivityPub 網站進行同步。這個系統提供了完整的聯邦實例生命週期管理，從自動發現到核准、封鎖和監控。

## 核心功能

### 1. 自動發現
- **NodeInfo 發現**: 透過 NodeInfo 協議自動發現聯邦實例
- **WebFinger 發現**: 透過 WebFinger 協議發現實例
- **ActivityPub 發現**: 直接透過 ActivityPub 端點發現
- **活動中發現**: 從收到的活動中自動發現新的實例

### 2. 實例管理
- **手動建立**: 手動添加已知的聯邦實例
- **狀態管理**: 啟用/停用、核准/封鎖實例
- **設定管理**: 控制每個實例的行為設定
- **連接測試**: 定期測試與實例的連接狀態

### 3. 監控和統計
- **連接記錄**: 記錄所有聯邦連接的狀態
- **活動記錄**: 記錄所有聯邦活動
- **統計資訊**: 提供詳細的聯邦統計資料
- **錯誤追蹤**: 追蹤連接錯誤和失敗

## 資料庫結構

### FederationInstance（聯邦實例）
```sql
CREATE TABLE federation_instances (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    description TEXT,
    software VARCHAR(100),
    version VARCHAR(50),
    protocol VARCHAR(10) DEFAULT 'https',
    port INTEGER DEFAULT 443,
    
    -- 狀態資訊
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP WITH TIME ZONE,
    last_successful_connection TIMESTAMP WITH TIME ZONE,
    
    -- 統計資訊
    user_count INTEGER DEFAULT 0,
    post_count INTEGER DEFAULT 0,
    connection_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    -- 設定
    auto_follow BOOLEAN DEFAULT FALSE,
    auto_announce BOOLEAN DEFAULT TRUE,
    max_followers INTEGER DEFAULT 1000,
    max_following INTEGER DEFAULT 1000,
    
    -- 技術資訊
    nodeinfo_url VARCHAR(500),
    webfinger_url VARCHAR(500),
    inbox_url VARCHAR(500),
    outbox_url VARCHAR(500),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### FederationConnection（聯邦連接）
```sql
CREATE TABLE federation_connections (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES federation_instances(id),
    connection_type VARCHAR(50) NOT NULL,
    direction VARCHAR(20) NOT NULL,
    source_actor VARCHAR(500),
    target_actor VARCHAR(500),
    activity_id VARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);
```

### FederationActivity（聯邦活動）
```sql
CREATE TABLE federation_activities (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER REFERENCES federation_instances(id),
    activity_type VARCHAR(100) NOT NULL,
    activity_id VARCHAR(500) UNIQUE NOT NULL,
    actor_id VARCHAR(500),
    object_data JSONB,
    target_data JSONB,
    is_processed BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT TRUE,
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);
```

## API 端點詳解

### 實例管理

#### 取得實例列表
```http
GET /api/v1/federation/instances?limit=100&offset=0&approved_only=false&active_only=true
```

**參數**:
- `limit`: 每頁數量（預設：100）
- `offset`: 偏移量（預設：0）
- `approved_only`: 只顯示已核准的實例（預設：false）
- `active_only`: 只顯示活躍的實例（預設：true）

#### 取得特定實例
```http
GET /api/v1/federation/instances/{domain}
```

#### 建立實例
```http
POST /api/v1/federation/instances
Content-Type: application/json

{
    "domain": "mastodon.social",
    "name": "Mastodon Social",
    "description": "The original Mastodon instance",
    "software": "Mastodon",
    "version": "4.0.0",
    "auto_follow": false,
    "auto_announce": true,
    "max_followers": 1000,
    "max_following": 1000
}
```

#### 更新實例
```http
PUT /api/v1/federation/instances/{domain}
Content-Type: application/json

{
    "is_approved": true,
    "auto_follow": true,
    "description": "Updated description"
}
```

#### 核准實例
```http
POST /api/v1/federation/instances/{domain}/approve
```

#### 封鎖實例
```http
POST /api/v1/federation/instances/{domain}/block
```

#### 刪除實例
```http
DELETE /api/v1/federation/instances/{domain}
```

### 發現功能

#### 手動發現
```http
POST /api/v1/federation/discover
Content-Type: application/json

{
    "domain": "mastodon.social"
}
```

#### 自動發現
```http
POST /api/v1/federation/discover/auto
```

### 測試功能

#### 測試單一實例
```http
POST /api/v1/federation/instances/{domain}/test
```

#### 測試所有實例
```http
POST /api/v1/federation/test-all
```

### 統計和監控

#### 取得統計資訊
```http
GET /api/v1/federation/stats
```

**回應**:
```json
{
    "total_instances": 150,
    "active_instances": 120,
    "approved_instances": 100,
    "blocked_instances": 5,
    "discovery_rate": 0.8
}
```

#### 清理舊實例
```http
POST /api/v1/federation/cleanup?days=30
```

## 發現機制

### 1. NodeInfo 發現
系統會嘗試從以下端點取得 NodeInfo 資訊：
- `https://{domain}/.well-known/nodeinfo/2.0`
- `https://{domain}/.well-known/nodeinfo/1.0`

### 2. WebFinger 發現
系統會嘗試從以下端點取得 WebFinger 資訊：
- `https://{domain}/.well-known/webfinger?resource=acct:test@{domain}`

### 3. ActivityPub 發現
系統會嘗試直接存取 ActivityPub 端點：
- `https://{domain}/users/admin`

### 4. 活動中發現
系統會從收到的 ActivityPub 活動中提取域名：
- 從 `actor` 欄位提取域名
- 從 `object` 欄位提取域名
- 從 `target` 欄位提取域名

## 實例狀態

### 狀態欄位
- `is_active`: 是否啟用（預設：true）
- `is_approved`: 是否已核准（預設：false）
- `is_blocked`: 是否被封鎖（預設：false）

### 狀態流程
1. **發現**: 新實例被發現，`is_active=true`, `is_approved=false`
2. **核准**: 管理員核准實例，`is_approved=true`
3. **封鎖**: 管理員封鎖實例，`is_blocked=true`, `is_approved=false`
4. **停用**: 管理員停用實例，`is_active=false`

## 設定選項

### 自動追蹤 (auto_follow)
- `true`: 自動接受來自此實例的追蹤請求
- `false`: 手動審核追蹤請求

### 自動轉發 (auto_announce)
- `true`: 自動轉發此實例的內容
- `false`: 手動審核轉發內容

### 限制設定
- `max_followers`: 最大追蹤者數量
- `max_following`: 最大追蹤中數量

## 監控和維護

### 定期任務
1. **連接測試**: 定期測試所有活躍實例的連接
2. **統計更新**: 定期更新實例統計資訊
3. **清理任務**: 定期清理無效的舊實例
4. **自動發現**: 定期執行自動發現任務

### 錯誤處理
- 連接失敗會增加 `error_count`
- 連續失敗會自動停用實例
- 錯誤訊息會記錄在 `federation_connections` 表中

### 效能優化
- 使用背景任務處理耗時操作
- 並行處理多個實例的連接
- 快取實例資訊減少重複查詢

## 使用建議

### 1. 初始設定
```bash
# 1. 發現知名實例
curl -X POST "http://localhost:8000/api/v1/federation/discover" \
  -d '{"domain": "mastodon.social"}'

# 2. 核准實例
curl -X POST "http://localhost:8000/api/v1/federation/instances/mastodon.social/approve"

# 3. 測試連接
curl -X POST "http://localhost:8000/api/v1/federation/instances/mastodon.social/test"
```

### 2. 定期維護
```bash
# 1. 檢查統計
curl -X GET "http://localhost:8000/api/v1/federation/stats"

# 2. 測試所有連接
curl -X POST "http://localhost:8000/api/v1/federation/test-all"

# 3. 清理舊實例
curl -X POST "http://localhost:8000/api/v1/federation/cleanup?days=30"
```

### 3. 監控設定
- 設定定期執行自動發現任務
- 監控連接錯誤率
- 定期檢查實例活躍度
- 設定警報通知

## 安全考量

### 1. 實例審核
- 新發現的實例預設為未核准狀態
- 需要管理員手動核准才能進行聯邦
- 可以設定自動核准規則

### 2. 內容過濾
- 可以設定內容過濾規則
- 支援敏感內容標記
- 可以封鎖特定實例

### 3. 連接限制
- 限制每個實例的連接數量
- 防止惡意實例的濫用
- 支援連接速率限制

## 故障排除

### 常見問題

#### 1. 實例無法連接
- 檢查實例是否仍然活躍
- 檢查網路連接
- 檢查防火牆設定

#### 2. 發現失敗
- 檢查實例是否支援 ActivityPub
- 檢查 NodeInfo 端點是否可用
- 檢查 DNS 解析

#### 3. 活動同步失敗
- 檢查實例是否已核准
- 檢查實例設定
- 檢查活動格式

### 日誌檢查
```bash
# 檢查聯邦相關日誌
grep "federation" /var/log/application.log

# 檢查連接錯誤
grep "connection.*failed" /var/log/application.log
```

這個聯邦網站管理系統提供了完整的聯邦實例生命週期管理，讓您可以安全、有效地與其他 ActivityPub 網站進行同步。
