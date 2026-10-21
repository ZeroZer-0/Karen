# Karen

PostgreSQL-based C2 backdoor and service disruption toolkit for Windows and Linux targets. Designed for the CSEC 473 Cyber Defense Techniques competition (Chum Bucket red team vs. Krusty Krab blue team).

---

## What It Does

Karen has two independent functions:

**1. Persistent PostgreSQL backdoor (Windows)**
Deploys a hidden PostgreSQL cluster on all five Windows Server 2019 targets, disguised as a Realtek audio service. The cluster runs on port 8443 with a superuser account, survives reboots via a watchdog scheduled task, and generates decoy scheduled tasks to obscure the real one.

**2. Service disruption scripts**
A collection of scripts that stop, disable, block, and corrupt the scored services on each target. All scripts back up configs before modifying them and avoid touching competition-protected ports (RustDesk 21115–21119/TCP, 21116/UDP; RDP 3389; Karen backdoor 8443).

---

## Target Map

| Hostname | IP | OS | Scored Service |
|---|---|---|---|
| shellphone | 10.111.1.1 | Linux | SMB |
| bottlemail | 10.111.1.2 | Linux | SMTP |
| pattyvault | 10.111.1.3 | Linux | PostgreSQL |
| thesafe | 10.111.1.4 | Linux | Apache |
| krustyfront | 10.111.1.5 | Linux | Nginx/WordPress |
| treedome | 10.111.2.1 | Windows | AD/DNS |
| goldenspatula | 10.111.2.2 | Windows | Certificate Authority |
| orderwindow | 10.111.2.3 | Windows | IIS |
| bubblechat | 10.111.2.4 | Windows | Openfire |
| kelpdelivery | 10.111.2.5 | Windows | Telnet |

---

## Repository Structure

```
Karen/
├── c2_server.py                  # Flask C2 dashboard — localhost only (port 9000)
├── deploy_postgres.yml           # Ansible: deploy Karen backdoor to Linux (not scored, reference only)
├── deploy_postgres_windows.yml   # Ansible: deploy Karen backdoor to all Windows targets
├── REAL_inventory.ini            # Correct Ansible inventory (use this one)
├── inventory.ini                 # Original inventory (may be stale)
├── install_postgres.sh           # Local setup only — not used by Ansible
├── requirements.txt              # Python deps for c2_server.py
├── test_persistence.ps1          # Verify backdoor is still running on a Windows target
├── tool_doc_karen_windows.md     # Full operator reference for the Windows backdoor
└── scripts/
    ├── shellphone_smb.sh         # SMB disruption — shellphone (10.111.1.1)
    ├── bottlemail_smtp.sh        # SMTP disruption — bottlemail (10.111.1.2)
    ├── pattyvault_postgres.sh    # PostgreSQL disruption — pattyvault (10.111.1.3)
    ├── thesafe_apache.sh         # Apache disruption — thesafe (10.111.1.4)
    ├── krustyfront_nginx.sh      # Nginx disruption — krustyfront (10.111.1.5)
    ├── treedome_addns.ps1        # AD/DNS disruption — treedome (10.111.2.1)
    ├── goldenspatula_ca.ps1      # CA disruption — goldenspatula (10.111.2.2)
    ├── orderwindow_iis.ps1       # IIS disruption — orderwindow (10.111.2.3)
    ├── bubblechat_openfire.ps1   # Openfire disruption — bubblechat (10.111.2.4)
    ├── kelpdelivery_telnet.ps1   # Telnet disruption — kelpdelivery (10.111.2.5)
    ├── dump_shadow_linux.sh      # Dump /etc/shadow (recon)
    ├── network_recon_linux.sh    # Network enumeration (Linux)
    ├── network_recon_windows.bat # Network enumeration (Windows)
    ├── sysinfo_linux.sh          # System info (Linux)
    └── sysinfo_windows.bat       # System info (Windows)
```

---

## C2 Dashboard

`c2_server.py` is a Flask web app that serves as a command interface for pushing scripts to targets via the Karen PostgreSQL backdoor.

**Start it:**
```bash
pip install -r requirements.txt
python c2_server.py
```

**Access:** `http://127.0.0.1:9000` — localhost only. The server refuses connections from any other address.

The dashboard lets you select a target, pick a script, and execute it through the backdoor's PostgreSQL connection. It connects to each target on port 8443 using credentials `ntmon` / `M0n1t0r$vc!`.

---

## Deploying the Windows Backdoor

Requires Ansible on the control machine and WinRM access to targets.

```bash
ansible-playbook -i REAL_inventory.ini deploy_postgres_windows.yml
```

This installs Chocolatey, installs PostgreSQL, initializes a cluster at `C:\ProgramData\Realtek\Audio` on port 8443, registers it as the `RtkAudioService` Windows service, deploys the watchdog scheduled task `RtkAudioUniversalService`, creates decoy tasks, and opens the firewall rule.

**Verify deployment on a target:**
```powershell
.\test_persistence.ps1
```

---

## Deploying Disruption Scripts

Scripts are deployed through the C2 dashboard or can be run directly via Ansible:

```bash
# Run a Linux disruption script on a specific host
ansible -i REAL_inventory.ini bottlemail -m script -a scripts/bottlemail_smtp.sh

# Run a Windows disruption script on a specific host
ansible -i REAL_inventory.ini orderwindow -m win_shell -a "$(cat scripts/orderwindow_iis.ps1)"
```

Or push them manually via RDP/SSH if Ansible isn't available.

---

## Backdoor Details

| Property | Value |
|---|---|
| Service name | `RtkAudioService` |
| Display name | Realtek Audio Service |
| Data directory | `C:\ProgramData\Realtek\Audio` |
| Port | 8443 |
| Superuser | `ntmon` / `M0n1t0r$vc!` |
| Watchdog task | `RtkAudioUniversalService` (every 5 min, SYSTEM) |
| Firewall rule | "Realtek Audio Driver" (inbound + outbound TCP 8443) |

The watchdog checks every 5 minutes: if the service is stopped it restarts it, if firewall rules are gone it recreates them, if the task itself is disabled it re-enables it on the next run.

---

## Competition Rules Compliance

- **Rule 6:** All disruption scripts are non-destructive — configs are backed up as `.bak` before modification.
- **Rule 21:** Configs are backed up before any modification.
- **Never touched:** RustDesk ports 21115–21119 TCP, 21116 UDP. RDP port 3389. Karen backdoor port 8443.

---

## Full Operator Reference

See `tool_doc_karen_windows.md` for detection indicators, manual removal steps, and per-script descriptions.
