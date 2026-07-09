import re, json, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = SCRIPT_DIR


def fetch_results(date_str):
    """Fetch match results from 500.com for a given date (YYYY-MM-DD)."""
    import urllib.request
    
    url = f"https://zx.500.com/jczq/kaijiang.php?d={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN",
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("gbk", errors="ignore")
    except Exception as e:
        print(f"  Error: {e}")
        return []
    
    rows = re.findall(r"<tr[^>]*>.*?</tr>", html, re.DOTALL)
    results = []
    
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        cells = [c.replace("&nbsp;", "") for c in cells]
        if not cells or not cells[0].startswith(("周六", "周日", "周一", "周二", "周三", "周四", "周五")):
            continue
        
        match_id = cells[0]
        score_raw = cells[6] if len(cells) > 6 else ""
        score_match = re.search(r"\((\d+):(\d+)\)\s*(\d+):(\d+)", score_raw)
        
        if not score_match:
            continue
        
        result = {
            "match_id": match_id,
            "home": cells[3] if len(cells) > 3 else "",
            "full_score": f"{score_match.group(3)}:{score_match.group(4)}",
            "half_score": f"{score_match.group(1)}:{score_match.group(2)}",
        }
        
        result["away"] = cells[5] if len(cells) > 5 else ""
        
        # half_full: cells[17] (last data column)
        if len(cells) > 17 and cells[17]:
            result["half_full"] = cells[17]
        else:
            result["half_full"] = ""
        
        results.append(result)
    
    return results


def update_db(results):
    """Write results to framework.db and match_info.json."""
    import sqlite3
    
    db_path = os.path.join(BASE, "framework.db")
    conn = sqlite3.connect(db_path)
    updated = 0
    
    for r in results:
        if not r["full_score"]:
            continue
        cur = conn.execute(
            "UPDATE matches SET actual_score=?, half_full=? WHERE match_id=? AND (actual_score IS NULL OR actual_score='')",
            (r["full_score"], r["half_full"], r["match_id"])
        )
        if cur.rowcount > 0:
            updated += 1
            print(f"  DB: {r['match_id']} {r['home']} vs {r.get('away','?')}  score={r['full_score']}  half={r['half_full']}")
    
    conn.commit()

    # Auto-calculate hit for updated matches
    for r in results:
        if not r["full_score"] or ":" not in r["full_score"]:
            continue
        dr_row = conn.execute(
            "SELECT direction, jc_handicap FROM matches WHERE match_id=? AND (hit IS NULL OR hit='') LIMIT 1",
            (r["match_id"],)
        ).fetchone()
        if not dr_row or not dr_row[0]:
            continue
        dr = dr_row[0] or ""
        hcp = dr_row[1] or 0
        try:
            hg, ag = map(int, r["full_score"].split(":"))
            adj = hg + hcp - ag
            if dr == "让胜":   h = 1 if adj > 0 else 0
            elif dr == "让平": h = 1 if adj == 0 else 0
            elif dr == "让负": h = 1 if adj < 0 else 0
            elif dr == "胜":   h = 1 if hg > ag else 0
            elif dr == "负":   h = 1 if hg < ag else 0
            elif dr == "平":   h = 1 if hg == ag else 0
            else: h = None
            if h is not None:
                conn.execute("UPDATE matches SET hit=? WHERE match_id=?", (h, r["match_id"]))
                print(f"  hit: {r['match_id']} {'命中' if h else '未命中'}")
        except:
            pass

    conn.commit()
    conn.close()
    
    # Update match_info.json
    mi_path = os.path.join(BASE, "data", "match_info.json")
    with open(mi_path, "r", encoding="utf-8") as f:
        mi = json.load(f)
    
    updated_mi = 0
    for m in mi.get("matches", []):
        for r in results:
            if r["match_id"] == m["id"] and r["full_score"] and not m.get("actual_score"):
                m["actual_score"] = r["full_score"]
                m["half_full"] = r["half_full"]
                updated_mi += 1
                break
    
    if updated_mi > 0:
        with open(mi_path, "w", encoding="utf-8") as f:
            json.dump(mi, f, ensure_ascii=False, indent=2)
        print(f"  match_info.json: {updated_mi} scores added")
    
    return updated


if __name__ == "__main__":
    dates = sys.argv[1].split(",") if len(sys.argv) > 1 else []
    if not dates:
        print("Usage: python fetch_results.py YYYY-MM-DD[,YYYY-MM-DD]")
        sys.exit(1)
    
    for d in dates:
        d = d.strip()
        print(f"\n=== {d} ===")
        results = fetch_results(d)
        if not results:
            print("  No results")
            continue
        print(f"  Found {len(results)} matches")
        count = update_db(results)
        print(f"  DB updated: {count}")
