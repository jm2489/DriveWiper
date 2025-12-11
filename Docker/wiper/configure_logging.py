import os
from db_logger import DatabaseLogger
from file_logger import FileLogger

def main():
    db_enabled = os.getenv("DB_ENABLED", "false").lower() == "true"

    print("=== Drive Wiper Logging Configuration ===")
    if db_enabled:
        db = DatabaseLogger()
        try:
            db._connect()  # not ideal to call private method, but ok for setup script
            print("[OK] Database logging enabled and connection successful.")
            print(f"    Host: {os.getenv('DB_HOST')}")
            print(f"    DB:   {os.getenv('DB_NAME')}")
        except Exception as e:
            print("[FAIL] Could not connect to database:")
            print(f"       {e}")
            print("       Logging will fall back to local file storage.")
    else:
        print("[INFO] Database logging is DISABLED (DB_ENABLED=false).")

    fl = FileLogger()
    print(f"[INFO] Local fallback log path will be something like: {fl.log_path}")

if __name__ == "__main__":
    main()
