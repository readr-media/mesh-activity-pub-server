#!/bin/bash

# ActivityPub 測試腳本
# 自動啟動服務並執行測試

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BASE_URL="http://localhost:8000"
SERVICE_PID=""
PYTHON_CMD="python3"

# 函數：打印帶顏色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 函數：檢查服務是否運行
check_service() {
    if curl -s "$BASE_URL/" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 函數：啟動服務
start_service() {
    print_info "檢查服務是否已運行..."
    
    if check_service; then
        print_success "服務已在運行"
        return 0
    fi
    
    print_info "啟動 ActivityPub 服務..."
    
    # 清理舊的進程
    pkill -f uvicorn 2>/dev/null || true
    sleep 2
    
    # 啟動服務
    $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /dev/null 2>&1 &
    SERVICE_PID=$!
    
    # 等待服務啟動
    print_info "等待服務啟動..."
    for i in {1..30}; do
        if check_service; then
            print_success "服務啟動成功"
            return 0
        fi
        sleep 1
    done
    
    print_error "服務啟動超時"
    return 1
}

# 函數：停止服務
stop_service() {
    if [ ! -z "$SERVICE_PID" ]; then
        print_info "停止服務 (PID: $SERVICE_PID)..."
        kill $SERVICE_PID 2>/dev/null || true
        wait $SERVICE_PID 2>/dev/null || true
    fi
    
    # 清理所有 uvicorn 進程
    pkill -f uvicorn 2>/dev/null || true
    print_success "服務已停止"
}

# 函數：執行測試
run_tests() {
    print_info "執行 ActivityPub 功能測試..."
    
    if ! $PYTHON_CMD test_activitypub.py "$BASE_URL"; then
        print_error "測試執行失敗"
        return 1
    fi
    
    print_success "測試完成"
    return 0
}

# 函數：顯示幫助
show_help() {
    echo "ActivityPub 測試腳本"
    echo ""
    echo "用法: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  -h, --help     顯示此幫助訊息"
    echo "  -s, --start     僅啟動服務"
    echo "  -t, --test      僅執行測試（假設服務已運行）"
    echo "  -k, --kill      停止服務"
    echo "  -f, --full      完整測試（啟動服務 + 執行測試 + 停止服務）"
    echo ""
    echo "範例:"
    echo "  $0 --full       # 完整測試流程"
    echo "  $0 --start      # 僅啟動服務"
    echo "  $0 --test       # 僅執行測試"
    echo "  $0 --kill       # 停止服務"
}

# 主函數
main() {
    local action="full"
    
    # 解析命令行參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--start)
                action="start"
                shift
                ;;
            -t|--test)
                action="test"
                shift
                ;;
            -k|--kill)
                action="kill"
                shift
                ;;
            -f|--full)
                action="full"
                shift
                ;;
            *)
                print_error "未知選項: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 設置清理函數
    trap 'stop_service' EXIT
    
    case $action in
        "start")
            start_service
            print_info "服務已啟動，按 Ctrl+C 停止"
            wait
            ;;
        "test")
            if ! check_service; then
                print_error "服務未運行，請先啟動服務"
                exit 1
            fi
            run_tests
            ;;
        "kill")
            stop_service
            ;;
        "full")
            print_info "開始完整測試流程..."
            
            # 啟動服務
            if ! start_service; then
                print_error "無法啟動服務"
                exit 1
            fi
            
            # 執行測試
            if ! run_tests; then
                print_error "測試失敗"
                exit 1
            fi
            
            # 停止服務
            stop_service
            
            print_success "完整測試流程完成"
            ;;
    esac
}

# 執行主函數
main "$@"
