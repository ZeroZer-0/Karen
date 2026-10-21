# Karen

PostgreSQL-based C2 backdoor and service disruption toolkit for Windows and Linux targets. Designed for the CSEC 473 Cyber Defense Techniques competition (Chum Bucket red team vs. Krusty Krab blue team).

---

## What It Does

Karen has two independent functions:

**1. Persistent PostgreSQL backdoor (Windows)**
Deploys a hidden PostgreSQL cluster on all five Windows Server 2019 targets, disguised as a Realtek audio service. The cluster runs on port 8443 with a superuser account, survives reboots via a watchdog scheduled task, and generates decoy scheduled tasks to obscure the real one.

**2. Service disruption scripts**
A collection of scripts that stop, disable, block, and corrupt the scored services on each target. All scripts back up configs before modifying them and avoid touching anything protected by competition rules.

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
├── requirements.txt              # Python deps for c2_server.py
└── scripts/
    ├── whoami.sh         # Exmaple script that runs whoami (Linux)
    └── hostname.bat      # Exmaple script that runs hostname (Windows)
```

---

## C2 Dashboard

`c2_server.py` is a Flask web app that serves as a command interface for pushing scripts to targets via the Karen PostgreSQL backdoor.

**Start it:**
```bash
pip install -r requirements.txt
python c2_server.py
```

**Access:** `http://127.0.0.1:9000` - localhost only. The server refuses connections from any other address.

The dashboard lets you select a target, pick a script, and execute it through the backdoor's PostgreSQL connection. It connects to each target on port 8443 using credentials `ntmon` / `M0n1t0r$vc!`.

---

## Deploying the Windows Backdoor

Requires Ansible on the control machine and WinRM access to targets.

```bash
ansible-playbook -i REAL_inventory.ini deploy_postgres_windows.yml
```

This installs Chocolatey, installs PostgreSQL, initializes a cluster at `C:\ProgramData\Realtek\Audio` on port 8443, registers it as the `RtkAudioService` Windows service, deploys the watchdog scheduled task `RtkAudioUniversalService`, creates decoy tasks, and opens the firewall rule.

---

## Deploying Disruption Scripts

Scripts are stored in ./scripts/. Scripts are read dynamicly by c2_server.py. Scripts should specify a target or an os that the script is ment to be run against. No real scripts are included in this repo, however a example linux whoami script and windows hostname script have been included in example_scripts. Simply rename the folder or move these scripts into the ./scripts/ flolder to be used.

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
