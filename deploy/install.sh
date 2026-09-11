#!/usr/bin/env bash
# 一键安装为 systemd 服务（参考实现，按服务器实际情况调整）。
# 用法：在仓库根目录执行  sudo bash deploy/install.sh
# 需要：python3 (>=3.10, 含 venv)、node/npm (构建前端；已有 frontend/dist 时可跳过)。
# 系统 python 太旧（如 Ubuntu 20.04 的 3.8）时用 uv 装一个：
#   curl -LsSf https://astral.sh/uv/install.sh | sh && uv python install 3.12
#   sudo PYTHON="$(uv python find 3.12)" bash deploy/install.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=calib-cloud
# 运行服务的用户：默认是执行 sudo 的那个人；也可 RUN_USER=xxx 覆盖
RUN_USER="${RUN_USER:-${SUDO_USER:-$(id -un)}}"
PYTHON="${PYTHON:-python3}"

echo "==> 应用目录 $APP_DIR，运行用户 $RUN_USER"

# 1. .env
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  TOKEN="$(openssl rand -hex 32 2>/dev/null || "$PYTHON" -c 'import secrets;print(secrets.token_hex(32))')"
  sed -i "s|^CALIB_API_TOKEN=.*|CALIB_API_TOKEN=$TOKEN|" "$APP_DIR/.env"
  # 端口可用 CALIB_PORT=xxx 覆盖（同机已有别的服务占 8080 时）
  if [ -n "${CALIB_PORT:-}" ]; then
    sed -i "s|^CALIB_PORT=.*|CALIB_PORT=$CALIB_PORT|" "$APP_DIR/.env"
  fi
  echo "==> 已生成 .env，写 token：$TOKEN（机器人侧推送要用，请保存）"
else
  echo "==> 已有 .env，保留"
fi

PORT="$(grep -E '^CALIB_PORT=' "$APP_DIR/.env" | cut -d= -f2)"
PORT="${PORT:-8080}"
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${PORT}$" && ! systemctl is-active -q "$SERVICE"; then
  echo "!! 端口 $PORT 已被其他进程占用，请改 .env 里的 CALIB_PORT 后重跑（或首装时 CALIB_PORT=8090 sudo bash deploy/install.sh）" >&2
  ss -ltnp | grep -E "[:.]${PORT} " >&2 || true
  exit 1
fi

# 2. 前端
if [ ! -f "$APP_DIR/frontend/dist/index.html" ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "==> 构建前端"
    (cd "$APP_DIR/frontend" && npm ci && npm run build)
  else
    echo "!! 没有 npm，跳过前端构建；可在别处 npm run build 后把 frontend/dist 拷过来" >&2
  fi
fi

# 3. 后端 venv
echo "==> 安装后端依赖"
if [ ! -x "$APP_DIR/backend/.venv/bin/python" ]; then
  "$PYTHON" -m venv "$APP_DIR/backend/.venv"
fi
"$APP_DIR/backend/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/backend/.venv/bin/pip" install -q -r "$APP_DIR/backend/requirements.txt"

# 4. 数据目录 + 权限
mkdir -p "$APP_DIR/data"
chown -R "$RUN_USER":"$RUN_USER" "$APP_DIR/data" "$APP_DIR/backend/.venv"
chown "$RUN_USER":"$RUN_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# 5. systemd
echo "==> 安装 systemd 单元 /etc/systemd/system/$SERVICE.service"
sed -e "s|__APP_DIR__|$APP_DIR|g" -e "s|__USER__|$RUN_USER|g" \
  "$APP_DIR/deploy/$SERVICE.service" > "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable --now "$SERVICE"
sleep 1
systemctl --no-pager --lines=5 status "$SERVICE" || true

echo
echo "==> 完成。健康检查：curl http://127.0.0.1:${PORT}/api/health"
echo "    日志：journalctl -u $SERVICE -f"
echo "    更新：git pull && (cd frontend && npm run build) && sudo systemctl restart $SERVICE"
