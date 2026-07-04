import sqlite3
import datetime, json, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "framework.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    try:
        conn.execute("ALTER TABLE runs ADD COLUMN run_type TEXT NOT NULL DEFAULT 'live'")
    except:
        pass
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        factor_params TEXT,
        run_type TEXT NOT NULL DEFAULT 'live',
        total_matches INTEGER DEFAULT 0,
        hit_count INTEGER DEFAULT 0,
        avg_fit_score REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL REFERENCES runs(id),
        match_id TEXT NOT NULL,
        home TEXT NOT NULL, away TEXT NOT NULL,
        event TEXT, match_time TEXT,
        match_type TEXT, league TEXT,
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
        wc_group TEXT, jc_sp_home REAL, jc_sp_draw REAL, jc_sp_away REAL,
        ah_home REAL, ah_draw REAL, ah_away REAL, match_date TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        result_updated_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_matches_run_id ON matches(run_id);
    CREATE INDEX IF NOT EXISTS idx_matches_match_id ON matches(match_id);
    """)
    conn.commit()
    conn.close()

def insert_run(date, factor_params=None, run_type='live', prediction_date=None):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO runs (date, factor_params, run_type, prediction_date) VALUES (?, ?, ?, ?)",
        (date, json.dumps(factor_params, ensure_ascii=False) if factor_params else None, run_type, prediction_date or datetime.datetime.now().strftime('%Y-%m-%d'))
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id

def insert_match(run_id, m):
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO matches (
            run_id, match_id, home, away, event, match_time,
            match_type, league, asian_handicap, jc_handicap, handicap_change,
            lambda_h_final, lambda_a_final, lambda_diff,
            physical_home_win, physical_draw, physical_away_win,
            market_home_win, market_draw, market_away_win,
            ddi_home_win, ddi_draw, ddi_away_win,
            calibrated_home_win, calibrated_draw, calibrated_away_win,
            protection_triggered, sp_missing,
            fit_score, rating, direction, direction_warning,
            downgrade_count, meltdown, scenario_type,
            top2_total_goals, top2_half_full, top3_scores,
            s7_score, s7_reason, trap_analysis, key_risk,
            wc_group, jc_sp_home, jc_sp_draw, jc_sp_away,
            ah_home, ah_draw, ah_away, match_date,
            actual_score, half_time_score, half_full, hit, diagnosis, created_at, result_updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        run_id, m["match_id"], m["home"], m["away"],
        m.get("event"), m.get("match_time"),
        m.get("match_type"), m.get("league"),
        m.get("asian_handicap"), m.get("jc_handicap"), m.get("handicap_change"),
        m.get("lambda_h_final"), m.get("lambda_a_final"), m.get("lambda_diff"),
        m.get("physical_home_win"), m.get("physical_draw"), m.get("physical_away_win"),
        m.get("market_home_win"), m.get("market_draw"), m.get("market_away_win"),
        m.get("ddi_home_win"), m.get("ddi_draw"), m.get("ddi_away_win"),
        m.get("calibrated_home_win"), m.get("calibrated_draw"), m.get("calibrated_away_win"),
        1 if m.get("protection_triggered") else 0,
        1 if m.get("sp_missing") else 0,
        m.get("fit_score"), m.get("rating"), m.get("direction"),
        1 if m.get("direction_warning") else 0,
        m.get("downgrade_count", 0), 1 if m.get("meltdown") else 0,
        m.get("scenario_type"),
        json.dumps(m.get("top2_total_goals", []), ensure_ascii=False),
        json.dumps(m.get("top2_half_full", []), ensure_ascii=False),
        json.dumps(m.get("top3_scores", []), ensure_ascii=False),
        m.get("s7_score"), m.get("s7_reason"),
        m.get("trap_analysis"), m.get("key_risk"),
        m.get("wc_group"), m.get("jc_sp_home"), m.get("jc_sp_draw"), m.get("jc_sp_away"),
        m.get("ah_home"), m.get("ah_draw"), m.get("ah_away"), m.get("match_date"),
        m.get("actual_score"), m.get("half_time_score"),
        m.get("half_full"), m.get("hit"), m.get("diagnosis"),
        None, None
    ))
    conn.commit()
    conn.close()
    return cur.lastrowid

def update_result(match_id, run_id, actual_score, half_time_score="", half_full="", hit=False, diagnosis=""):
    conn = get_db()
    conn.execute("""
        UPDATE matches SET actual_score=?, half_time_score=?, half_full=?,
            hit=?, diagnosis=?, result_updated_at=datetime('now','localtime')
        WHERE match_id=? AND run_id=?
    """, (actual_score, half_time_score, half_full, 1 if hit else 0, diagnosis, match_id, run_id))
    conn.execute("""
        UPDATE runs SET total_matches=(SELECT COUNT(*) FROM matches WHERE run_id=?),
            hit_count=(SELECT COUNT(*) FROM matches WHERE run_id=? AND hit=1),
            avg_fit_score=(SELECT AVG(fit_score) FROM matches WHERE run_id=? AND fit_score IS NOT NULL)
        WHERE id=?
    """, (run_id, run_id, run_id, run_id))
    conn.commit()
    conn.close()

def get_reviews(limit=50):
    conn = get_db()
    rows = conn.execute("""
        SELECT match_id as id, match_time as date, home, away,
               direction, actual_score, hit, diagnosis
        FROM matches WHERE actual_score IS NOT NULL AND hit IS NOT NULL
        ORDER BY match_time DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_latest_run():
    conn = get_db()
    run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    if run:
        matches = conn.execute("SELECT * FROM matches WHERE run_id=? ORDER BY match_id",
                              (run["id"],)).fetchall()
        conn.close()
        return dict(run), [dict(m) for m in matches]
    conn.close()
    return None, []

if __name__ == "__main__":
    init_db()
    print("DB OK:", DB)


