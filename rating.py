# rating.py
# V3.3.3-Core-Rev1.13 Step 9: 推荐评级（S/A/B/C 输出 + ID排序版）
# P0-P4: 置信度/样本量感知优化

import json, os
from config import (
    DEEP_HANDICAP_THRESHOLD, MID_HANDICAP_MIN, MID_HANDICAP_MAX,
    MID_HANDICAP_LAMBDA_DIFF, FIT_SCORE_THRESHOLD_MELTDOWN, FIT_SCORE_THRESHOLD_BACKUP
)
from lambda_calc import _data_confidence_multiplier

HIGH_RISK_TYPES = ["解放者杯末轮", "附加赛", "南美杯末轮"]
HIGH_RISK_EVENTS = ["决赛", "半决赛"]


def calc_payout_rate(sp_home, sp_draw, sp_away):
    if not all([sp_home, sp_draw, sp_away]):
        return None
    implied_sum = 1/sp_home + 1/sp_draw + 1/sp_away
    return 1 / implied_sum


def _confidence_to_missing_count(match_data):
    """
    P0: 使用置信度字段计算数据缺失程度。
    返回等效的缺失计数，与旧版 xg_missing_count 逻辑兼容。
    """
    count = 0

    # xg_season: "infer" 等效于缺失
    season_conf = match_data.get("xg_season_confidence", "api")
    if season_conf == "infer":
        count += 1
    elif season_conf not in ("api", "calc"):
        # Fallback to old check
        if match_data.get("xg_season_missing", False):
            count += 1

    # away_xg: still a binary flag (no separate confidence field)
    if match_data.get("away_xg_missing", False):
        count += 1

    # xg_last3: "infer" 等效于缺失
    last3_conf = match_data.get("xg_last3_confidence", "calc")
    if last3_conf == "infer":
        count += 1
    elif last3_conf not in ("api", "calc"):
        if match_data.get("xg_last3_missing", False):
            count += 1

    return count


def _has_roster_data(match_data):
    """P0: Use roster_confidence field if available, else fallback to binary check."""
    if "roster_confidence" in match_data:
        return _data_confidence_multiplier(match_data.get("roster_confidence", "api")) >= 0.5
    return not match_data.get("roster_missing", False)


def classify_scenario(match_data, mc):
    event = match_data.get("event", "")
    match_type = match_data.get("match_type", "")

    sp_h = match_data.get("sp_home")
    sp_d = match_data.get("sp_draw")
    sp_a = match_data.get("sp_away")
    payout = calc_payout_rate(sp_h, sp_d, sp_a)

    if payout is not None and payout < 0.89:
        return "低返还率赛事", True

    xg_missing_count = _confidence_to_missing_count(match_data)

    if xg_missing_count >= 2:
        return "数据薄弱型", True

    is_high_risk_type = match_type in HIGH_RISK_TYPES
    is_playoff_or_friendly = match_type == "附加赛" or any(kw in event for kw in ["决赛"])

    if is_high_risk_type or is_playoff_or_friendly:
        has_roster = _has_roster_data(match_data)
        has_chaos_signal = (
            not has_roster or
            match_data.get("no_coach_statement", False) or
            "已出线" in match_data.get("home_motivation_type", "") or
            "已出线" in match_data.get("away_motivation_type", "") or
            "已降级" in match_data.get("home_motivation_type", "") or
            "已降级" in match_data.get("away_motivation_type", "") or
            "已夺冠" in match_data.get("home_motivation_type", "") or
            "已夺冠" in match_data.get("away_motivation_type", "")
        )
        if has_chaos_signal or xg_missing_count >= 1:
            return "混沌型", True
        else:
            return "轮换风险型", True

    return "稳定型", False


def is_high_risk(match_type, event):
    if match_type in HIGH_RISK_TYPES:
        return True
    for kw in HIGH_RISK_EVENTS:
        if kw in event:
            return True
    return False


def check_wind_control(asian_handicap, lambda_diff):
    downgrade = 0
    if abs(asian_handicap) >= DEEP_HANDICAP_THRESHOLD:
        downgrade += 1
    if (MID_HANDICAP_MIN <= abs(asian_handicap) <= MID_HANDICAP_MAX and abs(lambda_diff) < MID_HANDICAP_LAMBDA_DIFF):
        downgrade += 1
    return downgrade


def determine_direction(physical_prob, jc_handicap_prob, lambda_diff, sp_draw=None):
    xg_diff = abs(lambda_diff)
    if xg_diff < 0.2 and physical_prob.get("draw", 0) > 0:
        market_agrees_draw = sp_draw is not None and sp_draw < 3.20
        if not market_agrees_draw:
            home_share = 1.0
            away_share = 1.0
            total_prob = physical_prob["home_win"] + physical_prob["away_win"]
            if total_prob > 0:
                home_share = physical_prob["home_win"] / total_prob
                away_share = physical_prob["away_win"] / total_prob
            draw_reduction = physical_prob["draw"] * 0.3
            physical_prob["draw"] -= draw_reduction
            if home_share + away_share > 0:
                physical_prob["home_win"] += draw_reduction * (home_share / (home_share + away_share))
                physical_prob["away_win"] += draw_reduction * (away_share / (home_share + away_share))

    no_handicap = {"胜": physical_prob["home_win"], "平": physical_prob["draw"], "负": physical_prob["away_win"]}
    jc = {"让胜": jc_handicap_prob["rang_sheng"], "让平": jc_handicap_prob["rang_ping"], "让负": jc_handicap_prob["rang_fu"]}
    no_max_key = max(no_handicap, key=no_handicap.get)

    if max(jc.values()) > no_handicap[no_max_key]:
        direction = max(jc, key=jc.get)
    elif no_handicap[no_max_key] < 0.40:
        direction = "平"
    else:
        direction = no_max_key

    direction_warning = False
    if abs(lambda_diff) > 1.0:
        if direction in ["胜", "让胜"] and lambda_diff < -1.0:
            direction_warning = True
        elif direction in ["负", "让负"] and lambda_diff > 1.0:
            direction_warning = True

    return direction, direction_warning


def determine_rating(fit_final_total, downgrade_count, is_meltdown, match_type="", event="", scenario_high_risk=False):
    if is_meltdown:
        return "MELTDOWN"
    base = "BACKUP" if fit_final_total >= FIT_SCORE_THRESHOLD_BACKUP else "WATCH"
    if is_high_risk(match_type, event):
        if base == "BACKUP":
            base = "WATCH"
    if downgrade_count > 0 and base == "BACKUP":
        return "WATCH"
    return base


def get_rating_label(internal_rating, fit_score, scenario_type, direction_warning):
    """转换为 S/A/B/C 标签"""
    if internal_rating == "MELTDOWN":
        return "C"
    if internal_rating == "WATCH":
        return "B"
    # BACKUP 细分
    if fit_score >= 8.0 and scenario_type == "稳定型" and not direction_warning:
        return "S"
    else:
        return "A"


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    with open(os.path.join(data_dir, "match_info.json"), encoding="utf-8") as f:
        match_info = json.load(f)
    with open(os.path.join(data_dir, "monte_carlo_result.json"), encoding="utf-8") as f:
        mc_data = json.load(f)
    with open(os.path.join(data_dir, "fit_score_result.json"), encoding="utf-8") as f:
        fit_data = json.load(f)
    info_map = {m["id"]: m for m in match_info["matches"]}
    mc_map = {m["id"]: m for m in mc_data["matches"]}
    fit_map = {m["id"]: m for m in fit_data["matches"]}
    valid_ids = set(info_map.keys()) & set(mc_map.keys()) & set(fit_map.keys())

    results = []
    for mid in valid_ids:
        info, mc, fit = info_map[mid], mc_map[mid], fit_map[mid]["fit_score"]
        lambda_diff = info.get("lambda_diff", 0)
        sp_draw = info.get("sp_draw")

        scenario_type, scenario_high_risk = classify_scenario(info, mc)
        downgrade = check_wind_control(info.get("asian_handicap", 0), lambda_diff)

        physical_prob = mc["physical"].copy()
        jc_prob = mc["jc_handicap_prob"]
        direction, direction_warning = determine_direction(physical_prob, jc_prob, lambda_diff, sp_draw)

        internal_rating = determine_rating(
            fit["final_total"], downgrade, fit["meltdown"],
            info.get("match_type", ""), info.get("event", ""), scenario_high_risk
        )

        label = get_rating_label(internal_rating, fit["final_total"], scenario_type, direction_warning)

        results.append({
            "id": mid, "home": info["home"], "away": info["away"],
            "event": info["event"], "time": info["time"],
            "direction": direction, "fit_score": fit["final_total"],
            "rating": label,
            "downgrade_count": downgrade, "meltdown": fit["meltdown"],
            "scenario_type": scenario_type,
            "direction_warning": direction_warning
        })

        dg_str = f"DOWN{downgrade}" if downgrade > 0 else "OK"
        warn_str = " !" if direction_warning else ""
        print(f"  [{mid}] {direction:<6} fit={fit['final_total']:.1f} {dg_str} -> {label} [{scenario_type}]{warn_str}")

    # 按ID排序
    results.sort(key=lambda x: x['id'])

    # ==================== 终端汇总表（ID顺序·纯方向·S/A/B/C） ====================
    print(f"\n{'='*80}")
    print(f"  {'ID':<8}{'主队vs客队':<24}{'方向':<8}{'总进球':<12}{'半全场':<12}{'比分':<20}{'置信度':<8}{'评级':<6}")
    print(f"  {'-'*75}")

    for r in results:
        mid = r['id']
        vs = f"{r['home']} vs {r['away']}"
        direction = r['direction']
        fit = r['fit_score']
        label = r['rating']

        mc = mc_map.get(mid, {})
        total_goals = ", ".join(mc.get("top2_total_goals", ["-", "-"]))
        half_full = ", ".join(mc.get("top2_half_full", ["-", "-"]))
        scores = ", ".join(mc.get("top3_scores", ["-", "-", "-"]))

        display_id = "--" if label == "C" else mid

        print(f"  {display_id:<8}{vs:<24}{direction:<8}{total_goals:<12}{half_full:<12}{scores:<20}{fit:<8.1f}{label:<6}")

    print(f"{'='*80}")
    print(f"  评级标准：S=高置信备选 | A=备选 | B=关注 | C=熔断不推荐")
    print(f"{'='*80}")

    with open(os.path.join(data_dir, "rating_result.json"), "w", encoding="utf-8") as f:
        json.dump({"matches": results}, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] 推荐评级完成")


if __name__ == "__main__":
    print("=" * 55)
    print("  V3.3.3-Core-Rev1.13 Step 9: 推荐评级（S/A/B/C · ID排序版）")
    print("=" * 55)
    main()
