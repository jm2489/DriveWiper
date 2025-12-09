#!/usr/bin/env python3
"""
wipe_drive.py - simple NIST-style wipe engine

Features (MVP):
- List candidate drives:        --list
- Wipe a drive via hdparm:      --device /dev/sdX --method ata-secure-erase
- Optional pre/post sample hash: --sample-bytes 10485760
- Logs JSON lines to /var/wipelog/wipes-YYYY-MM-DD.jsonl

Run as root, typically inside your Docker container with /dev and /var/wipelog mounted.
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from parsers.hdparm_parser import parse_hdparm_identity
from pathlib import Path
from typing import Dict, Any, Optional, List

LOG_DIR = Path("/var/wipelog")
DEFAULT_SAMPLE_BYTES = 10 * 1024 * 1024  # 10 MiB

def utc_now_iso() -> str:
    """Return ISO8601 UTC timestamp without microseconds, ending with Z."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return CompletedProcess, raising on failure if not handled."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
        )
        return result
    except FileNotFoundError:
        print(f"[ERROR] Command not found: {cmd[0]}", file=sys.stderr)
        sys.exit(1)


def ensure_root():
    if os.geteuid() != 0:
        print("[ERROR] This script must be run as root.", file=sys.stderr)
        sys.exit(1)


def list_drives() -> List[Dict[str, Any]]:
    """Use lsblk JSON to list physical disks (not partitions/loops)."""
    result = run_cmd(["lsblk", "-J", "-o", "NAME,TYPE,SIZE,MODEL,SERIAL,TRAN"])
    if result.returncode != 0:
        print("[ERROR] lsblk failed:", result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    data = json.loads(result.stdout)
    devices = []

    def walk(block):
        if block.get("type") == "disk":
            # skip loop/ram if present as disks
            name = block.get("name")
            if name and name.startswith(("loop", "ram")):
                return
            devices.append(
                {
                    "name": name,
                    "path": f"/dev/{name}",
                    "size": block.get("size"),
                    "model": block.get("model"),
                    "serial": block.get("serial"),
                    "transport": block.get("tran"),
                }
            )
        for child in block.get("children", []) or []:
            walk(child)

    for blk in data.get("blockdevices", []):
        walk(blk)

    return devices


def print_drive_table(devices: List[Dict[str, Any]]) -> None:
    if not devices:
        print("No disks found.")
        return

    print(f"{'DEVICE':<12} {'SIZE':<10} {'TRAN':<6} {'SERIAL':<20} MODEL")
    print("-" * 80)
    for d in devices:
        print(
            f"{d.get('path',''):<12} "
            f"{(d.get('size') or ''):<10} "
            f"{(d.get('transport') or ''):<6} "
            f"{(d.get('serial') or ''):<20} "
            f"{(d.get('model') or '')}"
        )

def get_hdparm_info(device: str):
    result = run_cmd(["hdparm", "-I", device])
    if result.returncode != 0 or not result.stdout:
        return None
    return parse_hdparm_identity(result.stdout)


def sample_hash(device: str, num_bytes: int) -> Optional[str]:
    """
    Read num_bytes from the start of the device and return a hex sha256 hash.
    If num_bytes <= 0, or read fails, return None.
    """
    if num_bytes <= 0:
        return None

    import hashlib

    hasher = hashlib.sha256()
    try:
        with open(device, "rb") as f:
            remaining = num_bytes
            chunk_size = 1024 * 1024
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                hasher.update(chunk)
                remaining -= len(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"[WARN] Could not read sample from {device}: {e}", file=sys.stderr)
        return None


def ata_secure_erase(device: str, password: str = "p") -> Dict[str, Any]:
    """
    Perform ATA Secure Erase using hdparm. Returns a dict with command results.
    NOTE: This will erase data permanently if it succeeds.
    """
    result: Dict[str, Any] = {
        "device": device,
        "method": "ata-secure-erase",
        "steps": [],
        "success": False,
    }

    # Step 1: set password
    step = {"step": "security-set-pass", "cmd": "", "returncode": None, "stderr": ""}
    cmd = ["hdparm", "--user-master", "u", "--security-set-pass", password, device]
    step["cmd"] = " ".join(cmd)
    cp = run_cmd(cmd)
    step["returncode"] = cp.returncode
    step["stderr"] = cp.stderr
    result["steps"].append(step)
    if cp.returncode != 0:
        result["error"] = "Failed to set security password"
        return result

    # Step 2: security-erase
    step = {"step": "security-erase", "cmd": "", "returncode": None, "stderr": ""}
    cmd = ["hdparm", "--user-master", "u", "--security-erase", password, device]
    step["cmd"] = " ".join(cmd)
    cp = run_cmd(cmd)
    step["returncode"] = cp.returncode
    step["stderr"] = cp.stderr
    result["steps"].append(step)
    if cp.returncode != 0:
        result["error"] = "Security erase command failed"
        return result

    # If we got here, commands returned 0; we'll still verify later
    result["success"] = True
    return result


def write_log(record: Dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    day = utc_now_iso()
    log_file = LOG_DIR / f"wipes-{day}.jsonl"
    record["logged_at"] = utc_now_iso()
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def do_wipe(
    device: str,
    method: str,
    operator: Optional[str],
    session_id: Optional[str],
    sample_bytes: int,
    assume_yes: bool,
    dry_run: bool,
) -> None:
    # Basic sanity check: device should exist and be a block device
    if not os.path.exists(device):
        print(f"[ERROR] Device {device} does not exist.", file=sys.stderr)
        sys.exit(1)

    if not dry_run and not assume_yes:
        confirm = input(
            f"WARNING: This will ERASE all data on {device} using {method}.\n"
            f"Type 'YES' to continue: "
        )
        if confirm.strip() != "YES":
            print("Aborted by user.")
            sys.exit(0)

    # Gather info
    devices = list_drives()
    dev_info = next((d for d in devices if d["path"] == device), None)

    hdparm_before = get_hdparm_info(device)

    pre_hash = sample_hash(device, sample_bytes) if sample_bytes > 0 else None

    started_at = utc_now_iso()

    # Run selected method
    if method == "ata-secure-erase":
        if dry_run:
            method_result = {
                "device": device,
                "method": method,
                "dry_run": True,
                "steps": [
                    {"step": "security-set-pass", "simulated": True},
                    {"step": "security-erase", "simulated": True},
                ],
                "success": True,
                "dry_run": True,
            }
        else:
            method_result = ata_secure_erase(device)
    else:
        print(f"[ERROR] Unsupported method: {method}", file=sys.stderr)
        sys.exit(1)

    ended_at = utc_now_iso()

    hdparm_after = get_hdparm_info(device)
    post_hash = sample_hash(device, sample_bytes) if sample_bytes > 0 else None

    # Build log record
    record: Dict[str, Any] = {
        "device": device,
        "method": method,
        "dry_run": dry_run,
        "operator": operator,
        "session_id": session_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "pre_sample_bytes": sample_bytes if sample_bytes > 0 else 0,
        "pre_sample_hash": pre_hash,
        "post_sample_hash": post_hash,
        "device_info": dev_info,
        "hdparm_before": hdparm_before,
        "hdparm_after": hdparm_after,
        "method_result": method_result,
        "result": "PASS" if method_result.get("success") else "FAIL",
    }

    write_log(record)

    # Human-readable summary
    print(f"\n=== WIPE SUMMARY {'(DRY RUN)' if dry_run else ''} ===")
    print(f"Device     : {device}")
    if dev_info:
        print(f"Model      : {dev_info.get('model')}")
        print(f"Serial     : {dev_info.get('serial')}")
        print(f"Size       : {dev_info.get('size')}")
        print(f"Transport  : {dev_info.get('transport')}")
    print(f"Method     : {method}")
    print(f"Dry run    : {dry_run}")
    print(f"Operator   : {operator or '(not set)'}")
    print(f"Session ID : {session_id or '(not set)'}")
    print(f"Started    : {started_at}")
    print(f"Ended      : {ended_at}")
    print(f"Result     : {record['result']}")

    if pre_hash and post_hash:
        print(f"Pre-hash   : {pre_hash}")
        print(f"Post-hash  : {post_hash}")
        print(
            "Hash match : "
            + ("YES (unchanged sample!)" if pre_hash == post_hash else "NO (sample changed)")
        )

    if not method_result.get("success"):
        print("\n[ERROR] Wipe reported failure. See log file for details.", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drive wiper engine (ATA Secure Erase + logging)."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List detected drives and exit.",
    )
    parser.add_argument(
        "--device",
        help="Device path to wipe (e.g. /dev/sdX).",
    )
    parser.add_argument(
        "--method",
        default="ata-secure-erase",
        choices=["ata-secure-erase"],
        help="Wipe method to use.",
    )
    parser.add_argument(
        "--operator",
        help="Name/ID of operator performing the wipe (for logs).",
    )
    parser.add_argument(
        "--session-id",
        help="Optional session ID or ticket number.",
    )
    parser.add_argument(
        "--sample-bytes",
        type=int,
        default=0,
        help=(
            "Number of bytes to read from the start of the device for pre/post hashing. "
            f"0 disables sampling. Default: 0 (for safety); try {DEFAULT_SAMPLE_BYTES} for 10 MiB."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Do not prompt for confirmation (DANGEROUS).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate a wipe without sending destructive commands.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list:
        ensure_root()
        devices = list_drives()
        print_drive_table(devices)
        return

    if not args.device:
        print("[ERROR] --device is required unless using --list.", file=sys.stderr)
        sys.exit(1)

    ensure_root()
    do_wipe(
        device=args.device,
        method=args.method,
        operator=args.operator,
        session_id=args.session_id,
        sample_bytes=args.sample_bytes,
        assume_yes=args.yes,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
