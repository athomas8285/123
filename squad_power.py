# squad_power.py
# V3.3.3-Core-Rev1.15 赛前实力预测模块
# 用途：当缺少xG/SofaScore数据时，基于FIFA排名+阵容身价生成λ与概率
# 适用场景：世界杯等大型赛事的赛前预测（data freeze之前）

import json, os, math
import numpy as np
from collections import Counter
from config import MONTE_CARLO_RUNS

_DATA_DIR = None
_PROFILES_CACHE = None

def _data_dir():
    global _DATA_DIR
    if _DATA_DIR is None:
        _DATA_DIR = os.environ.get('BACKTEST_DATA_DIR',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
    return _DATA_DIR

def _load_profiles():
    global _PROFILES_CACHE
    if _PROFILES_CACHE is not None:
        return _PROFILES_CACHE
    path = os.path.join(_data_dir(), 'team_profiles.json')
    with open(path, 'r', encoding='utf-8') as f:
        _PROFILES_CACHE = json.load(f)
    return _PROFILES_CACHE

def _calc_power(profile):
    rank_score = max(0, 1.0 - (profile['fifa_rank'] - 1) / 49.0)
    value_score = profile['total_value_m'] / 1350.0
    power = 0.4 * rank_score + 0.6 * value_score
    return min(max(power, 0.01), 1.0)

def _confed_penalty(confed, power):
    from config import CONFED_DEFLATION
    rate = CONFED_DEFLATION.get(confed, 1.0)
    return power * rate

def load_team_profiles():
    global _PROFILES_CACHE
    _PROFILES_CACHE = None
    return _load_profiles()

def calc_power_score(team_name):
    profiles = _load_profiles()
    if team_name not in profiles:
        raise ValueError(f"队伍 {team_name} 不在 team_profiles.json 中")
    return _calc_power(profiles[team_name])

def predict_match(home_team, away_team, neutral_venue=False, base_rate=1.35, mc_runs=2000):
    profiles = _load_profiles()
    if home_team not in profiles:
        raise ValueError(f"主队 {home_team} 不在档案中")
    if away_team not in profiles:
        raise ValueError(f"客队 {away_team} 不在档案中")

    hp = profiles[home_team]
    ap = profiles[away_team]
    raw_h_power = _calc_power(hp)
    raw_a_power = _calc_power(ap)
    h_power = _confed_penalty(hp['confed'], raw_h_power)
    a_power = _confed_penalty(ap['confed'], raw_a_power)

    avg_power = (h_power + a_power) / 2
    if avg_power == 0:
        avg_power = 0.5
    lambda_h = base_rate * (h_power / avg_power)
    lambda_a = base_rate * (a_power / avg_power)

    # neutral venue: no home advantage adjustment needed

    lambda_h = round(min(max(lambda_h, 0.3), 4.0), 4)
    lambda_a = round(min(max(lambda_a, 0.3), 4.0), 4)

    np.random.seed(42)
    home_goals = np.random.poisson(lambda_h, mc_runs)
    away_goals = np.random.poisson(lambda_a, mc_runs)
    diff = home_goals - away_goals
    p_home = round(np.sum(diff > 0) / mc_runs, 4)
    p_draw = round(np.sum(diff == 0) / mc_runs, 4)
    p_away = round(np.sum(diff < 0) / mc_runs, 4)

    total_goals = home_goals + away_goals
    gc = Counter(total_goals)
    top2_goals = [f"{g}\u7403" for g, _ in gc.most_common(2)]

    score_labels = [f"{int(h)}-{int(a)}" for h, a in zip(home_goals, away_goals)]
    sc = Counter(score_labels)
    top3_scores = [s for s, _ in sc.most_common(3)]

    return {
        'home_team': home_team, 'away_team': away_team,
        'neutral_venue': neutral_venue, 'method': 'squad_power',
        'power': {
            'home_raw': round(raw_h_power, 4), 'away_raw': round(raw_a_power, 4),
            'home_final': round(h_power, 4), 'away_final': round(a_power, 4),
            'home_confed': hp['confed'], 'away_confed': ap['confed'],
        },
        'lambda': {'home': lambda_h, 'away': lambda_a},
        'probabilities': {'home_win': p_home, 'draw': p_draw, 'away_win': p_away},
        'top2_total_goals': top2_goals, 'top3_scores': top3_scores,
    }

def predict_all_wc_matches(schedule_path=None, base_rate=1.35, mc_runs=2000):
    if schedule_path is None:
        schedule_path = os.path.join(_data_dir(), 'wc_schedule.json')
    with open(schedule_path, 'r', encoding='utf-8') as f:
        schedule = json.load(f)
    results = []
    for m in schedule['matches']:
        try:
            result = predict_match(m['home'], m['away'], neutral_venue=True,
                                   base_rate=base_rate, mc_runs=mc_runs)
            result['id'] = m.get('odds') or {}.get('id', '')
            result['group'] = m.get('group', '')
            result['round'] = m.get('round', 0)
            result['date'] = m.get('date', '')
            result['time'] = m.get('time', '')
            result['venue'] = m.get('venue', '')
            results.append(result)
        except (ValueError, KeyError) as e:
            print(f"  [SKIP] {m.get('home','?')} vs {m.get('away','?')}: {e}")
    return results

def estimate_match(home_team, away_team, home_league=None, away_league=None,
                   round_type=None, neutral_venue=None, base_rate=1.35):
    profiles = _load_profiles()
    if home_team not in profiles or away_team not in profiles:
        return None
    result = predict_match(home_team, away_team, neutral_venue=bool(neutral_venue), base_rate=base_rate)
    return {
        'method': 'squad_power',
        'lambda_h': result['lambda']['home'],
        'lambda_a': result['lambda']['away'],
        'prob_home_win': result['probabilities']['home_win'],
        'prob_draw': result['probabilities']['draw'],
        'prob_away_win': result['probabilities']['away_win'],
        'top2_total_goals': result['top2_total_goals'],
        'top3_scores': result['top3_scores'],
        'power_home': result['power']['home_final'],
        'power_away': result['power']['away_final'],
    }

if __name__ == '__main__':
    r = predict_match('墨西哥', '南非', neutral_venue=True)
    print(json.dumps(r, ensure_ascii=False, indent=2))