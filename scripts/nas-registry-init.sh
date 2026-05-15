#!/usr/bin/env bash
set -euo pipefail

REGISTRY_PORT="${REGISTRY_PORT:-5000}"
REGISTRY_NAME="${REGISTRY_NAME:-zhiqu-registry}"
REGISTRY_DATA_DIR="${REGISTRY_DATA_DIR:-$HOME/zhiqu-registry/data}"

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

mkdir -p "$REGISTRY_DATA_DIR"

if docker_cmd ps -a --format '{{.Names}}' | grep -qx "$REGISTRY_NAME"; then
  docker_cmd start "$REGISTRY_NAME" >/dev/null
else
  docker_cmd run -d \
    --name "$REGISTRY_NAME" \
    --restart unless-stopped \
    -p "${REGISTRY_PORT}:5000" \
    -v "${REGISTRY_DATA_DIR}:/var/lib/registry" \
    registry:2 >/dev/null
fi

echo "Registry container:"
docker_cmd ps --filter "name=${REGISTRY_NAME}"

echo
echo "Registry health:"
curl -fsS "http://127.0.0.1:${REGISTRY_PORT}/v2/" >/dev/null
echo "ok: http://127.0.0.1:${REGISTRY_PORT}/v2/"
