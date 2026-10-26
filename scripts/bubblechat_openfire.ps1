# bubblechat (10.111.2.4) - Openfire disruption
# Openfire is a Java-based XMPP server, typically runs as "Openfire" service

# Stop and disable the service
Stop-Service -Name "Openfire" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "Openfire" -StartupType Disabled -ErrorAction SilentlyContinue

# Kill any java.exe processes running Openfire
Get-Process -Name "java" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
    if ($cmdline -match "openfire") {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

# Block Openfire ports
$rules = @(
    @{Name="Block Openfire XMPP";       Port=5222},  # client-to-server
    @{Name="Block Openfire XMPPS";      Port=5223},  # legacy SSL
    @{Name="Block Openfire S2S";        Port=5269},  # server-to-server
    @{Name="Block Openfire Admin HTTP"; Port=9090},  # admin console
    @{Name="Block Openfire Admin HTTPS";Port=9091}   # admin console SSL
)
foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol TCP -LocalPort $r.Port -Action Block
    }
}

# Corrupt openfire.xml (main config) with backup
$openfireBase = "C:\Program Files\Openfire"
$ofConfig = "$openfireBase\conf\openfire.xml"
if (Test-Path $ofConfig) {
    Copy-Item $ofConfig "$ofConfig.bak" -ErrorAction SilentlyContinue
    # Wipe the database connection so it can't start cleanly
    $content = Get-Content $ofConfig -Raw
    $content = $content -replace '<connectionProvider[^>]*>.*?</connectionProvider>', ''
    Set-Content $ofConfig $content -ErrorAction SilentlyContinue
}

Write-Host "[*] Openfire disruption complete on bubblechat"
