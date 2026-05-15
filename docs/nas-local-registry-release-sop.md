# NAS Local Registry Release SOP

This SOP publishes zhiqu-classroom Docker images through a private registry on the NAS.
It avoids repeated NAS access to GitHub and Docker Hub during deployment.

## Architecture

```text
Windows dev machine
  -> git commit / push GitHub for source history
  -> docker build Linux images
  -> docker push 192.168.1.6:5000/zhiqu-*:TAG
  -> SSH NAS
NAS
  -> local registry container on :5000
  -> docker compose pull images from local registry
  -> docker compose up -d
Cloudflare
  -> zqback.yueying.cloud  -> localhost:8002
  -> zqstud.yueying.cloud  -> localhost:3000
  -> zqadmin.yueying.cloud -> localhost:3001
```

GitHub remains the source history. The NAS registry is the release artifact channel.

## One-Time NAS Setup

Run on NAS:

```bash
cd /home/18457113512/zhiqu-classroom
bash scripts/nas-registry-init.sh
```

Expected health:

```bash
curl http://127.0.0.1:5000/v2/
```

The registry stores data in:

```text
/home/18457113512/zhiqu-registry/data
```

Do not expose port `5000` to the public internet.

## One-Time Windows Docker Setup

The NAS registry is HTTP inside the LAN. Docker Desktop must trust it as an insecure registry.

Open Docker Desktop settings and add:

```json
{
  "insecure-registries": ["192.168.1.6:5000"]
}
```

Restart Docker Desktop after changing this.

Check:

```powershell
docker version
curl http://192.168.1.6:5000/v2/
```

## Normal Release

From repo root on Windows:

```powershell
git status --short --branch
git add <files>
git commit -m "fix: describe change"
git push origin main
```

Build and push images:

```powershell
.\scripts\release-build-push.ps1 -RegistryHost 192.168.1.6:5000 -PushLatest
```

Deploy on NAS:

```powershell
.\scripts\release-deploy-nas-registry.ps1 -RegistryHost 192.168.1.6:5000
```

Or run both:

```powershell
.\scripts\release-registry-all.ps1 -RegistryHost 192.168.1.6:5000 -PushLatest
```

The default tag is the current Git commit short hash. You can pin a tag:

```powershell
.\scripts\release-registry-all.ps1 -RegistryHost 192.168.1.6:5000 -Tag 6e091b6
```

## NAS Deploy Command

The Windows deploy script runs:

```bash
cd /home/18457113512/zhiqu-classroom
REGISTRY_HOST=192.168.1.6:5000 IMAGE_TAG=<tag> bash scripts/nas-deploy-registry.sh
```

This uses:

```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.registry.yml pull backend app admin
docker compose -f docker-compose.yml -f deploy/docker-compose.registry.yml up -d backend app admin
```

Infrastructure services still use upstream images:

- postgres
- redis
- minio

Application services use local registry images:

- `192.168.1.6:5000/zhiqu-backend:<tag>`
- `192.168.1.6:5000/zhiqu-app:<tag>`
- `192.168.1.6:5000/zhiqu-admin:<tag>`

## Verification

NAS local:

```bash
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:3000/
curl http://127.0.0.1:3001/
```

Public:

```powershell
curl https://zqback.yueying.cloud/health
curl https://zqstud.yueying.cloud/
curl https://zqadmin.yueying.cloud/
```

## Rollback

List tags in the registry from any machine that can reach the NAS:

```powershell
curl http://192.168.1.6:5000/v2/zhiqu-backend/tags/list
```

Deploy a previous tag:

```powershell
.\scripts\release-deploy-nas-registry.ps1 -RegistryHost 192.168.1.6:5000 -Tag <previous-tag>
```

## Troubleshooting

If Windows push fails with `http: server gave HTTP response to HTTPS client`,
Docker Desktop has not been configured with the NAS registry as an insecure registry.

If NAS pull fails, check registry health:

```bash
curl http://127.0.0.1:5000/v2/
sudo docker ps --filter name=zhiqu-registry
```

If the NAS repository is behind GitHub because NAS network is down, registry deployment can still work
as long as `docker-compose.yml`, `deploy/docker-compose.registry.yml`, and the deploy scripts already exist on NAS.
