"""Auto-generated route file."""
from flask import jsonify, request, send_from_directory
from .helpers import db_get, load_json, _build_result_cache, _RESULT_CACHE, _console_log
from .helpers import BASE, APP_DATA, WEEKDAY_CN, parse_weekday, get_today_cn
from .helpers import enrich_row_with_results, get_results_for
from .helpers import _sync_match_json
from . import console_bp as bp
import os

@bp.route("/api/dashboard/action/fetch_results")
def action_fetch_results():
    import urllib.request, re, subprocess, os
    from datetime import datetime, timedelta

    db = db_get()
    rid = db.execute("SELECT MAX(run_id) FROM matches").fetchone()[0]
    # Matches that finished but no score
    need = db.execute("""
        SELECT DISTINCT match_id, home, away, match_time FROM matches
        WHERE run_id=? AND match_time < datetime('now', '+8 hours')
        AND match_time > datetime('now', '-3 days')
        AND (actual_score IS NULL OR actual_score='')
        ORDER BY match_time
    """, (rid,)).fetchall()
    db.close()

    if not need:
        return jsonify({"ok": True, "msg": "没有需要补赛果的比赛", "updated": 0, "total_pending": 0, "logs": ["没有需要补赛果的比赛"]})

    # Group by date
    dates = {}
    for r in need:
        mt = r["match_time"] if r["match_time"] else ""
        if not mt or len(mt) < 10:
            continue
        d = mt[:10]
        if d not in dates:
            dates[d] = []
        dates[d].append(dict(r))

    logs = []
    results_list = []
    updated = 0

    for date_str, matches in dates.items():
        logs.append(f"=== {date_str} ({len(matches)}场比赛) ===")

        # --- Try 1: 竞彩网 ---
        jczq_results = _try_jczq_results(date_str, matches)
        if jczq_results:
            logs.append(f"竞彩网: 获取到 {len(jczq_results)} 条赛果")
            for r in jczq_results:
                ok = _write_result(r)
                if ok:
                    updated += 1
                    logs.append(f"  OK: {r['match_id']} {r.get('full_score','')}")
                    for m in matches:
                        if m["match_id"] == r["match_id"]:
                            results_list.append({"match_id": r["match_id"], "home": m.get("home",""), "away": m.get("away",""), "full_score": r.get("full_score",""), "half_full": r.get("half_full","")})
                            break
            continue

        # --- Try 2: 500.com (try match date, then day before, then day after) ---
        logs.append("竞彩网: 无数据, 尝试500.com...")
        from datetime import datetime as dt500, timedelta
        wb_results = _try_500_results(date_str)
        if not wb_results:
            prev_day = (dt500.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            wb_results = _try_500_results(prev_day)
            if wb_results:
                logs.append(f"500.com: {date_str}无数据, 使用前一天 {prev_day} 找到 {len(wb_results)} 条")
        if not wb_results:
            next_day = (dt500.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            wb_results = _try_500_results(next_day)
            if wb_results:
                logs.append(f"500.com: {date_str}无数据, 使用后一天 {next_day} 找到 {len(wb_results)} 条")
        if wb_results:
            logs.append(f"500.com: 获取到 {len(wb_results)} 条赛果")
            for r in wb_results:
                # Match by match_id
                for m in matches:
                    if r["match_id"] == m["match_id"]:
                        ok = _write_result({"match_id": r["match_id"], "full_score": r["full_score"], "half_full": r.get("half_full","")})
                        if ok:
                            updated += 1
                            logs.append(f"  OK: {r['match_id']} {r['full_score']}")
                            results_list.append({"match_id": r["match_id"], "home": m["home"], "away": m["away"], "full_score": r["full_score"], "half_full": r.get("half_full","")})
                        break
            continue

        # --- Both failed ---
        ids = [m["match_id"] for m in matches]
        logs.append(f"竞彩网和500.com均无数据, 需手动录入: {', '.join(ids)}")

    # Auto-regenerate fundamental_analysis.json and plan_data after results update
    if updated > 0:
        try:
            _console_log("赛果已更新，自动重建分析数据...")
            subprocess.run(["python", os.path.join(BASE, "gen_fundamental.py")],
                capture_output=True, timeout=60, cwd=BASE)
            _console_log("自动重建: fundamental_analysis.json 完成")
            subprocess.run(["python", os.path.join(BASE, "gen_plan.py")],
                capture_output=True, timeout=60, cwd=BASE)
            subprocess.run(["python", os.path.join(BASE, "gen_plan_html.py")],
                capture_output=True, timeout=60, cwd=BASE)
            _console_log("自动重建: 计划池已更新")
            subprocess.run(["python", os.path.join(BASE, "gen_featured.py")],
                capture_output=True, timeout=60, cwd=BASE)
            subprocess.run(["python", os.path.join(BASE, "gen_featured_html.py")],
                capture_output=True, timeout=60, cwd=BASE)
            _console_log("自动重建: 精选计划单已更新")
        except Exception as e:
            _console_log(f"自动重建失败: {e}")
    summary = f"一键查询赛果: 更新 {updated}/{len(need)} 场"
    _console_log(summary)
    return jsonify({
        "ok": True,
        "updated": updated,
        "total_pending": len(need),
        "logs": logs,
        "results": results_list
    })


def _try_jczq_results(date_str, matches):
    """Try ??? API for results (only works for currently-on-sale matches with scores)."""
    try:
        import requests as jcr, json
        url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=had,hhad"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.sporttery.cn/",
            "Origin": "https://www.sporttery.cn",
            "Connection": "keep-alive",
        }
        resp = jcr.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        days = data.get("value", {}).get("matchInfoList", [])
        for day in days:
            for m in day.get("subMatchList", []):
                num = m.get("matchNumStr", "")
                if num not in [x["match_id"] for x in matches]:
                    continue
                # Check if match has a final score
                hscore = m.get("homeTeamScore")
                ascore = m.get("awayTeamScore")
                if hscore is not None and ascore is not None and hscore >= 0 and ascore >= 0:
                    results.append({
                        "match_id": num,
                        "full_score": f"{hscore}:{ascore}",
                        "half_full": m.get("halfFullResult", "")
                    })
        return results
    except:
        return []


def _try_500_results(date_str):
    """Fetch results from 500.com using mobile User-Agent (desktop version requires login)."""
    try:
        import requests as req500, re as re500
        url = f"https://zx.500.com/jczq/kaijiang.php?d={date_str}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        resp = req500.get(url, headers=headers, timeout=15)
        resp.encoding = "gbk"
        html = resp.text
        # Find all match IDs (weekday + number)
        weekdays_re = "周[一二三四五六日]"
        all_ids = re500.findall(weekdays_re + r"\d+", html)
        results = []
        for mid in all_ids:
            pos = html.find(mid)
            best = None
            best_dist = 99999
            for sm in re500.finditer(r"\((\d+):(\d+)\)\s*(\d+):(\d+)", html):
                if sm.start() > pos and sm.start() - pos < best_dist:
                    best_dist = sm.start() - pos
                    best = (sm.group(1), sm.group(2), sm.group(3), sm.group(4))
            if best and best_dist < 2000:
                h_h, h_a = int(best[0]), int(best[1])
                f_h, f_a = int(best[2]), int(best[3])
                half_r = "胜" if h_h > h_a else ("平" if h_h == h_a else "负")
                full_r = "胜" if f_h > f_a else ("平" if f_h == f_a else "负")
                results.append({
                    "match_id": mid,
                    "full_score": f"{f_h}:{f_a}",
                    "half_time_score": f"{h_h}:{h_a}",
                    "half_full": half_r + full_r
                })
        return results
    except:
        return []


def _write_result(r):
    import sqlite3, os
    db_path = os.path.join(BASE, "framework.db")
    conn = sqlite3.connect(db_path)
    hts = r.get("half_time_score", "")
    if hts:
        cur = conn.execute(
            "UPDATE matches SET actual_score=?, half_full=?, half_time_score=?, result_updated_at=datetime('now') WHERE match_id=? AND (actual_score IS NULL OR actual_score='')",
            (r.get("full_score",""), r.get("half_full",""), hts, r["match_id"])
        )
    else:
        cur = conn.execute(
            "UPDATE matches SET actual_score=?, half_full=?, result_updated_at=datetime('now') WHERE match_id=? AND (actual_score IS NULL OR actual_score='')",
            (r.get("full_score",""), r.get("half_full",""), r["match_id"])
        )
    ok = cur.rowcount > 0
    # Calculate hit
    if ok:
        direction_row = conn.execute("SELECT direction FROM matches WHERE match_id=? LIMIT 1", (r["match_id"],)).fetchone()
        if direction_row:
            direction = (direction_row[0] or "")
        else:
            direction = ""
        score = r.get("full_score","")
        if score and ":" in score and direction:
            try:
                hg, ag = map(int, score.split(":"))
                # Read jc_handicap from DB for handicap-adjusted calculation
                hc_row = conn.execute("SELECT jc_handicap FROM matches WHERE match_id=? LIMIT 1", (r["match_id"],)).fetchone()
                jc_hc = hc_row[0] if hc_row and hc_row[0] is not None else 0
                adj = hg + jc_hc - ag
                dc = ord(direction[0]) if direction else 0
                if direction == "让负":  # rang fu: away wins after handicap
                    hit = adj < 0
                elif direction == "让胜":  # rang sheng: home wins after handicap
                    hit = adj > 0
                elif direction == "让平":  # rang ping: draw after handicap
                    hit = adj == 0
                elif dc == 32988:  # sheng: home win
                    hit = hg > ag
                elif dc == 36127:  # fu: away win
                    hit = hg < ag
                elif dc == 24179:  # ping: draw
                    hit = hg == ag
                else:
                    hit = False
                hit_val = 1 if hit else 0
                diag = "命中" if hit else "未命中"
                import sqlite3 as _sq3
                _conn2 = _sq3.connect(db_path)
                _conn2.execute("UPDATE matches SET hit=?, diagnosis=? WHERE match_id=? AND (hit IS NULL OR hit='')", (hit_val, diag, r["match_id"]))
                _conn2.commit()
                _conn2.close()
            except:
                pass
    conn.commit()
    conn.close()
    if ok:
        _sync_match_json(r["match_id"], r.get("full_score",""), r.get("half_full",""))
    return ok


@bp.route("/api/dashboard/action/fetch_jczq")
def action_fetch_jczq():
    """Fetch current on-sale matches from 竞彩网 API, save raw data,
    insert new matches into framework.db, and update match_info.json."""
    import json, datetime, sqlite3

    logs = []
    api_url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=hhad,had,ttg,crs,hafu"

    # Step 1: Fetch from API ? requests first, Playwright fallback
    import time
    api_data = None
    fetch_error = None

    # --- Method 1: requests with browser headers ---
    try:
        import requests as req_lib
        s = req_lib.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.sporttery.cn/",
            "Origin": "https://www.sporttery.cn",
            "Connection": "keep-alive",
        })
        resp = s.get(api_url, timeout=15)
        if resp.status_code == 403:
            fetch_error = "竞彩网 WAF 拦截 (403), 切换 Playwright..."
        else:
            resp.raise_for_status()
            api_data = resp.json()
            logs.append("requests 获取成功")
        s.close()
    except Exception as e:
        if not fetch_error:
            fetch_error = f"requests失败: {e}"

    # --- Method 2: Playwright real browser fallback ---
    if api_data is None:
        logs.append(fetch_error)
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(api_url, wait_until="networkidle", timeout=30000)
                body = page.content()
                # The API returns raw JSON, not HTML. Extract from <pre> or body text.
                import re
                pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", body, re.DOTALL)
                if pre_match:
                    api_data = json.loads(pre_match.group(1))
                else:
                    # Try body text directly (Chrome wraps JSON in <html><body><pre>)
                    text = page.evaluate("() => document.body.innerText")
                    api_data = json.loads(text)
                browser.close()
                logs.append("Playwright 获取成功")
        except Exception as e2:
            # --- Method 3: Auto-discover new API endpoint from website network ---
            logs.append("Playwright direct call also failed: " + str(e2))
            logs.append("Trying auto-discovery on sporttery.cn...")
            try:
                from playwright.sync_api import sync_playwright as pw3
                discovered_url = None
                with pw3() as pw:
                    browser = pw.chromium.launch(headless=True)
                    page = browser.new_page()
                    captured = []
                    def on_response(resp):
                        if "webapi.sporttery.cn" in resp.url.lower() and resp.status == 200:
                            try:
                                ct = resp.headers.get("content-type", "")
                                if "json" in ct or "javascript" in ct:
                                    body = resp.body()
                                    if body and len(body) > 200:
                                        captured.append({"url": resp.url, "body": body[:500].decode("utf-8", errors="ignore")})
                            except:
                                pass
                    page.on("response", on_response)
                    page.goto("https://www.sporttery.cn/jczq/", wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(3000)
                    browser.close()
                for cap in captured:
                    b = cap["body"]
                    if "matchNumStr" in b or "matchInfoList" in b or "homeTeam" in b or "getMatchCalculator" in cap["url"]:
                        discovered_url = cap["url"]
                        break
                if discovered_url:
                    cfg = {"api_url": discovered_url, "last_updated": datetime.datetime.now().isoformat()}
                    cfg_path = os.path.join(BASE, "data", "api_config.json")
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, ensure_ascii=False, indent=2)
                    logs.append("Discovered new API: " + discovered_url.split("?")[0].split("/")[-1])
                    try:
                        import requests as req2
                        s2 = req2.Session()
                        s2.headers.update({
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept-Language": "zh-CN,zh;q=0.9",
                            "Referer": "https://www.sporttery.cn/",
                        })
                        resp2 = s2.get(discovered_url, timeout=15)
                        resp2.raise_for_status()
                        api_data = resp2.json()
                        s2.close()
                        logs.append("New API call succeeded")
                    except Exception as e3:
                        err_logs = [
                            "ERROR: requests -> " + str(fetch_error),
                            "ERROR: Playwright -> " + str(e2),
                            "DISCOVERED: " + discovered_url,
                            "ERROR: retry -> " + str(e3)
                        ]
                        return jsonify({"ok": False, "msg": "Discovered " + discovered_url + " but call failed: " + str(e3), "logs": err_logs})
                else:
                    err_logs = [
                        "ERROR: requests -> " + str(fetch_error),
                        "ERROR: Playwright -> " + str(e2),
                        "ERROR: no matching API found in website network"
                    ]
                    return jsonify({"ok": False, "msg": "All methods failed, auto-discovery found nothing. Please check sporttery.cn manually.", "logs": err_logs})
            except Exception as e4:
                err_logs = [
                    "ERROR: requests -> " + str(fetch_error),
                    "ERROR: Playwright -> " + str(e2),
                    "ERROR: auto-discover -> " + str(e4)
                ]
                return jsonify({"ok": False, "msg": "All methods failed (including auto-discovery): " + str(e4), "logs": err_logs})

    # Step 2: Validate response structure
    value = api_data.get("value")
    if not value or not isinstance(value, dict):
        return jsonify({"ok": False, "msg": "API返回格式异常：缺少 value 字段，接口可能已变更", "logs": ["ERROR: 响应缺少 value 字段，请检查竞彩网网站更新的 API 地址"]})
    match_days = value.get("matchInfoList")
    if match_days is None:
        return jsonify({"ok": False, "msg": "API返回格式异常：缺少 matchInfoList 字段", "logs": ["ERROR: value 中缺少 matchInfoList，可能接口结构已变"]})
    if not isinstance(match_days, list) or len(match_days) == 0:
        return jsonify({"ok": False, "msg": "API返回空列表，当前没有在售比赛或接口参数已过期", "logs": ["ERROR: matchInfoList 为空，可能当前无在售比赛或 poolCode 参数已变"]})

    # Step 3: Save raw data (only after validation passes)
    raw_dir = os.path.join(BASE, "data")
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, "raw_jczq.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(api_data, f, ensure_ascii=False, indent=2)
    logs.append("raw_jczq.json saved")
    total_matches = sum(len(day.get("subMatchList", [])) for day in match_days)
    logs.append(f"API返回 {len(match_days)} 个比赛日，共 {total_matches} 场比赛")

        # Step 4: Check existing match_ids in DB (only for preview -- no insertion)
    db_path = os.path.join(BASE, "framework.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    existing = set(r["match_id"] for r in conn.execute("SELECT DISTINCT match_id FROM matches").fetchall())
    conn.close()

    # Step 5: Build preview list (user confirms via modal)
    new_count = 0
    new_matches_list = []

    for day in match_days:
        business_date = day.get("businessDate", "")
        subs = day.get("subMatchList", [])
        for m in subs:
            mid = m.get("matchNumStr", "")
            if not mid:
                continue
            home = m.get("homeTeamAllName", "") or m.get("homeTeamName", "") or m.get("home", "")
            away = m.get("awayTeamAllName", "") or m.get("awayTeamName", "") or m.get("away", "")
            if not home or not away:
                continue
            if mid in existing:
                continue
            match_time = (m.get("matchDate", "") + " " + m.get("matchTime", "")).strip()
            league = m.get("leagueAllName", "")
            event = m.get("tournamentAllName", "") or league
            had = m.get("had", {})
            jc_sp_home = float(had["h"]) if had.get("h") is not None else None
            jc_sp_draw = float(had["d"]) if had.get("d") is not None else None
            jc_sp_away = float(had["a"]) if had.get("a") is not None else None
            hhad = m.get("hhad", {})
            gl = m.get("goalLine") or hhad.get("goalLine")
            jc_handicap = int(gl) if gl is not None else None
            new_count += 1
            new_matches_list.append({
                "match_id": mid, "home": home, "away": away,
                "match_time": match_time, "league": league, "event": event,
                "business_date": business_date,
                "jc_sp_home": jc_sp_home, "jc_sp_draw": jc_sp_draw, "jc_sp_away": jc_sp_away,
                "jc_handicap": jc_handicap
            })

    logs.append(f"预览：{new_count} 场新比赛（待用户确认）")
    _console_log(f"获取竞彩网比赛: 预览 {new_count} 场新比赛（待确认）")
    return jsonify({
        "ok": True,
        "msg": f"获取完成，{new_count} 场新比赛待确认入库",
        "logs": logs,
        "new_count": new_count,
        "total": total_matches,
        "new_matches": new_matches_list
    })


@bp.route("/api/dashboard/action/confirm_jczq_matches", methods=["POST"])
def action_confirm_jczq_matches():
    """Insert user-confirmed matches from raw_jczq.json into DB + JSON files."""
    import flask as _flask
    data = _flask.request.get_json(force=True, silent=True)
    if not data or "match_ids" not in data:
        return jsonify({"ok": False, "msg": "缺少 match_ids"})
    match_ids = data["match_ids"]
    if not match_ids or not isinstance(match_ids, list):
        return jsonify({"ok": False, "msg": "match_ids 格式错误"})

    import sqlite3 as _sql
    import datetime as _dt
    import json

    # Load raw_jczq.json
    raw_path = os.path.join(BASE, "data", "raw_jczq.json")
    if not os.path.exists(raw_path):
        return jsonify({"ok": False, "msg": "raw_jczq.json 不存在，请先获取比赛"})
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Index matches by match_id
    match_days = raw_data.get("value", {}).get("matchInfoList", [])
    all_matches = {}
    for day in match_days:
        for m in day.get("subMatchList", []):
            mid = m.get("matchNumStr", "")
            if mid:
                all_matches[mid] = m

    # Filter to requested match_ids
    selected = []
    for mid in match_ids:
        if mid not in all_matches:
            continue
        m = all_matches[mid]
        home = m.get("homeTeamAllName", "") or m.get("homeTeamName", "") or m.get("home", "")
        away = m.get("awayTeamAllName", "") or m.get("awayTeamName", "") or m.get("away", "")
        match_time = (m.get("matchDate", "") + " " + m.get("matchTime", "")).strip()
        league = m.get("leagueAllName", "")
        event = m.get("tournamentAllName", "") or league
        had = m.get("had", {})
        jc_sp_home = float(had["h"]) if had.get("h") is not None else None
        jc_sp_draw = float(had["d"]) if had.get("d") is not None else None
        jc_sp_away = float(had["a"]) if had.get("a") is not None else None
        hhad = m.get("hhad", {})
        gl = m.get("goalLine") or hhad.get("goalLine")
        jc_handicap = int(gl) if gl is not None else None
        hafu = m.get("hafu", {})
        hafu_odds = {}
        if hafu:
            for k in ("hh","hd","ha","dh","dd","da","ah","ad","aa"):
                v = hafu.get(k)
                if v is not None and str(v) != "-1":
                    try:
                        hafu_odds[k] = float(v)
                    except:
                        pass
        ttg = m.get("ttg", {})
        ttg_odds = {}
        if ttg:
            for k in ("s0","s1","s2","s3","s4","s5","s6","s7"):
                v = ttg.get(k)
                if v is not None:
                    try:
                        ttg_odds[k] = float(v)
                    except:
                        pass
        crs = m.get("crs", {})
        crs_odds = {}
        if crs:
            for k in crs:
                if k in ("goalLine","goalLineValue","id","updateDate","updateTime"):
                    continue
                if k.endswith("f"):
                    continue
                v = crs.get(k)
                if v is not None:
                    try:
                        crs_odds[k] = float(v)
                    except:
                        pass
        selected.append({
            "mid": mid, "home": home, "away": away,
            "match_time": match_time, "league": league, "event": event,
            "business_date": day.get("businessDate", ""),
            "jc_sp_home": jc_sp_home, "jc_sp_draw": jc_sp_draw, "jc_sp_away": jc_sp_away,
            "jc_handicap": jc_handicap,
            "jc_hhad_win": float(hhad["h"]) if hhad.get("h") is not None else None,
            "jc_hhad_draw": float(hhad["d"]) if hhad.get("d") is not None else None,
            "jc_hhad_lose": float(hhad["a"]) if hhad.get("a") is not None else None,
            "hafu_odds": hafu_odds,
            "ttg_odds": ttg_odds,
            "crs_odds": crs_odds
        })

    if not selected:
        return jsonify({"ok": False, "msg": "未找到有效比赛数据"})

    logs = []

    # === Insert into DB ===
    db_path = os.path.join(BASE, "framework.db")
    conn = _sql.connect(db_path)
    conn.row_factory = _sql.Row
    rid = conn.execute("SELECT COALESCE(MAX(run_id), 0) FROM matches").fetchone()[0]

    # Get existing match_ids to avoid duplicates
    existing_db = set(r["match_id"] for r in conn.execute("SELECT DISTINCT match_id FROM matches").fetchall())

    inserted = 0
    for s in selected:
        if s["mid"] in existing_db:
            continue
        conn.execute(
            """INSERT INTO matches (run_id, match_id, home, away, match_time, event, league, match_date,
               jc_sp_home, jc_sp_draw, jc_sp_away, jc_handicap,
               jc_hhad_win, jc_hhad_draw, jc_hhad_lose)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, s["mid"], s["home"], s["away"], s["match_time"], s["event"], s["league"],
             s["business_date"], s["jc_sp_home"], s["jc_sp_draw"], s["jc_sp_away"], s["jc_handicap"],
             s["jc_hhad_win"], s["jc_hhad_draw"], s["jc_hhad_lose"])
        )
        existing_db.add(s["mid"])
        inserted += 1
    conn.commit()
    conn.close()
    logs.append(f"DB 插入 {inserted} 场比赛")

    if inserted == 0:
        return jsonify({"ok": True, "msg": "所选比赛已存在，无需重复插入", "inserted": 0, "logs": logs})

    # === Update match_info.json ===
    mi_path = os.path.join(BASE, "data", "match_info.json")
    mi_data = {"matches": []}
    if os.path.exists(mi_path):
        with open(mi_path, "r", encoding="utf-8") as f:
            mi_data = json.load(f)
    mi_ids = set(m.get("id", "") for m in mi_data.get("matches", []))
    mi_changed = False
    for s in selected:
        if s["mid"] not in mi_ids:
            mi_data["matches"].append({
                "id": s["mid"], "home": s["home"], "away": s["away"],
                "time": s["match_time"], "event": s["event"],
                "jc_sp_win": s["jc_sp_home"], "jc_sp_draw": s["jc_sp_draw"], "jc_sp_lose": s["jc_sp_away"],
                "sp_home": s["jc_sp_home"], "sp_draw": s["jc_sp_draw"], "sp_away": s["jc_sp_away"],
                "jc_handicap": s["jc_handicap"],
                "jc_hhad_win": s["jc_hhad_win"], "jc_hhad_draw": s["jc_hhad_draw"], "jc_hhad_lose": s["jc_hhad_lose"],
                "hafu_odds": s["hafu_odds"],
                "ttg_odds": s["ttg_odds"],
                "crs_odds": s["crs_odds"]
            })
            mi_ids.add(s["mid"])
            mi_changed = True
    if mi_changed:
        with open(mi_path, "w", encoding="utf-8") as f:
            json.dump(mi_data, f, ensure_ascii=False, indent=2)
        logs.append(f"match_info.json 更新（共 {len(mi_data['matches'])} 条）")

    # === Update locked_data.json ===
    ld_path = os.path.join(BASE, "data", "locked_data.json")
    ld_data = {"matches": [], "updated": ""}
    if os.path.exists(ld_path):
        with open(ld_path, "r", encoding="utf-8") as f:
            ld_data = json.load(f)
    ld_ids = set(m.get("id", "") for m in ld_data.get("matches", []))
    ld_changed = False
    for s in selected:
        if s["mid"] in ld_ids:
            continue
        ld_entry = {
            "id": s["mid"], "home": s["home"], "away": s["away"],
            "time": s["match_time"], "event": s["event"],
            "home_league": "", "away_league": "",
            "sp_home": s["jc_sp_home"], "sp_draw": s["jc_sp_draw"], "sp_away": s["jc_sp_away"],
            "jc_handicap": s["jc_handicap"] or 0, "asian_handicap": 0, "match_type": "group",
            "initial_sp_home": s["jc_sp_home"], "initial_sp_draw": s["jc_sp_draw"], "initial_sp_away": s["jc_sp_away"],
            "handicap_change": "",
            "home_goals": 0, "home_goals_conceded": 0,
            "away_goals": 0, "away_goals_conceded": 0,
            "h2h_missing": True, "xg_last3_missing": True, "xg_season_missing": True,
            "roster_missing": True, "injury_home_missing": True, "injury_away_missing": True,
            "injury_source_unreliable": True, "no_coach_statement": True,
            "motivation_ambiguous": True, "multi_team_linkage": False,
            "home_xg": None, "home_xga": None, "away_xg": None, "away_xga": None,
            "is_home_life_death": False
        }
        ld_data["matches"].append(ld_entry)
        ld_ids.add(s["mid"])
        ld_changed = True
    if ld_changed:
        ld_data["updated"] = _dt.datetime.now().isoformat()[:10]
        with open(ld_path, "w", encoding="utf-8") as f:
            json.dump(ld_data, f, ensure_ascii=False, indent=2)
        logs.append(f"locked_data.json 更新（共 {len(ld_data['matches'])} 条）")

    # === Update factor_params.json ===
    fp_path = os.path.join(BASE, "data", "factor_params.json")
    fp_data = {"matches": []}
    if os.path.exists(fp_path):
        with open(fp_path, "r", encoding="utf-8") as f:
            fp_data = json.load(f)
    fp_ids = set(m.get("id", "") for m in fp_data.get("matches", []))
    fp_changed = False
    for s in selected:
        if s["mid"] in fp_ids:
            continue
        fp_data["matches"].append({
            "id": s["mid"],
            "injury_home": 0, "injury_away": 0,
            "injury_home_boost": 0, "injury_away_boost": 0,
            "motivation_home": 0, "motivation_away": 0,
            "pressure_home": 0, "pressure_away": 0,
            "slack_home": 0, "slack_away": 0,
            "altitude_home": 0, "altitude_away": 0
        })
        fp_ids.add(s["mid"])
        fp_changed = True
    if fp_changed:
        with open(fp_path, "w", encoding="utf-8") as f:
            json.dump(fp_data, f, ensure_ascii=False, indent=2)
        logs.append(f"factor_params.json 更新（共 {len(fp_data['matches'])} 条）")

    _console_log(f"确认入库: {inserted} 场比赛")
    return jsonify({"ok": True, "msg": f"已确认入库 {inserted} 场比赛", "inserted": inserted, "logs": logs})


@bp.route("/api/dashboard/action/refresh_odds", methods=["POST"])
def action_refresh_odds():
    """Refresh all 5 pool odds from 竞彩网 API for specified matches."""
    import flask as _flask
    import sqlite3 as _sql
    import datetime as _dt
    import subprocess as _sp
    import json as _json

    data = _flask.request.get_json(force=True, silent=True)
    if not data or "match_ids" not in data:
        return jsonify({"ok": False, "msg": "缺少 match_ids"})
    match_ids = data["match_ids"]
    if not match_ids or not isinstance(match_ids, list):
        return jsonify({"ok": False, "msg": "match_ids 格式错误"})

    logs = []
    logs.append(f"正在刷新 {len(match_ids)} 场比赛的赔率...")

    # Step 1: Fetch from 竞彩网 API (try requests first, Playwright fallback)
    import requests as _req
    api_url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=hhad,had,ttg,crs,hafu"
    api_data = None
    fetch_error = None

    try:
        s = _req.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.sporttery.cn/",
            "Origin": "https://www.sporttery.cn",
            "Connection": "keep-alive",
        })
        resp = s.get(api_url, timeout=15)
        resp.raise_for_status()
        api_data = resp.json()
        s.close()
        logs.append("requests 获取成功")
    except Exception as e:
        fetch_error = str(e)
        logs.append(f"requests 失败: {e}")

    if api_data is None:
        logs.append("正在用 Playwright 重试...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(api_url, wait_until="networkidle", timeout=30000)
                import re
                text = page.evaluate("() => document.body.innerText")
                api_data = json.loads(text)
                browser.close()
            logs.append("Playwright 获取成功")
        except Exception as e2:
            return jsonify({"ok": False, "msg": f"竞彩网 API 请求失败 (requests+Playwright): {fetch_error} / {e2}", "logs": logs})

    # Index matches from API response
    match_days = api_data.get("value", {}).get("matchInfoList", [])
    api_matches = {}
    for day in match_days:
        for m in day.get("subMatchList", []):
            mid = m.get("matchNumStr", "")
            if mid:
                api_matches[mid] = m

    # Index match_info.json
    mi_path = os.path.join(BASE, "data", "match_info.json")
    mi_data = {"matches": []}
    if os.path.exists(mi_path):
        with open(mi_path, "r", encoding="utf-8") as f:
            mi_data = _json.load(f)
    mi_map = {m["id"]: m for m in mi_data.get("matches", [])}

    # Index locked_data.json
    ld_path = os.path.join(BASE, "data", "locked_data.json")
    ld_data = {"matches": [], "updated": ""}
    if os.path.exists(ld_path):
        with open(ld_path, "r", encoding="utf-8") as f:
            ld_data = _json.load(f)
    ld_map = {m["id"]: m for m in ld_data.get("matches", [])}

    # Step 2: Update each match
    updated = 0
    mi_changed = False
    ld_changed = False
    db_path = os.path.join(BASE, "framework.db")
    conn = _sql.connect(db_path)

    for mid in match_ids:
        if mid not in api_matches:
            logs.append(f"  {mid}: 不在竞彩网响应中，跳过")
            continue
        m = api_matches[mid]
        had = m.get("had", {})
        hhad = m.get("hhad", {})
        gl = m.get("goalLine") or hhad.get("goalLine")

        jc_sp_h = float(had["h"]) if had.get("h") is not None else None
        jc_sp_d = float(had["d"]) if had.get("d") is not None else None
        jc_sp_a = float(had["a"]) if had.get("a") is not None else None
        jc_sp_hf = int(had["hf"]) if had.get("hf") is not None else 0
        jc_sp_df = int(had["df"]) if had.get("df") is not None else 0
        jc_sp_af = int(had["af"]) if had.get("af") is not None else 0
        jc_hh_w = float(hhad["h"]) if hhad.get("h") is not None else None
        jc_hh_d = float(hhad["d"]) if hhad.get("d") is not None else None
        jc_hh_a = float(hhad["a"]) if hhad.get("a") is not None else None
        jc_hh_wf = int(hhad["hf"]) if hhad.get("hf") is not None else 0
        jc_hh_df = int(hhad["df"]) if hhad.get("df") is not None else 0
        jc_hh_af = int(hhad["af"]) if hhad.get("af") is not None else 0
        jc_hc = int(gl) if gl is not None else None

        # TTG odds
        ttg = m.get("ttg", {})
        ttg_o = {}
        if ttg:
            for k in ("s0","s1","s2","s3","s4","s5","s6","s7"):
                v = ttg.get(k)
                if v is not None:
                    try: ttg_o[k] = float(v)
                    except: pass

        # CRS odds
        crs = m.get("crs", {})
        crs_o = {}
        if crs:
            for k in crs:
                if k in ("goalLine","goalLineValue","id","updateDate","updateTime") or k.endswith("f"):
                    continue
                v = crs.get(k)
                if v is not None:
                    try: crs_o[k] = float(v)
                    except: pass

        # HAFU odds
        hafu = m.get("hafu", {})
        hafu_o = {}
        if hafu:
            for k in ("hh","hd","ha","dh","dd","da","ah","ad","aa"):
                v = hafu.get(k)
                if v is not None and str(v) != "-1":
                    try: hafu_o[k] = float(v)
                    except: pass

        # Update DB
        conn.execute(
            """UPDATE matches SET jc_sp_home=?, jc_sp_draw=?, jc_sp_away=?,
               jc_hhad_win=?, jc_hhad_draw=?, jc_hhad_lose=?, jc_handicap=?,
               jc_sp_home_flag=?, jc_sp_draw_flag=?, jc_sp_away_flag=?,
               jc_hhad_win_flag=?, jc_hhad_draw_flag=?, jc_hhad_lose_flag=?
               WHERE match_id=?""",
            (jc_sp_h, jc_sp_d, jc_sp_a, jc_hh_w, jc_hh_d, jc_hh_a, jc_hc,
             jc_sp_hf, jc_sp_df, jc_sp_af, jc_hh_wf, jc_hh_df, jc_hh_af, mid)
        )

        # Update match_info.json
        if mid in mi_map:
            mi_m = mi_map[mid]
            if jc_sp_h is not None: mi_m["jc_sp_win"] = mi_m["sp_home"] = jc_sp_h
            if jc_sp_d is not None: mi_m["jc_sp_draw"] = mi_m["sp_draw"] = jc_sp_d
            if jc_sp_a is not None: mi_m["jc_sp_lose"] = mi_m["sp_away"] = jc_sp_a
            mi_m["jc_sp_home_flag"] = jc_sp_hf
            mi_m["jc_sp_draw_flag"] = jc_sp_df
            mi_m["jc_sp_away_flag"] = jc_sp_af
            if jc_hh_w is not None: mi_m["jc_hhad_win"] = jc_hh_w
            if jc_hh_d is not None: mi_m["jc_hhad_draw"] = jc_hh_d
            if jc_hh_a is not None: mi_m["jc_hhad_lose"] = jc_hh_a
            mi_m["jc_hhad_win_flag"] = jc_hh_wf
            mi_m["jc_hhad_draw_flag"] = jc_hh_df
            mi_m["jc_hhad_lose_flag"] = jc_hh_af
            if jc_hc is not None: mi_m["jc_handicap"] = jc_hc
            if ttg_o: mi_m["ttg_odds"] = ttg_o
            if crs_o: mi_m["crs_odds"] = crs_o
            if hafu_o: mi_m["hafu_odds"] = hafu_o
            mi_changed = True

        # Update locked_data.json
        if mid in ld_map:
            ld_m = ld_map[mid]
            if jc_sp_h is not None: ld_m["sp_home"] = ld_m["initial_sp_home"] = jc_sp_h
            if jc_sp_d is not None: ld_m["sp_draw"] = ld_m["initial_sp_draw"] = jc_sp_d
            if jc_sp_a is not None: ld_m["sp_away"] = ld_m["initial_sp_away"] = jc_sp_a
            if jc_hc is not None: ld_m["jc_handicap"] = jc_hc
            ld_changed = True

        updated += 1

    conn.commit()
    conn.close()
    logs.append(f"DB 更新 {updated} 条")

    # Save match_info.json
    if mi_changed:
        with open(mi_path, "w", encoding="utf-8") as f:
            _json.dump(mi_data, f, ensure_ascii=False, indent=2)
        logs.append(f"match_info.json 已更新（共 {len(mi_data['matches'])} 条）")

    # Save locked_data.json
    if ld_changed:
        ld_data["updated"] = _dt.datetime.now().isoformat()[:10]
        with open(ld_path, "w", encoding="utf-8") as f:
            _json.dump(ld_data, f, ensure_ascii=False, indent=2)
        logs.append(f"locked_data.json 已更新（共 {len(ld_data['matches'])} 条）")

    # Step 3: Regen plan pool + featured
    logs.append("正在重新生成计划池...")
    try:
        r = _sp.run(["python", os.path.join(BASE, "gen_plan.py")], capture_output=True, text=True, timeout=120, cwd=BASE, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            logs.append("gen_plan.py 完成")
        else:
            logs.append(f"gen_plan.py 失败 (code {r.returncode})")
    except Exception as e:
        logs.append(f"gen_plan.py 异常: {e}")

    logs.append("正在重新生成计划池页面...")
    try:
        _sp.run(["python", os.path.join(BASE, "gen_plan_html.py")], capture_output=True, timeout=60, cwd=BASE)
        logs.append("plan.html 已更新")
    except Exception as e:
        logs.append(f"gen_plan_html.py 异常: {e}")

    logs.append("正在重新生成精选计划单...")
    try:
        _sp.run(["python", os.path.join(BASE, "gen_featured.py")], capture_output=True, timeout=60, cwd=BASE)
        logs.append("gen_featured.py 完成")
    except Exception as e:
        logs.append(f"gen_featured.py 异常: {e}")

    try:
        _sp.run(["python", os.path.join(BASE, "gen_featured_html.py")], capture_output=True, timeout=60, cwd=BASE)
        logs.append("featured.html 已更新")
    except Exception as e:
        logs.append(f"gen_featured_html.py 异常: {e}")

    _console_log(f"刷新赔率: {updated}/{len(match_ids)} 场")
    return jsonify({"ok": True, "msg": f"赔率刷新完成: {updated}/{len(match_ids)} 场", "logs": logs, "updated": updated})

@bp.route("/api/dashboard/action/save_manual_result", methods=["POST"])
def action_save_manual_result():
    """Save manually entered match result (score + half_full)."""
    import flask as _flask
    data = _flask.request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "msg": "No data"})
    mid = data.get("match_id", "").strip()
    score = data.get("actual_score", "").strip()
    hf = data.get("half_full", "").strip()
    if not mid:
        return jsonify({"ok": False, "msg": "Missing match_id"})
    if not score:
        return jsonify({"ok": False, "msg": "Missing actual_score"})
    import sqlite3 as _sql
    db_path = os.path.join(BASE, "framework.db")
    conn = _sql.connect(db_path)
    cur = conn.execute(
        'UPDATE matches SET actual_score=?, half_full=?, result_updated_at=datetime("now") WHERE match_id=? AND (actual_score IS NULL OR actual_score="")',
        (score, hf if hf else None, mid)
    )
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    if ok:
        _sync_match_json(mid, score, hf)
        return jsonify({"ok": True, "msg": f"Saved {mid}: {score}" + (f" ({hf})" if hf else "")})
    else:
        return jsonify({"ok": False, "msg": f"{mid} not found or already has score"})


@bp.route("/api/dashboard/action/run_predict", methods=["GET", "POST"])
def action_run_predict():
    import subprocess, os, threading
    base = BASE
    log_path = os.path.join(base, "data", "pipeline_run.log")
    
    # Get match_ids from POST body (priority)
    match_ids_arg = []
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        match_ids_arg = body.get("match_ids", [])
    
    if not match_ids_arg:
        return jsonify({"ok": False, "msg": "未选择任何比赛，请先在待预测列表中勾选"})
    
    ids_file = os.path.join(base, "data", "_predict_ids.txt")
    with open(ids_file, "w", encoding="utf-8") as f:
        f.write(",".join(match_ids_arg))
    _console_log(f"运行预测: 选择性预测 {len(match_ids_arg)} 场比赛")
    
    def run_pipeline_wrapper():
        cmd = ["python", "run_all.py", "--match-ids", ",".join(match_ids_arg)]
        try:
            with open(log_path, "w", encoding="utf-8") as logf:
                logf.write("")
                subprocess.run(cmd, cwd=base, stdout=logf, stderr=subprocess.STDOUT, timeout=600)
            # Regenerate fundamental_analysis.json with updated prediction data
            try:
                subprocess.run(["python", os.path.join(base, "gen_fundamental.py")],
                               capture_output=True, timeout=60, cwd=base)
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write("\n[OK] fundamental_analysis.json regenerated\n")
            except Exception as _fe:
                with open(log_path, "a", encoding="utf-8") as logf:
                    logf.write(f"\n[WARN] gen_fundamental failed: {_fe}\n")
        except subprocess.TimeoutExpired:
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write("\n[TIMEOUT] Pipeline exceeded 10 minutes")
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"\n[ERROR] {e}")
    
    t = threading.Thread(target=run_pipeline_wrapper, daemon=True)
    t.start()
    msg = f"预测管道已启动，正在后台运行 run_all.py（{len(match_ids_arg)} 场），日志：data/pipeline_run.log"
    return jsonify({"ok": True, "msg": msg, "match_count": len(match_ids_arg)})
    

@bp.route('/api/dashboard/action/gen_featured', methods=['GET','POST'])
def action_gen_featured():
    import subprocess, threading

@bp.route("/api/dashboard/action/fetch_match_data", methods=["POST"])
def action_fetch_match_data():
    import flask, threading
    data = flask.request.get_json(force=True, silent=True)
    if not data or not data.get("match_ids"):
        return jsonify({"ok": False, "msg": "Missing match_ids"})
    match_ids = data["match_ids"]
    import json as _j, os as _os, sys as _sys
    _sys.path.insert(0, BASE)

    result_holder = {}

    def run_collection():
        from match_data_collector import collect_all
        try:
            res = collect_all(match_ids)
            result_holder["result"] = res
        except Exception as e:
            result_holder["error"] = str(e)

    thread = threading.Thread(target=run_collection, daemon=True)
    thread.start()
    thread.join(timeout=120)

    if "result" in result_holder:
        _console_log("获取比赛数据: 完成 " + str(len(result_holder["result"].get("results", {}))) + " 场")
        # Regenerate ai_judgment.json so pipeline steps have data for these matches
        try:
            import subprocess as _sp
            _sp.run(["python", _os.path.join(BASE, "gen_fundamental.py")],
                    capture_output=True, timeout=60, cwd=BASE)
            _console_log("自动重建: ai_judgment.json 完成")
        except Exception as _e:
            _console_log("自动重庺 ai_judgment 失败: " + str(_e))
        import json as _j2, os as _os2
        sel_path = _os2.path.join(BASE, "data", "selected_match_ids.json")
        with open(sel_path, "w", encoding="utf-8") as _sf:
            _j2.dump({"match_ids": match_ids, "updated": __import__("datetime").datetime.now().isoformat()}, _sf)
        return jsonify(result_holder["result"])
    elif "error" in result_holder:
        return jsonify({"ok": False, "msg": result_holder["error"]})
    else:
        return jsonify({"ok": True, "msg": "Collection still running in background", "match_ids": match_ids})
@bp.route("/api/dashboard/action/gen_plan", methods=["GET", "POST"])
def action_gen_plan():
    """Generate plan data and HTML page for today's matches."""
    import subprocess, os, json

    # Step 1: Run gen_plan.py
    try:
        result = subprocess.run(
            ["python", os.path.join(BASE, "gen_plan.py")],
            capture_output=True, text=True, timeout=120, cwd=BASE,
            encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            _console_log(f"\u751f\u6210\u8ba1\u5212\u5355: gen_plan.py failed (code {result.returncode})")
            return jsonify({"ok": False, "msg": f"gen_plan.py failed (code {result.returncode})"})
    except Exception as e:
        _console_log(f"\u751f\u6210\u8ba1\u5212\u5355: gen_plan.py exception: {e}")
        return jsonify({"ok": False, "msg": f"gen_plan.py exception: {e}"})

    # Step 2: Run gen_plan_html.py
    try:
        result2 = subprocess.run(
            ["python", os.path.join(BASE, "gen_plan_html.py")],
            capture_output=True, text=True, timeout=60, cwd=BASE,
            encoding="utf-8", errors="replace"
        )
        if result2.returncode != 0:
            _console_log(f"\u751f\u6210\u8ba1\u5212\u5355: gen_plan_html.py failed (code {result2.returncode})")
    except Exception as e:
        _console_log(f"\u751f\u6210\u8ba1\u5212\u5355: gen_plan_html.py exception: {e}")

    
    # Step 2.5: Run gen_featured.py + gen_featured_html.py (精选计划单跟随更新)
    try:
        result3 = subprocess.run(
            ["python", os.path.join(BASE, "gen_featured.py")],
            capture_output=True, text=True, timeout=60, cwd=BASE,
            encoding="utf-8", errors="replace"
        )
        if result3.returncode == 0:
            result4 = subprocess.run(
                ["python", os.path.join(BASE, "gen_featured_html.py")],
                capture_output=True, text=True, timeout=60, cwd=BASE,
                encoding="utf-8", errors="replace"
            )
            if result4.returncode != 0:
                _console_log("生成计划单: gen_featured_html.py failed")
        else:
            _console_log("生成计划单: gen_featured.py failed")
    except Exception as e:
        _console_log(f"生成计划单: gen_featured exception: {e}")

# Step 3: Count plans and identify predicting date groups
    plan_path = os.path.join(BASE, "data", "plan_data.json")
    mi_path = os.path.join(BASE, "data", "match_info.json")
    plan_count = 0
    predicting_dates = []

    # Build score lookup from match_info.json
    score_map = {}
    if os.path.exists(mi_path):
        with open(mi_path, "r", encoding="utf-8") as f:
            mi = json.load(f)
        for m in mi.get("matches", []):
            mid = m.get("id", "")
            sc = m.get("actual_score") or m.get("score") or ""
            score_map[mid] = sc

    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            pd = json.load(f)
        for g in pd.get("date_groups", []):
            g_plans = len(g.get("plan_2", [])) + len(g.get("plan_3", []))
            plan_count += g_plans
            # A date group is "predicting" if any of its match_ids has no score yet
            mids = g.get("match_ids", [])
            if mids and any(not score_map.get(mid, "") for mid in mids):
                predicting_dates.append(g["date"])

    msg = f"\u8ba1\u5212\u5355\u5df2\u66f4\u65b0 ({plan_count} \u65b9\u6848)"
    if predicting_dates:
        msg += ", \u5f53\u524d\u9884\u6d4b\u4e2d: " + ", ".join(predicting_dates)
    _console_log(f"\u751f\u6210\u8ba1\u5212\u5355: {msg}")
    return jsonify({"ok": True, "msg": msg, "plan_count": plan_count})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5021, debug=True, threaded=True, use_reloader=False)




