# factors.py
# V3.3.3-Core-Rev1.12 Step 4：因子修正计算引擎

import json, os
from config import (
    INJURY_CORE_MAX, INJURY_ROTATION_MAX,
    SLACK_PENALTY, ALTITUDE_BONUS, ALTITUDE_THRESHOLD,
    MOTIVATION_CAP_PLAYOFF, MOTIVATION_CAP_REGULAR
)


def apply_injury_factor(lambda_val, injury_home, injury_away_boost):
    if abs(injury_home) > INJURY_CORE_MAX:
        raise ValueError(f"伤停修正幅度 {injury_home} 超过上限")
    if abs(injury_away_boost) > INJURY_CORE_MAX:
        raise ValueError(f"伤停对手加成 {injury_away_boost} 超过上限")
    lambda_val *= (1 + injury_home)
    lambda_val *= (1 + injury_away_boost)
    return lambda_val


def apply_motivation_factor(lambda_val, motivation, pressure_triggered, lambda_diff, is_reverse):
    if is_reverse and abs(lambda_diff) > 0.3:
        motivation = motivation / 2
    if pressure_triggered and motivation > 0:
        lambda_val *= (1 + motivation / 2)
    else:
        lambda_val *= (1 + motivation)
    return lambda_val


def apply_slack_factor(lambda_val, slack_triggered):
    if slack_triggered:
        lambda_val *= (1 - SLACK_PENALTY)
    return lambda_val


def apply_altitude_factor(lambda_val, altitude_bonus):
    if altitude_bonus > 0:
        lambda_val *= (1 + altitude_bonus)
    return lambda_val


def process_match(match_data, factor_params):
    lh = match_data["lambda_raw_h"]
    la = match_data["lambda_raw_a"]
    diff = lh - la
    fp = factor_params

    mot_h_reverse = (fp["motivation_home"] > 0 and diff < -0.3) or (fp["motivation_home"] < 0 and diff > 0.3)
    mot_a_reverse = (fp["motivation_away"] > 0 and diff > 0.3) or (fp["motivation_away"] < 0 and diff < -0.3)

    lh = apply_injury_factor(lh, fp['injury_home'], 0)
    la = apply_injury_factor(la, fp['injury_away'], 0)
    if fp.get("injury_away_boost", 0) != 0:
        lh *= (1 + fp["injury_away_boost"])
    if fp.get("injury_home_boost", 0) != 0:
        la *= (1 + fp["injury_home_boost"])

    lh = apply_motivation_factor(lh, fp["motivation_home"], fp["pressure_home"], diff, mot_h_reverse)
    la = apply_motivation_factor(la, fp["motivation_away"], fp.get("pressure_away", False), -diff, mot_a_reverse)

    lh = apply_slack_factor(lh, fp["slack_home"])
    la = apply_slack_factor(la, fp.get("slack_away", False))

    lh = apply_altitude_factor(lh, fp.get("altitude_home", 0))
    la = apply_altitude_factor(la, fp.get("altitude_away", 0))

    return round(lh, 4), round(la, 4)
