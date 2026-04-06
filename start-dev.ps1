# start-dev.ps1 — 启动所有开发服务，日志输出到 logs/ 目录
# 用法: .\start-dev.ps1 [-RestartOnly <backend|app|admin|all>]

param(
    [string]$RestartOnly = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "logs"

# 确保日志目录存在
@("backend", "app", "admin") | ForEach-Object {
    $dir = Join-Path $logDir $_
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

function Stop-ServiceByPort($port) {
    $pids = netstat -ano | Select-String "LISTENING" | Select-String ":${port}\s" |
        ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
    foreach ($pid in $pids) {
        if ($pid -and $pid -ne "0") {
            Write-Host "Stopping PID $pid on port $port..."
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

function Start-Backend {
    Write-Host "`n[Backend] Starting uvicorn on :8003..."
    $logFile = Join-Path $logDir "backend\uvicorn.log"
    $job = Start-Process -NoNewWindow -PassThru -FilePath "python" `
        -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--reload" `
        -WorkingDirectory (Join-Path $root "services") `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError (Join-Path $logDir "backend\uvicorn-err.log")
    Write-Host "[Backend] PID: $($job.Id) | Log: $logFile"
}

function Start-App {
    Write-Host "`n[App/学生端] Starting vite on :3000..."
    $logFile = Join-Path $logDir "app\vite.log"
    $job = Start-Process -NoNewWindow -PassThru -FilePath "npx" `
        -ArgumentList "vite", "--host", "0.0.0.0", "--port", "3000" `
        -WorkingDirectory (Join-Path $root "app") `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError (Join-Path $logDir "app\vite-err.log")
    Write-Host "[App] PID: $($job.Id) | Log: $logFile"
}

function Start-Admin {
    Write-Host "`n[Admin/管理后台] Starting vite on :3001..."
    $logFile = Join-Path $logDir "admin\vite.log"
    $job = Start-Process -NoNewWindow -PassThru -FilePath "npx" `
        -ArgumentList "vite", "--host", "0.0.0.0", "--port", "3001" `
        -WorkingDirectory (Join-Path $root "admin") `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError (Join-Path $logDir "admin\vite-err.log")
    Write-Host "[Admin] PID: $($job.Id) | Log: $logFile"
}

# 主逻辑
if ($RestartOnly -eq "" -or $RestartOnly -eq "all") {
    Write-Host "=== Stopping all services ==="
    Stop-ServiceByPort 8003
    Stop-ServiceByPort 3000
    Stop-ServiceByPort 3001
    Start-Sleep -Seconds 2
    Start-Backend
    Start-App
    Start-Admin
} elseif ($RestartOnly -eq "backend") {
    Stop-ServiceByPort 8003; Start-Sleep 1; Start-Backend
} elseif ($RestartOnly -eq "app") {
    Stop-ServiceByPort 3000; Start-Sleep 1; Start-App
} elseif ($RestartOnly -eq "admin") {
    Stop-ServiceByPort 3001; Start-Sleep 1; Start-Admin
}

Write-Host "`n=== All services started ==="
Write-Host "Logs directory: $logDir"
Write-Host "  Backend:  logs\backend\uvicorn.log + backend.log (structlog)"
Write-Host "  App:      logs\app\vite.log"
Write-Host "  Admin:    logs\admin\vite.log"
