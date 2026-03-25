$file = 'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\api\content-engine.md'
$lines = Get-Content $file
foreach ($line in $lines) {
    if ($line -match '^#{1,3} ') {
        Write-Output $line
    }
}
