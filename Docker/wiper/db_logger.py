import os
import psycopg2
from psycopg2.extras import Json


class DatabaseLogger:
    def __init__(self):
        self.enabled = os.getenv("DB_ENABLED", "false").lower() == "true"
        self._conn = None

    def _connect(self):
        if not self.enabled:
            return

        if self._conn is not None:
            return

        self._conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "drivewiper"),
            user=os.getenv("DB_USER", "wiper"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        self._conn.autocommit = True

    def log(self, event: dict):
        if not self.enabled:
            raise RuntimeError("DB logging disabled")

        self._connect()

        device_info = event.get("device_info") or {}
        method_result = event.get("method_result") or {}
        hdparm_before = event.get("hdparm_before") or {}
        hdparm_after = event.get("hdparm_after") or {}

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO wipe_logs (
                    device,
                    method,
                    dry_run,
                    operator,
                    session_id,
                    started_at,
                    ended_at,
                    logged_at,
                    result,
                    method_success,
                    pre_sample_bytes,
                    pre_sample_hash,
                    post_sample_hash,
                    device_name,
                    device_path,
                    device_size,
                    device_model,
                    device_serial,
                    device_transport,
                    hdparm_before_raw,
                    hdparm_after_raw,
                    method_result,
                    raw_log
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
                """,
                (
                    event.get("device"),
                    event.get("method"),
                    bool(event.get("dry_run", False)),
                    event.get("operator"),
                    event.get("session_id"),
                    event.get("started_at"),
                    event.get("ended_at"),
                    event.get("logged_at"),
                    event.get("result"),
                    method_result.get("success"),
                    event.get("pre_sample_bytes", 0),
                    event.get("pre_sample_hash"),
                    event.get("post_sample_hash"),
                    device_info.get("name"),
                    device_info.get("path"),
                    device_info.get("size"),
                    device_info.get("model"),
                    device_info.get("serial"),
                    device_info.get("transport"),
                    hdparm_before.get("raw"),
                    hdparm_after.get("raw"),
                    Json(method_result),
                    Json(event),
                ),
            )

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None
