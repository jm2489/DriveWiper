#!/usr/bin/env bash
#
# uninstall_docker_env.sh
# Remove Docker Engine, related packages, data, and repo configuration.

set -euo pipefail

RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
CYAN="\e[36m"
RESET="\e[0m"

log()  { printf "\n${GREEN}[+]${RESET} %b\n" "$*"; }
warn() { printf "\n${YELLOW}[!] WARNING:${RESET} %b\n" "$*"; }
err()  { printf "\n${RED}[X] ERROR:${RESET} %b\n" "$*" >&2; }

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
  printf "\r\033[K"
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

require_root

printf "${CYAN}Docker environment uninstaller starting...${RESET}\n"

run_step "Stopping Docker and containerd services..." "
systemctl stop docker docker.socket containerd 2>/dev/null || true
"

run_step "Purging Docker packages..." "
apt-get purge -y \
  docker-ce docker-ce-cli docker-ce-rootless-extras \
  docker.io containerd.io \
  docker-buildx-plugin docker-compose-plugin \
  docker docker-engine containerd runc || true
"

run_step "Autoremoving unused dependencies..." "
apt-get autoremove -y --purge || true
"

run_step "Removing Docker data directories..." "
rm -rf /var/lib/docker /var/lib/containerd /etc/docker
"

run_step "Removing Docker APT repo and key (if present)..." "
rm -f /etc/apt/sources.list.d/docker.list
rm -f /etc/apt/keyrings/docker.gpg
"

run_step "Updating APT index after removal..." "
apt-get update -y
"

warn "Docker group (if it exists) and user group membership are left intact."
warn "If you want to fully clean, you can manually run: groupdel docker (only if no users rely on it)."

printf "\n${GREEN}[✓] Docker environment has been uninstalled.${RESET}\n"
