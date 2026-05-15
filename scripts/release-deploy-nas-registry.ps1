param(
  [string]$NasHost = "192.168.1.6",
  [int]$NasPort = 10010,
  [string]$NasUser = "18457113512",
  [string]$RegistryHost = "192.168.1.6:5000",
  [string]$Tag = ""
)

$ErrorActionPreference = "Stop"

if (-not $Tag) {
  $Tag = (git rev-parse --short HEAD).Trim()
}

$remote = "$NasUser@$NasHost"
$command = "cd /home/18457113512/zhiqu-classroom && REGISTRY_HOST=$RegistryHost IMAGE_TAG=$Tag bash scripts/nas-deploy-registry.sh"

Write-Host "Deploying NAS from registry..."
Write-Host "Remote: $remote"
Write-Host "Tag: $Tag"

ssh -o StrictHostKeyChecking=no -p $NasPort $remote $command
