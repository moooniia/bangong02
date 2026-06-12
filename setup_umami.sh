#!/bin/bash
# 在服务器上执行：部署 Umami 访问统计并写入前端 tracking ID
set -euo pipefail

TOOLBOX=/home/toolbox
UMAMI_DIR=$TOOLBOX/umami
SITE_URL="${UMAMI_SITE_URL:-http://139.196.28.78}"
ADMIN_USER="${UMAMI_ADMIN_USER:-admin}"
ADMIN_PASS="${UMAMI_ADMIN_PASS:-$(openssl rand -hex 8)}"
APP_SECRET="${UMAMI_APP_SECRET:-$(openssl rand -hex 16)}"

mkdir -p "$UMAMI_DIR"
cd "$UMAMI_DIR"

if [ ! -f docker-compose.yml ]; then
  echo "docker-compose.yml missing in $UMAMI_DIR"
  exit 1
fi

if grep -q UMAMI_APP_SECRET_PLACEHOLDER docker-compose.yml 2>/dev/null; then
  sed -i "s/UMAMI_APP_SECRET_PLACEHOLDER/$APP_SECRET/" docker-compose.yml
fi

docker compose pull
docker compose up -d

echo "Waiting for Umami..."
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:3000/api/heartbeat >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

python3 /home/toolbox/umami_init.py
echo "Umami ready"