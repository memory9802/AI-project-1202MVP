# ====================================
# AI 穿搭推薦專案 Dockerfile
# 符合 OpenSpec Docker 環境標準化規格
# Python 3.12+ | Flask 3.1.2 | 多階段建置
# ====================================

# 基礎階段 - Python 3.12+ (符合標準化要求)
FROM python:3.12-slim as base

# 系統依賴 (生產環境最小化)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 非 root 用戶 (安全最佳實踐)
RUN groupadd -r appgroup && useradd -r -g appgroup -s /bin/false appuser

# 工作目錄
WORKDIR /app

# Python 環境最佳化
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ====================================
# 開發環境階段
# ====================================
FROM base as development

ENV FLASK_ENV=development \
    FLASK_DEBUG=1 \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

# 複製依賴檔案 (利用 Docker 層快取)
COPY app/requirements.txt app/requirements-dev.txt ./

# 安裝開發依賴
RUN pip install --no-cache-dir -r requirements-dev.txt

# 複製應用程式碼
COPY app/ .

# 設定權限
RUN chown -R appuser:appgroup /app
USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

# 開發模式啟動 (支援熱重載)
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

# ====================================
# 生產環境階段
# ====================================
FROM base as production

ENV FLASK_ENV=production \
    FLASK_DEBUG=0 \
    GUNICORN_BIND=0.0.0.0:5000 \
    GUNICORN_WORKERS=4 \
    GUNICORN_WORKER_CLASS=gevent \
    GUNICORN_WORKER_CONNECTIONS=1000

# 複製依賴檔案
COPY app/requirements.txt ./

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY app/ .

# 設定權限
RUN chown -R appuser:appgroup /app
USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

# 生產模式啟動 (Gunicorn + Gevent)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--worker-class", "gevent", "--worker-connections", "1000", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
