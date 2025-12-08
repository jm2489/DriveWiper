#!/usr/bin/env bash
set -e

echo "====================================================="
echo "   Drive Wiper Container (ShredOS-like environment)"
echo "   WARNING: Commands run here can PERMANENTLY erase"
echo "   data on any visible /dev/sdX or /dev/nvmeX devices."
echo "====================================================="
echo

echo "[Info] Logs directory inside container: /var/wipelog"
echo

echo "[Info] Detected block devices:"
lsblk -d -o NAME,SIZE,MODEL,SERIAL || true
echo

if [ $# -gt 0 ]; then
    echo "[Info] Executing command: $*"
    echo
    exec "$@"
else
    echo "[Info] Dropping to interactive shell. Use tools like:"
    echo "       - nwipe"
    echo "       - hdparm"
    echo "       - nvme"
    echo "       - smartctl"
    echo
    exec bash
fi
