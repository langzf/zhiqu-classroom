#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/zhiqu-classroom}"
REGISTRY_HOST="${REGISTRY_HOST:-192.168.1.6:5000}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

cd "$PROJECT_DIR"

echo "Deploying zhiqu-classroom images from ${REGISTRY_HOST} with tag ${IMAGE_TAG}"
curl -fsS "http://${REGISTRY_HOST}/v2/" >/dev/null

export REGISTRY_HOST IMAGE_TAG

docker_cmd compose -f docker-compose.yml -f deploy/docker-compose.registry.yml pull backend app admin
docker_cmd compose -f docker-compose.yml -f deploy/docker-compose.registry.yml up -d backend app admin

echo
docker_cmd compose -f docker-compose.yml -f deploy/docker-compose.registry.yml ps backend app admin

echo
echo "Local health checks:"
curl -fsS --max-time 10 http://127.0.0.1:8002/health
echo
curl -fsS --max-time 10 http://127.0.0.1:3000/ >/dev/null
echo "student app ok"
curl -fsS --max-time 10 http://127.0.0.1:3001/ >/dev/null
echo "admin app ok"
