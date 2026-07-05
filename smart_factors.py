# smart_factors.py

# V3.3.3-Core-Rev1.15 因子参数 + AI 判断智能生成器

# 读取 locked_data.json → 自动生成 factor_params.json + ai_judgment.json

# 用法: python smart_factors.py [locked_data路径]


import json, os, sys, re

from config import INJURY_CORE_MAX, MOTIVATION_CAP_PLAYOFF, MOTIVATION_CAP_REGULAR, OPPONENT_PREDICTABILITY_MIN


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================

# 知识库：球队档次（用于判断战意基线）

# tier 0 = 争冠/欧冠级别, tier 4 = 保级队

# ============================================================

TEAM_TIERS = {

    # 英超

    "曼城": 0, "阿森纳": 0, "利物浦": 0,

    "曼联": 1, "切尔西": 1, "热刺": 1, "纽卡斯尔联": 1,

    "阿斯顿维拉": 1, "托特纳姆热刺": 1,

    "布莱顿": 2, "西汉姆联": 2, "富勒姆": 2, "水晶宫": 2,

    "布伦特福德": 2, "狼队": 2, "伯恩茅斯": 2,

    "诺丁汉森林": 3, "埃弗顿": 2, "利兹联": 3,

    "桑德兰": 3, "伯恩利": 3, "莱斯特城": 2,

    # 西甲

    "皇家马德里": 0, "巴塞罗那": 0, "马德里竞技": 0,

    "皇家社会": 1, "皇家贝蒂斯": 1, "毕尔巴鄂竞技": 1, "比利亚雷亚尔": 1,

    "塞维利亚": 2, "巴伦西亚": 2,

    # 德甲

    "拜仁慕尼黑": 0, "多特蒙德": 1, "RB莱比锡": 1, "勒沃库森": 0,

    "斯图加特": 2, "门兴格拉德巴赫": 2, "法兰克福": 2,

    "沃尔夫斯堡": 2, "柏林联合": 2,

    # 意甲

    "尤文图斯": 0, "国际米兰": 0, "AC米兰": 0,

    "罗马": 1, "佛罗伦萨": 2, "那不勒斯": 0, "拉齐奥": 1,

    "亚特兰大": 1, "博洛尼亚": 2,

    # 法甲

    "巴黎圣日耳曼": 0, "摩纳哥": 1, "里昂": 1, "马赛": 1,

    "里尔": 2, "尼斯": 2, "朗斯": 2,

    # 其他

    "凯尔特人": 1, "流浪者": 1, "阿贾克斯": 1,

}


# ============================================================

# 知识库：球场海拔（单位：米）

# ============================================================

STADIUM_ALTITUDE = {
    "拉巴斯": 3637,

    "基多": 2850,

    "波哥大": 2640,

    "基尔梅斯": 2500,

}


_TREND_CACHE = None
def _load_trend_features():

    """Load trend_features.json (cached)"""

    global _TREND_CACHE

    if _TREND_CACHE is not None:

        return _TREND_CACHE

    path = os.path.join(BASE_DIR, "data", "trend_features.json")

    if os.path.exists(path):

        with open(path, "r", encoding="utf-8") as f:

            _TREND_CACHE = json.load(f)

        return _TREND_CACHE

    _TREND_CACHE = {}

    return _TREND_CACHE


def _extract_round(event_str):

    m = re.search(r"第(\d+)轮", str(event_str))

    return int(m.group(1)) if m else None


def _is_late_season(round_num, league):

    total_rounds = {"英超": 38, "西甲": 38, "德甲": 34, "意甲": 38, "法甲": 38,

                    "葡超": 34, "荷甲": 34, "苏超": 38}

    total = total_rounds.get(league, 38)

    if round_num is None:

        return False

    return round_num >= total - 6


def _find_trend_match(trend_data, mid, home, away):
    """Look up in trend_data by ID, match_num_index, or team name fallback."""
    mt = trend_data.get("matches", {}).get(mid)
    if not mt:
        oh_id = trend_data.get("match_num_index", {}).get(mid)
        if oh_id:
            mt = trend_data.get("matches", {}).get(oh_id)
    if not mt and home and away:
        for _mid, _mr in trend_data.get("matches", {}).items():
            if _mr.get("home") == home and _mr.get("away") == away:
                mt = _mr
                break
    return mt

# ============================================================
# 德比关键词库
# ============================================================
DERBY_KEYWORDS = [
    "德比", "国家德比", "伦敦德比", "曼市德比", "北伦敦德比",
    "米兰德比", "罗马德比", "马德里德比", "默西塞德德比",
    "西班牙国家德比", "意大利国家德比",
]


# AI 判断函数：S7 心理扰动分

# ============================================================


def _estimate_s7_score(match_data, trend_data=None):

    """Estimate psychological disturbance score.

    Returns 0 (none), 0.5 (moderate), 1.0 (severe).

    Now includes rapid late odds movement detection.

    """

    score = 0.0

    event = match_data.get("event", "")

    match_type = match_data.get("match_type", "")


    if any(kw in event for kw in DERBY_KEYWORDS):

        score = max(score, 0.5)

    if match_type in ["附加赛", "解放者杯末轮", "南美杯末轮"]:

        score = max(score, 0.5)

    if match_data.get("roster_missing", False):

        score = max(score, 0.5)

    if match_data.get("motivation_ambiguous", False) and match_data.get("no_coach_statement", False):

        score = max(score, 0.5)


    # S7 trigger: rapid late odds movement

    if trend_data:

        mt = _find_trend_match(trend_data,
            match_data.get("id", ""),
            match_data.get("home", ""),
            match_data.get("away", ""))

        if mt:

            cb = mt.get("combined", {})

            change_count = cb.get("change_count", 0)

            late_acc = cb.get("late_acceleration", False)

            h_vel = abs(cb.get("h_velocity", 0))

            a_vel = abs(cb.get("a_velocity", 0))

            max_vel = max(h_vel, a_vel)


            # Rapid late movement: velocity > 0.1/day with >=3 changes

            if change_count >= 3 and max_vel > 0.08:

                score = max(score, 0.5)

            if late_acc and max_vel > 0.1:

                score = max(score, 0.5)

            if change_count >= 4 and max_vel > 0.15:

                score = max(score, 1.0)


    uncertainty_count = sum([

        match_data.get("roster_missing", False),

        match_data.get("injury_home_missing", False),

        match_data.get("injury_away_missing", False),

        match_data.get("injury_source_unreliable", False),

        match_data.get("motivation_ambiguous", False),

        match_data.get("no_coach_statement", False),

        match_data.get("multi_team_linkage", False),

    ])

    if uncertainty_count >= 4:

        score = 1.0


    return score

def _s7_reason(match_data, score, trend_data=None):

    """Generate reason text for S7 score."""

    event = match_data.get("event", "")

    match_type = match_data.get("match_type", "")


    if score == 0:

        return "无特殊扰动，比赛环境正常"

    parts = []

    if any(kw in event for kw in DERBY_KEYWORDS):

        parts.append("德比战氛围紧张")

    if match_type in ["附加赛", "解放者杯末轮", "南美杯末轮"]:

        parts.append("淘汰赛关键轮次，心理压力大")

    if match_data.get("roster_missing", False):

        parts.append("阵容信息缺失，球队可能处于变动期")

    if match_data.get("motivation_ambiguous", False) and match_data.get("no_coach_statement", False):

        parts.append("战意不明确且无主帅表态，球队方向感缺失")


    # Trend-based reasons

    if trend_data:

        mt = _find_trend_match(trend_data,
            match_data.get("id", ""),
            match_data.get("home", ""),
            match_data.get("away", ""))

        if mt:

            cb = mt.get("combined", {})

            if cb.get("late_acceleration", False):

                parts.append("后期赔率加速变动，市场情绪剧烈")

            max_v = max(abs(cb.get("h_velocity", 0)), abs(cb.get("a_velocity", 0)))

            if cb.get("change_count", 0) >= 3 and max_v > 0.08:

                parts.append("赔率连续性快变，市场分歧明显")


    if score >= 1.0:

        parts.append("多重不确定性因素叠加，环境极不稳定")

    return "；".join(parts)

# ============================================================

# AI 判断函数：对手可预测性系数

# ============================================================


def _estimate_opponent_predictability(match_data, side):

    """估算对手可预测性系数 (OPPONENT_PREDICTABILITY_MIN ~ 1.00)

       1.00 = 完全可预测

       越低 = 越不可预测

    """

    other_side = "away" if side == "home" else "home"

    other_team = match_data.get(other_side, "")

    other_tier = TEAM_TIERS.get(other_team, 3)


    coeff = 1.0

    if match_data.get(f"injury_{other_side}_missing", False):

        coeff -= 0.04

    if match_data.get("roster_missing", False):

        coeff -= 0.03

    if match_data.get("motivation_ambiguous", False):

        coeff -= 0.02

    if match_data.get("no_coach_statement", False):

        coeff -= 0.02


    home_league = match_data.get("home_league", "")

    away_league = match_data.get("away_league", "")

    if home_league and away_league and home_league != away_league:

        coeff -= 0.03

    if other_tier == 2:

        coeff -= 0.02

    if other_tier >= 3:

        coeff -= 0.02

    if match_data.get("multi_team_linkage", False):

        coeff -= 0.02


    return max(coeff, OPPONENT_PREDICTABILITY_MIN)


def _predictability_reason(match_data, side, coeff):

    other_side = "away" if side == "home" else "home"

    other_team = match_data.get(other_side, "")


    if coeff >= 0.98:

        return f"{other_team} 数据完整，表现稳定"

    parts = [f"系数={coeff:.2f}"]

    if match_data.get(f"injury_{other_side}_missing", False):

        parts.append("对手伤停未知")

    if match_data.get("roster_missing", False):

        parts.append("阵容不确定")

    if match_data.get("motivation_ambiguous", False):

        parts.append("战意不明")

    home_league = match_data.get("home_league", "")

    away_league = match_data.get("away_league", "")

    if home_league and away_league and home_league != away_league:

        parts.append("跨联赛参考数据有限")

    other_tier = TEAM_TIERS.get(other_team, 3)

    if other_tier == 2:

        parts.append("中游球队表现波动")

    return f"{other_team}：" + "，".join(parts)


# ============================================================

# AI 判断函数：诱盘分析

# ============================================================


def _analyze_trap(match_data):

    asian_hcp = match_data.get("asian_handicap", 0)

    hcp_change = match_data.get("handicap_change", 0)

    match_type = match_data.get("match_type", "")


    analysis_parts = []

    if abs(asian_hcp) >= 1.0 and abs(hcp_change) >= 0.25:

        analysis_parts.append("深盘（≥1.0）伴随盘口异动（≥0.25），存在诱盘可能")

    if asian_hcp < 0 and abs(asian_hcp) < 0.5:

        analysis_parts.append("让球偏浅，机构对强队信心不足")

    if hcp_change != 0 and ((asian_hcp < 0 and hcp_change > 0) or (asian_hcp > 0 and hcp_change < 0)):

        direction = "升盘" if hcp_change > 0 else "降盘"

        analysis_parts.append(f"盘口{hcp_change:+.2f}与初始方向相反，需警惕诱盘")

    if match_type in ["附加赛", "解放者杯末轮", "南美杯末轮"]:

        analysis_parts.append("淘汰赛环境，诱盘可能性较低")

    if not analysis_parts:

        analysis_parts.append("无明显诱盘特征，盘口与实力匹配")


    return "；".join(analysis_parts)


# ============================================================

# AI 判断函数：关键风险识别

# ============================================================


def _identify_key_risk(match_data):

    risks = []

    if match_data.get("xg_last3_missing", False) and match_data.get("xg_season_missing", False):

        risks.append("近期+赛季xG均缺失，物理面判断误差大")

    elif match_data.get("xg_last3_missing", False):

        risks.append("近期3场xG缺失，状态判断依赖赛季均值")

    elif match_data.get("xg_season_missing", False):

        risks.append("赛季xG缺失，使用实际进球替代")

    if match_data.get("h2h_missing", False):

        risks.append("历史交锋数据缺失")

    if match_data.get("injury_home_missing", False) and match_data.get("injury_away_missing", False):

        risks.append("双方伤停信息均缺失")

    elif match_data.get("injury_home_missing", False):

        risks.append("主队伤停信息缺失")

    elif match_data.get("injury_away_missing", False):

        risks.append("客队伤停信息缺失")

    if match_data.get("injury_source_unreliable", False):

        risks.append("伤停数据源不可靠")

    if match_data.get("motivation_ambiguous", False):

        risks.append("战意判断存在不确定性")

    if match_data.get("no_coach_statement", False):

        risks.append("缺少主帅赛前表态参考")

    if match_data.get("multi_team_linkage", False):

        risks.append("多队关联赛果，外部变量多")

    match_type = match_data.get("match_type", "")

    if match_type in ["附加赛", "解放者杯末轮", "南美杯末轮"]:

        risks.append("淘汰赛单场决胜，偶然性大")


    return "；".join(risks) if risks else ""


# ============================================================

# 因子参数生成（原有逻辑）

# ============================================================


def _estimate_injury(match_data, side, key_risk_text=""):

    missing_key = f"injury_{side}_missing"

    is_missing = match_data.get(missing_key, False)

    source_unreliable = match_data.get("injury_source_unreliable", False)


    team_name = match_data.get(side, "")

    injury_mentioned = team_name in key_risk_text and ("缺阵" in key_risk_text or "伤" in key_risk_text)


    if injury_mentioned:

        return -0.12

    if is_missing:

        return -0.06

    if source_unreliable:

        return -0.03

    return -0.03


def _estimate_injury_boost(match_data, side, key_risk_text=""):

    other_side = "away" if side == "home" else "home"

    other_team = match_data.get(other_side, "")

    if other_team in key_risk_text and ("缺阵" in key_risk_text or "伤" in key_risk_text):

        return 0.08

    return 0.0


def _estimate_motivation(match_data, side):

    match_type = match_data.get("match_type", "常规")

    team = match_data.get(side, "")

    event = match_data.get("event", "")

    home_league = match_data.get("home_league", "")

    away_league = match_data.get("away_league", "")

    league = home_league if side == "home" else away_league


    if match_type in ["附加赛", "解放者杯末轮", "南美杯末轮"]:

        return MOTIVATION_CAP_PLAYOFF

    if match_type == "友谊赛" or "友谊赛" in event or "热身赛" in event:

        return -0.05

    if any(kw in event for kw in ["争冠", "天王山", "榜首"]):

        return 0.12


    tier = TEAM_TIERS.get(team, 3)

    round_num = _extract_round(event)


    if tier >= 3:

        return 0.10

    if tier <= 1:

        return 0.08

    if tier == 2:

        if round_num and _is_late_season(round_num, league):

            return 0.03

        return 0.05

    return 0.05


def _check_pressure(match_data, side):

    match_type = match_data.get("match_type", "常规")

    asian_hcp = match_data.get("asian_handicap", 0)

    event = match_data.get("event", "")


    is_must_win = match_type == "附加赛" or "保级" in event or "争冠" in event

    if is_must_win and abs(asian_hcp) >= 1.0:

        return True

    if side == "home" and match_type == "常规" and asian_hcp <= -1.0:

        return True

    return False


def _check_slack(match_data, side):

    team = match_data.get(side, "")

    event = match_data.get("event", "")

    home_league = match_data.get("home_league", "")

    away_league = match_data.get("away_league", "")

    league = home_league if side == "home" else away_league


    tier = TEAM_TIERS.get(team, 3)

    round_num = _extract_round(event)


    if round_num and _is_late_season(round_num, league) and tier == 2:

        return True

    if match_data.get("roster_missing", False) and tier <= 2:

        return True

    return False


def _check_altitude(match_data, side):

    team = match_data.get(side, "")

    alt = STADIUM_ALTITUDE.get(team, 0)

    for city, alt_val in STADIUM_ALTITUDE.items():

        if city in team:

            alt = alt_val

            break

    if alt >= 2500:

        return 0.15

    return 0.0


def generate_factors(match_data, key_risk_text=""):

    """为单场比赛生成所有因子参数"""

    injury_home = max(-INJURY_CORE_MAX, min(INJURY_CORE_MAX, _estimate_injury(match_data, "home", key_risk_text)))

    injury_away = max(-INJURY_CORE_MAX, min(INJURY_CORE_MAX, _estimate_injury(match_data, "away", key_risk_text)))

    injury_home_boost = _estimate_injury_boost(match_data, "home", key_risk_text)

    injury_away_boost = _estimate_injury_boost(match_data, "away", key_risk_text)


    mot_home = max(-MOTIVATION_CAP_REGULAR, min(MOTIVATION_CAP_REGULAR, _estimate_motivation(match_data, "home")))

    mot_away = max(-MOTIVATION_CAP_REGULAR, min(MOTIVATION_CAP_REGULAR, _estimate_motivation(match_data, "away")))


    return {

        "injury_home": round(injury_home, 2),

        "injury_away_boost": round(injury_away_boost, 2),

        "injury_away": round(injury_away, 2),

        "injury_home_boost": round(injury_home_boost, 2),

        "motivation_home": round(mot_home, 2),

        "motivation_away": round(mot_away, 2),

        "pressure_home": _check_pressure(match_data, "home"),

        "pressure_away": _check_pressure(match_data, "away"),

        "slack_home": _check_slack(match_data, "home"),

        "slack_away": _check_slack(match_data, "away"),

        "altitude_home": round(_check_altitude(match_data, "home"), 2),

        "altitude_away": round(_check_altitude(match_data, "away"), 2)

    }


def generate_ai_judgment(match_data, trend_data=None):

    """Generate AI judgment fields, including trend-based S7."""

    s7_score = _estimate_s7_score(match_data, trend_data)

    s7_reason = _s7_reason(match_data, s7_score, trend_data)


    home_pred = _estimate_opponent_predictability(match_data, "home")

    away_pred = _estimate_opponent_predictability(match_data, "away")

    opponent_predictability = min(home_pred, away_pred)


    opp_reason_home = _predictability_reason(match_data, "home", home_pred)

    opp_reason_away = _predictability_reason(match_data, "away", away_pred)


    return {

        "s7_score": s7_score,

        "s7_reason": s7_reason,

        "opponent_predictability": round(opponent_predictability, 2),

        "opponent_reason": "主队视角：{}；客队视角：{}".format(opp_reason_home, opp_reason_away),

        "trap_analysis": _analyze_trap(match_data),

        "key_risk": _identify_key_risk(match_data),

    }

def main():

    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):

        locked_path = sys.argv[1]

    else:

        locked_path = os.path.join(BASE_DIR, "data", "locked_data.json")


    if not os.path.exists(locked_path):

        print(f"[ERROR] 找不到 {locked_path}")

        return


    with open(locked_path, "r", encoding="utf-8") as f:

        locked_data = json.load(f)

        # Load trend features for S7 scoring
        trend_data = _load_trend_features()


    # 读取已有 ai_judgment.json（如有 key_risk 则用于因子生成）

    ai_path = os.path.join(BASE_DIR, "data", "ai_judgment.json")

    ai_map = {}

    if os.path.exists(ai_path):

        with open(ai_path, "r", encoding="utf-8") as f:

            ai_data = json.load(f)

        ai_map = {m["id"]: m.get("key_risk", "") for m in ai_data.get("matches", [])}


    factor_results = []

    ai_results = []


    print(f"\n{'='*68}")

    print(f"  因子参数 + AI 判断 智能生成")

    print(f"{'='*68}")


    for m in locked_data.get("matches", []):

        mid = m["id"]

        key_risk = ai_map.get(mid, "")

        factors = generate_factors(m, key_risk)

        ai_judgment = generate_ai_judgment(m, trend_data)


        home = m.get("home", "")

        away = m.get("away", "")

        event = m.get("event", "")

        print(f"\n  [{mid}] {home} vs {away}")

        print(f"        事件: {event} | 类型: {m.get('match_type', '')}")


        reasons = []

        if factors["injury_home"] < 0:

            reasons.append(f"主队伤停={factors['injury_home']}")

        if factors["injury_away"] < 0:

            reasons.append(f"客队伤停={factors['injury_away']}")

        if factors["injury_home_boost"] > 0:

            reasons.append(f"主队伤停加成={factors['injury_home_boost']}")

        if factors["injury_away_boost"] > 0:

            reasons.append(f"客队伤停加成={factors['injury_away_boost']}")

        reasons.append(f"主队战意={factors['motivation_home']:+.2f}")

        reasons.append(f"客队战意={factors['motivation_away']:+.2f}")

        if factors["pressure_home"] or factors["pressure_away"]:

            reasons.append("压力修正触发")

        if factors["slack_home"] or factors["slack_away"]:

            reasons.append("松懈修正触发")

        if factors["altitude_home"] > 0 or factors["altitude_away"] > 0:

            reasons.append("高原加成触发")

        if key_risk:

            reasons.append(f"外部伤病提示: {key_risk[:30]}")

        print(f"        【因子】{' | '.join(reasons)}")


        ai_parts = [

            f"S7心理扰动={ai_judgment['s7_score']}",

            f"对手可预测性={ai_judgment['opponent_predictability']}",

        ]

        if ai_judgment['key_risk']:

            ai_parts.append(f"风险: {ai_judgment['key_risk'][:50]}")

        print(f"        【AI判断】{' | '.join(ai_parts)}")


        factor_results.append({"id": mid, **factors})

        ai_results.append({"id": mid, **ai_judgment})


    # 输出 factor_params.json

    factor_path = os.path.join(BASE_DIR, "data", "factor_params.json")

    with open(factor_path, "w", encoding="utf-8") as f:

        json.dump({"matches": factor_results}, f, ensure_ascii=False, indent=2)

    print(f"\n  [OK] 因子参数 -> {factor_path}")


    # 输出 ai_judgment.json

    ai_path_out = os.path.join(BASE_DIR, "data", "ai_judgment.json")

    with open(ai_path_out, "w", encoding="utf-8") as f:

        json.dump({"matches": ai_results}, f, ensure_ascii=False, indent=2)

    print(f"  [OK] AI 判断   -> {ai_path_out}")

    print(f"  [提示] 因子值受强制上限约束: INJURY_CORE_MAX={INJURY_CORE_MAX}")


if __name__ == "__main__":

    main()

