$file = 'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\api-spec.md'
$lines = Get-Content $file
foreach ($i in 0..($lines.Count-1)) {
    $l = $lines[$i]
    if ($l -match '^## ') { Write-Output ('{0}: {1}' -f ($i+1), $l) }
}
