# kelpdelivery (10.111.2.5) - Telnet disruption

# Stop and disable the Telnet server service
Stop-Service -Name "tlntsvr" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "tlntsvr" -StartupType Disabled -ErrorAction SilentlyContinue

# Block port 23 in Windows Firewall
$existing = Get-NetFirewallRule -DisplayName "Block Telnet" -ErrorAction SilentlyContinue
if (-not $existing) {
    New-NetFirewallRule -DisplayName "Block Telnet" -Direction Inbound -Protocol TCP -LocalPort 23 -Action Block
}

# Disable the Telnet Client/Server Windows feature entirely
Disable-WindowsOptionalFeature -Online -FeatureName "TelnetServer" -NoRestart -ErrorAction SilentlyContinue

Write-Host "[*] Telnet disruption complete on kelpdelivery"
