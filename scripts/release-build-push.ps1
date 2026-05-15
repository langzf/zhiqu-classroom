param(
  [string]$RegistryHost = "192.168.1.6:5000",
  [string]$Tag = "",
  [switch]$PushLatest,
  [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
  param(
    [string]$Title,
    [scriptblock]$Action
  )
  Write-Host ""
  Write-Host "==> $Title" -ForegroundColor Cyan
  & $Action
}

if (-not $Tag) {
  $Tag = (git rev-parse --short HEAD).Trim()
}

$images = @(
  @{ Name = "zhiqu-backend"; Dockerfile = "services/Dockerfile"; Context = "services" },
  @{ Name = "zhiqu-app"; Dockerfile = "Dockerfile.app"; Context = "." },
  @{ Name = "zhiqu-admin"; Dockerfile = "Dockerfile.admin"; Context = "." }
)

Invoke-Step "Checking Docker daemon" {
  docker version | Out-Host
}

foreach ($image in $images) {
  $fullName = "$RegistryHost/$($image.Name):$Tag"
  if (-not $NoBuild) {
    Invoke-Step "Building $fullName" {
      docker build -t $fullName -f $image.Dockerfile $image.Context
    }
  }

  Invoke-Step "Pushing $fullName" {
    docker push $fullName
  }

  if ($PushLatest) {
    $latestName = "$RegistryHost/$($image.Name):latest"
    Invoke-Step "Tagging and pushing $latestName" {
      docker tag $fullName $latestName
      docker push $latestName
    }
  }
}

Write-Host ""
Write-Host "Images pushed successfully." -ForegroundColor Green
Write-Host "Registry: $RegistryHost"
Write-Host "Tag: $Tag"
Write-Host ""
Write-Host "Next NAS command:"
Write-Host "REGISTRY_HOST=$RegistryHost IMAGE_TAG=$Tag bash scripts/nas-deploy-registry.sh"
