$files = @(
    'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\api\README.md',
    'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\api\content-engine.md',
    'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\api\media-generation.md'
)
foreach ($f in $files) {
    $n = [System.IO.Path]::GetFileName($f)
    $l = (Get-Content $f).Count
    Write-Output "$n : $l lines"
}
# Check headings in media-generation.md
Write-Output "--- media-generation headings ---"
$lines = Get-Content $files[2]
foreach ($line in $lines) {
    if ($line -match '^#{1,3} ') { Write-Output $line }
}
