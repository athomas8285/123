
# V3.3.3-Core gen_fundamental.py
# Auto-generate fundamental analysis & update ai_judgment before pipeline

import json, sqlite3, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
DB_PATH = os.path.join(BASE, "framework.db")

def load_json(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, name):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_group_standings():
    """Calculate group standings from completed match results."""
    wc = load_json("wc_schedule.json")
    groups = wc.get("groups", {})
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get all completed matches with scores
    cur.execute("""
        SELECT DISTINCT match_id, home, away, actual_score, half_full 
        FROM matches 
        WHERE actual_score IS NOT NULL AND actual_score != ''
        ORDER BY match_id
    """)
    results = cur.fetchall()
    conn.close()
    
    # Build standings: {group: {team: {pts, gf, ga, gd, played, results}}}
    standings = {}
    team_group = {}
    for g, teams in groups.items():
        standings[g] = {}
        for t in teams:
            standings[g][t] = {"pts": 0, "gf": 0, "ga": 0, "gd": 0, "played": 0, "results": []}
            team_group[t] = g
    
    for r in results:
        home = r["home"]
        away = r["away"]
        score = r["actual_score"].replace(":", "-")
        try:
            hg, ag = map(int, score.split("-"))
        except:
            continue
        
        hg_name = find_team(home, team_group)
        ag_name = find_team(away, team_group)
        if not hg_name or not ag_name:
            continue
        
        hg_g = team_group[hg_name]
        ag_g = team_group[ag_name]
        
        # Update home team
        if hg_name in standings.get(hg_g, {}):
            s = standings[hg_g][hg_name]
            s["played"] += 1
            s["gf"] += hg
            s["ga"] += ag
            s["gd"] = s["gf"] - s["ga"]
            if hg > ag:
                s["pts"] += 3
                s["results"].append("W")
            elif hg == ag:
                s["pts"] += 1
                s["results"].append("D")
            else:
                s["results"].append("L")
        
        # Update away team
        if ag_name in standings.get(ag_g, {}):
            s = standings[ag_g][ag_name]
            s["played"] += 1
            s["gf"] += ag
            s["ga"] += hg
            s["gd"] = s["gf"] - s["ga"]
            if ag > hg:
                s["pts"] += 3
                s["results"].append("W")
            elif ag == hg:
                s["pts"] += 1
                s["results"].append("D")
            else:
                s["results"].append("L")
    
    return standings, team_group

def find_team(name, team_group):
    """Find team name in group mapping, handling name variations."""
    if name in team_group:
        return name
    # Try common variations
    for t in team_group:
        if name in t or t in name:
            return t
    return None

def get_recent_form(team, n=3):
    """Get recent N match results for a team."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT home, away, actual_score, direction FROM matches 
        WHERE (home=? OR away=?) AND actual_score IS NOT NULL AND actual_score != ''
        ORDER BY id DESC LIMIT ?
    """, (team, team, n))
    rows = cur.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        score = r["actual_score"].replace(":", "-")
        try:
            hg, ag = map(int, score.split("-"))
        except:
            continue
        if r["home"] == team:
            if hg > ag: results.append("W")
            elif hg == ag: results.append("D")
            else: results.append("L")
        else:
            if ag > hg: results.append("W")
            elif ag == hg: results.append("D")
            else: results.append("L")
    return results

def calc_motivation(team, group, standings, played_matches):
    """Determine team motivation based on group standings."""
    if group not in standings:
        return "unknown"
    
    s = standings[group].get(team)
    if not s or s["played"] == 0:
        return "unknown"
    
    # Sort standings
    ranked = sorted(standings[group].items(), key=lambda x: (-x[1]["pts"], -x[1]["gd"], -x[1]["gf"]))
    rank = next(i for i, (t, _) in enumerate(ranked) if t == team) + 1
    
    max_games = 3  # group stage
    remaining = max_games - s["played"]
    max_possible = s["pts"] + remaining * 3
    
    # Check if already qualified
    if rank <= 2 and remaining == 0:
        if s["pts"] > ranked[2][1]["pts"]:
            return "qualified"
    
    # Check if eliminated
    if remaining == 0 and rank > 2:
        if s["pts"] < ranked[1][1]["pts"]:
            return "eliminated"
    
    # Can still qualify
    if remaining > 0:
        third_max = ranked[2][1]["pts"] + (max_games - ranked[2][1]["played"]) * 3 if len(ranked) > 2 else 0
        if max_possible < third_max:
            return "eliminated"
    
    if remaining == 0 and rank <= 2:
        # Check if 3rd can catch up in last round
        if len(ranked) > 2:
            third_pts = ranked[2][1]["pts"]
            if s["pts"] > third_pts:
                return "qualified"
            elif s["pts"] == third_pts:
                return "qualified_gd"  # qualified but GD matters
    
    if remaining == 1:
        if rank <= 2:
            second_pts = ranked[1][1]["pts"] if len(ranked) > 1 else 0
            if s["pts"] - second_pts >= 3:
                return "qualified"
            elif s["pts"] - second_pts >= 1:
                return "draw_qualifies"
        if rank >= 3:
            second_pts = ranked[1][1]["pts"] if len(ranked) > 1 else 0
            if max_possible >= second_pts:
                return "must_win"
    
    return "normal"

def get_match_group(home, away, team_group):
    """Find which group a match belongs to."""
    hg = find_team(home, team_group)
    ag = find_team(away, team_group)
    if hg and ag and team_group.get(hg) == team_group.get(ag):
        return team_group[hg]
    return None

def generate(match_ids=None):
    """Main generation function."""
    print("=" * 55)
    print("  V3.3.3-Core gen_fundamental.py")
    print("=" * 55)
    
    # Load data
    standings, team_group = get_group_standings()
    match_info = load_json("match_info.json")
    rating = load_json("rating_result.json")
    ai_judgment = load_json("ai_judgment.json")
    
    mi_map = {m["id"]: m for m in match_info["matches"]}
    rr_map = {m["id"]: m for m in rating["matches"]}
    ai_map = {m["id"]: m for m in ai_judgment["matches"]}
    
    # Find matches to analyze: have direction but no actual_score
    targets = []
    for m in match_info["matches"]:
        mid = m["id"]
        if mid in rr_map:
            r = rr_map[mid]
            if r.get("direction"):  # include both predicting and completed matches
                targets.append(mid)
    
    if match_ids:
        targets = [m for m in targets if m in match_ids]
    
    print(f"Matches to analyze: {len(targets)}")
    
    fundamentals = []
    for mid in sorted(targets):
        mi = mi_map.get(mid, {})
        rr = rr_map.get(mid, {})
        ai = ai_map.get(mid, {})
        
        home = mi.get("home", "")
        away = mi.get("away", "")
        direction = rr.get("direction", "")
        rating_val = rr.get("rating", "")
        fit = rr.get("fit_score", 0)
        
        group = get_match_group(home, away, team_group)
        
        # Get SP odds
        sp_h = mi.get("sp_home") or mi.get("jc_sp_win")
        sp_d = mi.get("sp_draw") or mi.get("jc_sp_draw")
        sp_a = mi.get("sp_away") or mi.get("jc_sp_lose")
        
        # Data quality
        sp_missing = not all([sp_h, sp_d, sp_a])
        injury_missing = mi.get("injury_home_missing", True) or mi.get("injury_away_missing", True)
        form_missing = mi.get("xg_last3_missing", True)
        
        # Motivation
        h_motiv = calc_motivation(home, group, standings, []) if group else "unknown"
        a_motiv = calc_motivation(away, group, standings, []) if group else "unknown"
        
        # Recent form
        h_form = get_recent_form(home)
        a_form = get_recent_form(away)
        
        # === AI Judgment updates ===
        ai_entry = ai_map.get(mid, {
            "id": mid, "s7_score": 5.0, "s7_reason": "",
            "opponent_predictability": 0.5, "opponent_reason": "",
            "trap_analysis": "", "key_risk": ""
        })
        
        # s7_score: 0-10 based on data completeness and scenario clarity
        s7 = 5.0
        reasons = []
        
        if sp_missing:
            s7 -= 2.0
            reasons.append("SP\u7f3a\u5931")
        if injury_missing:
            s7 -= 1.0
            reasons.append("\u4f24\u505c\u4fe1\u606f\u7f3a\u5931")
        if form_missing:
            s7 -= 1.0
            reasons.append("\u8fd1\u671f\u6218\u7ee9\u6570\u636e\u7f3a\u5931")
        
        # Motivation bonus/penalty
        if h_motiv == "qualified" or a_motiv == "qualified":
            s7 -= 1.5
            reasons.append("\u5df2\u51fa\u7ebf\u7403\u961f\u53ef\u80fd\u8f6e\u6362")
        if h_motiv == "eliminated" or a_motiv == "eliminated":
            s7 -= 1.0
            reasons.append("\u5df2\u6dd8\u6c70\u7403\u961f\u6218\u610f\u4e0d\u660e")
        if h_motiv == "must_win" and a_motiv == "must_win":
            s7 += 1.0
            reasons.append("\u53cc\u65b9\u751f\u6b7b\u6218\u589e\u52a0\u4e0d\u786e\u5b9a\u6027")
        
        # Odds vs prediction consistency
        trap = "\u65e0\u660e\u663e\u8bf1\u76d8\u7279\u5f81\uff0c\u76d8\u53e3\u4e0e\u5b9e\u529b\u5339\u914d"
        risk = ""
        
        if direction and sp_h and sp_a:
            # Check if odds imply different direction than prediction
            if direction in ("\u8d1f", "\u8ba9\u8d1f") and sp_h and sp_a:
                if sp_h < sp_a:
                    trap = "\u76d8\u53e3\u770b\u597d\u4e3b\u961f\uff0c\u4f46\u7cfb\u7edf\u9884\u6d4b\u5ba2\u961f\u65b9\u5411\uff0c\u5b58\u5728\u5206\u6b67"
                    risk = "\u5e02\u573a\u4e0e\u6a21\u578b\u65b9\u5411\u5206\u6b67\uff0c\u8c28\u614e\u53c2\u8003"
            elif direction in ("\u80dc", "\u8ba9\u80dc") and sp_a and sp_h:
                if sp_a < sp_h:
                    trap = "\u76d8\u53e3\u770b\u597d\u5ba2\u961f\uff0c\u4f46\u7cfb\u7edf\u9884\u6d4b\u4e3b\u961f\u65b9\u5411\uff0c\u5b58\u5728\u5206\u6b67"
                    risk = "\u5e02\u573a\u4e0e\u6a21\u578b\u65b9\u5411\u5206\u6b67\uff0c\u8c28\u614e\u53c2\u8003"
        
        # Melting matches
        if rating_val == "C" or rr.get("meltdown"):
            risk = (risk + " " if risk else "") + "\u8d34\u5408\u5ea6\u4f4e\uff0c\u7194\u65ad\u8b66\u544a"
        
        ai_entry["s7_score"] = max(1.0, min(9.0, s7))
        ai_entry["s7_reason"] = "\uff1b".join(reasons) if reasons else "\u6570\u636e\u5b8c\u6574\uff0c\u573a\u666f\u6e05\u6670"
        ai_entry["trap_analysis"] = trap
        ai_entry["key_risk"] = risk or "\u6682\u65e0\u660e\u663e\u98ce\u9669\u70b9"
        
        # Store updated AI entry
        ai_map[mid] = ai_entry
        
        # === Narrative generation ===
        lines = []
        lines.append(f"{mid} {home} vs {away}")
        lines.append("")
        
        # Group standings
        if group and group in standings:
            lines.append("\u25cf \u5c0f\u7ec4\u5f62\u52bf")
            ranked = sorted(standings[group].items(), key=lambda x: (-x[1]["pts"], -x[1]["gd"], -x[1]["gf"]))
            parts = []
            for i, (t, s) in enumerate(ranked):
                parts.append(f"{i+1}.{t} {s['pts']}\u5206(GD{s['gd']:+d})")
            lines.append(f"{group}\u7ec4\u79ef\u5206\u699c: {' | '.join(parts)}")
            lines.append("")
        
        # Motivation
        lines.append("\u25cf \u6218\u610f\u80cc\u666f")
        motiv_labels = {
            "qualified": "\u5df2\u63d0\u524d\u51fa\u7ebf\uff0c\u53ef\u80fd\u8f6e\u6362",
            "eliminated": "\u5df2\u6dd8\u6c70\uff0c\u6218\u610f\u5b58\u7591",
            "must_win": "\u5fc5\u987b\u53d6\u80dc\u624d\u80fd\u51fa\u7ebf\uff0c\u751f\u6b7b\u6218",
            "draw_qualifies": "\u6253\u5e73\u5373\u51fa\u7ebf",
            "normal": "\u6b63\u5e38\u4e89\u593a\u51fa\u7ebf\u8d44\u683c",
            "unknown": "\u5c0f\u7ec4\u4fe1\u606f\u4e0d\u660e"
        }
        lines.append(f"{home}: {motiv_labels.get(h_motiv, h_motiv)}")
        lines.append(f"{away}: {motiv_labels.get(a_motiv, a_motiv)}")
        lines.append("")
        
        # Recent form
        lines.append("\u25cf \u8fd1\u671f\u6218\u7ee9")
        h_form_str = "".join(h_form) if h_form else "\u65e0\u6570\u636e"
        a_form_str = "".join(a_form) if a_form else "\u65e0\u6570\u636e"
        lines.append(f"{home}: \u8fd1{len(h_form)}\u573a {h_form_str}")
        lines.append(f"{away}: \u8fd1{len(a_form)}\u573a {a_form_str}")
        lines.append("")
        
        # Odds
        lines.append("\u25cf \u7ade\u5f69\u8d54\u7387")
        if sp_missing:
            lines.append("SP\u6570\u636e\u7f3a\u5931")
        else:
            lines.append(f"\u80dc: {sp_h} / \u5e73: {sp_d} / \u8d1f: {sp_a}")
        lines.append("")
        
        # System prediction
        lines.append("\u25cf \u7cfb\u7edf\u9884\u6d4b")
        lines.append(f"\u65b9\u5411: {direction or '\u65e0'}  \u8bc4\u7ea7: {rating_val or '\u65e0'}  \u8d34\u5408\u5ea6: {fit}")
        lines.append("")
        
        # Data quality
        lines.append("\u25cf \u6570\u636e\u8d28\u91cf")
        flags = []
        if sp_missing: flags.append("\u274c SP\u7f3a\u5931")
        else: flags.append("\u2705 SP\u5b8c\u6574")
        if injury_missing: flags.append("\u274c \u4f24\u505c\u4fe1\u606f\u7f3a\u5931")
        else: flags.append("\u2705 \u4f24\u505c\u5df2\u77e5")
        if form_missing: flags.append("\u274c \u8fd1\u671f\u6218\u7ee9\u7f3a\u5931")
        else: flags.append("\u2705 \u8fd1\u671f\u6218\u7ee9\u5df2\u77e5")
        lines.append(" | ".join(flags))
        
        narrative = "\n".join(lines)
        fundamentals.append({
            "id": mid,
            "home": home,
            "away": away,
            "narrative": narrative
        })
        
        print(f"  [{mid}] {home} vs {away} s7={ai_entry['s7_score']:.1f}")
    
    # Save ai_judgment.json
    ai_judgment["matches"] = list(ai_map.values())
    save_json(ai_judgment, "ai_judgment.json")
    print(f"\n  ai_judgment.json: {len(ai_judgment['matches'])} entries")
    
    # Save fundamental_analysis.json
    save_json(fundamentals, "fundamental_analysis.json")
    print(f"  fundamental_analysis.json: {len(fundamentals)} entries")
    
    print("\n  [OK] gen_fundamental complete")
    return fundamentals

if __name__ == "__main__":
    # Accept optional match_id filter
    target_ids = sys.argv[1:] if len(sys.argv) > 1 else None
    generate(target_ids)
