# READr Mesh ActivityPub Server

為 READr Mesh 添加 ActivityPub 支援的服務，實現聯邦宇宙（Federation）功能。

## 功能特色

- ✅ 完整的 ActivityPub 協議支援
- ✅ **Mesh Pick + Comment 功能** - 類似 Facebook 的分享連結 + 貼文
- ✅ **Mesh Member 整合** - 完整的使用者資料同步
- ✅ Follow、Post、Like、Share 等核心功能
- ✅ 聯邦宇宙互通性
- ✅ WebFinger 和 NodeInfo 支援
- ✅ GraphQL 整合
- ✅ GCP Cloud Run 部署
- ✅ 自動化 CI/CD

## Mesh Pick + Comment 功能

### 概述
Mesh 的 Pick + Comment 功能類似使用者在 Facebook 上分享連結並加上貼文。這個功能是 READr Mesh 的核心特色，現在透過 ActivityPub 協議可以與其他聯邦宇宙實例互通。

### 功能特點
- **Pick（分享）**: 使用者可以分享文章連結，並加上自己的評論或說明
- **Comment（評論）**: 使用者可以對 Pick 進行評論，支援多層回覆
- **Like（按讚）**: 對 Pick 和 Comment 進行互動
- **Announce（轉發）**: 轉發其他使用者的 Pick

### ActivityPub 對應
- **Pick** → `Create` 活動 + `Note` 物件（包含 `attachment` 連結）
- **Comment** → `Create` 活動 + `Note` 物件（包含 `inReplyTo`）
- **Like** → `Like` 活動
- **Announce** → `Announce` 活動

## Mesh Member 整合

### 概述
系統完全整合 Mesh 的 Member 系統，自動同步使用者資料並建立對應的 ActivityPub Actor。

### Member 資料對應
| Mesh Member 欄位 | ActivityPub Actor 欄位 | 說明 |
|------------------|----------------------|------|
| `id` | `mesh_member_id` | Mesh Member ID |
| `customId` | `mesh_custom_id` | 自定義 ID |
| `name` | `display_name` | 顯示名稱 |
| `nickname` | `username` | 使用者名稱 |
| `intro` | `summary` | 個人簡介 |
| `avatar` | `icon_url` | 頭像 |
| `email` | `email` | 電子郵件 |
| `is_active` | `is_active` | 是否啟用 |
| `verified` | `verified` | 是否驗證 |
| `language` | `language` | 語言設定 |

### 自動同步機制
- 當 Member 首次使用 ActivityPub 功能時，自動建立對應的 Actor
- 同步 Member 的基本資料、追蹤關係、Pick 和 Comment
- 支援雙向資料同步

## 技術架構

- **後端框架**: FastAPI (Python 3.11)
- **資料庫**: PostgreSQL (Cloud SQL)
- **快取**: Redis (Cloud Memorystore)
- **部署**: Google Cloud Run
- **CI/CD**: Cloud Build + GitHub Actions
- **容器化**: Docker

## 快速開始

### 本地開發

1. **克隆專案**
```bash
git clone https://github.com/readr-media/mesh-activity-pub-server.git
cd mesh-activity-pub-server
```

2. **設定環境**
```bash
./deploy.sh setup
```

3. **修改設定**
編輯 `.env` 檔案，填入您的設定值：
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/readr_mesh
GRAPHQL_ENDPOINT=http://localhost:4000/graphql
ACTIVITYPUB_DOMAIN=activity.readr.tw
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379
```

4. **本地建置和測試**
```bash
# 建置 Docker 映像
./deploy.sh build

# 本地測試
./deploy.sh test
```

5. **啟動開發伺服器**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### GCP 部署

#### 方法一：使用部署腳本

1. **設定 GCP 認證**
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

2. **部署到 Cloud Run**
```bash
./deploy.sh deploy --project-id YOUR_PROJECT_ID
```

#### 方法二：使用 Terraform

1. **進入 Terraform 目錄**
```bash
cd terraform
```

2. **設定變數**
```bash
cp terraform.tfvars.example terraform.tfvars
# 編輯 terraform.tfvars 填入實際值
```

3. **初始化並部署**
```bash
terraform init
terraform plan
terraform apply
```

#### 方法三：使用 GitHub Actions

1. **設定 GitHub Secrets**
在 GitHub 儲存庫設定中添加以下 secrets：
- `GCP_PROJECT_ID`: GCP 專案 ID
- `GCP_SA_KEY`: GCP 服務帳戶金鑰 (JSON)
- `DATABASE_URL`: 資料庫連接字串
- `GRAPHQL_ENDPOINT`: GraphQL 端點
- `ACTIVITYPUB_DOMAIN`: ActivityPub 域名
- `SECRET_KEY`: 應用程式密鑰
- `REDIS_URL`: Redis 連接字串

2. **推送程式碼**
```bash
git push origin main
```

## API 端點

### ActivityPub 端點

- `GET /.well-known/webfinger` - WebFinger 發現
- `GET /.well-known/nodeinfo` - NodeInfo 資訊
- `GET /users/{username}` - 取得 Actor 資訊
- `GET /users/{username}/followers` - 追蹤者列表
- `GET /users/{username}/following` - 追蹤中列表
- `GET /users/{username}/outbox` - 發件匣
- `POST /inbox` - 收件匣

### 管理 API

- `GET /api/v1/health` - 健康檢查
- `GET /api/v1/actors` - 列出所有 Actor
- `POST /api/v1/actors` - 建立新 Actor

### Mesh 功能 API

- `GET /api/v1/mesh/members/{member_id}` - 取得 Member 資訊
- `GET /api/v1/mesh/members/{member_id}/activitypub-settings` - 取得 Member 的 ActivityPub 設定
- `PUT /api/v1/mesh/members/{member_id}/activitypub-settings` - 更新 Member 的 ActivityPub 設定
- `POST /api/v1/mesh/picks` - 建立新的 Pick（分享文章）
- `POST /api/v1/mesh/comments` - 建立新的 Comment
- `GET /api/v1/mesh/picks/{pick_id}/comments` - 取得 Pick 的評論列表
- `POST /api/v1/mesh/picks/{pick_id}/like` - 對 Pick 按讚
- `POST /api/v1/mesh/picks/{pick_id}/announce` - 轉發 Pick
- `GET /api/v1/mesh/members/{member_id}/picks` - 取得 Member 的 Picks

### 聯邦網站管理 API

- `GET /api/v1/federation/instances` - 取得聯邦實例列表
- `GET /api/v1/federation/instances/{domain}` - 取得特定聯邦實例資訊
- `POST /api/v1/federation/instances` - 手動建立聯邦實例
- `PUT /api/v1/federation/instances/{domain}` - 更新聯邦實例設定
- `POST /api/v1/federation/instances/{domain}/approve` - 核准聯邦實例
- `POST /api/v1/federation/instances/{domain}/block` - 封鎖聯邦實例
- `POST /api/v1/federation/instances/{domain}/test` - 測試聯邦實例連接
- `POST /api/v1/federation/discover` - 發現新的聯邦實例
- `POST /api/v1/federation/discover/auto` - 自動發現新的聯邦實例
- `GET /api/v1/federation/stats` - 取得聯邦統計資訊
- `POST /api/v1/federation/test-all` - 測試所有聯邦實例的連接
- `DELETE /api/v1/federation/instances/{domain}` - 刪除聯邦實例
- `POST /api/v1/federation/cleanup` - 清理舊的無效實例

## 使用範例

### 取得 Member 資訊

```bash
curl -X GET "http://localhost:8000/api/v1/mesh/members/member_123"
```

### 建立 Pick（分享文章）

```bash
curl -X POST "http://localhost:8000/api/v1/mesh/picks" \
  -H "Content-Type: application/json" \
  -d '{
    "story_id": "story_123",
    "objective": "這篇文章很有趣，推薦大家閱讀！",
    "kind": "share",
    "paywall": false
  }' \
  -G "member_id=member_123"
```

### 建立 Comment

```bash
curl -X POST "http://localhost:8000/api/v1/mesh/comments" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "我也覺得這篇文章很棒！",
    "pick_id": "pick_456"
  }' \
  -G "member_id=member_456"
```

### 對 Pick 按讚

```bash
curl -X POST "http://localhost:8000/api/v1/mesh/picks/pick_456/like" \
  -G "member_id=member_123"
```

### 取得 Member 的 Picks

```bash
curl -X GET "http://localhost:8000/api/v1/mesh/members/member_123/picks?limit=10&offset=0"
```

### 取得 Member 的 ActivityPub 設定

```bash
curl -X GET "http://localhost:8000/api/v1/mesh/members/member_123/activitypub-settings"
```

### 更新 Member 的 ActivityPub 設定

```bash
curl -X PUT "http://localhost:8000/api/v1/mesh/members/member_123/activitypub-settings" \
  -H "Content-Type: application/json" \
  -d '{
    "activitypub_enabled": true,
    "activitypub_auto_follow": true,
    "activitypub_public_posts": true,
    "activitypub_federation_enabled": true
  }'
```

### 發現新的聯邦實例

```bash
curl -X POST "http://localhost:8000/api/v1/federation/discover" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "mastodon.social"
  }'
```

### 取得聯邦實例列表

```bash
curl -X GET "http://localhost:8000/api/v1/federation/instances?limit=10&approved_only=true"
```

### 核准聯邦實例

```bash
curl -X POST "http://localhost:8000/api/v1/federation/instances/mastodon.social/approve"
```

### 測試聯邦實例連接

```bash
curl -X POST "http://localhost:8000/api/v1/federation/instances/mastodon.social/test"
```

### 取得聯邦統計資訊

```bash
curl -X GET "http://localhost:8000/api/v1/federation/stats"
```

### 自動發現新的聯邦實例

```bash
curl -X POST "http://localhost:8000/api/v1/federation/discover/auto"
```

## 資料庫結構

### 主要表格

- `actors` - ActivityPub Actor 資訊（對應 Mesh Member）
- `activities` - ActivityPub 活動記錄
- `follows` - 追蹤關係（對應 Mesh Member 追蹤）
- `stories` - 文章內容（對應 Mesh Story）
- `picks` - 分享記錄（對應 Mesh Pick）
- `comments` - 評論記錄（對應 Mesh Comment）
- `notes` - 一般文章內容
- `inbox_items` - 收件匣項目
- `outbox_items` - 發件匣項目
- `federation_instances` - 聯邦實例管理
- `federation_connections` - 聯邦連接記錄
- `federation_activities` - 聯邦活動記錄

### Mesh 資料對應

| Mesh 欄位 | ActivityPub 對應 | 說明 |
|-----------|------------------|------|
| `pick.objective` | `Note.content` | 分享時的說明文字 |
| `pick.story` | `Note.attachment[].href` | 分享的文章連結 |
| `comment.content` | `Note.content` | 評論內容 |
| `comment.parent` | `Note.inReplyTo` | 回覆的評論 |
| `pick.kind` | 自定義欄位 | 分享類型（share, like, bookmark） |
| `member.name` | `Actor.display_name` | 顯示名稱 |
| `member.nickname` | `Actor.username` | 使用者名稱 |
| `member.intro` | `Actor.summary` | 個人簡介 |
| `member.activitypub_enabled` | `Actor.activitypub_enabled` | 是否啟用 ActivityPub 功能 |
| `member.activitypub_auto_follow` | `Actor.activitypub_auto_follow` | 是否自動接受追蹤請求 |
| `member.activitypub_public_posts` | `Actor.activitypub_public_posts` | 是否公開發布內容 |
| `member.activitypub_federation_enabled` | `Actor.activitypub_federation_enabled` | 是否啟用聯邦功能 |

## 開發指南

### 新增 ActivityPub 活動類型

1. 在 `app/models/activitypub.py` 中定義資料模型
2. 在 `app/core/activitypub/` 中實作處理邏輯
3. 更新 API 路由

### 整合 GraphQL

使用 `app/core/graphql_client.py` 與現有的 GraphQL 服務整合：

```python
from app.core.graphql_client import GraphQLClient

client = GraphQLClient()
result = await client.get_member("member_123")
picks = await client.get_member_picks("member_123")
```

### Mesh 功能擴展

1. **新增 Pick 類型**：
   - 在 `Pick.kind` 欄位中添加新類型
   - 更新 `create_pick_object` 函數處理新類型

2. **新增互動功能**：
   - 在 `app/api/v1/endpoints/mesh.py` 中添加新端點
   - 建立對應的 ActivityPub 活動

3. **Member 資料同步**：
   - 在 `app/core/graphql_client.py` 中添加新的 Member 查詢
   - 更新 Actor 建立邏輯

## 監控和日誌

### Cloud Logging

所有日誌會自動發送到 Cloud Logging，可以設定警報和監控。

### 健康檢查

```bash
curl https://your-service-url/health
```

## 故障排除

### 常見問題

1. **資料庫連接失敗**
   - 檢查 `DATABASE_URL` 設定
   - 確認 Cloud SQL 實例運行中

2. **Redis 連接失敗**
   - 檢查 `REDIS_URL` 設定
   - 確認 Redis 實例運行中

3. **ActivityPub 簽名驗證失敗**
   - 檢查金鑰設定
   - 確認域名設定正確

4. **GraphQL 整合失敗**
   - 檢查 `GRAPHQL_ENDPOINT` 設定
   - 確認 GraphQL 服務運行中

5. **Member 同步失敗**
   - 檢查 Member ID 是否正確
   - 確認 GraphQL 查詢權限

### 日誌查看

```bash
# Cloud Run 日誌
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mesh-activity-pub-server"

# 本地日誌
docker logs mesh-activity-pub-test
```

## 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案。

## 支援

如有問題或建議，請開啟 [GitHub Issue](https://github.com/readr-media/mesh-activity-pub-server/issues)。
