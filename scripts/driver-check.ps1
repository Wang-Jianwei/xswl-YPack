<#
Snapshot current driver state to a JSON file for later inspection or diffs.
Run as Administrator for complete results.
#>
param(
    [string]$OutFile = "drivers_snapshot.json",
    [switch]$IncludeSetupApiLog,
    [int]$SetupApiTail = 200
)

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Run as Administrator for full results (right-click PowerShell -> Run as Administrator)."
}

$time = Get-Date -Format o

Write-Output "Collecting PnP devices..."
$pnpDevices = Get-PnpDevice -ErrorAction SilentlyContinue | Select-Object Class, FriendlyName, InstanceId, Service, Status

Write-Output "Collecting signed PnP drivers..."
$pnpsigned = Get-CimInstance Win32_PnPSignedDriver -ErrorAction SilentlyContinue | Select-Object DeviceName, Manufacturer, DriverVersion, @{n='DriverDate';e={(Get-Date $_.DriverDate -ErrorAction SilentlyContinue).ToString('yyyy-MM-dd')}}, InfName, DeviceID, DriverProviderName

Write-Output "Collecting system drivers (kernel services)..."
$systemDrivers = Get-CimInstance Win32_SystemDriver -ErrorAction SilentlyContinue | Select-Object Name, PathName, State, StartMode, ServiceType

Write-Output "Enumerating driver store (pnputil)..."
$driverStoreRaw = & pnputil /enum-drivers 2>&1

$setupApiTail = $null
if ($IncludeSetupApiLog) {
    $logPath = Join-Path $env:SystemRoot 'inf\setupapi.dev.log'
    if (Test-Path $logPath) { $setupApiTail = Get-Content $logPath -Tail $SetupApiTail -ErrorAction SilentlyContinue }
}

$snapshot = [PSCustomObject]@{
    Time = $time
    PnpDevices = $pnpDevices
    PnPSignedDrivers = $pnpsigned
    SystemDrivers = $systemDrivers
    DriverStoreRaw = $driverStoreRaw
    SetupapiLogTail = $setupApiTail
}

$snapshot | ConvertTo-Json -Depth 6 | Out-File -Encoding UTF8 $OutFile
Write-Output "Snapshot saved to $OutFile"

# also write simple CSV summaries for quick reading
$csvBase = [IO.Path]::ChangeExtension($OutFile, '.drivers.csv')
$pnpsigned | Export-Csv -Path $csvBase -NoTypeInformation -Encoding UTF8
Write-Output "CSV summary saved to $csvBase"