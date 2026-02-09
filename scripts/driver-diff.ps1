<#
Compare two snapshots created by driver-check.ps1 and print added/removed drivers & services.
#>
param(
    [string]$Old = "before.json",
    [string]$New = "after.json",
    [switch]$SaveOutput
)

if (-not (Test-Path $Old)) { Write-Error "Old snapshot $Old not found"; exit 1 }
if (-not (Test-Path $New)) { Write-Error "New snapshot $New not found"; exit 1 }

$old = Get-Content $Old -Raw | ConvertFrom-Json
$new = Get-Content $New -Raw | ConvertFrom-Json

# Compare PnP signed drivers by InfName + DeviceName
function make-key($d) { "{0}|{1}" -f ($d.InfName -as [string]), ($d.DeviceName -as [string]) }

$oldMap = @{}
foreach ($d in $old.PnPSignedDrivers) { $k = make-key $d; $oldMap[$k] = $d }

$newMap = @{}
foreach ($d in $new.PnPSignedDrivers) { $k = make-key $d; $newMap[$k] = $d }

$addedKeys = $newMap.Keys | Where-Object { -not $oldMap.ContainsKey($_) }
$removedKeys = $oldMap.Keys | Where-Object { -not $newMap.ContainsKey($_) }

$added = $addedKeys | ForEach-Object { $obj = $newMap[$_]; [PSCustomObject]@{ InfName = $obj.InfName; DeviceName = $obj.DeviceName; Manufacturer = $obj.Manufacturer; DriverVersion = $obj.DriverVersion } }
$removed = $removedKeys | ForEach-Object { $obj = $oldMap[$_]; [PSCustomObject]@{ InfName = $obj.InfName; DeviceName = $obj.DeviceName; Manufacturer = $obj.Manufacturer; DriverVersion = $obj.DriverVersion } }

# Compare system (kernel) drivers by Name
$oldSys = ($old.SystemDrivers | Select-Object -ExpandProperty Name) -as [string[]]
$newSys = ($new.SystemDrivers | Select-Object -ExpandProperty Name) -as [string[]]

$addedSys = Compare-Object -ReferenceObject $oldSys -DifferenceObject $newSys -PassThru | Where-Object { $_ -and ($newSys -contains $_) }
$removedSys = Compare-Object -ReferenceObject $oldSys -DifferenceObject $newSys -PassThru | Where-Object { $_ -and ($oldSys -contains $_) }

$result = [PSCustomObject]@{
    Time = (Get-Date).ToString('o')
    AddedDrivers = $added
    RemovedDrivers = $removed
    AddedSystemDrivers = $addedSys
    RemovedSystemDrivers = $removedSys
}

Write-Output "=== Drivers added ==="
if ($added) { $added | Format-Table -AutoSize } else { Write-Output "(no new PnP signed drivers)" }

Write-Output "`n=== Drivers removed ==="
if ($removed) { $removed | Format-Table -AutoSize } else { Write-Output "(no removed PnP signed drivers)" }

Write-Output "`n=== System drivers added ==="
if ($addedSys) { $addedSys | ForEach-Object { Write-Output "  $_" } } else { Write-Output "(no new system drivers)" }

Write-Output "`n=== System drivers removed ==="
if ($removedSys) { $removedSys | ForEach-Object { Write-Output "  $_" } } else { Write-Output "(no removed system drivers)" }

if ($SaveOutput) {
    $outFile = "driver-diff-" + (Get-Date -Format "yyyyMMddHHmmss") + ".json"
    $result | ConvertTo-Json -Depth 5 | Out-File -Encoding UTF8 $outFile
    Write-Output "Saved diff to $outFile"
}
