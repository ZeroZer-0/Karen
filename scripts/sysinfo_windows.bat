REM os: windows
REM description: Basic system info — hostname, OS version, uptime, logged-on users
hostname
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Boot Time"
net user
whoami /all
