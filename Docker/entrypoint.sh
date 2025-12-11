#!/usr/bin/env bash
set -e

# App home
cd /wiper

LOG_DIR="${LOG_FALLBACK_DIR:-/wiper/logs}"

echo "====================================================="
echo "   Drive Wiper Container (ShredOS-like environment)"
echo "   WARNING: Commands run here can PERMANENTLY erase"
echo "   data on any visible /dev/sdX or /dev/nvmeX devices."
echo "====================================================="
echo

echo "[Info] Logs directory inside container: $LOG_DIR"
echo

echo "[Info] Detected block devices:"
lsblk -d -o NAME,SIZE,MODEL,SERIAL || true
echo

if [ $# -gt 0 ]; then
    # If user passed a command (e.g. 'bash', 'nwipe', or manual python)
    echo "[Info] Executing command: $*"
    echo
    exec "$@"
fi

# Default behavior: configure logging, then run the wiper
echo "[Info] No command provided. Running drive wiper..."
echo "[Info] Checking logging configuration..."
python3 configure_logging.py || true
echo

echo "[Info] Starting wipe_drive.py"
exec python3 wipe_drive.py
