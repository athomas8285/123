import requests, json, os

url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=hhad,had,ttg,crs,hafu"

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.sporttery.cn/",
    "Origin": "https://www.sporttery.cn",
    "Connection": "keep-alive",
})
resp = s.get(url, timeout=15)
resp.raise_for_status()
data = resp.json()
s.close()

# Save to local data dir
script_dir = os.path.dirname(os.path.abspath(__file__))
local_dir = os.path.join(script_dir, "data")
os.makedirs(local_dir, exist_ok=True)
local_path = os.path.join(local_dir, "raw_jczq.json")
with open(local_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

matches = data["value"]["matchInfoList"]
print(f"{len(matches)} days, {sum(len(d.get('subMatchList',[])) for d in matches)} matches")
