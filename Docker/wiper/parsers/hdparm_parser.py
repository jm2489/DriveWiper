# hdparm_parser.py
# Parses `hdparm -I` output into structured fields.

from typing import Dict, Any


def parse_hdparm_identity(text: str) -> Dict[str, Any]:
    """
    Parse hdparm -I output into a structured dictionary suitable
    for Elasticsearch indexing. Keeps full raw text under 'raw'.
    """
    data: Dict[str, Any] = {"raw": text}

    lines = text.splitlines()
    in_security = False

    for line in lines:
        stripped = line.strip()

        # Basic drive identity
        if stripped.startswith("Model Number:"):
            data["model"] = stripped.split("Model Number:", 1)[1].strip()
        elif stripped.startswith("Serial Number:"):
            data["serial"] = stripped.split("Serial Number:", 1)[1].strip()
        elif stripped.startswith("Firmware Revision:"):
            data["firmware"] = stripped.split("Firmware Revision:", 1)[1].strip()

        # Optional sizes (best effort)
        if "device size with M = 1000*1000:" in stripped:
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                data["reported_size_m10"] = parts[1].strip()

        # Enter security block
        if stripped.startswith("Security:"):
            in_security = True
            continue

        # Security parsing block
        if in_security:
            # If indentation disappears, exit block
            if stripped and not line.startswith((" ", "\t")):
                in_security = False
                continue

            lower = stripped.lower()

            # Security support detection
            if "supported" in lower:
                data["security_supported"] = not ("not" in lower)

            # enabled / locked / frozen flags
            if lower.startswith("enabled"):
                data["security_enabled"] = not ("not" in lower)
            if lower.startswith("locked"):
                data["security_locked"] = not ("not" in lower)
            if lower.startswith("frozen"):
                data["security_frozen"] = not ("not" in lower)

            # Enhanced erase support
            if "enhanced erase" in lower:
                data["enhanced_erase_supported"] = not ("not" in lower)

            # Raw erase timing info
            if "erase time" in lower or "security erase unit" in lower:
                data.setdefault("erase_time_raw", stripped)

    return data
