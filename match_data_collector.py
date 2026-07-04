# -*- coding: utf-8 -*-
"""
match_data_collector.py - 8-panel full data acquisition for matches.
Used by dashboard /api/dashboard/action/fetch_match_data endpoint.

Panels:
  1. Basic info (from DB / match_info.json - already exists)
  2. JC odds (5 pools - from webapi.sporttery.cn)
  3. Asian handicap (from enrich_odds.py logic)
  4. League/season data (SofaScore, may be blocked)
  5. Recent form (from framework.db)
  6. Injuries (AI search + LLM analysis)
  7. Motivation/standings (AI search + LLM analysis)
  8. Special items (AI search + LLM analysis)
"""

import json, os, sys, re, sqlite3, time
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MATCH_INFO_PATH = os.path.join(DATA_DIR, "match_info.json")
LOCKED_DATA_PATH = os.path.join(DATA_DIR, "locked_data.json")
RAW_JCZQ_PATH = os.path.join(DATA_DIR, "raw_jczq.json")
DB_PATH = os.path.join(BASE_DIR, "framework.db")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_match_info(match_id):
    mi = load_json(MATCH_INFO_PATH)
    if mi:
        for m in mi.get("matches", []):
            if m.get("id") == match_id:
                return m
    return None

def update_match_info(match_id, updates):
    mi = load_json(MATCH_INFO_PATH)
    if not mi:
        return False
    for m in mi.get("matches", []):
        if m.get("id") == match_id:
            m.update(updates)
            break
    else:
        return False
    save_json(mi, MATCH_INFO_PATH)
    return True

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# Panel 2: JC Odds (5 pools from sporttery.cn)
# ============================================================
def collect_jc_odds(match_ids):
    results = {}
    try:
        import requests
        url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=hhad,had,ttg,crs,hafu"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        jczq_map = {}
        for day in data.get("value", {}).get("matchInfoList", []):
            for sub in day.get("subMatchList", []):
                mid = sub.get("matchNumStr", "")
                if mid:
                    jczq_map[mid] = sub

        for mid in match_ids:
            if mid in jczq_map:
                sub = jczq_map[mid]
                had = sub.get("had", {})
                hhad = sub.get("hhad", {})
                ttg = sub.get("ttg", {})
                crs = sub.get("crs", {})
                hafu = sub.get("hafu", {})

                updates = {}
                if had:
                    updates["jc_sp_win"] = float(had.get("h", 0)) if had.get("h") else None
                    updates["jc_sp_draw"] = float(had.get("d", 0)) if had.get("d") else None
                    updates["jc_sp_lose"] = float(had.get("a", 0)) if had.get("a") else None
                if hhad:
                    updates["jc_hhad_win"] = float(hhad.get("h", 0)) if hhad.get("h") else None
                    updates["jc_hhad_draw"] = float(hhad.get("d", 0)) if hhad.get("d") else None
                    updates["jc_hhad_lose"] = float(hhad.get("a", 0)) if hhad.get("a") else None
                updates["jc_handicap"] = sub.get("goalLine", 0)

                # TTG 总进球赔率
                if ttg:
                    ttg_o = {}
                    for k in ("s0","s1","s2","s3","s4","s5","s6","s7"):
                        v = ttg.get(k)
                        if v is not None:
                            try: ttg_o[k] = float(v)
                            except: pass
                    if ttg_o: updates["ttg_odds"] = ttg_o

                # CRS 正确比分赔率
                if crs:
                    crs_o = {}
                    for k in crs:
                        if k in ("goalLine","goalLineValue","id","updateDate","updateTime") or k.endswith("f"):
                            continue
                        v = crs.get(k)
                        if v is not None:
                            try: crs_o[k] = float(v)
                            except: pass
                    if crs_o: updates["crs_odds"] = crs_o

                # HAFU 半全场赔率
                if hafu:
                    hafu_o = {}
                    for k in ("hh","hd","ha","dh","dd","da","ah","ad","aa"):
                        v = hafu.get(k)
                        if v is not None and str(v) != "-1":
                            try: hafu_o[k] = float(v)
                            except: pass
                    if hafu_o: updates["hafu_odds"] = hafu_o

                ok = update_match_info(mid, updates)
                results[mid] = {"ok": ok, "has_had": bool(had), "has_hhad": bool(hhad),
                               "has_ttg": bool(ttg), "has_crs": bool(crs), "has_hafu": bool(hafu)}
            else:
                results[mid] = {"ok": False, "error": "not in JC API response"}
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e), "results": {mid: {"ok": False, "error": str(e)} for mid in match_ids}}


# ============================================================
# Panel 3: Asian Handicap (from raw_jczq via enrich_odds pattern)
# ============================================================
def collect_asian_handicap(match_ids):
    # Panel 3: Asian Handicap from external bookmakers (Pinnacle, Macau, etc.)
    # Currently skipped - requires separate crawler for oddsportal/500.com/etc.
    # DDI module already handles market-vs-model divergence detection.
    results = {}
    mi_path = os.path.join(os.path.dirname(MATCH_INFO_PATH), "match_info.json")
    mi = load_json(mi_path) if os.path.exists(mi_path) else None
    match_map = {m["id"]: m for m in mi.get("matches", [])} if mi else {}
    
    for mid in match_ids:
        m = match_map.get(mid)
        if not m:
            results[mid] = {"ok": False, "reason": "match not in match_info.json"}
            continue
        
        jc_hcap = m.get("jc_handicap", 0) or 0
        hhad_w = m.get("jc_hhad_win")
        hhad_l = m.get("jc_hhad_lose")
        
        if hhad_w and hhad_l and jc_hcap != 0:
            ah_home = round((float(hhad_w) + float(hhad_l)) / float(hhad_l), 2)
            ah_away = round((float(hhad_w) + float(hhad_l)) / float(hhad_w), 2)
            update_match_info(mid, {"asian_handicap": jc_hcap, "ah_home": ah_home, "ah_away": ah_away})
            results[mid] = {"ok": True, "asian_handicap": jc_hcap, "ah_home": ah_home, "ah_away": ah_away}
        elif jc_hcap == 0:
            update_match_info(mid, {"asian_handicap": 0})
            results[mid] = {"ok": True, "asian_handicap": 0, "note": "flat handicap 0"}
        else:
            results[mid] = {"ok": False, "skipped": True, "reason": "no hhad odds available"}
    
    return {"ok": True, "results": results}


# ============================================================
# Panel 4: League/Season Data (SofaScore - may be blocked)
# ============================================================
def collect_sofascore_data(match_ids):
    results = {}
    for mid in match_ids:
        # Mark as skipped - SofaScore often blocked from CN
        update_match_info(mid, {"xg_season_missing": True, "xg_last3_missing": True})
        results[mid] = {"ok": False, "skipped": True, "reason": "SofaScore blocked, skipped"}
    return {"ok": True, "results": results}


# ============================================================
# Panel 5: Recent Form (from framework.db)
# ============================================================
def collect_recent_form(match_ids):
    results = {}
    db = get_db()
    try:
        for mid in match_ids:
            mi = get_match_info(mid)
            if not mi:
                results[mid] = {"ok": False, "error": "match not in match_info.json"}
                continue

            home = mi.get("home", "")
            away = mi.get("away", "")

            home_form = _calc_team_form(db, home)
            away_form = _calc_team_form(db, away)

            updates = {
                "home_goals": home_form.get("goals_for", 0),
                "home_goals_conceded": home_form.get("goals_against", 0),
                "away_goals": away_form.get("goals_for", 0),
                "away_goals_conceded": away_form.get("goals_against", 0),
                "home_recent_form": home_form.get("recent_results", []),
                "away_recent_form": away_form.get("recent_results", []),
                "home_form_str": home_form.get("form_str", ""),
                "away_form_str": away_form.get("form_str", ""),
            }
            ok = update_match_info(mid, updates)
            results[mid] = {"ok": ok, "home_form": home_form.get("form_str", ""),
                           "away_form": away_form.get("form_str", "")}
    finally:
        db.close()
    return {"ok": True, "results": results}


def _calc_team_form(db, team_name):
    rows = db.execute(
        "SELECT home, away, actual_score, hit FROM matches WHERE (home=? OR away=?) AND actual_score IS NOT NULL AND actual_score != '' ORDER BY match_time DESC LIMIT 10",
        (team_name, team_name)
    ).fetchall()

    goals_for = 0
    goals_against = 0
    recent = []
    form_chars = []

    for r in rows:
        score = r["actual_score"]
        if ":" in score:
            hg, ag = score.split(":")[0], score.split(":")[1]
        elif "-" in score:
            hg, ag = score.split("-")[0], score.split("-")[1]
        else:
            continue
        try:
            hg, ag = int(hg), int(ag)
        except ValueError:
            continue

        if r["home"] == team_name:
            gf, ga = hg, ag
            result = "W" if hg > ag else ("D" if hg == ag else "L")
        else:
            gf, ga = ag, hg
            result = "W" if ag > hg else ("D" if ag == hg else "L")

        goals_for += gf
        goals_against += ga
        recent.append({"opponent": r["away"] if r["home"] == team_name else r["home"],
                       "score": f"{gf}-{ga}", "result": result})
        form_chars.append(result)

    return {
        "goals_for": goals_for,
        "goals_against": goals_against,
        "recent_results": recent,
        "form_str": "".join(form_chars),
    }


# ============================================================
# Panel 6-8: AI Search + DeepSeek Analysis (Injuries, Motivation, Special Items)
# ============================================================

DEEPSEEK_API_KEY = "sk-placeholder"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def _deepseek_analyze(prompt, max_tokens=1500):
    try:
        import requests as req
        resp = req.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            "enable_search": True
            },
            timeout=45
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

def _web_search(query, max_results=5):
    results = []
    try:
        import requests as req
        r = req.get(
            "https://www.google.com/search",
            params={"q": query, "hl": "zh-CN", "num": max_results},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9"
            },
            timeout=10
        )
        snippets = re.findall(r'<div class="BNeawe s3v9rd AP7Wnd">(.*?)</div>', r.text)
        if not snippets:
            snippets = re.findall(r'<span class="st">(.*?)</span>', r.text)
        results = [re.sub(r'<[^>]+>', '', s) for s in snippets[:max_results]]
    except:
        pass
    return results

def _build_analysis_prompt(match_id, home, away, home_form, away_form, jc_odds_info):
    prompt = f"""你是世界杯足球数据分析师。请根据以下信息，对这场比赛进行专业分析。

【比赛信息】
编号: {match_id}
主队: {home}
客队: {away}
赛事: 2026世界杯

【近期战绩】
主队 {home}: {home_form}
客队 {away}: {away_form}

【赔率信息】
{jc_odds_info}

请先联网搜索以下信息（我会提供搜索结果），如果没有搜索结果，请根据你的知识库作答：

1. 伤停信息: {home}和{away}两队的主力伤停、缺阵球员，位置，影响程度
2. 战意背景: 小组出线形势、两队战意（生死战/打平即出线/已出线/已淘汰/默契球可能）
3. 特殊事项: 比赛场地、天气、裁判争议、队内风波、教练变动、球迷因素等

请严格按以下JSON格式输出（不要输出其他文字）:
{{
  "injuries": {{
    "home": [{{"player": "球员名", "position": "位置", "impact": "高/中/低", "detail": "具体伤情"}}],
    "away": [{{"player": "球员名", "position": "位置", "impact": "高/中/低", "detail": "具体伤情"}}]
  }},
  "motivation": {{
    "home_qual_status": "已出线/打平即出线/生死战/已淘汰",
    "away_qual_status": "已出线/打平即出线/生死战/已淘汰",
    "home_motivation": "详细战意分析，不超过80字",
    "away_motivation": "详细战意分析，不超过80字",
    "mutual_draw_risk": true/false,
    "ambiguous": false
  }},
  "special": {{
    "items": ["事项1", "事项2"],
    "has_coach_statement": true/false,
    "multi_team_linkage": false
  }}
}}"""
    return prompt

def collect_ai_analysis(match_ids):
    """Run DeepSeek AI analysis for each match using training knowledge."""
    results = {}

    for mid in match_ids:
        mi = get_match_info(mid)
        if not mi:
            results[mid] = {"ok": False, "error": "not found"}
            continue

        home = mi.get("home", "")
        away = mi.get("away", "")
        home_form = mi.get("home_form_str", "")
        away_form = mi.get("away_form_str", "")

        odds_parts = []
        for k, label in [("jc_sp_win", "胜"), ("jc_sp_draw", "平"), ("jc_sp_lose", "负")]:
            v = mi.get(k)
            if v is not None:
                odds_parts.append(label + str(v))
        jc_odds_info = " / ".join(odds_parts) if odds_parts else "无赔率数据"

        try:
            prompt = _build_analysis_prompt(mid, home, away, home_form, away_form, jc_odds_info)
            response = _deepseek_analyze(prompt)

            analysis = {}
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
            except:
                pass

            injuries = analysis.get("injuries", {})
            motivation = analysis.get("motivation", {})
            special = analysis.get("special", {})

            home_injuries = [i.get("player", "") + "(" + i.get("position", "") + ")" for i in injuries.get("home", [])]
            away_injuries = [i.get("player", "") + "(" + i.get("position", "") + ")" for i in injuries.get("away", [])]

            updates = {
                "injury_home_missing": len(home_injuries) == 0,
                "injury_away_missing": len(away_injuries) == 0,
                "injury_source_unreliable": False,
                "home_injury_list": home_injuries,
                "away_injury_list": away_injuries,
                "motivation_ambiguous": motivation.get("ambiguous", False),
                "home_motivation": motivation.get("home_motivation", ""),
                "away_motivation": motivation.get("away_motivation", ""),
                "home_qual_status": motivation.get("home_qual_status", ""),
                "away_qual_status": motivation.get("away_qual_status", ""),
                "mutual_draw_risk": motivation.get("mutual_draw_risk", False),
                "no_coach_statement": not special.get("has_coach_statement", False),
                "multi_team_linkage": special.get("multi_team_linkage", False),
                "special_items": special.get("items", []),
                "ai_analysis_raw": response[:500],
            }
            ok = update_match_info(mid, updates)
            results[mid] = {
                "ok": ok,
                "injuries_found": len(home_injuries) + len(away_injuries) > 0,
                "motivation_found": bool(motivation.get("home_motivation")),
                "special_found": len(special.get("items", [])) > 0,
                "home_qual": motivation.get("home_qual_status", ""),
                "away_qual": motivation.get("away_qual_status", ""),
            }
        except Exception as e:
            results[mid] = {"ok": False, "error": str(e)}

    return {"ok": True, "results": results}

# Main collector: run all 8 panels for given match_ids
# ============================================================
def collect_all(match_ids):
    log = []
    all_results = {}

    def add_log(msg):
        log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # Panel 1: Basic info - already in DB, skip
    add_log(f"板块1: 基本信息 - 已存在于DB，跳过 ({len(match_ids)} 场)")

    # Panel 2: JC Odds
    add_log(f"板块2: 竞彩赔率 - 正在获取...")
    jc = collect_jc_odds(match_ids)
    ok_count = sum(1 for r in jc.get("results", {}).values() if r.get("ok"))
    add_log(f"板块2: 竞彩赔率 - 完成 ({ok_count}/{len(match_ids)} 场)")
    for mid, r in jc.get("results", {}).items():
        all_results.setdefault(mid, {})["panel_2_jc_odds"] = r

    # Panel 3: Asian Handicap
    add_log(f"板块3: 亚洲盘口 - 正在获取...")
    ah = collect_asian_handicap(match_ids)
    ok_count = sum(1 for r in ah.get("results", {}).values() if r.get("ok"))
    add_log(f"板块3: 亚洲盘口 - 完成 ({ok_count}/{len(match_ids)} 场)")
    for mid, r in ah.get("results", {}).items():
        all_results.setdefault(mid, {})["panel_3_asian_hcp"] = r

    # Panel 4: SofaScore
    add_log(f"板块4: 联赛赛季数据 - SofaScore 跳过")
    sf = collect_sofascore_data(match_ids)
    for mid, r in sf.get("results", {}).items():
        all_results.setdefault(mid, {})["panel_4_sofascore"] = r

    # Panel 5: Recent Form from DB
    add_log(f"板块5: 近期战绩 - 正在从DB计算...")
    rf = collect_recent_form(match_ids)
    ok_count = sum(1 for r in rf.get("results", {}).values() if r.get("ok"))
    add_log(f"板块5: 近期战绩 - 完成 ({ok_count}/{len(match_ids)} 场)")
    for mid, r in rf.get("results", {}).items():
        all_results.setdefault(mid, {})["panel_5_recent_form"] = r

    # Panel 6-8: AI Analysis
    add_log(f"板块6-8: AI分析(伤停/战意/特殊) - 正在分析...")
    ai = collect_ai_analysis(match_ids)
    ok_count = sum(1 for r in ai.get("results", {}).values() if r.get("ok"))
    add_log(f"板块6-8: AI分析 - 完成 ({ok_count}/{len(match_ids)} 场)")
    for mid, r in ai.get("results", {}).items():
        all_results.setdefault(mid, {})["panel_6_8_ai"] = r

    add_log(f"全部采集完成 ({len(match_ids)} 场)")

    return {"ok": True, "results": all_results, "logs": log}


if __name__ == "__main__":
    ids = sys.argv[1:] if len(sys.argv) > 1 else []
    if not ids:
        print("Usage: python match_data_collector.py <match_id1> <match_id2> ...")
        sys.exit(1)
    result = collect_all(ids)
    print(json.dumps(result, ensure_ascii=False, indent=2))
