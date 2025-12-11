CREATE TABLE IF NOT EXISTS wipe_logs (
    id                  BIGSERIAL PRIMARY KEY,

    -- High-level wipe info
    device              TEXT NOT NULL,           -- "/dev/nvme0n1"
    method              TEXT NOT NULL,           -- "ata-secure-erase"
    dry_run             BOOLEAN NOT NULL,
    operator            TEXT,
    session_id          UUID,

    started_at          TIMESTAMPTZ NOT NULL,
    ended_at            TIMESTAMPTZ NOT NULL,
    logged_at           TIMESTAMPTZ NOT NULL,

    result              TEXT,                    -- "PASS" / "FAIL"
    method_success      BOOLEAN,                 -- method_result.success

    -- Sampling / verification data
    pre_sample_bytes    INTEGER DEFAULT 0,
    pre_sample_hash     TEXT,
    post_sample_hash    TEXT,

    -- Device info (flattened)
    device_name         TEXT,
    device_path         TEXT,
    device_size         TEXT,                    -- ex: "232.9G"
    device_model        TEXT,
    device_serial       TEXT,
    device_transport    TEXT,                    -- nvme/sata/etc.

    -- Raw tool output
    hdparm_before_raw   TEXT,
    hdparm_after_raw    TEXT,

    -- JSON blobs
    method_result       JSONB,
    raw_log             JSONB
);

CREATE INDEX IF NOT EXISTS idx_wipe_logs_device_serial
    ON wipe_logs(device_serial);

CREATE INDEX IF NOT EXISTS idx_wipe_logs_logged_at
    ON wipe_logs(logged_at DESC);

CREATE INDEX IF NOT EXISTS idx_wipe_logs_result
    ON wipe_logs(result);
