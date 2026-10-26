# os: linux
# description: Network interfaces, listening ports, ARP table, routes
echo "=== interfaces ==="
ip addr show 2>/dev/null || ifconfig 2>/dev/null
echo ""
echo "=== listening ports ==="
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null
echo ""
echo "=== arp table ==="
arp -n 2>/dev/null || ip neigh 2>/dev/null
echo ""
echo "=== routes ==="
ip route 2>/dev/null || route -n 2>/dev/null
