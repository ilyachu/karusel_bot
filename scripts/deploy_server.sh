#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${DEPLOY_SERVER_HOST:-5.253.188.164}"
REMOTE_USER="${DEPLOY_SERVER_USER:-root}"
REMOTE_PATH="${DEPLOY_SERVER_PATH:-/root/karusel_bot_v2}"

if command -v sshpass >/dev/null 2>&1; then
  if [[ -z "${SSHPASS:-}" && -n "${DEPLOY_SERVER_PASSWORD:-}" ]]; then
    export SSHPASS="$DEPLOY_SERVER_PASSWORD"
  fi
  if [[ -n "${SSHPASS:-}" ]]; then
    SSH_PREFIX=(sshpass -e)
  else
    SSH_PREFIX=()
  fi
else
  SSH_PREFIX=()
fi

echo "Deploy -> ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

"${SSH_PREFIX[@]}" rsync -avz \
  handlers \
  services \
  tests \
  utils \
  middlewares \
  assets \
  main.py \
  config.py \
  requirements.txt \
  Dockerfile \
  docker-compose.yml \
  README.md \
  DEPLOY.md \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"

"${SSH_PREFIX[@]}" ssh "${REMOTE_USER}@${REMOTE_HOST}" \
  "cd '${REMOTE_PATH}' && docker compose up -d --build bot && docker logs karusel_bot_new --tail 30"
