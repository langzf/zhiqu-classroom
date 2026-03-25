$file = 'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\api\learning-orchestrator.md'
$lines = Get-Content $file
Write-Output "Total lines: $($lines.Count)"
Write-Output "--- headings ---"
foreach ($line in $lines) {
    if ($line -match '^#{1,3} ') { Write-Output $line }
}
Write-Output "--- last 5 lines ---"
$lines[($lines.Count-5)..($lines.Count-1)] | ForEach-Object { Write-Output $_ }
