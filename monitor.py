"""
monitor.py - Auto match result monitor + sync

Checks 500.com every hour for new match results.
When new scores found: updates DB, match_info.json, rating_result.json, runs review.py.

Usage:
  python monitor.py              # Continuous hourly loop
  python monitor.py --once       # Single check
"""

import re, json, os, sys, time, sqlite3, urllib.request, subprocess
from datetime import datetime, timedelta

BASE = r"D:\V3.3.3-Core"
LOG_PATH = os.path.join(BASE, "data", "monitor.log")
CHECK_DAYS = 3

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    except:
        pass
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def fetch_500(date_str):
    """Fetch results from 500.com for a given date."""
    url = "https://zx.500.com/jczq/kaijiang.php?d=" + date_str
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("gbk", errors="ignore")
    except Exception as e:
        log("  [500.com] %s: %s" % (date_str, e))
        return []

    rows = re.findall(r"<tr[^>]*>.*?</tr>", html, re.DOTALL)
    results = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        cells = [c.replace("&nbsp;", "") for c in cells]
        if not cells:
            continue
        c0 = cells[0]
        # Match IDs look like: \u5468\u65e5\u0030\u0033\u0037 etc
        if not c0 or len(c0) < 3:
            continue
        if c0[0] != "\u5468":
            continue
        score_raw = cells[6] if len(cells) > 6 else ""
        m = re.search(r"\((\d+):(\d+)\)\s*(\d+):(\d+)", score_raw)
        if not m:
            continue
        results.append({
            "match_id": cells[0],
            "home": cells[3] if len(cells) > 3 else "",
            "away": cells[5] if len(cells) > 5 else "",
            "full_score": "%s:%s" % (m.group(3), m.group(4)),
            "half_score": "%s:%s" % (m.group(1), m.group(2)),
            "half_full": cells[17] if len(cells) > 17 and cells[17] else "",
        })
    return results

def update_db(results):
    """Write new scores to framework.db. Returns count of new entries."""
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
            log("  DB: %s %s vs %s  %s  half=%s" % (r["match_id"], r["home"], r["away"], r["full_score"], r["half_full"]))
    conn.commit()
    conn.close()
    return updated

def update_mi(results):
    """Update match_info.json with new scores."""
    mi_path = os.path.join(BASE, "data", "match_info.json")
    if not os.path.exists(mi_path):
        return 0
    with open(mi_path, "r", encoding="utf-8") as f:
        mi = json.load(f)
    updated = 0
    for m in mi.get("matches", []):
        for r in results:
            if r["match_id"] == m["id"] and r["full_score"] and not m.get("actual_score"):
                m["actual_score"] = r["full_score"]
                m["half_full"] = r["half_full"]
                updated += 1
                break
    if updated > 0:
        with open(mi_path, "w", encoding="utf-8") as f:
            json.dump(mi, f, ensure_ascii=False, indent=2)
        log("  match_info.json: %d updated" % updated)
    return updated

def sync_hit():
    """Update hit values in rating_result.json based on actual scores."""
    rr_path = os.path.join(BASE, "data", "rating_result.json")
    mi_path = os.path.join(BASE, "data", "match_info.json")
    if not os.path.exists(rr_path) or not os.path.exists(mi_path):
        return
    with open(rr_path, "r", encoding="utf-8") as f:
        rr = json.load(f)
    with open(mi_path, "r", encoding="utf-8") as f:
        mi = json.load(f)
    mi_map = {m["id"]: m for m in mi.get("matches", [])}
    updated = 0
    for item in rr.get("results", []):
        mid = item.get("match_id", "")
        if mid in mi_map:
            score = mi_map[mid].get("actual_score", "")
            direction = item.get("direction", "")
            if score and direction:
                parts = score.split(":")
                if len(parts) == 2:
                    try:
                        h, a = int(parts[0]), int(parts[1])
                        if direction == "\u80dc":
                            hit = h > a
                        elif direction == "\u8d1f":
                            hit = h < a
                        elif direction == "\u5e73":
                            hit = h == a
                        else:
                            continue
                        if item.get("hit") != hit:
                            item["hit"] = hit
                            updated += 1
                    except:
                        pass
    if updated > 0:
        with open(rr_path, "w", encoding="utf-8") as f:
            json.dump(rr, f, ensure_ascii=False, indent=2)
        log("  rating_result.json: %d hit updates" % updated)

def run_review():
    """Execute review.py if it exists."""
    review_path = os.path.join(BASE, "review.py")
    if not os.path.exists(review_path):
        return
    try:
        result = subprocess.run(
            ["python", review_path],
            cwd=BASE, capture_output=True, text=True, timeout=60
        )
        out = result.stdout.strip()
        if out:
            for line in out.split("\n")[-5:]:
                if line.strip():
                    log("  [review] " + line.strip()[:200])
        if result.stderr and "Traceback" in result.stderr:
            log("  [review] ERROR: " + result.stderr.strip()[-300:])
    except Exception as e:
        log("  [review] failed: " + str(e))

def check_now():
    """Check last CHECK_DAYS for new results."""
    log("=" * 50)
    log("Checking for new match results...")
    total = 0
    today = datetime.now()
    for i in range(CHECK_DAYS):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        results = fetch_500(date_str)
        if not results:
            continue
        log("  [%s] %d matches" % (date_str, len(results)))
        n = update_db(results)
        update_mi(results)
        total += n
    if total > 0:
        log("Total new scores: %d, syncing hits + running review..." % total)
        sync_hit()
        run_review()
    else:
        log("No new results found")
    log("Check complete\n")

def main():
    once = "--once" in sys.argv
    log("Monitor started")
    log("Source: 500.com, checking last %d days" % CHECK_DAYS)
    log("Mode: %s" % ("single run" if once else "hourly loop"))

    check_now()
    if once:
        return

    while True:
        time.sleep(3600)
        try:
            check_now()
        except Exception as e:
            log("Loop error: " + str(e))
            time.sleep(60)

if __name__ == "__main__":
    main()
