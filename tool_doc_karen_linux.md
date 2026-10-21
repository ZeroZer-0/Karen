# Karen — Linux Red Team Tool
## Chum Bucket Red Team | CSEC 473 Competition Documentation

---

## What It Is

Karen is the Linux persistence tool deployed to all five Ubuntu 24.04 blue team boxes. It runs a hidden PostgreSQL cluster as a systemd service using a disguised service name (`systemd-logind-helper`) to blend in, with cron-based watchdogs that keep the service running and the firewall open.

**PostgreSQL backdoor service:** PostgreSQL is installed via apt, and a separate cluster is initialized at `/var/lib/postgresql/.config`. This cluster runs on port 8443 (not the standard 5432), listens on all interfaces, and has a superuser account (`ntmon` / `M0n1t0r$vc!`). It is registered as a systemd service named `systemd-logind-helper` with `Restart=always`.

**Persistence watchdogs:**
- `/etc/cron.d/sys-helper` — runs every minute as root. If `systemd-logind-helper` is not active it starts it.
- `/etc/cron.d/sys-policy` — runs every 5 minutes as root. Rewrites `/etc/sudoers.d/99-policy` granting `postgres ALL=(ALL) NOPASSWD: ALL` if blue team removes it.
- `/etc/cron.d/net-policy` — runs every 5 minutes as root. Ensures `iptables` has ACCEPT rules for TCP 8443 inbound and outbound, recreating them if removed.

**Privilege escalation:** `/etc/sudoers.d/99-policy` grants the `postgres` user full NOPASSWD sudo. This lets red team escalate from a postgres shell to root.

> **Note:** The `99-policy` sudoers entry and `sys-policy` cron are shared with Sudowoodo. If both tools are deployed, removing one tool's components does not remove these — the other tool's cron will recreate them.

---

## How to Spot It

### Check what's listening on 8443
```bash
ss -tlnp | grep 8443
# or
netstat -tlnp | grep 8443
```
Port 8443 listening under the `postgres` process is the backdoor cluster.

### Check the service
```bash
systemctl status systemd-logind-helper
systemctl list-units --type=service | grep logind-helper
```
The real `systemd-logind` service is `systemd-logind.service` (no `-helper`). The extra one is Karen.

### Check the data directory
```bash
ls /var/lib/postgresql/.config/
# PG_VERSION file and postgresql.conf confirm it's a Postgres cluster
```

### Check the service unit file
```bash
cat /etc/systemd/system/systemd-logind-helper.service
```

### Check the watchdog cron jobs
```bash
cat /etc/cron.d/sys-helper
cat /etc/cron.d/sys-policy
cat /etc/cron.d/net-policy
```

### Check the sudoers entry
```bash
cat /etc/sudoers.d/99-policy
```
If this grants `postgres` NOPASSWD, either Karen or Sudowoodo (or both) are deployed.

### Check installed packages
```bash
dpkg -l | grep postgresql
```

---

## How to Remove It

### 1. Stop and disable the service
```bash
systemctl stop systemd-logind-helper
systemctl disable systemd-logind-helper
rm /etc/systemd/system/systemd-logind-helper.service
systemctl daemon-reload
```

### 2. Remove the data directory
```bash
rm -rf /var/lib/postgresql/.config
```

### 3. Remove the cron watchdogs
```bash
rm /etc/cron.d/sys-helper
rm /etc/cron.d/net-policy
```

### 4. Remove the sudoers entry (only if Sudowoodo is also gone)
```bash
# WARNING: 99-policy and sys-policy are shared with Sudowoodo.
# Only remove these if Sudowoodo has also been removed — otherwise
# sys-policy will recreate 99-policy every 5 minutes.
rm /etc/sudoers.d/99-policy
rm /etc/cron.d/sys-policy
```

### 5. Optionally remove PostgreSQL
```bash
apt-get remove --purge postgresql postgresql-* -y
apt-get autoremove -y
```

### 6. Block port 8443 (belt-and-suspenders)
```bash
iptables -I INPUT -p tcp --dport 8443 -j DROP
iptables -I OUTPUT -p tcp --sport 8443 -j DROP
```

### 7. Verify removal
```bash
systemctl status systemd-logind-helper    # should say "not found"
ss -tlnp | grep 8443                      # should return nothing
ls /var/lib/postgresql/.config 2>/dev/null  # should not exist
cat /etc/cron.d/sys-helper 2>/dev/null    # should not exist
```

---

## Backdoor Details

| Property | Value |
|---|---|
| Service name | `systemd-logind-helper` |
| Data directory | `/var/lib/postgresql/.config` |
| Port | 8443 |
| Superuser | `ntmon` / `M0n1t0r$vc!` |
| Database | `telemetry` |
| Service watchdog | `/etc/cron.d/sys-helper` (every 1 min, root) |
| Sudoers watchdog | `/etc/cron.d/sys-policy` (every 5 min, root) |
| Firewall watchdog | `/etc/cron.d/net-policy` (every 5 min, root) |
| Sudoers entry | `/etc/sudoers.d/99-policy` |

---

## Scripts Reference

The following scripts were prepared for Linux service disruption. All scripts back up config files before modifying them (`.bak`). None touch RustDesk ports (21115–21119 TCP, 21116 UDP) or the Karen backdoor port (8443).

### shellphone_smb.sh — SMB (10.111.1.1)
Stops and disables `smbd`, `nmbd`, and `winbind`. Blocks ports 445 and 139. Wipes `/etc/samba/smb.conf` (backed up as `.bak`) so Samba can't serve shares on restart.

---

### bottlemail_smtp.sh — SMTP (10.111.1.2)
Stops and disables `postfix`, `exim4`, `sendmail`, and `dovecot`. Blocks ports 25, 465, and 587. Corrupts `main.cf` by setting `inet_interfaces = 127.0.0.1` (backed up as `.bak`) and purges the postfix queue so the service starts empty and broken on restart.

---

### pattyvault_postgres.sh — PostgreSQL (10.111.1.3)
Stops and disables the system PostgreSQL (port 5432 only — leaves 8443 alone). Blocks port 5432. Empties `pg_hba.conf` for all clusters not in our data dir (backed up as `.bak`) so the service can't authenticate connections on restart.

---

### thesafe_apache.sh — Apache (10.111.1.4)
Stops and disables `apache2`. Blocks ports 80 and 443. Corrupts the main Apache config (backed up as `.bak`) so it can't start cleanly.

---

### krustyfront_nginx.sh — Nginx/WordPress (10.111.1.5)
Stops and disables `nginx` and any Docker containers serving WordPress. Blocks ports 80 and 443. Wipes the nginx default site config (backed up as `.bak`).

---

*Chum Bucket Red Team — CSEC 473 | For gray team and instructor reference*
