"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory, render_template
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for
from . import overview_bp as bp
import os
from datetime import datetime, timedelta

@bp.route("/")
def index():
    return render_template("dashboard.html")


@bp.route("/api/dashboard/stats")
def stats():
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    
    # Cross-run: get latest record for each unique match_id
    all_match_rows = db.execute(
        "SELECT id, match_id, home, away, match_time, event, direction, rating, fit_score, actual_score, hit FROM matches WHERE id IN (SELECT MAX(id) FROM matches GROUP BY match_id) ORDER BY match_id"
    ).fetchall()
    total = len(all_match_rows)
    match_ids = [r["match_id"] for r in all_match_rows]
    predicted = sum(1 for r in all_match_rows if r["direction"])
    
    scored = 0; hit = 0; miss = 0
    for mid in match_ids:
        if mid in _RESULT_CACHE:
            scored += 1
            h = _RESULT_CACHE[mid]["hit"]
            if h == 1: hit += 1
            elif h == 0: miss += 1
    
    need_predict = total - predicted
    recent = all_match_rows[-20:] if len(all_match_rows) > 20 else all_match_rows
    recent_list = [enrich_row_with_results({k: r[k] for k in r.keys()}) for r in recent]
    
    db.close()
    
    analysis = load_json(os.path.join(APP_DATA, "analysis.json"))
    al = list(analysis.get("AL", {}).keys()) if analysis else []
    return jsonify({
        "total": total, "scored": scored, "predicted": predicted,
        "hit": hit, "miss": miss, "today_need_predict": need_predict,
        "al_groups": al, "recent": recent_list
    })


@bp.route("/api/dashboard/analysis")
def analysis():
    data = load_json(os.path.join(APP_DATA, "analysis.json"))
    if not data:
        return jsonify({"error": "no analysis.json"})
    ratings = data.get("rating", [])
    return jsonify({
        "total_ratings": len(ratings),
        "completed": len([r for r in ratings if r.get("actual_score")]),
        "predicted": len([r for r in ratings if r.get("direction") and not r.get("actual_score")]),
        "waiting": len([r for r in ratings if not r.get("direction")]),
        "al_keys": list(data.get("AL", {}).keys())
    })

# ==================== New endpoints ====================


@bp.route("/api/dashboard/overview")
def overview():
    db = db_get()
    _build_result_cache(db)
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    
    # Cross-run: get latest record for each unique match_id
    all_match_rows = db.execute(
        "SELECT id, match_id, home, away, match_time, event, league, direction, rating, fit_score, actual_score, hit, sp_missing FROM matches WHERE id IN (SELECT MAX(id) FROM matches GROUP BY match_id) ORDER BY match_id"
    ).fetchall()
    total = len(all_match_rows)
    match_ids = [r["match_id"] for r in all_match_rows]
    predicted = sum(1 for r in all_match_rows if r["direction"])
    
    scored = 0; hit = 0; miss = 0
    for mid in match_ids:
        if mid in _RESULT_CACHE:
            scored += 1
            h = _RESULT_CACHE[mid]["hit"]
            if h == 1: hit += 1
            elif h == 0: miss += 1
    
    hitrate = round(hit / (hit + miss) * 100, 1) if (hit + miss) > 0 else 0
    
    # Today's active predictions: matches with direction but no actual_score yet
    today_matches_raw = []
    seen_today = set()
    for r in all_match_rows:
        mid = r["match_id"]
        if r["direction"] and mid not in seen_today and (not r["actual_score"] or r["actual_score"] == ''):
            seen_today.add(mid)
            today_matches_raw.append(r)
    today_matches = [enrich_row_with_results({k: r[k] for k in r.keys()}) for r in today_matches_raw]

    # Need results: matches with direction but result not yet in _RESULT_CACHE
    need_results = sum(1 for r in all_match_rows if r["direction"] and r["match_id"] not in _RESULT_CACHE)
    missing_results = need_results
    sp_missing = sum(1 for r in all_match_rows if r["sp_missing"])

    # === Flow status for today ===
    from datetime import datetime as _flow_dt, timedelta as _flow_td
    today_str = _flow_dt.now().strftime("%Y-%m-%d")
    today_cn = get_today_cn() if 'get_today_cn' in dir() else ""
    # Count matches by date
    today_match_ids = set()
    pending_today = 0
    predicted_today = 0
    for r in all_match_rows:
        mt = r["match_time"] or ""
        mid = r["match_id"]
        if mt and mt[:10] == today_str:
            today_match_ids.add(mid)
            if r["direction"]:
                predicted_today += 1
            else:
                pending_today += 1
        elif today_cn and mid.startswith(today_cn):
            today_match_ids.add(mid)
            if r["direction"]:
                predicted_today += 1
            else:
                pending_today += 1

    plan = load_json(os.path.join(BASE, "data", "plan_data.json"))
    plan_info = None
    if plan:
        plan_count = 0
        for g in plan.get("date_groups", []):
            plan_count += len(g.get("plan_2", [])) + len(g.get("plan_3", []))
        plan_info = {"date": plan.get("date"), "total_matches": plan.get("total_matches"), "plan_count": plan_count}

    has_today_matches = len(today_match_ids) > 0
    has_data_collected = pending_today == 0 and has_today_matches
    has_predicted = predicted_today > 0
    has_plan = bool(plan_info and plan_info.get("plan_count", 0) > 0)
    need_fetch = not has_today_matches
    need_data = pending_today > 0
    need_predict = pending_today > 0 or (has_today_matches and not has_predicted)
    need_results_check = missing_results > 0
    need_plan = not has_plan

    flow_steps = [
        {"id": "fetch", "label": "获取竞彩网比赛", "done": has_today_matches, "desc": (f"已获取 {len(today_match_ids)} 场" if has_today_matches else "未获取"), "action": need_fetch},
        {"id": "data", "label": "获取比赛数据", "done": has_data_collected, "desc": (f"已采集" if has_data_collected else f"待采集 {pending_today} 场"), "action": need_data},
        {"id": "predict", "label": "运行预测", "done": has_predicted, "desc": (f"已预测 {predicted_today} 场" if has_predicted else f"待预测 {pending_today} 场"), "action": need_predict},
        {"id": "results", "label": "查询赛果", "done": not need_results_check, "desc": (f"需补 {missing_results} 场" if need_results_check else "无需补录"), "action": need_results_check},
        {"id": "plan", "label": "生成计划池", "done": has_plan, "desc": (f"已生成" if has_plan else "待生成"), "action": need_plan},
    ]

    
    db.close()
    
    return jsonify({
        "stats": {"total": total, "scored": scored, "predicted": predicted, "hit": hit, "miss": miss, "hitrate": hitrate},
        "today_matches": today_matches,
        "missing_results": missing_results,
        "health": {"sp_missing": sp_missing, "total": total},
        "flow_steps": flow_steps,
        "plan_info": plan_info
    })


@bp.route("/api/dashboard/pipeline_progress")
def pipeline_progress():
    """Return the last 50 lines of pipeline_run.log for progress tracking."""
    log_path = os.path.join(BASE, "data", "pipeline_run.log")
    if os.path.exists(log_path):
        # Try UTF-8 first, fall back to GBK (Windows Chinese)
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except:
            with open(log_path, "r", encoding="gbk", errors="replace") as f:
                lines = f.readlines()
        # Return last 50 lines, also check if pipeline is done
        tail = "".join(lines[-50:])
        done = "[OK] All steps complete" in tail or "[ERROR]" in tail or "complete" in tail.lower()
        return jsonify({"log": tail, "done": done})
    return jsonify({"log": "", "done": False})


@bp.route("/api/dashboard/console_log")
def console_log():
    """Return console log lines as a list."""
    log_path = os.path.join(BASE, "data", "console.log")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return jsonify({"log": "".join(lines[-100:])})
    return jsonify({"log": ""})

# ==================== Routes ====================

