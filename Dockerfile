# 单容器：先构建前端，再用 Python 镜像同时托管 API 与静态页面
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    CALIB_DATA_DIR=/data \
    CALIB_FRONTEND_DIST=/app/frontend/dist
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/calib_cloud backend/calib_cloud
COPY --from=frontend /app/frontend/dist frontend/dist
VOLUME ["/data"]
EXPOSE 8080
WORKDIR /app/backend
CMD ["uvicorn", "calib_cloud.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*"]
