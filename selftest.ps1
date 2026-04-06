$base = "http://[::1]:8001"
$adminBase = "http://[::1]:3000"
$results = @()
$token = $null

function Test-API {
    param([string]$Name, [string]$Method, [string]$Url, [hashtable]$Headers = @{}, [string]$Body = $null, [int[]]$ExpectedCodes = @(200))
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
        }
        if ($Headers.Count -gt 0) { $params.Headers = $Headers }
        if ($Body) { 
            $params.Body = [System.Text.Encoding]::UTF8.GetBytes($Body)
            $params.ContentType = "application/json; charset=utf-8"
        }
        $r = Invoke-WebRequest @params
        $ok = $r.StatusCode -in $ExpectedCodes
        $script:results += [PSCustomObject]@{ Test=$Name; Status=if($ok){"PASS"}else{"FAIL"}; Code=$r.StatusCode; Detail="" }
        if ($ok) { Write-Host "[PASS] $Name ($($r.StatusCode))" -ForegroundColor Green }
        else { Write-Host "[FAIL] $Name - Got $($r.StatusCode), expected $($ExpectedCodes -join ','))" -ForegroundColor Red }
        return $r
    } catch {
        $code = 0
        $detail = $_.Exception.Message
        if ($_.Exception.Response) { 
            $code = [int]$_.Exception.Response.StatusCode
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                $reader = New-Object System.IO.StreamReader($stream)
                $detail = $reader.ReadToEnd()
                $reader.Close()
            } catch {}
        }
        $ok = $code -in $ExpectedCodes
        if ($ok) { 
            $script:results += [PSCustomObject]@{ Test=$Name; Status="PASS"; Code=$code; Detail="" }
            Write-Host "[PASS] $Name ($code)" -ForegroundColor Green
        } else {
            $script:results += [PSCustomObject]@{ Test=$Name; Status="FAIL"; Code=$code; Detail=$detail }
            Write-Host "[FAIL] $Name ($code) - $detail" -ForegroundColor Red
        }
        return $null
    }
}

Write-Host "`n========== ADMIN SELF-TEST (IPv6) ==========`n" -ForegroundColor Cyan

# 1. Backend OpenAPI docs
Test-API -Name "Backend Docs" -Method GET -Url "$base/docs"

# 2. Frontend serves HTML
Test-API -Name "Frontend Serves" -Method GET -Url "$adminBase/"

# 3. Admin Login (phone-based)
$loginBody = '{"phone":"13800000001"}'
$r = Test-API -Name "Admin Login" -Method POST -Url "$base/api/v1/user/login/admin" -Body $loginBody
if ($r) {
    $data = $r.Content | ConvertFrom-Json
    Write-Host "  -> Login Response keys: $($data.PSObject.Properties.Name -join ', ')" -ForegroundColor DarkGray
    # Try common token fields
    foreach ($field in @("access_token", "token")) {
        if ($data.$field) {
            $token = $data.$field
            Write-Host "  -> Got token from '$field'" -ForegroundColor DarkGray
            break
        }
    }
    if (-not $token -and $data.data) {
        foreach ($field in @("access_token", "token")) {
            if ($data.data.$field) {
                $token = $data.data.$field
                Write-Host "  -> Got token from 'data.$field'" -ForegroundColor DarkGray
                break
            }
        }
    }
    if (-not $token) {
        Write-Host "  -> Full response: $($r.Content)" -ForegroundColor Yellow
    }
}

$authHeaders = @{}
if ($token) {
    $authHeaders = @{ Authorization = "Bearer $token" }
    Write-Host "  -> Token: $($token.Substring(0, [Math]::Min(30, $token.Length)))...`n" -ForegroundColor DarkGray
    
    # 4. Get current user
    $r = Test-API -Name "Get Current User (me)" -Method GET -Url "$base/api/v1/user/me" -Headers $authHeaders
    if ($r) { Write-Host "  -> $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))" -ForegroundColor DarkGray }

    # 5. List users (admin)
    $r = Test-API -Name "List Users" -Method GET -Url "$base/api/v1/user/users" -Headers $authHeaders
    if ($r) { Write-Host "  -> $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))" -ForegroundColor DarkGray }

    # 6. List textbooks
    $r = Test-API -Name "List Textbooks" -Method GET -Url "$base/api/v1/admin/content/textbooks" -Headers $authHeaders
    if ($r) { Write-Host "  -> $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))" -ForegroundColor DarkGray }

    # 7. List knowledge points
    $r = Test-API -Name "List Knowledge Points" -Method GET -Url "$base/api/v1/admin/content/knowledge-points" -Headers $authHeaders
    if ($r) { Write-Host "  -> $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))" -ForegroundColor DarkGray }

    # 8. List exercises 
    $r = Test-API -Name "List Exercises" -Method GET -Url "$base/api/v1/admin/content/exercises" -Headers $authHeaders
    if ($r) { Write-Host "  -> $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))" -ForegroundColor DarkGray }

    # 9. List tutor conversations
    $r = Test-API -Name "List Tutor Conversations" -Method GET -Url "$base/api/v1/admin/tutor/conversations" -Headers $authHeaders
    if ($r) { Write-Host "  -> $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))" -ForegroundColor DarkGray }

    # 10. List learning tasks
    $r = Test-API -Name "List Learning Tasks" -Method GET -Url "$base/api/v1/admin/learning/tasks" -Headers $authHeaders
    if ($r) { Write-Host "  -> $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))" -ForegroundColor DarkGray }

    # 11. Frontend proxy tests
    Write-Host "`n--- Frontend Proxy Tests ---" -ForegroundColor Cyan
    Test-API -Name "Frontend Proxy -> Login" -Method POST -Url "$adminBase/api/v1/user/login/admin" -Body '{"phone":"13800000001"}'
    Test-API -Name "Frontend Proxy -> Textbooks" -Method GET -Url "$adminBase/api/v1/admin/content/textbooks" -Headers $authHeaders
    Test-API -Name "Frontend Proxy -> Users" -Method GET -Url "$adminBase/api/v1/user/users" -Headers $authHeaders
    
} else {
    Write-Host "`n[SKIP] Skipping authenticated tests - no token obtained" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========== SUMMARY ==========" -ForegroundColor Cyan
$pass = ($results | Where-Object Status -eq "PASS").Count
$fail = ($results | Where-Object Status -eq "FAIL").Count
Write-Host "PASS: $pass  FAIL: $fail  TOTAL: $($results.Count)" -ForegroundColor $(if($fail -gt 0){"Red"}else{"Green"})
if ($fail -gt 0) {
    Write-Host "`nFailed tests:" -ForegroundColor Red
    $results | Where-Object Status -eq "FAIL" | ForEach-Object { 
        $d = $_.Detail
        if ($d.Length -gt 200) { $d = $d.Substring(0, 200) + "..." }
        Write-Host "  - $($_.Test) [$($_.Code)]: $d" -ForegroundColor Red 
    }
}
