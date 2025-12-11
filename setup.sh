#!/usr/bin/env bash
#
# setup_docker_env.sh
# Bootstrap Docker Engine and basic dependencies on Ubuntu 24.04 (noble)
# for the Drive Wiper project — with colors, spinner, and summary.

set -euo pipefail

# ---- Color Codes ----
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
MAGENTA="\e[35m"
CYAN="\e[36m"
RESET="\e[0m"

# ---- Helper Functions ----
log() {
  printf "\n${GREEN}[+]${RESET} %b\n" "$*"
}

info() {
  printf "${CYAN}[i]${RESET} %b\n" "$*"
}

warn() {
  printf "\n${YELLOW}[!] WARNING:${RESET} %b\n" "$*"
}

err() {
  printf "\n${RED}[X] ERROR:${RESET} %b\n" "$*" >&2
}

require_root() {
  if [[ "$EUID" -ne 0 ]]; then
    err "This script must be run as root. Try: sudo $0"
    exit 1
  fi
}

spinner() {
  local pid="$1"
  local delay=0.1
  local spin='|/-\'
  local i=0

  tput civis 2>/dev/null || true
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r${CYAN}[...]${RESET} Working %s" "${spin:i++%4:1}"
    sleep "$delay"
  done

  wait "$pid"
  local rc=$?
  printf "\r\033[K"   # clear line
  tput cnorm 2>/dev/null || true
  return $rc
}

run_step() {
  local msg="$1"; shift
  log "$msg"
  bash -c "$*" &
  local pid=$!
  if ! spinner "$pid"; then
    err "Step failed: $msg"
    exit 1
  fi
}

# ---- Main ----
require_root

UBUNTU_CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"

printf "${MAGENTA}==============================${RESET}\n"
printf "${MAGENTA} DriveWiper Docker Setup      ${RESET}\n"
printf "${MAGENTA}==============================${RESET}\n"

info "Detected Ubuntu codename: $UBUNTU_CODENAME"
if [[ "$UBUNTU_CODENAME" != "noble" ]]; then
  warn "This script is optimized for Ubuntu 24.04 (noble). Continuing anyway."
fi

# 1. Remove any existing Docker packages (safe to rerun)
run_step "Removing any existing Docker packages (if present)..." "
apt-get remove -y \
  docker docker-engine docker.io containerd runc \
  docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin || true
"

# 2. Update APT
run_step "Updating APT package index..." "apt-get update -y"

# 3. Install prerequisites
run_step "Installing prerequisite packages..." "
apt-get install -y ca-certificates curl gnupg lsb-release
"

# 4. Docker GPG key
log "Configuring Docker GPG key..."
mkdir -p /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  run_step "Adding Docker GPG key..." "
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
"
else
  info "Docker GPG key already exists — skipping."
fi
chmod a+r /etc/apt/keyrings/docker.gpg

# 5. Docker APT repository
log "Adding Docker APT repository..."
cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $UBUNTU_CODENAME stable
EOF

# 6. Update APT again with Docker repo
run_step "Updating APT with Docker repository..." "apt-get update -y"

# 7. Install Docker Engine + components
run_step "Installing Docker Engine and components..." "
apt-get install -y \
  docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
"

# 8. Enable and start Docker
run_step "Enabling and starting Docker service..." "
systemctl enable --now docker
"

# 9. Install additional utilities
run_step 'Installing DriveWiper utilities (hdparm, nvme-cli, etc.)...' "
apt-get install -y \
  hdparm nvme-cli smartmontools \
  python3 python3-pip python3-venv jq
"

# 10. Add user to docker group
log "Adding invoking user to 'docker' group (if applicable)..."
TARGET_USER="${SUDO_USER:-ubuntu}"

if id "$TARGET_USER" &>/dev/null; then
  usermod -aG docker "$TARGET_USER"
  info "User '$TARGET_USER' added to 'docker' group."
  warn "Log out and log back in (or reboot) for docker group membership to apply."
else
  err "User '$TARGET_USER' not found. Skipping docker group modification."
fi

# 11. Test Docker
log "Testing Docker with hello-world container..."
if docker run --rm hello-world >/dev/null 2>&1; then
  printf "${GREEN}[✓] Docker hello-world test passed.${RESET}\n"
else
  printf "${RED}[X] Docker hello-world test FAILED. Check: systemctl status docker${RESET}\n"
fi

# 12. Summary table
log "Collecting component versions for summary..."

DOCKER_V="$(docker --version 2>/dev/null || echo 'not installed')"
COMPOSE_V="$(docker compose version 2>/dev/null | head -n1 || echo 'not available')"
HDPARM_V="$(hdparm -V 2>/dev/null || echo 'not installed')"
NVME_V="$(nvme version 2>/dev/null || echo 'not installed')"
SMARTCTL_V="$(smartctl -V 2>/dev/null | head -n1 || echo 'not installed')"
PYTHON_V="$(python3 --version 2>/dev/null || echo 'not installed')"
PIP_V="$(pip3 --version 2>/dev/null || echo 'not installed')"
JQ_V="$(jq --version 2>/dev/null || echo 'not installed')"

printf "\n${MAGENTA}=========== Install Summary ===========${RESET}\n"
printf "%-15s | %s\n" "Component" "Version / Status"
printf "%-15s-+-%s\n" "---------------" "-------------------------------"
printf "%-15s | %s\n" "Docker" "$DOCKER_V"
printf "%-15s | %s\n" "Docker Compose" "$COMPOSE_V"
printf "%-15s | %s\n" "hdparm" "$HDPARM_V"
printf "%-15s | %s\n" "nvme-cli" "$NVME_V"
printf "%-15s | %s\n" "smartctl" "$SMARTCTL_V"
printf "%-15s | %s\n" "python3" "$PYTHON_V"
printf "%-15s | %s\n" "pip3" "$PIP_V"
printf "%-15s | %s\n" "jq" "$JQ_V"
printf "${MAGENTA}=======================================${RESET}\n\n"

log "System is now ready for DriveWiper Docker containers."
