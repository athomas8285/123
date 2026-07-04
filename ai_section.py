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
                "temperature": 0.3
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
            search_queries = [
                home + " " + away + " 伤停 缺阵 2026世界杯",
                home + " " + away + " 出线形势 小组排名 2026世界杯",
                home + " " + away + " 赛前 动态 新闻",
            ]
            all_search_results = []
            for q in search_queries:
                snippets = _web_search(q)
                if snippets:
                    all_search_results.append("=== " + q + " ===" + chr(10) + chr(10).join(snippets[:3]))

            search_context = chr(10) + chr(10).join(all_search_results) if all_search_results else "（无搜索结果，请根据知识库作答）"

            prompt = _build_analysis_prompt(mid, home, away, home_form, away_form, jc_odds_info)
            full_prompt = prompt + chr(10) + chr(10) + "【网络搜索结果】" + chr(10) + search_context
            response = _deepseek_analyze(full_prompt)

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

