#!/bin/sh
# certbot 续期成功后的 deploy hook（deploy/nginx/setup.sh 会装到 /etc/letsencrypt/renewal-hooks/deploy/）
set -eu
nginx -t
systemctl reload nginx
