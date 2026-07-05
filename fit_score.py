
# fit_score.py
# V3.3.3-Core-Rev1.15 Step 8: fit score with trend support (8th dim)

import json, os
from config import FIT_SCORE_THRESHOLD_MELTDOWN, OPPONENT_PREDICTABILITY_MIN
from lambda_calc import _confidence_scale, detect_cross_tournament_xg, _data_confidence_multiplier

MAX_SCORE = 12.0
NORMALIZE = 10.0 / MAX_SCORE

_TREND_CACHE = None


def _load_trend_features():
    global _TREND_CACHE
    if _TREND_CACHE is not None:
        return _TREND_CACHE
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "trend_features.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            _TREND_CACHE = json.load(f)
        return _TREND_CACHE
    _TREND_CACHE = {}
    return _TREND_CACHE


def score_data_confidence(match_data):
    CONF_MAP = {"api": 1.0, "calc": 0.7, "infer": 0.3}
    score = 1.5
    has_conf = any(k in match_data for k in
                  ["h2h_confidence", "xg_last3_confidence",
                   "xg_season_confidence", "roster_confidence"])
    if has_conf:
        h2h = _data_confidence_multiplier(match_data.get("h2h_confidence", "api"))
        xg3 = _data_confidence_multiplier(match_data.get("xg_last3_confidence", "calc"))
        xgs = _data_confidence_multiplier(match_data.get("xg_season_confidence", "api"))
        rst = _data_confidence_multiplier(match_data.get("roster_confidence", "api"))
        score = 1.5 * (h2h + xg3 + xgs + rst) / 4.0
        if xgs < 0.5 and xg3 < 0.5:
            score *= 0.7
        score *= _confidence_scale(
            match_data.get("xg_home_sample", 0),
            match_data.get("xg_away_sample", 0),
            match_data.get("xg_last3_home_sample", 0),
            match_data.get("xg_last3_away_sample", 0))
        cp, _ = detect_cross_tournament_xg(
            match_data.get("xg_home_source_events", ""),
            match_data.get("xg_away_source_events", ""))
        score *= cp
    else:
        if match_data.get("h2h_missing", False): score -= 0.15
        if match_data.get("xg_last3_missing", False): score -= 0.4
        if match_data.get("xg_season_missing", False): score -= 0.25
        if match_data.get("xg_season_missing", False) and match_data.get("away_xg_missing", False):
            score -= 0.25
        if match_data.get("xg_last3_missing", False) and match_data.get("roster_missing", False):
            score = min(score, 0.75)
    return max(0, score)


def score_injury_reliability(match_data):
    score = 1.0
    if "injury_home_confidence" in match_data or "injury_away_confidence" in match_data:
        hc = _data_confidence_multiplier(match_data.get("injury_home_confidence", "api"))
        ac = _data_confidence_multiplier(match_data.get("injury_away_confidence", "api"))
        sc = _data_confidence_multiplier(match_data.get("injury_source_confidence", "calc"))
        score = 1.0 * (hc + ac) / 2.0 * sc
    else:
        if match_data.get("injury_home_missing", False): score -= 0.4
        if match_data.get("injury_away_missing", False): score -= 0.4
        if match_data.get("injury_source_unreliable", False): score -= 0.2
        if match_data.get("injury_home_missing", False) and match_data.get("injury_away_missing", False):
            score -= 0.15
    return max(0, score)


def score_motivation_clarity(match_data):
    score = 1.0
    if match_data.get("no_coach_statement", False): score -= 0.25
    if match_data.get("motivation_ambiguous", False): score -= 0.25
    if match_data.get("multi_team_linkage", False): score -= 0.2
    mt = match_data.get("match_type", "")
    if match_data.get("no_coach_statement", False) and mt in ["附加赛", "解放者杯末轮", "南美杯末轮"]:
        score -= 0.2
    return max(0, score)


def score_handicap_deviation(lambda_diff, asian_handicap):
    score = 2.0
    if lambda_diff > 1.5 and abs(asian_handicap) < 0.5: score -= 1.2
    elif lambda_diff < -0.15 and asian_handicap < 0: score -= 0.9
    elif abs(lambda_diff) < 0.5 and abs(asian_handicap) >= 1.0: score -= 0.9
    elif 0.5 <= abs(lambda_diff) < 1.0 and abs(asian_handicap) >= 1.5: score -= 0.6
    if abs(lambda_diff) > 1.0 and abs(asian_handicap) < 0.5: score -= 0.4
    xd = abs(lambda_diff)
    if xd < 0.1: score -= 1.0
    elif xd < 0.3: score -= 0.5
    elif xd < 0.5: score -= 0.2
    elif xd < 0.8: score -= 0.1
    elif xd > 2.0: score += 0.3
    elif xd > 1.2: score += 0.15
    return max(0, score)


def score_movement_match(handicap_change, physical_direction):
    score = 1.5
    if not isinstance(handicap_change, (int, float)):
        return score  # can't evaluate without numeric handicap_change
    if physical_direction == "away" and handicap_change > 0: score -= 0.4
    elif physical_direction == "home" and handicap_change < 0: score -= 0.4
    if abs(handicap_change or 0) >= 0.5: score -= 0.3
    return max(0, score)


def score_path_consistency(physical_prob, market_prob, sp_missing):
    score = 2.5
    if sp_missing: return max(0, min(score, 1.0))
    if market_prob.get("home_win", 0) == 0 and market_prob.get("away_win", 0) == 0:
        return max(0, min(score, 1.0))
    pd = max(physical_prob, key=physical_prob.get)
    md = max(market_prob, key=market_prob.get)
    if pd != md:
        score -= 1.0
        if abs(physical_prob[pd] - market_prob[md]) > 0.20: score -= 0.4
    else:
        if abs(physical_prob[pd] - market_prob[pd]) > 0.15: score -= 0.4
    return max(0, score)


def score_event_adaptability(match_data):
    score = 1.5
    event = match_data.get("event", "")
    hl = match_data.get("home_league", "")
    al = match_data.get("away_league", "")
    if any(kw in event for kw in ["决赛", "半决赛", "欧协", "欧冠", "欧联"]): score -= 0.5
    if any(kw in event for kw in ["解放者杯", "南美杯"]): score -= 0.5
    if hl != al: score -= 0.3
    return max(0, score)


def score_trend_support(match_data):
    """
    P0: trend support score (8th dimension)
    Reads trend_features.json, scores based on odds trend direction
    consistency with the prediction direction.
    -1.0 = strong contradiction, 0 = neutral/no data, +1.0 = strong support
    """
    td = _load_trend_features()
    if not td:
        return 0.0
    mid = match_data.get("id", "")
    if not mid:
        return 0.0
    mt = td.get("matches", {}).get(mid)
    if not mt:
        midx = td.get("match_num_index", {})
        oh_id = midx.get(mid)
        if oh_id:
            mt = td.get("matches", {}).get(oh_id)
    if not mt:
        home_n = match_data.get("home", "")
        away_n = match_data.get("away", "")
        for _mid, _mr in td.get("matches", {}).items():
            if _mr.get("home") == home_n and _mr.get("away") == away_n:
                mt = _mr
                break
        if not mt:
            return 0.0
    cb = mt.get("combined", {})
    if cb.get("change_count", 0) < 2:
        return 0.0
   
    direction = cb.get("direction", "stable")
    late_acc = cb.get("late_acceleration", False)
    ld = match_data.get("lambda_diff", 0)
    if ld > 0.3:
        pred_dir = "favors_home"
    elif ld < -0.3:
        pred_dir = "favors_away"
    else:
        pred_dir = "balanced"

    score = 0.0
    if pred_dir == "balanced":
        score = 0.1
    elif direction == "favors_home" and pred_dir == "favors_home":
        score = 0.5
    elif direction == "favors_away" and pred_dir == "favors_away":
        score = 0.5
    elif direction == "favors_home" and pred_dir == "favors_away":
        score = -0.3
    elif direction == "favors_away" and pred_dir == "favors_home":
        score = -0.3

    hhad = mt.get("hhad", {})
    if hhad:
        cons = hhad.get("consistency", 1.0)
        if cons > 0.85 and score > 0:
            score = min(score + 0.2, 1.0)
        elif cons < 0.6 and score < 0:
            score -= 0.2
    if late_acc:
        if score > 0:
            score = min(score + 0.3, 1.0)
        elif score < 0:
            score -= 0.2
        else:
            score = 0.2
    vel = abs(cb.get("h_velocity", 0))
    if vel > 0.1 and score > 0:
        score = min(score + 0.2, 1.0)
    elif vel > 0.15 and score < 0:
        score -= 0.2
    return round(max(-0.5, min(1.0, score)), 2)


def apply_veto_rules(scores, final_total):
    if scores.get("injury_confidence", 1.0) <= 0.3:
        final_total -= 0.3
    if scores.get("motivation_clarity", 1.0) <= 0.4:
        final_total -= 0.3
    if scores.get("event_fit", 1.0) <= 0.4:
        final_total -= 0.3
    return max(0, final_total)


def calc_fit_score(match_data, ddi_result, ai_judgment):
    sp_h = match_data.get("sp_home")
    sp_d = match_data.get("sp_draw")
    sp_a = match_data.get("sp_away")
    sp_missing = not all([sp_h, sp_d, sp_a])
    s1 = score_data_confidence(match_data)
    s2 = score_injury_reliability(match_data)
    s3 = score_motivation_clarity(match_data)
    s4 = score_handicap_deviation(match_data.get("lambda_diff", 0), match_data.get("asian_handicap", 0))
    s5 = score_movement_match(match_data.get("handicap_change", 0), match_data.get("physical_direction", "home"))
    s6 = score_path_consistency(ddi_result["p_physical"], ddi_result.get("p_market", {}), sp_missing)
    s_event = score_event_adaptability(match_data)
    s_trend = score_trend_support(match_data)
    s_ai = ai_judgment.get("s7_score", 0)
    mt = match_data.get("match_type", "")
    if mt in ["附加赛", "解放者杯末轮", "南美杯末轮"]:
        s_ai = max(s_ai, 0.5)
    oc = max(ai_judgment.get("opponent_predictability", 1.0), OPPONENT_PREDICTABILITY_MIN)
    raw = s1 + s2 + s3 + s4 + s5 + s6 + s_event + s_trend
    final = round((raw - s_ai) * oc * NORMALIZE, 2)
    final = apply_veto_rules({
        "injury_confidence": s2, "motivation_clarity": s3, "event_fit": s_event
    }, final)

    if final >= 8.0: level = "高贴合"
    elif final >= 6.0: level = "中等贴合"
    elif final >= 4.0: level = "低贴合"
    else: level = "低贴合熔断"
    return {
        "details": {
            "1_数据完整度": round(s1,1), "2_伤停确定度": round(s2,1),
            "3_战意清晰度": round(s3,1), "4_盘口偏离合理性": round(s4,1),
            "5_临场异动匹配度": round(s5,1), "6_物理市场一致性": round(s6,1),
            "7_赛事适配度": round(s_event,1), "8_趋势支持度": round(s_trend,1),
            "s7_心理扰动扣分": s_ai, "对手可预测性系数": oc
        },
        "raw_total": round(raw, 2), "final_total": final,
        "level": level, "meltdown": final < FIT_SCORE_THRESHOLD_MELTDOWN
    }


def main():
    sd = os.path.dirname(os.path.abspath(__file__))
    dd = os.path.join(sd, "data")
    with open(os.path.join(dd, "match_info.json"), encoding="utf-8") as f: mi = json.load(f)
    with open(os.path.join(dd, "ddi_result.json"), encoding="utf-8") as f: di = json.load(f)
    with open(os.path.join(dd, "ai_judgment.json"), encoding="utf-8") as f: ai = json.load(f)
    im = {m["id"]: m for m in mi["matches"]}
    dm = {m["id"]: m for m in di["matches"]}
    am = {m["id"]: m for m in ai["matches"]}
    all_ids = set(im.keys()) | set(dm.keys()) | set(am.keys())
    valid = set(im.keys()) & set(dm.keys()) & set(am.keys())
    dropped = all_ids - valid
    if dropped:
        print("  [WARN] {} matches dropped (incomplete): {}".format(len(dropped), sorted(dropped)))
    results = []
    for mid in valid:
        fit = calc_fit_score(im[mid], dm[mid], am[mid])
        results.append({"id": mid, "fit_score": fit})
        s = "MELTDOWN" if fit["meltdown"] else "PASS"
        print("  [{}] fit={} ({}) {}".format(mid, fit["final_total"], fit["level"], s))
    with open(os.path.join(dd, "fit_score_result.json"), "w", encoding="utf-8") as f:
        json.dump({"matches": results}, f, ensure_ascii=False, indent=2)
    print("")
    print("  [OK] fit score complete")


if __name__ == "__main__":
    print("=" * 55)
    print("  V3.3.3-Core-Rev1.15 Step 8: fit score + trend 8th dim")
    print("=" * 55)
    main()
