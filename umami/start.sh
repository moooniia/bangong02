#!/bin/bash
set -e
cd /home/toolbox/umami
echo START $(date) > pull.log
docker compose pull >> pull.log 2>&1
docker compose up -d >> pull.log 2>&1
echo DONE $(date) >> pull.log
