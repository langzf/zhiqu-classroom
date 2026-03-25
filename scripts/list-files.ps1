$dir = 'C:\Users\18513\.openclaw\workspace\zhiqu-classroom\docs\logging'
Get-ChildItem $dir -File | ForEach-Object {
    $n = $_.Name
    $l = (Get-Content $_.FullName).Count
    Write-Output "$n : $l lines"
}
