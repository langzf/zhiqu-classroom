$dir = 'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\api'
if (Test-Path $dir) {
    Get-ChildItem $dir -File | ForEach-Object {
        $n = $_.Name
        $l = (Get-Content $_.FullName).Count
        Write-Output "$n : $l lines"
    }
} else {
    Write-Output "api dir not found"
}
