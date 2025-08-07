# ActivityPub 設定功能實作說明

## 概述

我們已經成功為 READr Mesh ActivityPub Server 添加了 Member 的 ActivityPub 設定功能，讓使用者可以控制是否啟用 ActivityPub 同步功能。

## 新增功能

### 1. 資料庫欄位

在 `Actor` 模型中新增了以下 ActivityPub 控制欄位：

```python
# ActivityPub 功能控制
activitypub_enabled = Column(Boolean, default=False)  # 是否啟用 ActivityPub 功能
activitypub_auto_follow = Column(Boolean, default=True)  # 是否自動接受追蹤請求
activitypub_public_posts = Column(Boolean, default=True)  # 是否公開發布內容
activitypub_federation_enabled = Column(Boolean, default=True)  # 是否啟用聯邦功能
```

### 2. API 端點

新增了兩個 API 端點來管理 ActivityPub 設定：

#### 取得 ActivityPub 設定
- **端點**: `GET /api/v1/mesh/members/{member_id}/activitypub-settings`
- **功能**: 取得指定 Member 的 ActivityPub 設定
- **回應**: 包含所有 ActivityPub 設定欄位的 JSON 物件

#### 更新 ActivityPub 設定
- **端點**: `PUT /api/v1/mesh/members/{member_id}/activitypub-settings`
- **功能**: 更新指定 Member 的 ActivityPub 設定
- **請求體**: 包含要更新的設定欄位
- **回應**: 更新後的完整設定

### 3. GraphQL 整合

更新了 `GraphQLClient` 類別，新增了：

- `update_member_activitypub_settings()` 方法：更新 Member 的 ActivityPub 設定
- 在 `get_member()` 和 `get_member_by_custom_id()` 方法中加入了 ActivityPub 設定欄位的查詢

### 4. 功能控制邏輯

修改了所有會產生 ActivityPub 活動的函數，加入設定檢查：

- `create_pick()`: 只有在 `activitypub_enabled` 和 `activitypub_federation_enabled` 都為 `true` 時才進行聯邦
- `create_comment()`: 同樣的檢查邏輯
- `like_pick()`: 同樣的檢查邏輯
- `announce_pick()`: 同樣的檢查邏輯

## 設定欄位說明

### activitypub_enabled
- **類型**: Boolean
- **預設值**: `false`
- **說明**: 控制是否啟用該 Member 的 ActivityPub 功能
- **影響**: 當此欄位為 `false` 時，所有 ActivityPub 活動都不會產生

### activitypub_auto_follow
- **類型**: Boolean
- **預設值**: `true`
- **說明**: 控制是否自動接受來自其他聯邦實例的追蹤請求
- **影響**: 影響 Follow 活動的處理邏輯

### activitypub_public_posts
- **類型**: Boolean
- **預設值**: `true`
- **說明**: 控制是否將內容公開發布到聯邦網路
- **影響**: 影響活動的 `to` 和 `cc` 欄位設定

### activitypub_federation_enabled
- **類型**: Boolean
- **預設值**: `true`
- **說明**: 控制是否啟用聯邦功能（發送活動到其他實例）
- **影響**: 當此欄位為 `false` 時，活動不會發送到聯邦網路

## 使用範例

### 取得設定
```bash
curl -X GET "http://localhost:8000/api/v1/mesh/members/member_123/activitypub-settings"
```

### 更新設定
```bash
curl -X PUT "http://localhost:8000/api/v1/mesh/members/member_123/activitypub-settings" \
  -H "Content-Type: application/json" \
  -d '{
    "activitypub_enabled": true,
    "activitypub_auto_follow": false,
    "activitypub_public_posts": true,
    "activitypub_federation_enabled": false
  }'
```

## 測試

我們提供了測試腳本 `test_activitypub_settings.py` 來驗證功能：

```bash
python test_activitypub_settings.py
```

## 資料同步

系統會自動同步 GraphQL 和本地資料庫的 ActivityPub 設定：

1. 當透過 API 更新設定時，會同時更新 GraphQL 和本地資料庫
2. 當取得 Member 資訊時，會從 GraphQL 取得最新的設定
3. 本地 Actor 的設定會與 GraphQL 的設定保持同步

## 向後相容性

- 所有新增的欄位都有預設值，不會影響現有的資料
- 現有的 API 端點保持不變，只是回應中加入了新的欄位
- 現有的 ActivityPub 功能在沒有設定時會使用預設值

## 未來擴展

這個設計為未來的功能擴展提供了良好的基礎：

1. **更細緻的控制**: 可以為不同類型的活動設定不同的規則
2. **隱私控制**: 可以加入更詳細的隱私設定
3. **通知控制**: 可以控制是否接收來自聯邦網路的通知
4. **內容過濾**: 可以設定內容過濾規則
