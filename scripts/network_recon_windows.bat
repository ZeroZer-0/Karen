REM os: windows
REM description: Network interfaces, listening ports, ARP table, routes
echo === interfaces ===
ipconfig /all
echo.
echo === listening ports ===
netstat -ano | findstr LISTENING
echo.
echo === arp table ===
arp -a
echo.
echo === routes ===
route print
