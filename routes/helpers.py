"""Shared helper functions for dashboard route modules."""
import json, os, sqlite3, threading
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATA = os.path.join(BASE, "app-data")
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

_RESULT_CACHE = {}
_console_log_lock = threading.Lock()

def db_get():
    conn = sqlite3.connect(os.path.join(BASE, "framework.db"))
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db():
    """Create database tables if they don't exist. Safe to call on every startup."""
    conn = sqlite3.connect(os.path.join(BASE, "framework.db"))
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        factor_params TEXT,
        run_type TEXT NOT NULL DEFAULT 'live',
        total_matches INTEGER DEFAULT 0,
        hit_count INTEGER DEFAULT 0,
        avg_fit_score REAL DEFAULT 0,
        prediction_date TEXT
    );
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL REFERENCES runs(id),
        match_id TEXT NOT NULL,
        home TEXT NOT NULL, away TEXT NOT NULL,
        event TEXT, match_time TEXT, match_type TEXT, league TEXT,
        asian_handicap REAL, jc_handicap INTEGER, handicap_change REAL,
        lambda_h_final REAL, lambda_a_final REAL, lambda_diff REAL,
        physical_home_win REAL, physical_draw REAL, physical_away_win REAL,
        market_home_win REAL, market_draw REAL, market_away_win REAL,
        ddi_home_win REAL, ddi_draw REAL, ddi_away_win REAL,
        calibrated_home_win REAL, calibrated_draw REAL, calibrated_away_win REAL,
        protection_triggered INTEGER DEFAULT 0, sp_missing INTEGER DEFAULT 0,
        fit_score REAL, rating TEXT, direction TEXT,
        direction_warning INTEGER DEFAULT 0,
        downgrade_count INTEGER DEFAULT 0, meltdown INTEGER DEFAULT 0,
        scenario_type TEXT,
        top2_total_goals TEXT, top2_half_full TEXT, top3_scores TEXT,
        s7_score REAL, s7_reason TEXT, trap_analysis TEXT, key_risk TEXT,
        actual_score TEXT, half_time_score TEXT, half_full TEXT,
        hit INTEGER, diagnosis TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        result_updated_at TEXT,
        wc_group TEXT, jc_sp_home REAL, jc_sp_draw REAL, jc_sp_away REAL,
        ah_home REAL, ah_draw REAL, ah_away REAL, match_date TEXT,
        jc_hhad_win REAL, jc_hhad_draw REAL, jc_hhad_lose REAL,
        jc_sp_home_flag INTEGER DEFAULT 0, jc_sp_draw_flag INTEGER DEFAULT 0, jc_sp_away_flag INTEGER DEFAULT 0,
        jc_hhad_win_flag INTEGER DEFAULT 0, jc_hhad_draw_flag INTEGER DEFAULT 0, jc_hhad_lose_flag INTEGER DEFAULT 0
    );
    """)
    conn.commit()
    conn.close()

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def parse_weekday(match_id):
    for wd in WEEKDAY_CN:
        if match_id.startswith(wd):
            return wd
    return None

def get_today_cn():
    return WEEKDAY_CN[date.today().weekday()]


def _sync_match_json(match_id, actual_score, half_full):
    """Sync a single match result to match_info.json and analysis.json."""
    import json as _j, os as _os
    mi_path = _os.path.join(BASE, "data", "match_info.json")
    if _os.path.exists(mi_path):
        with open(mi_path, "r", encoding="utf-8") as f:
            mi = _j.load(f)
        for m in mi.get("matches", []):
            if m.get("id") == match_id:
                m["actual_score"] = actual_score
                if half_full:
                    m["half_full"] = half_full
                break
        with open(mi_path, "w", encoding="utf-8") as f:
            _j.dump(mi, f, ensure_ascii=False, indent=2)
    an_path = _os.path.join(APP_DATA, "analysis.json")
    if _os.path.exists(an_path):
        with open(an_path, "r", encoding="utf-8") as f:
            an = _j.load(f)
        for r in an.get("rating", []):
            if r.get("id") == match_id:
                r["actual_score"] = actual_score
                if half_full:
                    r["half_full"] = half_full
                break
        with open(an_path, "w", encoding="utf-8") as f:
            _j.dump(an, f, ensure_ascii=False, indent=2)
    rr_path = _os.path.join(BASE, "data", "rating_result.json")
    if _os.path.exists(rr_path):
        with open(rr_path, "r", encoding="utf-8") as f:
            rr = _j.load(f)
        for m in rr.get("matches", []):
            if m.get("id") == match_id:
                m["actual_score"] = actual_score
                if half_full:
                    m["half_full"] = half_full
                direction = m.get("direction", "")
                if direction and actual_score:
                    parts = actual_score.replace(":", "-").split("-")
                    if len(parts) == 2:
                        try:
                            hg = int(parts[0]); ag = int(parts[1])
                            hcp = m.get("jc_handicap")
                            if not hcp and _os.path.exists(_os.path.join(BASE, "data", "match_info.json")):
                                # Fallback: try match_info.json for handicap
                                try:
                                    with open(_os.path.join(BASE, "data", "match_info.json"), "r", encoding="utf-8") as _mf:
                                        _mi_data = _j.load(_mf)
                                    for _mm in _mi_data.get("matches", []):
                                        if _mm.get("id") == match_id:
                                            hcp = _mm.get("jc_handicap", 0)
                                            break
                                except:
                                    pass
                            hcp = hcp or 0
                            adj = hg + hcp - ag
                            if direction == "让胜": m["hit"] = 1 if adj > 0 else 0
                            elif direction == "让平": m["hit"] = 1 if adj == 0 else 0
                            elif direction == "让负": m["hit"] = 1 if adj < 0 else 0
                            elif direction == "胜": m["hit"] = 1 if hg > ag else 0
                            elif direction == "负": m["hit"] = 1 if hg < ag else 0
                            elif direction == "平": m["hit"] = 1 if hg == ag else 0
                        except:
                            pass
                break
        with open(rr_path, "w", encoding="utf-8") as f:
            _j.dump(rr, f, ensure_ascii=False, indent=2)
    if _os.path.exists(rr_path):
        with open(rr_path, "r", encoding="utf-8") as f:
            rr2 = _j.load(f)
        for m in rr2.get("matches", []):
            if m.get("id") == match_id:
                hit_val = m.get("hit")
                if hit_val is not None:
                    import sqlite3 as _sq
                    db_path = _os.path.join(BASE, "framework.db")
                    if _os.path.exists(db_path):
                        conn = _sq.connect(db_path)
                        conn.execute("UPDATE matches SET hit=? WHERE match_id=? AND direction IS NOT NULL AND direction != ''", (hit_val, match_id))
                        conn.commit()
                        conn.close()
                break

def _build_result_cache(db):
    rows = db.execute("SELECT match_id, actual_score, half_full, hit, diagnosis FROM matches WHERE actual_score IS NOT NULL AND actual_score != '' ORDER BY run_id DESC").fetchall()
    _RESULT_CACHE.clear()
    for r in rows:
        if r["match_id"] not in _RESULT_CACHE:
            _RESULT_CACHE[r["match_id"]] = {"actual_score": r["actual_score"], "half_full": r["half_full"], "hit": r["hit"], "diagnosis": r["diagnosis"]}

def get_results_for(match_ids):
    if not _RESULT_CACHE:
        return []
    return [_RESULT_CACHE.get(mid, {}) for mid in match_ids]

def enrich_row_with_results(row_dict):
    mid = row_dict.get("match_id") or row_dict.get("id")
    if _RESULT_CACHE and mid in _RESULT_CACHE:
        r = _RESULT_CACHE[mid]
        if not row_dict.get("actual_score"):
            row_dict["actual_score"] = r.get("actual_score", "")
        row_dict["hit"] = r.get("hit")
        row_dict["diagnosis"] = r.get("diagnosis", "")
    return row_dict

def get_display_date(match_id, match_time):
    """Derive display date from match_id prefix (竞彩销售日).
    E.g. 周二077 + match_time=2026-07-01(Wed) → 2026-06-30(Tue)
    """
    wd = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
    if not match_id or not match_time:
        return (match_time or "")[:10] if match_time else ""
    prefix = match_id[:2]
    if prefix not in wd:
        return match_time[:10]
    target = wd[prefix]
    dt = datetime.strptime(match_time[:10], "%Y-%m-%d")
    days_back = (dt.weekday() - target) % 7
    return (dt - timedelta(days=days_back)).strftime("%Y-%m-%d")

def _console_log(msg):
    log_path = os.path.join(BASE, "data", "console.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with _console_log_lock:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

