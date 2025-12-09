

# **Dockerized Drive Wiper**

A containerized Linux drive wiping engine built with Python, `hdparm`, `nvme-cli`, `smartctl`, and `nwipe`.
Includes **dry-run mode**, **structured logging**, and a **modular parser system** for future Elasticsearch indexing.

---

# **Overview**

This project provides a secure, modular, Dockerized wiper system capable of:

* Listing connected drives
* Running **ATA Secure Erase** (with logging)
* Performing **dry-run simulations** (non-destructive)
* Capturing pre/post metadata and sample hashes
* Generating JSONL logs suitable for SIEM / Elasticsearch indexing
* Parsing drive identity data into structured fields
* Running inside a ShredOS-like container environment

The long-term goal is to expand this into a **multi-container stack** with an Elastic Stack backend (Elasticsearch + Kibana) for compliance visibility and documentation aligned with ***NIST SP 800-88 Purge*** controls.

---

# Project Architecture

```
/wiper
│
├── wipe_drive.py             # Main wiper engine (Python)
│
├── parsers/
│   ├── __init__.py
│   └── hdparm_parser.py      # Structured parser for hdparm -I output
│
├── Dockerfile                # ShredOS-style container base
└── entrypoint.sh             # Optional startup banner / shell
```

---

# **Core Features**

### Wipe Methods Supported

| Method                  | Description                                  | Applies To   |
| ----------------------- | -------------------------------------------- | ------------ |
| `ata-secure-erase`      | Uses `hdparm` ATA Secure Erase sequence      | SATA HDD/SSD |
| *(NVMe support coming)* | Will include `nvme sanitize` / `nvme format` | NVMe drives  |

---

### Non-Destructive Dry Run Mode

Run a **full simulation**, including logging, without issuing destructive commands.

```
./wipe_drive.py --device /dev/sdX --dry-run
```

---

### JSON Logging (One File Per Day)

Logs stored under `/var/wipelog/`:

* Automatically created
* JSONL format (one record per line)
* Ready for Kibana / Elasticsearch ingestion

Example drive wipe log entry:

```json
{
  "device": "/dev/sda",
  "method": "ata-secure-erase",
  "dry_run": true,
  "device_info": {
    "model": "Samsung SSD 860 EVO",
    "serial": "S3Z9NB0M123456A",
    "security_supported": true,
    "security_enabled": false,
    "raw": "full hdparm -I output..."
  },
  "result": "PASS",
  "logged_at": "2025-12-09T03:14:25Z"
}
```

---

# Docker Usage

### Build the image

```bash
docker build -t drive_wiper .
```

### Run it safely (non-destructive test mode)

```bash
docker run --rm -it shredos-like-wiper
```

### Run with drive access (WARNING: Destructive)

```bash
sudo docker run --rm -it \
  --privileged \
  -v /dev:/dev \
  -v /var/wipelog:/var/wipelog \
  shredos-like-wiper
```

---

# wipe_drive.py — arguments & examples

All commands assume you're inside the container at:

```
/wiper/wipe_drive.py
```

---

## **Help / Usage**

```bash
./wipe_drive.py --help
```

Displays all usage options.

---

## **List Detected Drives**

```bash
./wipe_drive.py --list
```

Outputs detected disks via `lsblk -J`:

```
DEVICE       SIZE      TRAN    SERIAL
/dev/sda     500G      sata    S3Z9NB0M...
/dev/nvme0n1 1TB       nvme    21352580...
```

---

## **Dry Run (Non-Destructive Simulation)**

```bash
./wipe_drive.py --device /dev/sdX --dry-run
```

Simulates:

* Pre-sample hashing
* hdparm parsing
* Wipe record creation
* Logging
* Summary output

No destructive commands are executed.

---

## **Perform ATA Secure Erase (REAL destructive wipe)**

```bash
./wipe_drive.py \
  --device /dev/sdX \
  --method ata-secure-erase \
  --operator "Jude" \
  --session-id "123456"
```

The script will prompt:

```
WARNING: This will ERASE all data on /dev/sdX using ata-secure-erase.
Type 'YES' to continue:
```

Bypass confirmation:

```bash
./wipe_drive.py --device /dev/sda --yes
```

---

## **Sample Data Hashing**

Capture the first 10 MiB before/after the wipe to verify data removal.:

```bash
./wipe_drive.py --device /dev/sda --sample-bytes 10M
```

In dry-run, this simulates hashing.

---

# Parsers & Extendability

This project uses a modular parser directory:

```
/wiper/parsers/
    hdparm_parser.py
```

### `hdparm_parser.py` extracts:

* Model
* Serial number
* Firmware revision
* Security state (enabled/locked/frozen)
* Enhanced erase support
* Raw ATA identity block

Structured fields make Elasticsearch indexing trivial.

---

# Planned Future Extensions

### **NVMe Support**

* `nvme sanitize --sanact=1`
* `nvme format --ses=1`
* Structured parser with `nvme id-ctrl`

### **Curses UI Integration**

A compiled ncurses interface will eventually call:

```bash
wipe_drive.py --device /dev/sdX --method ... --json-out
```

### **Docker Compose Stack**

* Wiper container
* Elasticsearch
* Kibana
* Filebeat log forwarder

### **NIST 800-88 Report Generator**

Automatically produce wipe certificates.

---

# **Safety Warnings**

* This tool is **destructive** when not in dry-run mode.
* Always test using:

  ```bash
  --dry-run
  ```
* Only run inside the container with:

  ```bash
  --privileged -v /dev:/dev
  ```

  if you **fully understand** the risks.
* ATA Secure Erase cannot be undone.

---

# Development Notes

### Python Requirements Inside Container

* Python 3.10+
* No external pip packages required
* Tools called internally:

  * `hdparm`
  * `nvme-cli`
  * `smartctl`
  * `lsblk`

### File Permissions

Your main script should be executable:

```bash
chmod +x wipe_drive.py
```

### Time Formatting

We use ISO8601 UTC timestamps:

```
2025-12-09T03:14:25Z
```

---
