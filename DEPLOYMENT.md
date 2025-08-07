# READr Mesh ActivityPub Server 部署指南

## 概述

本文檔提供完整的部署指南，包括本地開發、測試環境和生產環境的部署步驟。

## 前置需求

### 本地開發環境
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 14+
- Redis 6+
- Google Cloud SDK

### 生產環境
- Google Cloud Platform 專案
- Cloud SQL (PostgreSQL)
- Cloud Memorystore (Redis)
- Cloud Run
- Cloud Build

## 本地開發設定

### 1. 環境準備

```bash
# 克隆專案
git clone https://github.com/readr-media/mesh-activity-pub-server.git
cd mesh-activity-pub-server

# 設定環境變數
./deploy.sh setup

# 編輯 .env 檔案
nano .env
```

### 2. 資料庫設定

使用 Docker Compose 啟動本地服務：

```bash
# 建立 docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: readr_mesh
      POSTGRES_USER: mesh_user
      POSTGRES_PASSWORD: mesh_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
EOF

# 啟動服務
docker-compose up -d

# 更新 .env 檔案中的資料庫連接
DATABASE_URL=postgresql+asyncpg://mesh_user:mesh_password@localhost/readr_mesh
REDIS_URL=redis://localhost:6379
```

### 3. 本地測試

```bash
# 建置 Docker 映像
./deploy.sh build

# 本地測試
./deploy.sh test

# 啟動開發伺服器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## GCP 部署

### 方法一：使用 Terraform（推薦）

#### 1. 準備 Terraform

```bash
cd terraform

# 複製並編輯變數檔案
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

編輯 `terraform.tfvars`：

```hcl
project_id = "your-gcp-project-id"
region = "asia-east1"
db_password = "your-strong-database-password"
graphql_endpoint = "https://your-graphql-endpoint.com/graphql"
activitypub_domain = "activity.readr.tw"
secret_key = "your-strong-secret-key"
github_owner = "readr-media"
github_repo = "mesh-activity-pub-server"
```

#### 2. 部署基礎設施

```bash
# 初始化 Terraform
terraform init

# 檢視部署計畫
terraform plan

# 部署
terraform apply
```

#### 3. 設定 GitHub Actions

在 GitHub 儲存庫設定中添加 Secrets：

- `GCP_PROJECT_ID`: GCP 專案 ID
- `GCP_SA_KEY`: GCP 服務帳戶金鑰 (JSON)
- `DATABASE_URL`: 從 Terraform 輸出取得
- `GRAPHQL_ENDPOINT`: GraphQL 端點
- `ACTIVITYPUB_DOMAIN`: ActivityPub 域名
- `SECRET_KEY`: 應用程式密鑰
- `REDIS_URL`: 從 Terraform 輸出取得

### 方法二：使用部署腳本

#### 1. 手動建立基礎設施

```bash
# 建立 Cloud SQL 實例
gcloud sql instances create mesh-activity-pub-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=asia-east1 \
  --backup-start-time=02:00

# 建立資料庫
gcloud sql databases create readr_mesh \
  --instance=mesh-activity-pub-db

# 建立使用者
gcloud sql users create mesh_user \
  --instance=mesh-activity-pub-db \
  --password=your-strong-password

# 建立 Redis 實例
gcloud redis instances create mesh-activity-pub-cache \
  --size=1 \
  --region=asia-east1 \
  --redis-version=redis_6_x
```

#### 2. 部署應用程式

```bash
# 設定專案
gcloud config set project YOUR_PROJECT_ID

# 啟用必要 API
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 部署
./deploy.sh deploy --project-id YOUR_PROJECT_ID
```

### 方法三：使用 Cloud Build

#### 1. 設定 Cloud Build 觸發器

```bash
# 建立觸發器
gcloud builds triggers create github \
  --repo-name=mesh-activity-pub-server \
  --repo-owner=readr-media \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --substitutions=_DATABASE_URL="your-db-url",_GRAPHQL_ENDPOINT="your-graphql-url",_ACTIVITYPUB_DOMAIN="activity.readr.tw",_SECRET_KEY="your-secret",_REDIS_URL="your-redis-url"
```

#### 2. 推送程式碼觸發部署

```bash
git push origin main
```

## 域名和 SSL 設定

### 1. 設定自訂域名

```bash
# 對應 Cloud Run 服務到自訂域名
gcloud run domain-mappings create \
  --service=mesh-activity-pub-server \
  --domain=activity.readr.tw \
  --region=asia-east1
```

### 2. DNS 設定

在您的 DNS 提供商處添加記錄：

```
Type: CNAME
Name: activity
Value: ghs.googlehosted.com
```

### 3. SSL 憑證

Cloud Run 會自動處理 SSL 憑證。

## 監控和日誌

### 1. Cloud Logging

```bash
# 查看日誌
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mesh-activity-pub-server"

# 設定日誌過濾器
gcloud logging sinks create mesh-activity-pub-logs \
  storage.googleapis.com/YOUR_BUCKET \
  --log-filter="resource.type=cloud_run_revision AND resource.labels.service_name=mesh-activity-pub-server"
```

### 2. 監控儀表板

在 Google Cloud Console 中建立監控儀表板：

- Cloud Run 服務指標
- 資料庫連接指標
- Redis 指標
- 自訂應用程式指標

### 3. 警報設定

```bash
# 建立警報政策
gcloud alpha monitoring policies create \
  --policy-from-file=alert-policy.yaml
```

## 備份和災難恢復

### 1. 資料庫備份

```bash
# 啟用自動備份（已在 Terraform 中設定）
gcloud sql instances patch mesh-activity-pub-db \
  --backup-start-time=02:00 \
  --backup-retention-count=7
```

### 2. 手動備份

```bash
# 建立手動備份
gcloud sql backups create \
  --instance=mesh-activity-pub-db \
  --description="Manual backup before deployment"
```

### 3. 還原程序

```bash
# 從備份還原
gcloud sql instances restore-backup \
  --backup-instance=mesh-activity-pub-db \
  --backup-id=BACKUP_ID
```

## 安全設定

### 1. 網路安全

```bash
# 設定 VPC 連接器（如果需要）
gcloud compute networks vpc-access connectors create mesh-connector \
  --network=default \
  --region=asia-east1 \
  --range=10.8.0.0/28
```

### 2. IAM 權限

```bash
# 建立服務帳戶
gcloud iam service-accounts create mesh-activity-pub-sa \
  --display-name="Mesh ActivityPub Service Account"

# 授予必要權限
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:mesh-activity-pub-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:mesh-activity-pub-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/redis.viewer"
```

### 3. 密鑰管理

```bash
# 使用 Secret Manager 儲存敏感資訊
echo -n "your-secret-key" | gcloud secrets create mesh-secret-key --data-file=-

# 在 Cloud Run 中使用 Secret
gcloud run services update mesh-activity-pub-server \
  --update-secrets=SECRET_KEY=mesh-secret-key:latest \
  --region=asia-east1
```

## 效能優化

### 1. Cloud Run 設定

```bash
# 調整資源限制
gcloud run services update mesh-activity-pub-server \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=20 \
  --min-instances=1 \
  --region=asia-east1
```

### 2. 資料庫優化

```bash
# 升級資料庫規格
gcloud sql instances patch mesh-activity-pub-db \
  --tier=db-g1-small
```

### 3. 快取策略

```bash
# 調整 Redis 規格
gcloud redis instances update mesh-activity-pub-cache \
  --size=2 \
  --region=asia-east1
```

## 故障排除

### 常見問題

1. **資料庫連接失敗**
   ```bash
   # 檢查 Cloud SQL 代理
   gcloud sql instances describe mesh-activity-pub-db
   
   # 測試連接
   gcloud sql connect mesh-activity-pub-db --user=mesh_user
   ```

2. **Redis 連接失敗**
   ```bash
   # 檢查 Redis 實例狀態
   gcloud redis instances describe mesh-activity-pub-cache --region=asia-east1
   ```

3. **Cloud Run 服務無法啟動**
   ```bash
   # 查看詳細日誌
   gcloud run services describe mesh-activity-pub-server --region=asia-east1
   
   # 查看容器日誌
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mesh-activity-pub-server" --limit=50
   ```

### 支援

如有問題，請：
1. 查看 [GitHub Issues](https://github.com/readr-media/mesh-activity-pub-server/issues)
2. 檢查 [Cloud Logging](https://console.cloud.google.com/logs)
3. 聯絡技術團隊
