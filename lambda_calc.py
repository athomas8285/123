# lambda_calc.py
# V3.3.3-Core-Rev1.13 Step 3: 初始物理参数λ计算（含未来函数陷阱检测）
# P0-P4: 置信度/样本量感知优化

from config import LEAGUE_AVG_XGA, LEAGUE_EXCHANGE_RATE


def get_league_avg_xga(league):
    if not league:
        raise ValueError("联赛名称为空")
    if league in LEAGUE_AVG_XGA:
        return LEAGUE_AVG_XGA[league]
    else:
        print(f"  [WARN] 联赛 '{league}' 不在配置中，使用默认值 {LEAGUE_AVG_XGA['默认']}")
        return LEAGUE_AVG_XGA["默认"]


def calc_initial_lambda(home_xg, home_xga, away_xg, away_xga, home_league, away_league):
    params = {
        "主队xG": home_xg, "主队xGA": home_xga,
        "客队xG": away_xg, "客队xGA": away_xga,
        "主队联赛": home_league, "客队联赛": away_league,
    }
    missing = [k for k, v in params.items() if v is None]
    if missing:
        raise ValueError(f"λ 计算数据缺失: {', '.join(missing)}")

    home_league_avg = get_league_avg_xga(home_league)
    away_league_avg = get_league_avg_xga(away_league)

    if home_league != away_league:
        home_rate = LEAGUE_EXCHANGE_RATE.get(home_league, 1.0)
        away_rate = LEAGUE_EXCHANGE_RATE.get(away_league, 1.0)
        home_league_avg = home_league_avg * home_rate
        away_league_avg = away_league_avg * away_rate

    lambda_h = home_xg * away_xga / home_league_avg
    lambda_a = away_xg * home_xga / away_league_avg

    return lambda_h, lambda_a


def calc_initial_lambda_alt(home_goals, home_goals_conceded,
                             away_goals, away_goals_conceded,
                             home_league, away_league):
    return calc_initial_lambda(
        home_xg=home_goals, home_xga=home_goals_conceded,
        away_xg=away_goals, away_xga=away_goals_conceded,
        home_league=home_league, away_league=away_league
    )


def calc_kelly(sp, p_physical):
    if sp <= 1.0:
        return 0.0
    return (sp * p_physical - 1) / (sp - 1)


def _confidence_scale(xg_home_sample=0, xg_away_sample=0,
                      xg_last3_home_sample=0, xg_last3_away_sample=0):
    """
    P1: Sample-size-aware confidence scaling.
    Returns a multiplier in (0, 1] reflecting data reliability.
    Returns 1.0 (no penalty) when no sample data is available (backward compat).
    """
    if all(v is None or v == 0
           for v in [xg_home_sample, xg_away_sample,
                     xg_last3_home_sample, xg_last3_away_sample]):
        return 1.0

    samples = [v for v in [xg_home_sample, xg_away_sample,
                           xg_last3_home_sample, xg_last3_away_sample]
               if v is not None and v > 0]
    if not samples:
        return 0.50

    min_samples = min(samples)

    if min_samples >= 20:
        return 1.0
    elif min_samples >= 10:
        return 0.95
    elif min_samples >= 7:
        return 0.88
    elif min_samples >= 5:
        return 0.80
    elif min_samples >= 3:
        return 0.70
    elif min_samples >= 1:
        return 0.55
    else:
        return 0.50


def _tournament_category(event_name):
    """Categorize a tournament/event name into a broad category for cross-tournament detection."""
    league_keywords = ["联赛", "英超", "西甲", "意甲", "德甲", "法甲", "中超",
                       "J联赛", "J联", "K联赛", "K联", "澳超", "美职联",
                       "日职", "韩K", "巴甲", "阿甲", "荷甲", "葡超", "苏超",
                       "瑞典超", "挪超", "芬超", "俄超", "土超", "比甲",
                       "丹超", "瑞士超", "奥超", "捷甲", "克甲", "塞甲"]
    cup_keywords = ["杯", "协", "冠", "解放者", "南美",
                    "欧联", "欧协", "欧冠", "欧罗巴"]
    international_keywords = ["世", "洲", "国际", "友谊赛"]

    for kw in league_keywords:
        if kw in event_name:
            return "league"
    for kw in cup_keywords:
        if kw in event_name:
            return "cup"
    for kw in international_keywords:
        if kw in event_name:
            return "international"
    return "other"


def detect_cross_tournament_xg(home_source_events, away_source_events):
    """
    P2: Detect when xG data sources span different tournament categories.
    Returns (confidence_multiplier, reason_string).
    1.0 = same category, lower = cross-tournament penalty.
    """
    if not home_source_events or not away_source_events:
        return 1.0, ""

    home_events = [e.strip() for e in home_source_events.split(",") if e.strip()]
    away_events = [e.strip() for e in away_source_events.split(",") if e.strip()]

    if not home_events or not away_events:
        return 1.0, ""

    home_cats = set(_tournament_category(e) for e in home_events)
    away_cats = set(_tournament_category(e) for e in away_events)

    if home_cats == away_cats and len(home_cats) == 1:
        return 1.0, ""

    if not home_cats.intersection(away_cats):
        return 0.85, "主客xG数据来源赛事类型完全不同"

    if home_cats != away_cats:
        return 0.90, "主客xG数据来源赛事类型存在差异"

    if len(home_cats) > 1 or len(away_cats) > 1:
        return 0.92, "xG数据来源包含多种赛事类型"

    return 1.0, ""


def _data_confidence_multiplier(confidence_level):
    """Convert a confidence level string ("api"/"calc"/"infer") to a numeric multiplier."""
    conf_map = {"api": 1.0, "calc": 0.7, "infer": 0.3}
    return conf_map.get(confidence_level, 0.7)


def validate_temporal_integrity(match_data):
    """
    Rev1.13: 检测回测中的"未来函数"陷阱。
    如果数据截止日期晚于比赛日期，说明回测时可能使用了未来数据。
    """
    data_as_of = match_data.get("xg_data_as_of", "")
    match_time = match_data.get("time", "")

    if not data_as_of or not match_time:
        return

    try:
        data_date = data_as_of[:10]
        match_date = match_time[:10]

        from datetime import datetime
        data_dt = datetime.strptime(data_date, "%Y-%m-%d")
        match_dt = datetime.strptime(match_date, "%Y-%m-%d")

        days_diff = (data_dt - match_dt).days

        if days_diff > 1:
            print(f"  [WARN] 数据截止日期({data_date})晚于比赛日期({match_date})，"
                  f"可能存在未来数据泄漏！回测命中率可能虚高。")
        elif days_diff >= 0:
            print(f"  [INFO] 数据截止日期({data_date})与比赛日期({match_date})接近，时序正常。")
        else:
            print(f"  [INFO] 数据截止日期({data_date})早于比赛日期({match_date})，"
                  f"时序干净，回测结论可靠。")
    except:
        pass


# ============================================
# World Cup extensions (V3.3.3-Core-Rev1.15)
# ============================================

# ============================================
# ??????? (V3.3.3-Core-Rev1.15)
# ============================================

def _confed_deflate(league_name):
    """Apply confederation-level deflation to normalize cross-confed data.
    Returns multiplier to shrink inflated data from weaker confederations."""
    from config import CONFED_DEFLATION, CONFED_DEFAULT_XGA
    
    # Map known leagues/teams to confederations
    confed_keywords = {
        "UEFA": ["??", "??", "??", "??", "??", "??", "??", "??",
                 "??", "??", "??", "??", "???", "??", "??", "??",
                 "??", "???", "??", "??", "???", "??", "???",
                 "???", "??", "??", "??", "???", "????",
                 "Euro", "??", "???", "???"],
        "CONMEBOL": ["??", "??", "???", "???", "????", "?????",
                     "?????", "??", "?????", "???",
                     "??", "???", "???"],
        "CONCACAF": ["??", "???", "??", "???", "CONCACAF"],
        "CAF": ["??", "???", "???", "???", "???", "????",
                "????", "????", "?????"],
        "AFC": ["??", "?K", "??", "??", "??", "??", "???",
                "???", "???", "????", "????", "???"],
        "OFC": ["???", "??", "????"],
    }
    
    # Check against confederation keywords
    for confed, kws in confed_keywords.items():
        for kw in kws:
            if kw in league_name:
                rate = CONFED_DEFLATION.get(confed, 1.0)
                return rate, confed
    
    return 1.0, "UNKNOWN"


def calc_initial_lambda_wc(home_xg, home_xga, away_xg, away_xga,
                            home_league, away_league,
                            neutral_venue=False,
                            home_confed=None, away_confed=None):
    """World Cup version of lambda calculation with confederation deflation
    and neutral venue handling."""
    from config import LEAGUE_AVG_XGA, LEAGUE_EXCHANGE_RATE
    
    home_rate, home_confed = _confed_deflate(home_league)
    away_rate, away_confed = _confed_deflate(away_league)
    
    home_league_avg = LEAGUE_AVG_XGA.get(home_league, LEAGUE_AVG_XGA.get("??", 1.35))
    away_league_avg = LEAGUE_AVG_XGA.get(away_league, LEAGUE_AVG_XGA.get("??", 1.35))
    
    if home_league != away_league:
        hr = LEAGUE_EXCHANGE_RATE.get(home_league, 1.0)
        ar = LEAGUE_EXCHANGE_RATE.get(away_league, 1.0)
        home_league_avg *= hr
        away_league_avg *= ar
    
    # Base lambda calculation
    lambda_h = home_xg * away_xga / home_league_avg
    lambda_a = away_xg * home_xga / away_league_avg
    
    # Confed deflation: shrink inflated data
    geo_mean = (home_rate * away_rate) ** 0.5
    lambda_h *= geo_mean
    lambda_a *= geo_mean
    
    # Neutral venue: if match is at neutral site, equalize home/away baseline
    if neutral_venue:
        avg_lambda = (lambda_h + lambda_a) / 2
        lambda_h = avg_lambda
        lambda_a = avg_lambda
    
    return lambda_h, lambda_a


def friendly_filter(events, team_name, max_friendly=1):
    """Filter recent form to exclude or limit friendly matches.
    Returns filtered events list and count of excluded friendlies."""
    friendly_kw = ["Friendly", "???", "Club Friendly", "Int. Friendly"]
    filtered = []
    excluded = 0
    friendly_count = 0
    for ev in events:
        comp = ev.get("tournament", {}).get("name", "")
        is_friendly = any(kw in comp for kw in friendly_kw)
        if is_friendly:
            if friendly_count < max_friendly:
                filtered.append(ev)
                friendly_count += 1
            else:
                excluded += 1
        else:
            filtered.append(ev)
    return filtered, excluded


def get_confed_deflation(league_name):
    """Public interface to get confederation deflation rate for a league."""
    rate, confed = _confed_deflate(league_name)
    return rate, confed
