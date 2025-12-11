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

# No command given: just configure logging and stay on standby
echo "[Info] No command provided. Running logging check and going into standby..."
python3 configure_logging.py --log-dir "$LOG_DIR"
echo

# If a command is given, run that instead (e.g., bash, python ...)
if [ $# -gt 0 ]; then
    echo "[Info] Executing command: $*"
    echo
    exec "$@"
fi

echo "[Info] Drive Wiper is ready. To run a wipe, use:"
echo "       docker exec -it drive-wiper python3 /wiper/wipe_drive.py --list"
echo "       docker exec -it drive-wiper python3 /wiper/wipe_drive.py --device /dev/sdX --dry-run"
echo

# Keep the container running
exec tail -f /dev/null
