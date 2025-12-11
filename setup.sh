#!/usr/bin/env bash
#
# setup_docker_env.sh
# Bootstrap Docker Engine and basic dependencies on Ubuntu 24.04 (noble)
# for the Drive Wiper project.

set -euo pipefail

# ---- Helper functions ----
log() {
  printf "\n[+] %s\n" "$*"
}

err() {
  printf "\n[!] ERROR: %s\n" "$*" >&2
}

require_root() {
  if [[ "$EUID" -ne 0 ]]; then
    err "This script must be run as root. Try: sudo $0"
    exit 1
  fi
}

# ---- Main ----
require_root

UBUNTU_CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"

if [[ "$UBUNTU_CODENAME" != "noble" ]]; then
  err "This script is intended for Ubuntu 24.04 (noble). Detected: $UBUNTU_CODENAME"
  err "You can still try to run it, but Docker repo line may need adjustment."
fi

log "Updating APT package index..."
apt-get update

log "Installing prerequisite packages..."
apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release

log "Setting up Docker GPG key..."
mkdir -p /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
else
  log "Docker GPG key already exists, skipping."
fi
chmod a+r /etc/apt/keyrings/docker.gpg

log "Adding Docker APT repository..."
cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $UBUNTU_CODENAME stable
EOF

log "Updating APT package index (with Docker repo)..."
apt-get update

log "Installing Docker Engine and related components..."
apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

log "Enabling and starting Docker service..."
systemctl enable --now docker

log "Installing additional tools for drive wiping and Python support..."
apt-get install -y \
  hdparm \
  nvme-cli \
  smartmontools \
  python3 \
  python3-venv \
  python3-pip \
  jq

log "Adding non-root user to 'docker' group (if applicable)..."
# Try to infer the user who invoked sudo, or fall back to 'ubuntu'
TARGET_USER="${SUDO_USER:-ubuntu}"

if id "$TARGET_USER" &>/dev/null; then
  usermod -aG docker "$TARGET_USER"
  log "User '$TARGET_USER' added to 'docker' group."
  log "You must log out and log back in (or reboot) for group changes to take effect."
else
  err "Could not find user '$TARGET_USER'. Skipping docker group modification."
fi

log "Testing Docker with hello-world image (this may take a moment)..."
if docker run --rm hello-world >/dev/null 2>&1; then
  log "Docker hello-world test passed."
else
  err "Docker hello-world test FAILED. Check 'systemctl status docker' and logs."
fi

log "Setup complete. Docker Engine and basic dependencies are installed."

