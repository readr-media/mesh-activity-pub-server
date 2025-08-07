#!/bin/bash

# READr Mesh ActivityPub Server 部署腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 函數：顯示訊息
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# 檢查必要工具
check_requirements() {
    log "檢查必要工具..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker 未安裝"
    fi
    
    if ! command -v gcloud &> /dev/null; then
        error "Google Cloud SDK 未安裝"
    fi
    
    log "所有必要工具已安裝"
}

# 本地建置和測試
build_local() {
    log "本地建置 Docker 映像..."
    
    docker build -t mesh-activity-pub-server:latest .
    
    log "Docker 映像建置完成"
}

# 本地測試
test_local() {
    log "啟動本地測試容器..."
    
    docker run -d \
        --name mesh-activity-pub-test \
        -p 8080:8080 \
        -e DATABASE_URL="postgresql+asyncpg://test:test@localhost/test" \
        -e GRAPHQL_ENDPOINT="http://localhost:4000/graphql" \
        -e ACTIVITYPUB_DOMAIN="localhost:8080" \
        -e SECRET_KEY="test-secret-key" \
        -e REDIS_URL="redis://localhost:6379" \
        mesh-activity-pub-server:latest
    
    log "測試容器已啟動，訪問 http://localhost:8080"
    log "停止測試容器: docker stop mesh-activity-pub-test && docker rm mesh-activity-pub-test"
}

# 部署到 Cloud Run
deploy_cloud_run() {
    local PROJECT_ID=$1
    local REGION=${2:-"asia-east1"}
    
    if [ -z "$PROJECT_ID" ]; then
        error "請提供 GCP 專案 ID"
    fi
    
    log "部署到 Cloud Run (專案: $PROJECT_ID, 地區: $REGION)..."
    
    # 設定專案
    gcloud config set project $PROJECT_ID
    
    # 啟用必要 API
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com
    gcloud services enable containerregistry.googleapis.com
    
    # 建立 Cloud Build 觸發器
    log "建立 Cloud Build 觸發器..."
    
    # 提交程式碼觸發部署
    log "觸發 Cloud Build..."
    gcloud builds submit --config cloudbuild.yaml .
    
    log "部署完成！"
    log "服務 URL: https://mesh-activity-pub-server-$(gcloud config get-value project).an.r.appspot.com"
}

# 設定環境變數
setup_env() {
    log "設定環境變數..."
    
    if [ ! -f .env ]; then
        cat > .env << EOF
# 資料庫設定
DATABASE_URL=postgresql+asyncpg://user:password@localhost/readr_mesh

# GraphQL 設定
GRAPHQL_ENDPOINT=http://localhost:4000/graphql
GRAPHQL_TOKEN=

# ActivityPub 設定
ACTIVITYPUB_DOMAIN=activity.readr.tw
ACTIVITYPUB_PROTOCOL=https
ACTIVITYPUB_PORT=443

# 金鑰設定
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis 設定
REDIS_URL=redis://localhost:6379

# 檔案上傳設定
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760

# 聯邦設定
FEDERATION_ENABLED=true
MAX_FOLLOWERS=10000
MAX_FOLLOWING=10000
EOF
        log "已建立 .env 檔案，請根據您的環境修改設定"
    else
        log ".env 檔案已存在"
    fi
}

# 顯示使用說明
usage() {
    echo "使用方法: $0 [命令] [選項]"
    echo ""
    echo "命令:"
    echo "  setup     設定環境變數"
    echo "  build     本地建置 Docker 映像"
    echo "  test      本地測試"
    echo "  deploy    部署到 Cloud Run"
    echo "  clean     清理本地資源"
    echo ""
    echo "選項:"
    echo "  --project-id PROJECT_ID    指定 GCP 專案 ID (用於 deploy 命令)"
    echo "  --region REGION           指定部署地區 (預設: asia-east1)"
    echo ""
    echo "範例:"
    echo "  $0 setup"
    echo "  $0 build"
    echo "  $0 test"
    echo "  $0 deploy --project-id my-project-id"
}

# 清理本地資源
clean() {
    log "清理本地資源..."
    
    docker stop mesh-activity-pub-test 2>/dev/null || true
    docker rm mesh-activity-pub-test 2>/dev/null || true
    docker rmi mesh-activity-pub-server:latest 2>/dev/null || true
    
    log "清理完成"
}

# 主程式
main() {
    case "${1:-}" in
        "setup")
            setup_env
            ;;
        "build")
            check_requirements
            build_local
            ;;
        "test")
            check_requirements
            test_local
            ;;
        "deploy")
            check_requirements
            local PROJECT_ID=""
            local REGION="asia-east1"
            
            shift
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --project-id)
                        PROJECT_ID="$2"
                        shift 2
                        ;;
                    --region)
                        REGION="$2"
                        shift 2
                        ;;
                    *)
                        error "未知選項: $1"
                        ;;
                esac
            done
            
            deploy_cloud_run "$PROJECT_ID" "$REGION"
            ;;
        "clean")
            clean
            ;;
        *)
            usage
            ;;
    esac
}

main "$@"
