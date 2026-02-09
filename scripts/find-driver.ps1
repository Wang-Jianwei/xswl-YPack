<#
Search for drivers by name/INF/provider in live system or in a snapshot created by driver-check.ps1
Usage examples:
  .\scripts\find-driver.ps1 -Pattern 'siglent' -Type all
  .\scripts\find-driver.ps1 -Pattern 'oem' -Type store
  .\scripts\find-driver.ps1 -Pattern '^oem\d+\.inf$' -Regex -Type store
  .\scripts\find-driver.ps1 -Pattern 'USB' -Type pnp -Detailed
  .\scripts\find-driver.ps1 -Pattern 'mydriver' -Snapshot before.json -Type signed
#>
param(
    [Parameter(Mandatory=$true)][string]$Pattern,
    [switch]$Regex,
    [switch]$CaseSensitive,
    [ValidateSet('pnp','signed','system','store','setupapi','all')][string]$Type = 'all',
    [string]$Snapshot,
    [int]$SetupApiTail = 200,
    [switch]$Detailed
)

function _match($value) {
    if ($null -eq $value) { return $false }
    if ($Regex) {
        if ($CaseSensitive) { return $value -cmatch $Pattern }
        else { return $value -match $Pattern }
    } else {
        $pat = "*{0}*" -f $Pattern
        if ($CaseSensitive) { return $value -clike $pat }
        else { return $value -like $pat }
    }
}

# If snapshot is provided, search inside it
if ($Snapshot) {
    if (-not (Test-Path $Snapshot)) { Write-Error "Snapshot file $Snapshot not found"; exit 1 }
    $snap = Get-Content $Snapshot -Raw | ConvertFrom-Json
    if ($Type -in @('signed','all')) {
        $matches = @()
        foreach ($d in $snap.PnPSignedDrivers) {
            if (_match($d.DeviceName) -or _match($d.InfName) -or _match($d.DriverProviderName) -or _match($d.Manufacturer)) {
                $matches += $d
            }
        }
        if ($matches) {
            Write-Output "=== PnP signed drivers matching '$Pattern' ==="
            if ($Detailed) { $matches | Format-List -Property * }
            else { $matches | Select-Object InfName, DeviceName, Manufacturer, DriverVersion | Format-Table -AutoSize }
        } else { Write-Output "(no matching PnP signed drivers found in snapshot)" }
    }
    if ($Type -in @('system','all')) {
        $matches = $snap.SystemDrivers | Where-Object { _match($_.Name) -or _match($_.PathName) }
        if ($matches) {
            Write-Output "=== System drivers matching '$Pattern' ==="
            if ($Detailed) { $matches | Format-List -Property * }
            else { $matches | Select-Object Name, PathName, State | Format-Table -AutoSize }
        } else { Write-Output "(no matching system drivers found in snapshot)" }
    }
    return
}

# Live system searches
if ($Type -in @('pnp','all')) {
    try {
        $pnp = Get-PnpDevice -ErrorAction Stop
        $pnpMatches = $pnp | Where-Object { _match($_.FriendlyName) -or _match($_.InstanceId) -or _match($_.Service) -or _match($_.Class) }
        if ($pnpMatches) {
            Write-Output "=== PnP devices matching '$Pattern' ==="
            if ($Detailed) { $pnpMatches | Format-List -Property * }
            else { $pnpMatches | Select-Object Class, FriendlyName, InstanceId, Service, Status | Format-Table -AutoSize }
        } else { Write-Output "(no matching PnP devices)" }
    } catch { Write-Warning "Get-PnpDevice failed: $_" }
}

if ($Type -in @('signed','all')) {
    try {
        $signed = Get-CimInstance Win32_PnPSignedDriver -ErrorAction Stop
        $sMatches = $signed | Where-Object { _match($_.DeviceName) -or _match($_.InfName) -or _match($_.DriverProviderName) -or _match($_.Manufacturer) }
        if ($sMatches) {
            Write-Output "=== PnP signed drivers matching '$Pattern' ==="
            if ($Detailed) { $sMatches | Format-List -Property * }
            else { $sMatches | Select-Object InfName, DeviceName, Manufacturer, DriverVersion | Format-Table -AutoSize }
        } else { Write-Output "(no matching PnP signed drivers)" }
    } catch { Write-Warning "Get-CimInstance Win32_PnPSignedDriver failed: $_" }
}

if ($Type -in @('system','all')) {
    try {
        $sys = Get-CimInstance Win32_SystemDriver -ErrorAction Stop
        $sysMatches = $sys | Where-Object { _match($_.Name) -or _match($_.PathName) }
        if ($sysMatches) {
            Write-Output "=== System drivers matching '$Pattern' ==="
            if ($Detailed) { $sysMatches | Format-List -Property * }
            else { $sysMatches | Select-Object Name, PathName, State, StartMode | Format-Table -AutoSize }
        } else { Write-Output "(no matching system drivers)" }
    } catch { Write-Warning "Get-CimInstance Win32_SystemDriver failed: $_" }
}

if ($Type -in @('store','all')) {
    try {
        $store = & pnputil /enum-drivers 2>&1
        $storeText = $store -join "`n"
        if ($Regex) {
            if ($CaseSensitive) { $storeMatches = Select-String -InputObject $storeText -Pattern $Pattern }
            else { $storeMatches = Select-String -InputObject $storeText -Pattern $Pattern -CaseSensitive:$false }
        } else {
            $pat = $Pattern
            $storeMatches = Select-String -InputObject $storeText -SimpleMatch -Pattern $pat
        }
        if ($storeMatches) {
            Write-Output "=== Driver store entries matching '$Pattern' ==="
            $storeMatches | Select-Object -First 200
        } else { Write-Output "(no matching entries in driver store)" }
    } catch { Write-Warning "pnputil failed: $_" }
}

if ($Type -in @('setupapi','all')) {
    $logPath = Join-Path $env:SystemRoot 'inf\setupapi.dev.log'
    if (Test-Path $logPath) {
        $lines = Get-Content $logPath -Tail $SetupApiTail -ErrorAction SilentlyContinue
        if ($Regex) {
            if ($CaseSensitive) { $matches = $lines | Select-String -Pattern $Pattern }
            else { $matches = $lines | Select-String -Pattern $Pattern -CaseSensitive:$false }
        } else {
            $matches = $lines | Select-String -SimpleMatch -Pattern $Pattern
        }
        if ($matches) { Write-Output "=== setupapi.dev.log matches ==="; $matches | Select-Object -First 200 }
        else { Write-Output "(no matches in setupapi.dev.log)" }
    } else { Write-Warning "$logPath not found" }
}
