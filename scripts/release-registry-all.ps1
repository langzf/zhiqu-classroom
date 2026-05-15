param(
  [string]$RegistryHost = "192.168.1.6:5000",
  [string]$Tag = "",
  [switch]$PushLatest
)

$ErrorActionPreference = "Stop"

if (-not $Tag) {
  $Tag = (git rev-parse --short HEAD).Trim()
}

& "$PSScriptRoot\release-build-push.ps1" -RegistryHost $RegistryHost -Tag $Tag -PushLatest:$PushLatest
& "$PSScriptRoot\release-deploy-nas-registry.ps1" -RegistryHost $RegistryHost -Tag $Tag
