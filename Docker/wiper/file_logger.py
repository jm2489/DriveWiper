import os
import json
import datetime

class FileLogger:
    def __init__(self):
        base_dir = os.getenv("LOG_FALLBACK_DIR", "/wiper/logs")
        os.makedirs(base_dir, exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.log_path = os.path.join(base_dir, f"wipe_session_{timestamp}.jsonl")

    def log(self, event: dict):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
