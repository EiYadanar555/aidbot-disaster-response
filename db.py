import os, sqlite3, time, hashlib, secrets, json, re
from typing import Optional, Dict, Any, List
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "aidbot.db")

# ─────────────────────────────────────────────
# Security: PBKDF2 password hashing (+ legacy support)
# ─────────────────────────────────────────────
_ITER = 200_000

def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), _ITER)
    return f"pbkdf2_sha256${_ITER}${salt}${dk.hex()}"

def verify_password(pw: str, stored: str) -> bool:
    try:
        if isinstance(stored, str) and stored.startswith("pbkdf2_sha256$"):
            _, iters, salt, hexed = stored.split("$", 3)
            dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(iters))
            return dk.hex() == hexed
        # fallback (legacy plaintext)
        return pw == stored
    except Exception:
        return False

def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _now() -> int:
    return int(time.time())

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _password_is_hashed(p: str) -> bool:
    return isinstance(p, str) and p.startswith("pbkdf2_sha256$")

def _rehash_legacy_passwords(conn: sqlite3.Connection) -> None:
    """For any legacy plaintext user passwords, convert to PBKDF2 silently."""
    rows = conn.execute("SELECT user_id, password_hash FROM users").fetchall()
    changed = False
    for r in rows:
        ph = r["password_hash"] or ""
        if not _password_is_hashed(ph):
            conn.execute("UPDATE users SET password_hash=? WHERE user_id=?", (hash_password(ph), r["user_id"]))
            changed = True
    if changed:
        conn.commit()

def _next_numeric_id(prefix: str, table: str, column: str, width: int = 4) -> str:
    """
    Scan existing IDs in `table`.`column` and return the next like PREFIX0001.
    Works with mixed old IDs; only considers ^PREFIX-?(\\d+)$.
    """
    pat = re.compile(rf"^{re.escape(prefix)}-?(\d+)$")
    with _connect() as conn:
        vals = [str(r[column] or "") for r in conn.execute(f"SELECT {column} FROM {table}").fetchall()]
    max_n = 0
    for v in vals:
        m = pat.match(v)
        if m:
            try:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
            except Exception:
                pass
    return f"{prefix}{str(max_n + 1).zfill(width)}"

# Expose for app.py (kept as-is)
__all__ = ["_next_numeric_id"]

# ─────────────────────────────────────────────
# Init + schema + seeding
# ─────────────────────────────────────────────
def ensure_admin(username: str = "admin", password: str = "admin123") -> None:
    """Create admin if missing, or normalize its password to `password`."""
    with _connect() as conn:
        row = conn.execute("SELECT user_id, username, password_hash FROM users WHERE username=? LIMIT 1", (username,)).fetchone()
        if not row:
            admin_id = _next_numeric_id("User", "users", "user_id", width=3)
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash, role, created_at, deleted) "
                "VALUES (?,?,?,?,?,0)",
                (admin_id, username, hash_password(password), "admin", _now())
            )
            conn.commit()
        else:
            if not verify_password(password, row["password_hash"] or ""):
                conn.execute("UPDATE users SET password_hash=?, role='admin', deleted=0 WHERE username=?",
                             (hash_password(password), username))
                conn.commit()

def init_db():
    with _connect() as conn:
        # Users
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       TEXT PRIMARY KEY,
            username      TEXT UNIQUE,
            password_hash TEXT,
            role          TEXT,            -- admin | coordinator | volunteer | victim
            first_name    TEXT,
            last_name     TEXT,
            email         TEXT,
            phone         TEXT,
            country       TEXT,
            region        TEXT,
            skills        TEXT,
            photo_path    TEXT,
            avatar        TEXT,
            bio           TEXT,
            deleted       INTEGER DEFAULT 0,
            created_at    INTEGER
        )""")

        # Cases
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id         TEXT PRIMARY KEY,
            victim_name     TEXT,
            contact_email   TEXT,
            phone           TEXT,
            region          TEXT,
            country         TEXT,
            latitude        REAL,
            longitude       REAL,
            description     TEXT,
            status          TEXT,      -- new|acknowledged|en_route|arrived|closed|cancelled
            assigned_to     TEXT,      -- user_id (volunteer)
            shelter_id      TEXT,
            attachment_path TEXT,
            created_at      INTEGER,
            acknowledged_at INTEGER,
            arrived_at      INTEGER,
            closed_at       INTEGER,
            timeline        TEXT        -- JSON list of {ts, actor, action}
        )""")

        # Shelters
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shelters (
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
        )""")

        # Blood Inventory
        conn.execute("""
        CREATE TABLE IF NOT EXISTS blood_inventory (
            id          TEXT PRIMARY KEY,
            region      TEXT,
            country     TEXT,
            blood_type  TEXT,
            units       INTEGER,
            expires_on  TEXT
        )""")

        # Resources
        conn.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id          TEXT PRIMARY KEY,
            region      TEXT,
            country     TEXT,
            Volunteers  INTEGER,
            Trucks      INTEGER,
            Boats       INTEGER,
            MedKits     INTEGER,
            FoodKits    INTEGER,
            WaterKits   INTEGER
        )""")

        # Allocation (history)
        conn.execute("""CREATE TABLE IF NOT EXISTS allocation_runs (
            batch_id TEXT PRIMARY KEY, created_at INTEGER
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS allocation_outputs (
            batch_id TEXT, table_name TEXT, payload_csv TEXT
        )""")

        # Notifications
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          TEXT PRIMARY KEY,
            user_id     TEXT,
            message     TEXT,
            created_at  INTEGER,
            is_read     INTEGER
        )""")

        # Geocode cache
        conn.execute("""
        CREATE TABLE IF NOT EXISTS geocode_cache (
            place TEXT PRIMARY KEY,
            lat   REAL,
            lon   REAL,
            created_at INTEGER
        )""")

        # Audit log
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id           TEXT PRIMARY KEY,
            actor_id     TEXT,
            "table"      TEXT,
            payload_json TEXT,
            created_at   INTEGER
        )""")

        # ───────────── NEW: Emergency Form storage ─────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS emergency_form (
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
        )""")

        # ───────────── NEW: Contact messages storage ─────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            contact_id    TEXT PRIMARY KEY,
            name          TEXT,
            email         TEXT,
            message       TEXT,
            submitted_at  INTEGER,
            status        TEXT,             -- 'new'|'in_progress'|'closed'
            responded_by  TEXT,             -- FK users.user_id (nullable)
            responded_at  INTEGER
        )""")

        conn.commit()
        _rehash_legacy_passwords(conn)

    ensure_admin("admin", "admin123")

# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────
def get_user_by_credentials(username: str, pw: str) -> Optional[Dict[str, Any]]:
    username = (username or "").strip()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=? AND deleted=0", (username,)).fetchone()
        if row and verify_password(pw, row["password_hash"] or ""):
            return dict(row)
        return None

def create_user(username: str, pw: str, role: str, **extra) -> bool:
    username = (username or "").strip()
    if not username or not pw:
        return False
    try:
        with _connect() as conn:
            user_id = extra.get("user_id") or _next_numeric_id("User", "users", "user_id", width=3)
            conn.execute("""
            INSERT INTO users (user_id, username, password_hash, role, first_name, last_name,
                               email, phone, country, region, skills, photo_path, avatar, bio, deleted, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)
            """, (
                user_id, username, hash_password(pw), role,
                extra.get("first_name",""), extra.get("last_name",""),
                extra.get("email",""), extra.get("phone",""),
                extra.get("country",""), extra.get("region",""),
                extra.get("skills",""), extra.get("photo_path",""),
                extra.get("avatar",""), extra.get("bio",""), _now()
            ))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def update_user(user_id: str, fields: Dict[str, Any]):
    if not fields: return
    keys = ", ".join([f"{k}=?" for k in fields.keys()])
    with _connect() as conn:
        conn.execute(f"UPDATE users SET {keys} WHERE user_id=?", (*fields.values(), user_id))
        conn.commit()

def delete_user(user_id: str):
    with _connect() as conn:
        conn.execute("UPDATE users SET deleted=1 WHERE user_id=?", (user_id,))
        conn.commit()

def list_users(role: Optional[str]=None) -> List[Dict[str,Any]]:
    with _connect() as conn:
        if role:
            rows = conn.execute("SELECT * FROM users WHERE deleted=0 AND role=? ORDER BY created_at DESC", (role,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM users WHERE deleted=0 ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def list_volunteers() -> List[Dict[str,Any]]:
    return list_users("volunteer")

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("""
            SELECT user_id, username, role, email, phone, country, region, skills, avatar, bio,
                   first_name, last_name, photo_path
              FROM users
             WHERE user_id = ? AND deleted=0
        """, (user_id,)).fetchone()
        return dict(row) if row else None

def update_user_profile(user_id: str,
                        phone: Optional[str]=None,
                        region: Optional[str]=None,
                        avatar: Optional[str]=None,
                        bio: Optional[str]=None,
                        photo_path: Optional[str]=None,
                        country: Optional[str]=None,
                        skills: Optional[str]=None) -> None:
    """Update user profile fields"""
    with _connect() as conn:
        conn.execute("""
            UPDATE users
               SET phone      = COALESCE(?, phone),
                   region     = COALESCE(?, region),
                   avatar     = COALESCE(?, avatar),
                   bio        = COALESCE(?, bio),
                   photo_path = COALESCE(?, photo_path),
                   country    = COALESCE(?, country),
                   skills     = COALESCE(?, skills)
             WHERE user_id = ? AND deleted=0
        """, (phone, region, avatar, bio, photo_path, country, skills, user_id))
        conn.commit()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username (for forgot password feature)"""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND deleted=0", 
            (username.strip(),)
        ).fetchone()
        return dict(row) if row else None

# ─────────────────────────────────────────────
# Notifications (incl. helper to notify admins+coordinators)
# ─────────────────────────────────────────────
def add_notification(user_id: str, message: str):
    with _connect() as conn:
        conn.execute("INSERT INTO notifications (id, user_id, message, created_at, is_read) VALUES (?,?,?,?,0)",
                     (secrets.token_hex(8), user_id, message, _now()))
        conn.commit()

def notify_admins_coordinators(message: str):
    with _connect() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE deleted=0 AND role IN ('admin','coordinator')").fetchall()
        ids = [r["user_id"] for r in rows]
    for uid in ids:
        add_notification(uid, message)

def list_notifications(user_id: str, unread_only: bool=False) -> List[Dict[str,Any]]:
    with _connect() as conn:
        if unread_only:
            rows = conn.execute("SELECT * FROM notifications WHERE user_id=? AND is_read=0 ORDER BY created_at DESC", (user_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(r) for r in rows]

def mark_all_read(user_id: str):
    with _connect() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
        conn.commit()

# ─────────────────────────────────────────────
# Cases
# ─────────────────────────────────────────────
def _append_timeline(tl_json: Optional[str], actor: Optional[str], action: str) -> str:
    try:
        cur = json.loads(tl_json) if tl_json else []
    except Exception:
        cur = []
    cur.append({"ts": _now(), "actor": actor, "action": action})
    return json.dumps(cur)

def create_case(victim_name: str, email: str, phone: str, region: str, country: str,
                lat: Optional[float], lon: Optional[float], description: str,
                attachment_path: Optional[str], shelter_id: Optional[str]=None) -> str:
    cid = "C-" + secrets.token_hex(6)
    with _connect() as conn:
        conn.execute("""
        INSERT INTO cases (case_id, victim_name, contact_email, phone, region, country,
                           latitude, longitude, description, status, assigned_to, shelter_id,
                           attachment_path, created_at, acknowledged_at, arrived_at, closed_at, timeline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', NULL, ?, ?, ?, NULL, NULL, NULL, ?)
        """, (
            cid, victim_name, email, phone, region, country, lat, lon, description,
            shelter_id, attachment_path, _now(),
            _append_timeline(None, None, "created")
        ))
        conn.commit()
    return cid

def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        return dict(row) if row else None

def list_cases(status: Optional[str]=None, assigned_to: Optional[str]=None) -> List[Dict[str,Any]]:
    with _connect() as conn:
        q = "SELECT * FROM cases WHERE 1=1"
        args = []
        if status:
            q += " AND status=?"; args.append(status)
        if assigned_to:
            q += " AND assigned_to=?"; args.append(assigned_to)
        q += " ORDER BY created_at DESC"
        rows = conn.execute(q, tuple(args)).fetchall()
    return [dict(r) for r in rows]

def assign_case(case_id: str, user_id: Optional[str], shelter_id: Optional[str]=None):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if not row: return
        tl = _append_timeline(row["timeline"], None, f"assigned_to={user_id or ''}")
        conn.execute("UPDATE cases SET assigned_to=?, timeline=? WHERE case_id=?", (user_id, tl, case_id))
        if shelter_id:
            s = conn.execute("SELECT * FROM shelters WHERE shelter_id=?", (shelter_id,)).fetchone()
            if s:
                new_avail = max(0, int(s["available"] or 0) - 1)
                conn.execute("UPDATE shelters SET available=? WHERE shelter_id=?", (new_avail, shelter_id))
                tl2 = _append_timeline(tl, None, f"shelter_assigned={shelter_id}")
                conn.execute("UPDATE cases SET shelter_id=?, timeline=? WHERE case_id=?", (shelter_id, tl2, case_id))
        conn.commit()

def update_case_status(case_id: str, status: str):
    stamp_col = {
        "acknowledged": "acknowledged_at",
        "en_route": None,
        "arrived": "arrived_at",
        "closed": "closed_at",
        "cancelled": None
    }.get(status, None)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if not row: return
        tl = _append_timeline(row["timeline"], None, f"status={status}")
        if stamp_col:
            conn.execute(f"UPDATE cases SET status=?, {stamp_col}=?, timeline=? WHERE case_id=?",
                         (status, _now(), tl, case_id))
        else:
            conn.execute("UPDATE cases SET status=?, timeline=? WHERE case_id=?", (status, tl, case_id))
        conn.commit()

# ─────────────────────────────────────────────
# Shelters
# ─────────────────────────────────────────────
def create_shelter(name: str, region: str, country: str,
                   lat: Optional[float], lon: Optional[float],
                   capacity: int, available: int, contact: str, notes: str,
                   shelter_id: Optional[str] = None) -> str:
    sid = shelter_id or _next_numeric_id("S", "shelters", "shelter_id", width=4)
    with _connect() as conn:
        conn.execute("""
        INSERT INTO shelters (shelter_id, name, region, country, latitude, longitude,
                              capacity, available, contact, notes, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (sid, name, region, country, lat, lon, capacity, available, contact, notes, _now()))
        conn.commit()
    return sid

def update_shelter(shelter_id: str, fields: Dict[str, Any]):
    if not fields: return
    keys = ", ".join([f"{k}=?" for k in fields.keys()])
    with _connect() as conn:
        conn.execute(f"UPDATE shelters SET {keys} WHERE shelter_id=?", (*fields.values(), shelter_id))
        conn.commit()

def delete_shelter(shelter_id: str):
    with _connect() as conn:
        conn.execute("DELETE FROM shelters WHERE shelter_id=?", (shelter_id,))
        conn.commit()

def list_shelters(region: Optional[str]=None, country: Optional[str]=None) -> List[Dict[str,Any]]:
    with _connect() as conn:
        q, args = "SELECT * FROM shelters WHERE 1=1", []
        if region:
            q += " AND region=?"; args.append(region)
        if country:
            q += " AND country=?"; args.append(country)
        q += " ORDER BY created_at DESC"
        rows = conn.execute(q, tuple(args)).fetchall()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────
# Audit helpers
# ─────────────────────────────────────────────
def insert_audit(actor_id: Optional[str], table_name: str, payload: Dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute('INSERT INTO audit_log (id, actor_id, "table", payload_json, created_at) VALUES (?,?,?,?,?)',
                     (secrets.token_hex(8), actor_id or "", table_name, json.dumps(payload, ensure_ascii=False), _now()))
        conn.commit()

def list_audit(limit: int = 10) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute('SELECT id, actor_id, "table" as table_name, payload_json, created_at FROM audit_log ORDER BY created_at DESC LIMIT ?',
                            (int(limit),)).fetchall()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────
# Blood Inventory (both DataFrame and row-level CRUD)
# ─────────────────────────────────────────────
def _blood_threshold_message(units: int, expires_on: str) -> Optional[str]:
    try:
        if units <= 0:
            return "Blood inventory alert: units is 0."
        if (expires_on or "").strip():
            d = time.strptime(expires_on, "%Y-%m-%d")
            days = int((time.mktime(d) - time.time()) // 86400)
            if days < 0:
                return f"Blood inventory alert: record expired {abs(days)} day(s) ago."
            if days <= 7:
                return f"Blood inventory alert: record expiring in {days} day(s)."
    except Exception:
        # ignore parse errors
        pass
    return None

def read_blood_df() -> pd.DataFrame:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT id,
                   region  as Region,
                   country as Country,
                   blood_type as BloodType,
                   units    as Units,
                   expires_on as ExpiresOn
              FROM blood_inventory
        """).fetchall()
    if not rows:
        return pd.DataFrame(columns=["Region","Country","BloodType","Units","ExpiresOn"])
    return pd.DataFrame([dict(r) for r in rows])

def write_blood_df(df: pd.DataFrame, actor_id: Optional[str] = None) -> None:
    out = df.copy()
    for c in ("Region","Country","BloodType","Units","ExpiresOn"):
        if c not in out.columns: out[c] = "" if c!="Units" else 0
    out["Units"] = pd.to_numeric(out["Units"], errors="coerce").fillna(0).astype(int)
    with _connect() as conn:
        conn.execute("DELETE FROM blood_inventory")
        for _, r in out.iterrows():
            bid = str(r.get("id") or "") or _next_numeric_id("B", "blood_inventory", "id", width=4)
            conn.execute(
                "INSERT INTO blood_inventory (id, region, country, blood_type, units, expires_on) VALUES (?,?,?,?,?,?)",
                (bid, str(r["Region"]), str(r["Country"]), str(r["BloodType"]), int(r["Units"]), str(r["ExpiresOn"] or ""))
            )
        conn.commit()
    # Threshold checks + audit
    alerts = []
    for _, r in out.iterrows():
        msg = _blood_threshold_message(int(r.get("Units", 0)), str(r.get("ExpiresOn","") or ""))
        if msg: alerts.append(msg)
    for m in alerts:
        notify_admins_coordinators(m)
    insert_audit(actor_id, "blood_inventory", {"action":"bulk_write", "rows": len(out)})

# Row-level APIs used by the UI
def list_blood() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, region, country, blood_type, units, expires_on FROM blood_inventory ORDER BY country, region, blood_type").fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "Region": r["region"],
            "Country": r["country"],
            "BloodType": r["blood_type"],
            "Units": int(r["units"] or 0),
            "ExpiresOn": r["expires_on"] or ""
        })
    return out

def create_blood(region: str, country: str, blood_type: str, units: int, expires_on: str, id: Optional[str]=None, actor_id: Optional[str]=None) -> str:
    bid = id or _next_numeric_id("B", "blood_inventory", "id", width=4)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO blood_inventory (id, region, country, blood_type, units, expires_on) VALUES (?,?,?,?,?,?)",
            (bid, region, country, blood_type, int(units or 0), expires_on or "")
        )
        conn.commit()
    # Threshold + audit
    msg = _blood_threshold_message(int(units or 0), expires_on or "")
    if msg: notify_admins_coordinators(msg)
    insert_audit(actor_id, "blood_inventory", {"action":"create", "row":{
        "id": bid, "region": region, "country": country, "blood_type": blood_type, "units": int(units or 0), "expires_on": expires_on or ""
    }})
    return bid

def update_blood(id: str, fields: Dict[str, Any], actor_id: Optional[str]=None) -> None:
    if not fields: return
    mapping = {
        "Region": "region",
        "Country": "country",
        "BloodType": "blood_type",
        "Units": "units",
        "ExpiresOn": "expires_on",
        "region": "region",
        "country": "country",
        "blood_type": "blood_type",
        "units": "units",
        "expires_on": "expires_on",
    }
    fields2 = {mapping.get(k, k): v for k, v in fields.items()}
    keys = ", ".join([f"{k}=?" for k in fields2.keys()])
    with _connect() as conn:
        conn.execute(f"UPDATE blood_inventory SET {keys} WHERE id=?", (*fields2.values(), id))
        conn.commit()
    # Threshold + audit
    u = int(fields2.get("units", 0) if fields2.get("units", None) is not None else 0)
    ex = str(fields2.get("expires_on","") or "")
    msg = _blood_threshold_message(u, ex)
    if msg: notify_admins_coordinators(msg)
    insert_audit(actor_id, "blood_inventory", {"action":"update", "id": id, "fields": fields2})

def delete_blood(id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM blood_inventory WHERE id=?", (id,))
        conn.commit()
    insert_audit(None, "blood_inventory", {"action":"delete", "id": id})

# ─────────────────────────────────────────────
# Resources + Allocation results
# ─────────────────────────────────────────────
def read_resources_df() -> pd.DataFrame:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM resources").fetchall()
    if not rows:
        return pd.DataFrame(columns=["Region","Country","Volunteers","Trucks","Boats","MedKits","FoodKits","WaterKits"])
    df = pd.DataFrame([dict(r) for r in rows])
    return df[["region","country","Volunteers","Trucks","Boats","MedKits","FoodKits","WaterKits"]].rename(columns={"region":"Region","country":"Country"})

def write_resources_df(df: pd.DataFrame, actor_id: Optional[str] = None):
    with _connect() as conn:
        conn.execute("DELETE FROM resources")
        for _, r in df.fillna(0).iterrows():
            conn.execute("""
            INSERT INTO resources (id, region, country, Volunteers, Trucks, Boats, MedKits, FoodKits, WaterKits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                secrets.token_hex(6), str(r.get("Region","")), str(r.get("Country","")),
                int(r.get("Volunteers",0)), int(r.get("Trucks",0)), int(r.get("Boats",0)),
                int(r.get("MedKits",0)), int(r.get("FoodKits",0)), int(r.get("WaterKits",0))
            ))
        conn.commit()
    # Audit only (no thresholds by default)
    insert_audit(actor_id, "resources", {"action":"bulk_write", "rows": int(len(df))})

def write_run_outputs(alloc_df: pd.DataFrame, remain_df: pd.DataFrame) -> str:
    batch_id = "B-" + secrets.token_hex(6)
    with _connect() as conn:
        conn.execute("INSERT INTO allocation_runs (batch_id, created_at) VALUES (?,?)", (batch_id, _now()))
        conn.execute("INSERT INTO allocation_outputs (batch_id, table_name, payload_csv) VALUES (?,?,?)", (batch_id, "allocations", alloc_df.to_csv(index=False)))
        conn.execute("INSERT INTO allocation_outputs (batch_id, table_name, payload_csv) VALUES (?,?,?)", (batch_id, "remaining", remain_df.to_csv(index=False)))
        conn.commit()
    return batch_id

# NEW: pre-position plan writer + lister
def write_preposition_plan(df_plan: pd.DataFrame) -> str:
    """Store a pre-position (Ops Plan) table as CSV under table_name='preposition_plan'."""
    batch_id = "B-" + secrets.token_hex(6)
    with _connect() as conn:
        conn.execute("INSERT INTO allocation_runs (batch_id, created_at) VALUES (?,?)", (batch_id, _now()))
        conn.execute("INSERT INTO allocation_outputs (batch_id, table_name, payload_csv) VALUES (?,?,?)",
                     (batch_id, "preposition_plan", df_plan.to_csv(index=False)))
        conn.commit()
    insert_audit(None, "preposition_plan", {"action":"create", "batch_id": batch_id, "rows": int(len(df_plan))})
    return batch_id

def list_preposition_plans(limit: int = 10) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT ar.batch_id, ar.created_at, ao.payload_csv
              FROM allocation_runs ar
              JOIN allocation_outputs ao ON ar.batch_id = ao.batch_id
             WHERE ao.table_name='preposition_plan'
             ORDER BY ar.created_at DESC
             LIMIT ?
        """, (int(limit),)).fetchall()
    return [dict(r) for r in rows]

# ─────────────────────────────────────────────
# NEW: Emergency Form helpers
# ─────────────────────────────────────────────
def create_emergency_form(
    user_id: Optional[str],
    victim_name: str,
    contact_email: str,
    phone: str,
    region: str,
    country: str,
    latitude: Optional[float],
    longitude: Optional[float],
    description: str,
    attachment_path: Optional[str]
) -> str:
    """Store the submitted form before it becomes a case."""
    fid = "F-" + secrets.token_hex(6)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO emergency_form
            (form_id,user_id,victim_name,contact_email,phone,region,country,latitude,longitude,
             description,attachment_path,case_id,submitted_at,status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            fid, user_id, victim_name, contact_email, phone, region, country,
            latitude, longitude, description, attachment_path, None, _now(), "submitted"
        ))
        conn.commit()
    insert_audit(user_id, "emergency_form", {"action":"create", "form_id": fid})
    return fid

def link_form_to_case(form_id: str, case_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE emergency_form SET case_id=?, status='converted' WHERE form_id=?", (case_id, form_id))
        conn.commit()
    insert_audit(None, "emergency_form", {"action":"link_to_case", "form_id": form_id, "case_id": case_id})

def list_emergency_forms(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    with _connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM emergency_form WHERE status=? ORDER BY submitted_at DESC LIMIT ?",
                (status, int(limit))
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM emergency_form ORDER BY submitted_at DESC LIMIT ?",
                (int(limit),)
            ).fetchall()
    return [dict(r) for r in rows]

def update_emergency_form_status(form_id: str, status: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE emergency_form SET status=? WHERE form_id=?", (status, form_id))
        conn.commit()
    insert_audit(None, "emergency_form", {"action":"update_status", "form_id": form_id, "status": status})

# ─────────────────────────────────────────────
# NEW: Contact messages helpers
# ─────────────────────────────────────────────
def create_contact_message(name: str, email: str, message: str) -> str:
    cid = "M-" + secrets.token_hex(6)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO contact_messages
            (contact_id,name,email,message,submitted_at,status,responded_by,responded_at)
            VALUES (?,?,?,?,?,'new',NULL,NULL)
        """, (cid, name, email, message, _now()))
        conn.commit()
    insert_audit(None, "contact_messages", {"action":"create", "contact_id": cid})
    return cid

def list_contact_messages(status: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    with _connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM contact_messages WHERE status=? ORDER BY submitted_at DESC LIMIT ?",
                (status, int(limit))
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contact_messages ORDER BY submitted_at DESC LIMIT ?",
                (int(limit),)
            ).fetchall()
    return [dict(r) for r in rows]

def respond_contact_message(contact_id: str, responder_user_id: Optional[str], new_status: str = "closed") -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE contact_messages
               SET responded_by=?, responded_at=?, status=?
             WHERE contact_id=?
        """, (responder_user_id, _now(), new_status, contact_id))
        conn.commit()
    insert_audit(responder_user_id, "contact_messages", {"action":"respond", "contact_id": contact_id, "status": new_status})

