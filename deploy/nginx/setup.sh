#!/usr/bin/env bash
# 安装 Nginx 反代 + Let's Encrypt 证书（Debian/Ubuntu 的 sites-available 布局）。
# 用法（先跑完 deploy/install.sh，服务已在 127.0.0.1:8080 上）：
#   sudo bash deploy/nginx/setup.sh                       # 默认域名 bwt.xingxingdiandian.xyz
#   sudo DOMAIN=xxx.example.com EMAIL=me@example.com bash deploy/nginx/setup.sh
# 需要：nginx、certbot（apt install nginx certbot），域名 A 记录已指到本机，80/443 已放通。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "$HERE/../.." && pwd)"
DOMAIN="${DOMAIN:-bwt.xingxingdiandian.xyz}"
EMAIL="${EMAIL:-}"
# 后端端口跟 .env 走（本机 8080 被 netbridge-server 占了，所以不能写死）
PORT="$(grep -E '^CALIB_PORT=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2)"
PORT="${PORT:-8080}"
SITE=calib-cloud
AVAIL="/etc/nginx/sites-available/$SITE"
ENABLED="/etc/nginx/sites-enabled/$SITE"
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

command -v nginx >/dev/null || { echo "!! 未安装 nginx：apt install nginx" >&2; exit 1; }
command -v certbot >/dev/null || { echo "!! 未安装 certbot：apt install certbot" >&2; exit 1; }

# 1. 证书还没有时，先上一个只有 80 端口的临时站点，供 webroot 验证
if [ ! -f "$CERT" ]; then
  echo "==> 未找到 $DOMAIN 证书，先装临时 HTTP 站点并签发"
  mkdir -p /var/www/html
  cat > "$AVAIL" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { proxy_pass http://127.0.0.1:$PORT; include proxy_params; }
}
EOF
  ln -sf "$AVAIL" "$ENABLED"
  nginx -t && systemctl reload nginx

  if [ -n "$EMAIL" ]; then MAIL_ARGS=(-m "$EMAIL"); else MAIL_ARGS=(--register-unsafely-without-email); fi
  certbot certonly --webroot -w /var/www/html -d "$DOMAIN" \
    --non-interactive --agree-tos "${MAIL_ARGS[@]}"
fi

# 2. 安装正式配置（替换域名与后端端口；不动同机的其他站点）
echo "==> 安装 $AVAIL（域名 $DOMAIN，后端 127.0.0.1:$PORT）"
sed -e "s|bwt\.xingxingdiandian\.xyz|$DOMAIN|g" -e "s|127\.0\.0\.1:8080|127.0.0.1:$PORT|g" \
  "$HERE/$SITE.conf" > "$AVAIL"
ln -sf "$AVAIL" "$ENABLED"
nginx -t && systemctl reload nginx

# 3. 证书续期后自动 reload nginx
install -D -m 755 "$HERE/../letsencrypt/reload-nginx.sh" /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

echo
echo "==> 完成：https://$DOMAIN/        健康检查 curl -s https://$DOMAIN/api/health"
echo "    提醒：.env 里 CALIB_HOST 应为 127.0.0.1，公网只放 80/443，不要放 8080"
