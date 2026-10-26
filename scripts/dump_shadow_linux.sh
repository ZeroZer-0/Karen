# os: linux
# description: Dump /etc/passwd and /etc/shadow
echo "=== /etc/passwd ==="
cat /etc/passwd
echo ""
echo "=== /etc/shadow ==="
cat /etc/shadow 2>/dev/null || echo "[!] shadow not readable"
