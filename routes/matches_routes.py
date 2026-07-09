"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for, get_display_date
from . import matches_bp as bp


@bp.route("/api/dashboard/matches_grouped")
def matches_grouped():
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    rows = db.execute(
        """SELECT * FROM matches m1 WHERE m1.id = (
            SELECT id FROM matches m2 WHERE m2.match_id = m1.match_id
            ORDER BY CASE WHEN m2.direction IS NOT NULL AND m2.direction != '' THEN 0 ELSE 1 END, m2.id DESC LIMIT 1
        ) ORDER BY match_id"""
    ).fetchall()
    db.close()

    groups = {}
    for r in rows:
        enriched = enrich_row_with_results({k: r[k] for k in r.keys()})
        mt = r["match_time"] or ""
        key = mt[:10] if len(mt) >= 10 else "unknown"
        if key not in groups:
            groups[key] = []
        groups[key].append(enriched)

    result = []
    for key in sorted(groups.keys(), reverse=True):
        result.append({"sale_date": key, "matches": groups[key]})

    return jsonify({"groups": result})

