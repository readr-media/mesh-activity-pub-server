# ActivityPub Server Makefile

.PHONY: help install test test-full test-quick start stop clean

# 默認目標
help:
	@echo "ActivityPub Server 開發工具"
	@echo ""
	@echo "可用命令:"
	@echo "  make install     安裝依賴套件"
	@echo "  make start       啟動服務"
	@echo "  make stop        停止服務"
	@echo "  make test        快速測試（假設服務已運行）"
	@echo "  make test-full   完整測試（啟動服務 + 測試 + 停止服務）"
	@echo "  make test-quick  僅測試基本功能"
	@echo "  make clean       清理臨時文件"
	@echo "  make help        顯示此幫助訊息"

# 安裝依賴
install:
	@echo "📦 安裝依賴套件..."
	pip install -r requirements.txt

# 啟動服務
start:
	@echo "🚀 啟動 ActivityPub 服務..."
	./test_activitypub.sh --start

# 停止服務
stop:
	@echo "🛑 停止 ActivityPub 服務..."
	./test_activitypub.sh --kill

# 快速測試
test:
	@echo "🧪 執行快速測試..."
	python3 test_activitypub.py

# 完整測試
test-full:
	@echo "🧪 執行完整測試流程..."
	./test_activitypub.sh --full

# 快速測試（僅基本功能）
test-quick:
	@echo "🧪 執行快速測試（僅基本功能）..."
	@python3 test_activitypub.py

# 清理臨時文件
clean:
	@echo "🧹 清理臨時文件..."
	rm -f activitypub_test_report_*.json
	rm -f *.pyc
	rm -rf __pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 開發模式（啟動服務並保持運行）
dev:
	@echo "🔧 開發模式：啟動服務並保持運行..."
	@echo "按 Ctrl+C 停止服務"
	python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 檢查服務狀態
status:
	@echo "📊 檢查服務狀態..."
	@if curl -s http://localhost:8000/ > /dev/null 2>&1; then \
		echo "✅ 服務正在運行"; \
	else \
		echo "❌ 服務未運行"; \
	fi

# 顯示日誌
logs:
	@echo "📋 顯示服務日誌..."
	@if pgrep -f uvicorn > /dev/null; then \
		echo "服務正在運行，日誌會顯示在服務啟動的終端中"; \
	else \
		echo "服務未運行，請先執行 'make start' 或 'make dev'"; \
	fi
