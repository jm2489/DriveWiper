

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
DriveWiper
├── db
│   └── init.sql
├── Docker
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── fiserv.md
│   └── wiper
│       ├── configure_logging.py
│       ├── db_logger.py
│       ├── file_logger.py
│       ├── __init__.py
│       ├── logging_manager.py
│       ├── parsers
│       │   ├── hdparm_parser.py
│       │   └── __init__.py
│       └── wipe_drive.py
├── docker-compose.yml
├── README.md
├── setup.sh
└── uninstall.sh
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
### PostGreSQL Logging Backend

> This needs to be created before using `docker compose up` in order for the wiper to log to the database container.

Environment **sample** configuration

```env
# === Postgres Core Settings ===
POSTGRES_DB=drivewiper
POSTGRES_USER=wiper
POSTGRES_PASSWORD=supersecretpassword123

# === Wiper Database Logging Settings ===
DB_ENABLED=true
DB_HOST=db
DB_PORT=5432
DB_NAME=drivewiper
DB_USER=wiper
DB_PASSWORD=supersecretpassword123

# === File Logging Fallback ===
LOG_FALLBACK_DIR=/wiper/logs
```

---

# Docker Usage

## Docker build & run

### Build the image

```bash
docker build -t drive_wiper .
```

### Run it safely (non-destructive test mode)

```bash
docker run --rm -it drive_wiper .
```

### Run with drive access (WARNING: Destructive)

```bash
sudo docker run --rm -it \
  --privileged \
  -v /dev:/dev \
  -v /var/wipelog:/var/wipelog \
  drive_wiper
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
/dev/nvme0n1 1TB       nvme    21352580...-dry-run \
```

---

## **Dry Run (Non-Destructive Simulation)**

```bash
./wipe_drive.py \
  --device /dev/sdX \
  --dry-run \
  --operator "Jude" \
  --session-id $(uuidgen)
```

Simulates:

- ATA Secure Erase sequence
- Captures device info and logs it
- Logs user and session details

No destructive commands are executed.

---

## **Perform ATA Secure Erase (REAL destructive wipe)**

> **Note:** This will erase all data on the specified device.

```bash
./wipe_drive.py \
  --device /dev/sdX \
  --method ata-secure-erase \
  --operator "Jude" \
  --session-id $(uuidgen)
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

## Using Docker Compose

## **Build with Docker Compose**

While in the project root directory `DriveWiper/`

```bash
docker compose build
```
This will build the Docker image for both the postgres database and start the wiper service:

## **Run with Docker Compose**

```bash
docker compose up
```
For detached mode:
```bash
docker compose up -d
```

## Gaining Access to the Wiper Container

```bash
docker exec -it <container_id> /bin/bash
```

## Running wipe commands with `docker exec`
This will allow you to run the `wipe_drive.py` script with arguments directly from the host machine.

**To list detected drives:**
```bash
docker exec -it drive-wiper python3 /wiper/wipe_drive.py --list
```

**To perform a dry run on `/dev/sda` for example:**
```bash
docker exec -it drive-wiper python3 /wiper/wipe_drive.py \
  --device /dev/sda \
  --dry-run \
  --operator "Jude" \
  --session-id $(uuidgen)
```
## Runnin wipes (WARNING: Destructive)

```bash
docker exec -it drive-wiper python3 /wiper/wipe_drive.py \
  --device /dev/sdX \
  --method ata-secure-erase \
  --operator "Jude" \
  --session-id $(uuidgen) \
  --sample-bytes 1024
```
The following arguments does the following:
- Specifies the device to wipe (`/dev/sdX`)
- Uses the `ata-secure-erase` method
- Specifies the operator's name
- Specifies a unique session ID (generated by `uuidgen`)
- Specifies the number of bytes to sample (1024 bytes in this case) for pre-wipe and post-wipe sampling.
---

## **Logging**

To view logs, navigate to the log directory:

```bash
cd /var/wipelog/
```

List log files:

```bash
ls /var/wipelog/
```

## PostgreSQL Database Logging

If the PostgreSQL database is configured and running, the wiper will log to it as well.

### Verify PostgreSQL logs

```bash
docker exec -it <container_id> psql -U wiper -d drivewiper -c "SELECT * FROM wipe_logs;"
```
**OR**

```bash
docker exec -it wiper-db psql -U wiper -d drivewiper \
  -c "SELECT id, device, result, session_id, logged_at FROM wipe_logs ORDER BY id DESC LIMIT 5;"

```


# Modular Parser System

This project uses a modular parser directory:

```
/DriveWiper/Docker/wiper/parsers
├── __init__.py
└── hdparm_parser.py
```

### `hdparm_parser.py` extracts:

- Model
- Serial number
- Firmware revision
- Security state (enabled/locked/frozen)
- Enhanced erase support
- Raw ATA identity block

Structured fields make Elasticsearch indexing trivial.

---

# Planned Future Extensions

### **NVMe Support**

- `nvme sanitize --sanact=1`
- `nvme format --ses=1`
- Structured parser with `nvme id-ctrl`

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

- This tool is **destructive** when not in dry-run mode.
- Always test using:

  ```bash
  --dry-run
  ```
- Only run inside the container with:

  ```bash
  --privileged -v /dev:/dev
  ```

  if you **fully understand** the risks.
- ATA Secure Erase cannot be undone.

---

# Development Notes

### Python Requirements Inside Container

- Python 3.10+
- No external pip packages required
- Tools called internally:

  - `hdparm`
  - `nvme-cli`
  - `smartctl`
  - `lsblk`

### Time Formatting

We use ISO8601 UTC timestamps:

```
2025-12-09T03:14:25Z
```

---
