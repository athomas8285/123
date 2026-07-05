# Fix ddi.py - Step 7: DDI校准（修复版）
# Bug: 原公式 DDI = diff * log1p(0.15) * 0.05 = diff * 0.007，触发阈值0.08，信号被压死400倍
# 修复: DDI = P_physical - P_market，纯偏差，去掉压死信号的乘数

import json, os
from config import (
    DDI_TRIGGER_THRESHOLD, DDI_AMPLITUDE_CAP, DDI_AMPLITUDE_RATIO,
    AWAY_COLD_TREATMENT
)


def calc_market_prob(sp_home, sp_draw, sp_away):
    inv_h, inv_d, inv_a = 1/sp_home, 1/sp_draw, 1/sp_away
    s = inv_h + inv_d + inv_a
    return {
        "home_win": inv_h/s,
        "draw": inv_d/s,
        "away_win": inv_a/s
    }


def calc_ddi(p_physical, p_market):
    """DDI = 纯物理概率与市场概率的偏差（去掉原公式中的压死乘数）
       正值 = 模型比市场更看好该结果
       负值 = 市场比模型更看好该结果"""
    ddi = {}
    for key in ["home_win", "draw", "away_win"]:
        ddi[key] = p_physical[key] - p_market[key]
    return ddi


def apply_calibration(p_physical, ddi):
    calibrated = {}
    for key in p_physical:
        calibrated[key] = p_physical[key]
    for key in ["home_win", "draw", "away_win"]:
        d = ddi[key]
        if abs(d) > DDI_TRIGGER_THRESHOLD:
            adj = min(abs(d) * DDI_AMPLITUDE_RATIO, DDI_AMPLITUDE_CAP)
            calibrated[key] += adj if d > 0 else -adj
    return calibrated


def apply_away_cold_treatment(calibrated, predicted_direction, match_type, is_home_life_death):
    if predicted_direction != "away":
        return calibrated
    cold_types = ["附加赛", "解放者杯末轮", "南美杯末轮"]
    if match_type not in cold_types and not is_home_life_death:
        return calibrated
    reduction = calibrated["away_win"] * AWAY_COLD_TREATMENT
    calibrated["away_win"] -= reduction
    remaining = calibrated["home_win"] + calibrated["draw"]
    if remaining > 0:
        calibrated["home_win"] += reduction * (calibrated["home_win"] / remaining)
        calibrated["draw"] += reduction * (calibrated["draw"] / remaining)
    return calibrated


def apply_odds_momentum_correction(p_physical, match_data):
    """赔率动态修正规则（B路线新增）
       基于赛前赔率变动方向，动态调整概率"""
    calibrated = {}
    for key in p_physical:
        calibrated[key] = p_physical[key]

    sp_home = match_data.get("sp_home")
    sp_draw = match_data.get("sp_draw")
    sp_away = match_data.get("sp_away")
    init_sp_home = match_data.get("initial_sp_home")
    init_sp_draw = match_data.get("initial_sp_draw")
    init_sp_away = match_data.get("initial_sp_away")

    if not all([init_sp_home, init_sp_draw, init_sp_away]):
        return calibrated

    away_change = (init_sp_away - sp_away) / init_sp_away if sp_away and init_sp_away else 0
    draw_change = (init_sp_draw - sp_draw) / init_sp_draw if sp_draw and init_sp_draw else 0

    p_market = calc_market_prob(sp_home, sp_draw, sp_away)
    kelly_draw = (sp_draw * p_market["draw"] - 1) / (sp_draw - 1) if sp_draw > 1 else 0

    # 规则1：客胜赔率降幅>10% → 客胜概率+8%
    if away_change > 0.10 and kelly_draw < 0.93:
        reduction = 0.08
        calibrated["away_win"] += reduction
        remaining = calibrated["home_win"] + calibrated["draw"]
        if remaining > 0:
            calibrated["home_win"] -= reduction * (calibrated["home_win"] / remaining)
            calibrated["draw"] -= reduction * (calibrated["draw"] / remaining)
        print(f"  [INFO] 赔率修正触发：客胜赔率降幅{away_change:.1%}，客胜概率+8%")

    # 规则2：平局赔率降幅>5%且凯利指数<0.93 → 平局概率x1.2，上限45%
    if draw_change > 0.05 and kelly_draw < 0.93:
        new_draw = min(calibrated["draw"] * 1.2, 0.45)
        diff = new_draw - calibrated["draw"]
        calibrated["draw"] = new_draw
        remaining = calibrated["home_win"] + calibrated["away_win"]
        if remaining > 0:
            calibrated["home_win"] -= diff * (calibrated["home_win"] / remaining)
            calibrated["away_win"] -= diff * (calibrated["away_win"] / remaining)
        print(f"  [INFO] 赔率修正触发：平局赔率降幅{draw_change:.1%}，平局概率x1.2（上限45%）")

    return calibrated


def process_match(match_data, mc):
    p_physical = mc["physical"]
    sp_h, sp_d, sp_a = match_data.get("sp_home"), match_data.get("sp_draw"), match_data.get("sp_away")

    if not all([sp_h, sp_d, sp_a]):
        return {
            "p_physical": p_physical,
            "p_market": {"home_win": 0, "draw": 0, "away_win": 0},
            "ddi": {"home_win": 0, "draw": 0, "away_win": 0},
            "calibrated": p_physical,
            "protection_triggered": True,
            "sp_missing": True
        }

    p_market = calc_market_prob(sp_h, sp_d, sp_a)
    ddi = calc_ddi(p_physical, p_market)
    calibrated = apply_calibration(p_physical, ddi)

    # B路线新增：赔率动态修正
    calibrated = apply_odds_momentum_correction(calibrated, match_data)

    # Rev1.7：客场冷处理
    predicted_direction = match_data.get("predicted_direction", "home")
    match_type = match_data.get("match_type", "")
    is_home_life_death = match_data.get("is_home_life_death", False)
    calibrated = apply_away_cold_treatment(calibrated, predicted_direction, match_type, is_home_life_death)

    return {
        "p_physical": p_physical,
        "p_market": {k: round(v, 4) for k, v in p_market.items()},
        "ddi": {k: round(v, 4) for k, v in ddi.items()},
        "calibrated": {k: round(v, 4) for k, v in calibrated.items()},
        "protection_triggered": False,
        "sp_missing": False
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    mc_path = os.path.join(data_dir, "monte_carlo_result.json")
    info_path = os.path.join(data_dir, "match_info.json")
    with open(mc_path, "r", encoding="utf-8") as f:
        mc_data = json.load(f)
    with open(info_path, "r", encoding="utf-8") as f:
        match_info = json.load(f)
    info_map = {m["id"]: m for m in match_info["matches"]}
    results = []
    for mc in mc_data["matches"]:
        mid = mc["id"]
        info = info_map.get(mid, {})
        result = process_match(info, mc)
        results.append({"id": mid, **result})
        d = result["ddi"]
        print(f"  [{mid}] DDI: 主{d['home_win']:+.4f} 平{d['draw']:+.4f} 客{d['away_win']:+.4f}")
    output_path = os.path.join(data_dir, "ddi_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"matches": results}, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] DDI校准完成 -> {output_path}")


if __name__ == "__main__":
    print("=" * 55)
    print("  V3.3.3-Core-Rev1.14 Step 7: DDI校准（修复版，纯偏差）")
    print("=" * 55)
    main()
