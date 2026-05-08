# zhiqu-classroom Public Access Deployment

This project is deployed on the NAS with Docker Compose and exposed through a Cloudflare named tunnel on the user's own domain `yueying.cloud`.

## Public Hostnames

| Public hostname | Cloudflare service target | Docker/NAS service |
|---|---|---|
| `zqback.yueying.cloud` | `http://localhost:8002` | `zhiqu-backend` container port `8000`, host port `8002` |
| `zqstud.yueying.cloud` | `http://localhost:3000` | `zhiqu-app` nginx container port `80`, host port `3000` |
| `zqadmin.yueying.cloud` | `http://localhost:3001` | `zhiqu-admin` nginx container port `80`, host port `3001` |

Do not use Cloudflare Quick Tunnel `trycloudflare.com` URLs as the release target. Quick Tunnel URLs are only temporary diagnostics.

## NAS Docker Ports

`docker-compose.yml` should expose:

- backend: `8002:8000`
- student app: `3000:80`
- admin app: `3001:80`

The frontend nginx configs still proxy internal API calls to `http://zhiqu-backend:8000/api/` on the Compose network. The `8002` port is only the NAS host port used by Cloudflare.

## Verification

On the NAS:

```bash
cd /home/18457113512/zhiqu-classroom
sudo docker compose ps
curl -sS --max-time 10 http://localhost:8002/health
curl -sS --max-time 10 http://localhost:3000/ | head -5
curl -sS --max-time 10 http://localhost:3001/ | head -5
```

From an external machine:

```bash
curl -sS --max-time 15 https://zqback.yueying.cloud/health
curl -sS --max-time 15 https://zqstud.yueying.cloud/ | head -5
curl -sS --max-time 15 https://zqadmin.yueying.cloud/ | head -5
```

If the public hostnames return Cloudflare 530, the NAS Docker services may still be healthy but the Cloudflare named tunnel connector is not running or not authenticated on the NAS.
