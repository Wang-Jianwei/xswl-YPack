<#
Search setupapi.dev.log and common temp logs for driver installation evidence.
Usage: .\search-setupapi.ps1 -Pattern "oem" -Lines 200
#>
param(
    [Parameter(Mandatory=$true)][string]$Pattern,
    [int]$Lines = 200
)

$logPath = Join-Path $env:SystemRoot 'inf\setupapi.dev.log'
Write-Output "Searching $logPath for pattern '$Pattern' (last $Lines lines)"
if (Test-Path $logPath) {
    Get-Content $logPath -Tail $Lines -ErrorAction SilentlyContinue | Select-String -Pattern $Pattern -Context 2,2 -CaseSensitive:$false | ForEach-Object { $_ }
} else { Write-Warning "$logPath not found" }

Write-Output "\nSearching common temp logs under %TEMP% for pattern '$Pattern'"
Get-ChildItem -Path $env:TEMP -Filter *.log -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    $matches = Select-String -Path $_.FullName -Pattern $Pattern -SimpleMatch -ErrorAction SilentlyContinue
    if ($matches) { Write-Output "Matches in: $($_.FullName)"; $matches | Select-Object -First 20 }
}
