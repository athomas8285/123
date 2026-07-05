# validate.py
# V3.3.3-Core-Rev1.13 Step 5：参数交叉校验（无emoji版）

def validate_lambda_vs_handicap(lambda_h, lambda_a, asian_handicap, match_id, home, away):
    warnings = []
    diff = lambda_h - lambda_a
    if diff > 1.5 and abs(asian_handicap) < 0.5:
        warnings.append(f"严重背离：lambda差+{diff:.2f}（主队碾压），但盘口仅{asian_handicap:+.2f}。")
    elif diff < -0.15 and asian_handicap < 0:
        warnings.append(f"方向背离：lambda差{diff:+.2f}（客队占优），但盘口主让{asian_handicap:+.2f}。")
    elif abs(diff) < 0.5 and abs(asian_handicap) >= 1.0:
        warnings.append(f"盘口过深：lambda差仅{diff:+.2f}，但盘口{asian_handicap:+.2f}。")
    elif 0.5 <= abs(diff) < 1.0 and abs(asian_handicap) >= 1.5:
        warnings.append(f"盘口偏深：lambda差{diff:+.2f}，但盘口{asian_handicap:+.2f}。")
    return warnings


def validate_motivation_cap(motivation_home, motivation_away, match_type):
    warnings = []
    playoff_types = ["附加赛", "解放者杯末轮", "南美杯末轮"]
    cap = 0.05 if match_type in playoff_types else 0.15
    if abs(motivation_home) > cap:
        warnings.append(f"主队战意修正{motivation_home:+.0%}超过硬上限±{cap:.0%}")
    if abs(motivation_away) > cap:
        warnings.append(f"客队战意修正{motivation_away:+.0%}超过硬上限±{cap:.0%}")
    return warnings


def cross_validate(match, lambda_h_final, lambda_a_final, factor_params):
    mid = match["id"]
    home = match["home"]
    away = match["away"]
    asian_handicap = match.get("asian_handicap", 0)
    match_type = match.get("match_type", "")

    all_warnings = []
    w1 = validate_lambda_vs_handicap(lambda_h_final, lambda_a_final, asian_handicap, mid, home, away)
    all_warnings.extend(w1)

    if factor_params and factor_params.get("motivation_home") is not None:
        fp = factor_params
        w2 = validate_motivation_cap(fp["motivation_home"], fp["motivation_away"], match_type)
        all_warnings.extend(w2)

    if all_warnings:
        print(f"  [WARN] Step 5 交叉校验警告:")
        for w in all_warnings:
            print(f"    - {w}")
    else:
        print(f"  [OK] Step 5 交叉校验通过")

    return all_warnings

# ============================================
# World Cup extensions (V3.3.3-Core-Rev1.15)
# ============================================


# ============================================
# ??????? (V3.3.3-Core-Rev1.15)
# ============================================

def validate_wc_scenario(match_data, factor_params, lambda_h, lambda_a):
    """World Cup-specific cross-validation.
    Checks group stage dynamics, knockout adjustments, neutral venue."""
    warnings = []
    round_type = match_data.get("round_type", "group")
    matchday = match_data.get("matchday", 0)
    neutral_venue = match_data.get("neutral_venue", False)
    home_confed = factor_params.get("home_confed", "UNKNOWN")
    away_confed = factor_params.get("away_confed", "UNKNOWN")
    
    # 1. Neutral venue check
    if neutral_venue:
        diff = abs(lambda_h - lambda_a)
        if diff > 1.0:
            warnings.append("NEUTRAL_VENUE: ?????lambda?%.2f??????????????" % diff)
    
    # 2. Matchday dynamics
    if round_type == "group" and matchday == 3:
        if abs(lambda_h - lambda_a) < 0.3:
            warnings.append("MATCHDAY3_CLOSE: ???????????????")
    
    # 3. Cross-confederation data
    if home_confed != away_confed and home_confed != "UNKNOWN" and away_confed != "UNKNOWN":
        warnings.append("CROSS_CONFED: %s vs %s - ??????????????" % (home_confed, away_confed))
    
    # 4. Knockout stage
    if round_type == "knockout":
        total_lambda = lambda_h + lambda_a
        if total_lambda > 3.0:
            warnings.append("KNOCKOUT_HIGH: ??????=%.2f???????????(??0.90)" % total_lambda)
    
    return warnings


def validate_wc_injury(missing_players, team_name, confed):
    """Validate injury impact for World Cup context."""
    from config import INJURY_WORLD_CUP_MAX, KEY_PLAYER_INJURY_BOOST
    warnings = []
    if missing_players:
        key_positions = ["F", "M"]  # Forward and midfielder absences are critical
        key_missing = [p for p in missing_players if p.get("position") in key_positions]
        if key_missing:
            warnings.append("%s???????%d?????????%.2f" % (team_name, len(key_missing), INJURY_WORLD_CUP_MAX))
    return warnings


def validate_fifa_rank(fifa_rank_home, fifa_rank_away, lambda_h, lambda_a):
    """Cross-check lambda with FIFA ranking difference."""
    from config import FIFA_RANK_DIFF_THRESHOLD, FIFA_RANK_CLOSE_THRESHOLD
    warnings = []
    if fifa_rank_home and fifa_rank_away:
        rank_diff = abs(fifa_rank_home - fifa_rank_away)
        if rank_diff >= FIFA_RANK_DIFF_THRESHOLD:
            warnings.append("FIFA_RANK: ???%d??lambda?????%s" % (
                rank_diff,
                "??" if (fifa_rank_home < fifa_rank_away and lambda_h > lambda_a) or
                          (fifa_rank_home > fifa_rank_away and lambda_h < lambda_a) else "??"))
        elif rank_diff <= FIFA_RANK_CLOSE_THRESHOLD:
            warnings.append("FIFA_RANK: ????(?%d?)???????" % rank_diff)
    return warnings
