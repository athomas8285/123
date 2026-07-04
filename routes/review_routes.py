"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for
from . import review_bp as bp

@bp.route("/api/dashboard/review")
def review():
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    
    all_rows = db.execute("SELECT match_id FROM matches WHERE run_id=?", (rid,)).fetchall()
    match_ids = [r["match_id"] for r in all_rows]
    
    # Build enriched completed list
    completed_raw = db.execute(
        "SELECT id, match_id, home, away, match_time, event, direction, rating, fit_score, actual_score, half_time_score, hit, diagnosis, result_updated_at FROM matches WHERE run_id=? ORDER BY id DESC",
        (rid,)
    ).fetchall()
    
    completed_list = []
    for r in completed_raw:
        d = enrich_row_with_results({k: r[k] for k in r.keys()})
        if d.get("actual_score"):
            completed_list.append(d)
    
    # Limit to 50
    completed_list = completed_list[:50]
    
    # Cross-run stats
    total_rated = 0; total_hit = 0
    for mid in match_ids:
        if mid in _RESULT_CACHE and _RESULT_CACHE[mid]["hit"] is not None:
            total_rated += 1
            if _RESULT_CACHE[mid]["hit"] == 1:
                total_hit += 1

    # Trend
    trend_map = {}
    for mid in match_ids:
        if mid in _RESULT_CACHE:
            h = _RESULT_CACHE[mid]["hit"]
            if h is not None:
                wd = parse_weekday(mid)
                key = wd if wd else "other"
                if key not in trend_map:
                    trend_map[key] = {"total": 0, "hit": 0}
                trend_map[key]["total"] += 1
                if h == 1:
                    trend_map[key]["hit"] += 1
    
    trend = []
    for wd in WEEKDAY_CN:
        if wd in trend_map:
            t = trend_map[wd]
            trend.append({"label": wd, "hit": t["hit"], "total": t["total"], "rate": round(t["hit"]/t["total"]*100, 1) if t["total"] else 0})
    if "other" in trend_map:
        t = trend_map["other"]
        trend.append({"label": "\u65e9\u671f", "hit": t["hit"], "total": t["total"], "rate": round(t["hit"]/t["total"]*100, 1) if t["total"] else 0})
    
    db.close()
    
    cumulative_rate = round(total_hit / total_rated * 100, 1) if total_rated else 0
    
    return jsonify({
        "completed": completed_list,
        "cumulative": {"total": total_rated, "hits": total_hit, "rate": cumulative_rate},
        "trend": trend
    })


