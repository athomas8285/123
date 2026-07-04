"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for, get_display_date
from . import fundamental_bp as bp

@bp.route("/api/dashboard/fundamental")
def fundamental_analysis():
    """Return merged fundamental + prediction data for all matches, grouped by date."""
    import os, json, sqlite3 as _sq

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    # Load all data sources
    fund = load_json(os.path.join(BASE_DIR, "data", "fundamental_analysis.json")) or []
    mi = load_json(os.path.join(BASE_DIR, "data", "match_info.json")) or {}
    rat = load_json(os.path.join(BASE_DIR, "data", "rating_result.json")) or {}
    mc = load_json(os.path.join(BASE_DIR, "data", "monte_carlo_result.json")) or {}
    ddi = load_json(os.path.join(BASE_DIR, "data", "ddi_result.json")) or {}
    ai = load_json(os.path.join(BASE_DIR, "data", "ai_judgment.json")) or {}

    # Build lookup maps
    mi_map = {}
    for m in mi.get("matches", []):
        if m.get("id"):
            mi_map[m["id"]] = m

    rat_map = {}
    for m in rat.get("matches", []):
        mid = m.get("id") or m.get("match_id")
        if mid:
            rat_map[mid] = m

    mc_map = {}
    for m in mc.get("matches", []):
        if m.get("id"):
            mc_map[m["id"]] = m

    ddi_map = {}
    ai_map = {}
    ai_list = ai.get("matches", [])
    if isinstance(ai_list, list):
        for ai_row in ai_list:
            ai_map[ai_row.get("id", "")] = ai_row
    for m in ddi.get("matches", []):
        if m.get("id"):
            ddi_map[m["id"]] = m

    # Build hit cache from cross-run DB results
    _build_result_cache(db_get())

    # Merge data per match
    result = []
    for item in fund:
        mid = item.get("id", "")
        mi_data = mi_map.get(mid, {})
        rat_data = rat_map.get(mid, {})
        mc_data = mc_map.get(mid, {})
        ddi_data = ddi_map.get(mid, {})
        ai_data = ai_map.get(mid, {})

        merged = {
            "id": mid,
            "display_date": get_display_date(mid, mi_data.get("time", "")),
            "home": item.get("home", mi_data.get("home", "")),
            "away": item.get("away", mi_data.get("away", "")),
            "time": mi_data.get("time", ""),
            "narrative": item.get("narrative", ""),
            # SP odds
            "sp_home": mi_data.get("jc_sp_win") or mi_data.get("sp_home", ""),
            "sp_draw": mi_data.get("jc_sp_draw") or mi_data.get("sp_draw", ""),
            "sp_away": mi_data.get("jc_sp_lose") or mi_data.get("sp_away", ""),
            "sp_home_flag": mi_data.get("jc_sp_home_flag", 0),
            "sp_draw_flag": mi_data.get("jc_sp_draw_flag", 0),
            "sp_away_flag": mi_data.get("jc_sp_away_flag", 0),
            # Handicap
            "handicap": mi_data.get("jc_handicap") if mi_data.get("jc_handicap") is not None and mi_data.get("jc_handicap") != "" else (mi_data.get("asian_handicap") if mi_data.get("asian_handicap") is not None and mi_data.get("asian_handicap") != "" else ""),
            "hh_win": mi_data.get("jc_hhad_win", ""),
            "hh_draw": mi_data.get("jc_hhad_draw", ""),
            "hh_lose": mi_data.get("jc_hhad_lose", ""),
            "hh_win_flag": mi_data.get("jc_hhad_win_flag", 0),
            "hh_draw_flag": mi_data.get("jc_hhad_draw_flag", 0),
            "hh_lose_flag": mi_data.get("jc_hhad_lose_flag", 0),
            # Prediction
            "direction": rat_data.get("direction", ""),
            "backup_direction": rat_data.get("backup_direction", ""),
            "rating": rat_data.get("rating", ""),
            "fit_score": rat_data.get("fit_score"),
            # Result
            "actual_score": rat_data.get("actual_score", ""),
            "half_full": rat_data.get("half_full") or mi_data.get("half_full", ""),
            "hit": rat_data.get("hit"),
            # MC predictions
            "top2_goals": mc_data.get("top2_total_goals", []),
            "top2_hf": mc_data.get("top2_half_full", []),
            "top3_scores": mc_data.get("top3_scores", []),
            "physical": mc_data.get("physical", {}),
            "lambda_h": mc_data.get("lambda_h_final"),
            "lambda_a": mc_data.get("lambda_a_final"),
            "lambda_diff": mc_data.get("lambda_diff"),
            # AI analysis
            "s7_reason": ai_data.get("s7_reason", ""),
            "trap_analysis": ai_data.get("trap_analysis", ""),
            "key_risk": ai_data.get("key_risk", ""),
            "jc_hcp_prob": mc_data.get("jc_handicap_prob", {}),
            # DDI
            "p_market": ddi_data.get("p_market", {}),
            "ddi": ddi_data.get("ddi", {}),
            "protection": ddi_data.get("protection_triggered", False),
            "sp_missing": ddi_data.get("sp_missing", False),
        }

        # Enforce sp_missing when all three SP odds are absent
        if not merged.get("sp_missing") and merged.get("sp_home") in (None, "", 0) and merged.get("sp_draw") in (None, "", 0) and merged.get("sp_away") in (None, "", 0):
            merged["sp_missing"] = True
        # Unset sp_missing when SP odds are actually present (DDI data may be stale)
        if merged.get("sp_missing") and merged.get("sp_home") not in (None, "", 0) and merged.get("sp_draw") not in (None, "", 0) and merged.get("sp_away") not in (None, "", 0):
            merged["sp_missing"] = False

        # Override actual_score/hit from cross-run cache if available
        if mid in _RESULT_CACHE:
            merged["actual_score"] = _RESULT_CACHE[mid].get("actual_score", merged["actual_score"])
            merged["half_full"] = _RESULT_CACHE[mid].get("half_full", merged["half_full"])
            merged["hit"] = _RESULT_CACHE[mid].get("hit")

        result.append(merged)

    # Sort by time descending
    result.sort(key=lambda x: x.get("time", ""), reverse=True)

    return jsonify(result)


