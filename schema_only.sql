CREATE TABLE users (
            user_id     TEXT PRIMARY KEY,
            username    TEXT UNIQUE,
            password_hash TEXT,
            role        TEXT,            -- admin | coordinator | volunteer
            first_name  TEXT,
            last_name   TEXT,
            email       TEXT,
            phone       TEXT,
            country     TEXT,
            region      TEXT,
            skills      TEXT,            -- comma separated
            photo_path  TEXT,
            created_at  INTEGER
        , avatar TEXT, bio TEXT, deleted INTEGER, password TEXT DEFAULT '');
CREATE TABLE cases (
            case_id         TEXT PRIMARY KEY,
            victim_name     TEXT,
            contact_email   TEXT,
            phone           TEXT,
            region          TEXT,
            country         TEXT,
            latitude        REAL,
            longitude       REAL,
            description     TEXT,
            status          TEXT,  -- new|acknowledged|en_route|arrived|closed|cancelled
            assigned_to     TEXT,  -- user_id (volunteer)
            shelter_id      TEXT,
            attachment_path TEXT,
            created_at      INTEGER,
            acknowledged_at INTEGER,
            arrived_at      INTEGER,
            closed_at       INTEGER,
            timeline        TEXT    -- JSON list of {ts, actor, action}
        );
CREATE TABLE shelters (
            shelter_id  TEXT PRIMARY KEY,
            name        TEXT,
            region      TEXT,
            country     TEXT,
            latitude    REAL,
            longitude   REAL,
            capacity    INTEGER,
            available   INTEGER,
            contact     TEXT,
            notes       TEXT,
            created_at  INTEGER
        );
CREATE TABLE blood_inventory (
            id          TEXT PRIMARY KEY,
            region      TEXT,
            country     TEXT,
            blood_type  TEXT,
            units       INTEGER,
            expires_on  TEXT
        );
CREATE TABLE resources (
            id          TEXT PRIMARY KEY,
            region      TEXT,
            country     TEXT,
            Volunteers  INTEGER,
            Trucks      INTEGER,
            Boats       INTEGER,
            MedKits     INTEGER,
            FoodKits    INTEGER,
            WaterKits   INTEGER
        );
CREATE TABLE allocation_runs (
            batch_id TEXT PRIMARY KEY, created_at INTEGER
        );
CREATE TABLE allocation_outputs (
            batch_id TEXT, table_name TEXT, payload_csv TEXT
        );
CREATE TABLE notifications (
            id          TEXT PRIMARY KEY,
            user_id     TEXT,
            message     TEXT,
            created_at  INTEGER,
            is_read     INTEGER
        );
CREATE TABLE blood_snapshots (
            id TEXT PRIMARY KEY, ts INTEGER, region TEXT, country TEXT, blood_type TEXT, units INTEGER
        );
CREATE TABLE eval_events (
            id TEXT PRIMARY KEY, user_id TEXT, event_name TEXT, duration_ms REAL, created_at INTEGER
        );
CREATE TABLE eval_sus (
            id TEXT PRIMARY KEY, user_id TEXT,
            a1 INTEGER, a2 INTEGER, a3 INTEGER, a4 INTEGER, a5 INTEGER,
            a6 INTEGER, a7 INTEGER, a8 INTEGER, a9 INTEGER, a10 INTEGER,
            created_at INTEGER
        );
CREATE TABLE evaluation_sus (
            id           TEXT PRIMARY KEY,
            respondent   TEXT,
            answers_json TEXT,
            sus_score    REAL,
            notes        TEXT,
            created_at   INTEGER
        );
CREATE TABLE latency_metrics (
            id          TEXT PRIMARY KEY,
            action      TEXT,
            ms          REAL,
            meta        TEXT,
            user_id     TEXT,
            created_at  INTEGER
        );
CREATE TABLE geocode_cache (
            place TEXT PRIMARY KEY,
            lat   REAL,
            lon   REAL,
            created_at INTEGER
        );
CREATE TABLE audit_log (
            id           TEXT PRIMARY KEY,
            actor_id     TEXT,
            "table"      TEXT,
            payload_json TEXT,
            created_at   INTEGER
        );
CREATE TABLE emergency_form (
            form_id         TEXT PRIMARY KEY,
            user_id         TEXT,           -- FK users.user_id (nullable for guests)
            victim_name     TEXT,
            contact_email   TEXT,
            phone           TEXT,
            region          TEXT,
            country         TEXT,
            latitude        REAL,
            longitude       REAL,
            description     TEXT,
            attachment_path TEXT,
            case_id         TEXT,           -- FK cases.case_id (nullable until created)
            submitted_at    INTEGER,
            status          TEXT            -- 'submitted'|'converted'|'discarded'
        );
CREATE TABLE contact_messages (
            contact_id    TEXT PRIMARY KEY,
            name          TEXT,
            email         TEXT,
            message       TEXT,
            submitted_at  INTEGER,
            status        TEXT,             -- 'new'|'in_progress'|'closed'
            responded_by  TEXT,             -- FK users.user_id (nullable)
            responded_at  INTEGER
        );
