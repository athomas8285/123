"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for, get_display_date
from . import matches_bp as bp

@bp.route("/api/dashboard/matches")
def matches():
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    rows = db.execute(
        "SELECT match_id, home, away, match_time, event, direction, rating, actual_score, hit, fit_score, half_full, jc_sp_home, jc_sp_draw, jc_sp_away, jc_handicap FROM matches WHERE run_id=? ORDER BY match_id",
        (rid,)
    ).fetchall()
    db.close()
    result = []
    for r in rows:
        enriched = enrich_row_with_results({k: r[k] for k in r.keys()})
        enriched["display_date"] = get_display_date(enriched.get("match_id", ""), enriched.get("match_time", ""))
        result.append(enriched)
    return jsonify(result)


@bp.route("/api/dashboard/matches_grouped")
def matches_grouped():
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    rows = db.execute(
        "SELECT id, match_id, home, away, match_time, event, league, direction, rating, fit_score, actual_score, hit, half_full, jc_sp_home, jc_sp_draw, jc_sp_away, jc_handicap, asian_handicap, ah_home, ah_draw, ah_away, jc_hhad_win, jc_hhad_draw, jc_hhad_lose, jc_sp_home_flag, jc_sp_draw_flag, jc_sp_away_flag, jc_hhad_win_flag, jc_hhad_draw_flag, jc_hhad_lose_flag FROM matches WHERE id IN (SELECT id FROM matches m2 WHERE m2.match_id = matches.match_id ORDER BY (CASE WHEN m2.match_time IS NULL OR m2.match_time = '' THEN 1 ELSE 0 END), m2.id DESC LIMIT 1) ORDER BY match_id"
    ).fetchall()
    db.close()
    
    groups = {}
    for r in rows:
        enriched = enrich_row_with_results({k: r[k] for k in r.keys()})
        mid = enriched.get("match_id", "")
        mt = r["match_time"] or ""
        enriched["display_date"] = get_display_date(mid, mt)
        key = enriched["display_date"] or mt[:10] if len(mt) >= 10 else "unknown"
        if key not in groups:
            groups[key] = []
        groups[key].append(enriched)
    
    result = []
    for key in sorted(groups.keys(), reverse=True):
        result.append({"sale_date": key, "matches": groups[key]})
    
    return jsonify({"groups": result})


@bp.route("/api/dashboard/prediction/<match_id>")
def prediction_detail(match_id):
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    row = db.execute("SELECT * FROM matches WHERE run_id=? AND match_id=? ORDER BY id DESC LIMIT 1", (rid, match_id)).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "match not found"}), 404
    data = {k: row[k] for k in row.keys()}
    data = enrich_row_with_results(data)
    for k in data:
        if isinstance(data[k], bytes):
            data[k] = data[k].decode("utf-8", errors="replace")
    return jsonify(data)


@bp.route("/api/dashboard/matches_pending")
def matches_pending():
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    rows = db.execute(
        "SELECT match_id, home, away, match_time, event FROM matches WHERE id IN (SELECT id FROM matches m2 WHERE m2.match_id = matches.match_id ORDER BY (CASE WHEN m2.match_time IS NULL OR m2.match_time = '' THEN 1 ELSE 0 END), m2.id DESC LIMIT 1) AND (direction IS NULL OR direction='') ORDER BY match_time"
    ).fetchall()
    db.close()
    pending = []
    for r in rows:
        mt = r["match_time"] or ""
        pending.append({
            "match_id": r["match_id"], "home": r["home"], "away": r["away"],
            "match_time": mt, "event": r["event"]
        })
    return jsonify({"pending": pending})

