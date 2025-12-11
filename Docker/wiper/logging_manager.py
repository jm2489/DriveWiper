import traceback
from db_logger import DatabaseLogger
from file_logger import FileLogger

# Create global logger instances
_db_logger = DatabaseLogger()
_file_logger = FileLogger()

# State flag: start optimistic (DB first), switch permanently on error
_use_db = True


def log_wipe_event(event: dict):
    """
    Logs a wipe event.

    1. Try writing to Postgres if DB logging is enabled.
    2. On ANY failure, permanently switch to local JSONL file logging.
    3. Always guarantee the event is saved somewhere.
    """
    global _use_db

    # Try DB logging first (if still allowed)
    if _use_db and _db_logger.enabled:
        try:
            _db_logger.log(event)
            return  # DB logging succeeded
        except Exception as e:
            # DB failure → switch permanently to file logging
            _use_db = False
            print("[Warning] Database logging failed. Switching to fallback file logging.")
            print(f"Reason: {e}")
            traceback.print_exc()

    # Always log to file as fallback
    try:
        _file_logger.log(event)
    except Exception as e:
        # File logging should basically never fail, but if it does:
        print("[ERROR] FATAL: Could not log event to file either!")
        print(f"Event that failed to log: {event}")
        traceback.print_exc()
