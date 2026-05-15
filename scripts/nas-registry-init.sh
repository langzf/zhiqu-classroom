#!/usr/bin/env bash
set -euo pipefail

REGISTRY_PORT="${REGISTRY_PORT:-5000}"
REGISTRY_NAME="${REGISTRY_NAME:-zhiqu-registry}"
REGISTRY_DATA_DIR="${REGISTRY_DATA_DIR:-$HOME/zhiqu-registry/data}"
NAS_REGISTRY_HOST="${NAS_REGISTRY_HOST:-192.168.1.6:${REGISTRY_PORT}}"

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

configure_insecure_registry() {
  local hosts="${NAS_REGISTRY_HOST},127.0.0.1:${REGISTRY_PORT},localhost:${REGISTRY_PORT}"

  if docker_cmd info --format '{{json .RegistryConfig.IndexConfigs}}' 2>/dev/null | grep -q "\"${NAS_REGISTRY_HOST}\""; then
    return
  fi

  echo "Configuring Docker insecure registry: ${hosts}"
  if [ "$(id -u)" -eq 0 ]; then
    REGISTRY_INSECURE_HOSTS="$hosts" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path("/etc/docker/daemon.json")
config = json.loads(path.read_text() if path.exists() else "{}")
registries = config.setdefault("insecure-registries", [])
for item in os.environ["REGISTRY_INSECURE_HOSTS"].split(","):
    item = item.strip()
    if item and item not in registries:
        registries.append(item)
path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
PY
    systemctl restart docker
  else
    REGISTRY_INSECURE_HOSTS="$hosts" sudo -E python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path("/etc/docker/daemon.json")
config = json.loads(path.read_text() if path.exists() else "{}")
registries = config.setdefault("insecure-registries", [])
for item in os.environ["REGISTRY_INSECURE_HOSTS"].split(","):
    item = item.strip()
    if item and item not in registries:
        registries.append(item)
path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
PY
    sudo systemctl restart docker
  fi
}

configure_insecure_registry

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
