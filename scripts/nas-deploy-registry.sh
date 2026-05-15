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

wait_for_http() {
  local name="$1"
  local url="$2"
  local attempts="${3:-30}"
  local delay="${4:-2}"

  for _ in $(seq 1 "$attempts"); do
    if curl -fsS --max-time 10 "$url" >/tmp/zhiqu-health-check.out 2>/tmp/zhiqu-health-check.err; then
      cat /tmp/zhiqu-health-check.out
      return 0
    fi
    sleep "$delay"
  done

  echo "${name} health check failed: ${url}" >&2
  cat /tmp/zhiqu-health-check.err >&2 || true
  return 1
}

cd "$PROJECT_DIR"

echo "Deploying zhiqu-classroom images from ${REGISTRY_HOST} with tag ${IMAGE_TAG}"
curl -fsS "http://${REGISTRY_HOST}/v2/" >/dev/null

export REGISTRY_HOST IMAGE_TAG

docker_cmd compose -f docker-compose.yml -f deploy/docker-compose.registry.yml pull --ignore-buildable backend app admin
docker_cmd compose -f docker-compose.yml -f deploy/docker-compose.registry.yml up -d --no-build backend app admin

echo
docker_cmd compose -f docker-compose.yml -f deploy/docker-compose.registry.yml ps backend app admin

echo
echo "Local health checks:"
wait_for_http "backend" "http://127.0.0.1:8002/health" 30 2
echo
wait_for_http "student app" "http://127.0.0.1:3000/" 15 2 >/dev/null
echo "student app ok"
wait_for_http "admin app" "http://127.0.0.1:3001/" 15 2 >/dev/null
echo "admin app ok"
