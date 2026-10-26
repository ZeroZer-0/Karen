# os: linux
# description: Basic system info — hostname, OS, kernel, uptime, users
hostname
uname -a
cat /etc/os-release 2>/dev/null | grep -E "^(NAME|VERSION)="
uptime
who
id
