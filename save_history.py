# save_history.py
# V3.3.3-Core-Rev1.13-P0-P4: 历史数据归档（含置信度/样本量字段）

import json, os, csv

HISTORY_FILE = "history.csv"
COLUMNS = [
    "id", "date", "event", "home", "away", "league_home", "league_away",
    "sp_home", "sp_draw", "sp_away", "jc_handicap", "asian_handicap",
    "lambda_raw_h", "lambda_raw_a", "injury_home", "injury_away",
    "motivation_home", "motivation_away", "pressure_triggered", "slack_triggered",
    "altitude_bonus", "lambda_final_h", "lambda_final_a",
    "prob_home", "prob_draw", "prob_away", "ddi_home", "ddi_draw", "ddi_away",
    "cold_treatment", "direction", "fit_score", "s7_score", "opponent_predictability", "rating",
    # P0: 置信度字段
    "h2h_confidence", "xg_last3_confidence", "xg_season_confidence",
    "roster_confidence", "injury_home_confidence", "injury_away_confidence",
    "injury_source_confidence", "motivation_confidence",
    # P1: 样本量字段
    "xg_home_sample", "xg_away_sample", "xg_last3_home_sample", "xg_last3_away_sample",
    # P2: 跨赛事检测字段
    "xg_home_source_events", "xg_away_source_events",
    "trap_analysis", "key_risk", "actual_score", "hit", "diagnosis", "actual_ht"
]


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    locked = json.load(open(os.path.join(data_dir, "locked_data.json"), encoding="utf-8"))
    factors = json.load(open(os.path.join(data_dir, "factor_params.json"), encoding="utf-8"))
    mc = json.load(open(os.path.join(data_dir, "monte_carlo_result.json"), encoding="utf-8"))
    ddi_res = json.load(open(os.path.join(data_dir, "ddi_result.json"), encoding="utf-8"))
    fit_res = json.load(open(os.path.join(data_dir, "fit_score_result.json"), encoding="utf-8"))
    rating_res = json.load(open(os.path.join(data_dir, "rating_result.json"), encoding="utf-8"))
    ai = json.load(open(os.path.join(data_dir, "ai_judgment.json"), encoding="utf-8"))
    match_info = json.load(open(os.path.join(data_dir, "match_info.json"), encoding="utf-8"))
    factor_map = {m["id"]: m for m in factors["matches"]}
    mc_map = {m["id"]: m for m in mc["matches"]}
    ddi_map = {m["id"]: m for m in ddi_res["matches"]}
    fit_map = {m["id"]: m for m in fit_res["matches"]}
    rating_map = {m["id"]: m for m in rating_res["matches"]}
    ai_map = {m["id"]: m for m in ai["matches"]}
    info_map = {m["id"]: m for m in match_info["matches"]}
    valid_ids = set(factor_map.keys()) & set(mc_map.keys()) & set(ddi_map.keys()) & set(fit_map.keys()) & set(rating_map.keys()) & set(ai_map.keys())
    history_path = os.path.join(script_dir, HISTORY_FILE)
    existing = []
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8-sig") as f:
            existing = list(csv.DictReader(f))
    existing_keys = {(r["id"], r["date"], r["home"], r["away"]): i for i, r in enumerate(existing)}
    new_rows = []
    for match in locked["matches"]:
        mid = match["id"]
        if mid not in valid_ids:
            continue
        fac = factor_map[mid]
        mc_data = mc_map[mid]
        ddi_data = ddi_map[mid]
        fit_data = fit_map[mid]["fit_score"]
        rat_data = rating_map[mid]
        ai_data = ai_map[mid]
        info = info_map.get(mid, {})
        injury_home = fac.get("injury_home", 0) + fac.get("injury_home_boost", 0)
        injury_away = fac.get("injury_away", 0) + fac.get("injury_away_boost", 0)
        row = {
            "id": mid, "date": match.get("time", ""), "event": match.get("event", ""),
            "home": match["home"], "away": match["away"],
            "league_home": match.get("home_league", ""), "league_away": match.get("away_league", ""),
            "sp_home": match.get("sp_home", ""), "sp_draw": match.get("sp_draw", ""), "sp_away": match.get("sp_away", ""),
            "jc_handicap": match.get("jc_handicap", 0), "asian_handicap": match.get("asian_handicap", 0),
            "lambda_raw_h": mc_data.get("lambda_raw_h", ""), "lambda_raw_a": mc_data.get("lambda_raw_a", ""),
            "injury_home": injury_home, "injury_away": injury_away,
            "motivation_home": fac.get("motivation_home", 0), "motivation_away": fac.get("motivation_away", 0),
            "pressure_triggered": fac.get("pressure_home", False) or fac.get("pressure_away", False),
            "slack_triggered": fac.get("slack_home", False) or fac.get("slack_away", False),
            "altitude_bonus": fac.get("altitude_home", 0) + fac.get("altitude_away", 0),
            "lambda_final_h": mc_data.get("lambda_h_final", ""), "lambda_final_a": mc_data.get("lambda_a_final", ""),
            "prob_home": mc_data["physical"]["home_win"], "prob_draw": mc_data["physical"]["draw"], "prob_away": mc_data["physical"]["away_win"],
            "ddi_home": ddi_data["ddi"]["home_win"], "ddi_draw": ddi_data["ddi"]["draw"], "ddi_away": ddi_data["ddi"]["away_win"],
            "cold_treatment": not ddi_data.get("sp_missing", True),
            "direction": rat_data["direction"], "fit_score": fit_data["final_total"], "s7_score": ai_data["s7_score"], "opponent_predictability": ai_data["opponent_predictability"], "rating": rat_data["rating"],
            # P0: 置信度字段
            "h2h_confidence": info.get("h2h_confidence", ""),
            "xg_last3_confidence": info.get("xg_last3_confidence", ""),
            "xg_season_confidence": info.get("xg_season_confidence", ""),
            "roster_confidence": info.get("roster_confidence", ""),
            "injury_home_confidence": info.get("injury_home_confidence", ""),
            "injury_away_confidence": info.get("injury_away_confidence", ""),
            "injury_source_confidence": info.get("injury_source_confidence", ""),
            "motivation_confidence": info.get("motivation_confidence", ""),
            # P1: 样本量字段
            "xg_home_sample": info.get("xg_home_sample", ""),
            "xg_away_sample": info.get("xg_away_sample", ""),
            "xg_last3_home_sample": info.get("xg_last3_home_sample", ""),
            "xg_last3_away_sample": info.get("xg_last3_away_sample", ""),
            # P2: 跨赛事检测字段
            "xg_home_source_events": info.get("xg_home_source_events", ""),
            "xg_away_source_events": info.get("xg_away_source_events", ""),
            "trap_analysis": ai_data["trap_analysis"], "key_risk": ai_data["key_risk"],
            "actual_score": "", "hit": "", "diagnosis": ""
        }
        key = (row["id"], row["date"], row["home"], row["away"])
        if key in existing_keys:
            existing[existing_keys[key]] = row
        else:
            new_rows.append(row)
    all_rows = existing + new_rows
    with open(history_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"  [OK] 历史数据已保存，总记录数：{len(all_rows)}")


if __name__ == "__main__":
    print("=" * 55)
    print("  V3.3.3-Core-Rev1.13-P0-P4 历史数据归档")
    print("=" * 55)
    main()
