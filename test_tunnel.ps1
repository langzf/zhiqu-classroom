try {
    $response = Invoke-WebRequest -Uri "https://maui-wow-carol-richards.trycloudflare.com" -Method Head -TimeoutSec 5 -ErrorAction Stop
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Tunnel is alive"
} catch {
    Write-Host "Tunnel is dead or changed: $_"
}
