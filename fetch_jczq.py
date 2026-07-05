import requests, json, os

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.sporttery.cn/",
}
url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=hhad,had,ttg,crs,hafu"
resp = requests.get(url, headers=headers, timeout=15)
data = resp.json()

# Save to desktop path
desktop_path = r"C:\Users\gjj\Desktop\v333\data\raw_jczq.json"
os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
with open(desktop_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Save to local data dir
script_dir = os.path.dirname(os.path.abspath(__file__))
local_dir = os.path.join(script_dir, "data")
os.makedirs(local_dir, exist_ok=True)
local_path = os.path.join(local_dir, "raw_jczq.json")
with open(local_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

matches = data["value"]["matchInfoList"]
print(f"共 {len(matches)} 个比赛日\n")

for day in matches:
    date = day["businessDate"]
    subs = day["subMatchList"]
    print(f"=== {date} ({len(subs)} 场比赛) ===\n")

    for m in subs:
        num = m.get("matchNumStr", "?")
        league = m.get("leagueAllName", "")
        dt = m.get("matchDate", "") + " " + m.get("matchTime", "")
        home = m.get("homeTeamAllName", "")
        away = m.get("awayTeamAllName", "")
        goal = m.get("goalLine", 0)

        had = m.get("had", {})
        h_h = str(had.get("h", "-"))
        h_d = str(had.get("d", "-"))
        h_a = str(had.get("a", "-"))

        hhad = m.get("hhad", {})
        hh_h = str(hhad.get("h", "-"))
        hh_d = str(hhad.get("d", "-"))
        hh_a = str(hhad.get("a", "-"))

        gl = f"{goal:+d}" if goal != 0 else "0"

        # Row 1: standard SP
        row1 = f"{num:<10} {league:<10} {dt:<14} {home:<8} vs {away:<8}  0    {h_h:>6} / {h_d:>6} / {h_a:>6}"
        print(row1)
        # Row 2: handicap SP
        row2 = f"          {'':<10} {'':<14} {'':<8}  {'':<8}  {gl:>4}  {hh_h:>6} / {hh_d:>6} / {hh_a:>6}"
        print(row2)
        print()
