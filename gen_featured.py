# gen_featured.py - generate featured betting plan from plan pool
import json, os, math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

STRATEGY = {
    'base_stake': 1000,
    'multipliers': [1, 1, 2, 4, 8, 16],
    'max_rounds': 6
}

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate(output_dir=None):
    plan = load_json(os.path.join(DATA_DIR, 'plan_data.json'))
    matches = plan['matches']
    groups = plan['date_groups']
    
    # Walk through days chronologically
    sequence = []
    current_round = 0  # 0-based index into multipliers
    cumulative_profit = 0
    cumulative_invested = 0
    
    for g in sorted(groups, key=lambda g: g['date']):
        d = g['date']
        top_pick = None
        if g.get('plan_2'):
            top_pick = g['plan_2'][0]
        
        if not top_pick:
            sequence.append({
                'date': d,
                'round': current_round + 1,
                'stake': 0,
                'multiplier': 0,
                'pick': None,
                'result': 'no_pick',
                'profit': 0,
                'cumulative': cumulative_profit,
                'note': 'no qualified plan'
            })
            continue
        
        l1, l2 = top_pick['l1'], top_pick['l2']
        stake = STRATEGY['base_stake'] * STRATEGY['multipliers'][current_round]
        
        # Determine result (evaluate plan leg hit against actual score)
        h1 = judge_leg_hit(l1, matches.get(l1['mid'], {}))
        h2 = judge_leg_hit(l2, matches.get(l2['mid'], {}))
        
        if h1 is None or h2 is None:
            result = 'pending'
            profit = 0
        elif h1 and h2:
            result = 'hit'
            # Use min_odds for conservative profit calc
            odds = top_pick.get('min_odds', 2.0)
            profit = stake * (odds - 1)
            cumulative_profit += profit
            current_round = 0  # reset
        else:
            result = 'miss'
            profit = -stake
            cumulative_profit += profit
            current_round = min(current_round + 1, STRATEGY['max_rounds'] - 1)
            if current_round == STRATEGY['max_rounds'] - 1 and result == 'miss':
                # Check if next round would exceed max
                pass  # will be caught next iteration
        
        cumulative_invested += stake
        
        sequence.append({
            'date': d,
            'round': current_round if result == 'hit' else (current_round if result == 'pending' else min(current_round, STRATEGY['max_rounds'])),
            'stake': stake,
            'multiplier': STRATEGY['multipliers'][current_round if result != 'hit' else 0],
            'pick': top_pick,
            'result': result,
            'profit': round(profit, 2),
            'cumulative': round(cumulative_profit, 2),
            'cumulative_invested': round(cumulative_invested, 2)
        })
        
        # After processing: if hit, reset to 0. If miss at max_rounds, wrap around.
        if result == 'hit':
            current_round = 0
        elif result == 'miss':
            if current_round >= STRATEGY['max_rounds'] - 1:
                current_round = 0  # full cycle completed, reset
            # else current_round already incremented above
    
    # Determine current state
    last = sequence[-1] if sequence else None
    if last and last['result'] == 'pending':
        current_state = {
            'round': current_round + 1,
            'next_stake': STRATEGY['base_stake'] * STRATEGY['multipliers'][current_round],
            'next_multiplier': STRATEGY['multipliers'][current_round],
            'cumulative': round(cumulative_profit, 2),
            'cumulative_invested': round(cumulative_invested, 2)
        }
    elif last and last['result'] == 'hit':
        current_state = {
            'round': 1,
            'next_stake': STRATEGY['base_stake'],
            'next_multiplier': 1,
            'cumulative': round(cumulative_profit, 2),
            'cumulative_invested': round(cumulative_invested, 2)
        }
    else:
        current_state = {
            'round': current_round + 1 if current_round < STRATEGY['max_rounds'] else 1,
            'next_stake': STRATEGY['base_stake'] * STRATEGY['multipliers'][min(current_round, STRATEGY['max_rounds']-1)],
            'next_multiplier': STRATEGY['multipliers'][min(current_round, STRATEGY['max_rounds']-1)],
            'cumulative': round(cumulative_profit, 2),
            'cumulative_invested': round(cumulative_invested, 2)
        }
    
    data = {
        'strategy': STRATEGY,
        'sequence': sequence,
        'current': current_state,
        'matches': {mid: {'home': m['home'], 'away': m['away'], 'actual_score': m.get('actual_score', ''), 'half_full': m.get('half_full', ''), 'handicap': m.get('handicap', 0)} for mid, m in matches.items()}
    }
    
    out_path = os.path.join(output_dir or DATA_DIR, 'featured_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f'featured_data.json: {len(sequence)} days')
    hits = sum(1 for s in sequence if s['result'] == 'hit')
    misses = sum(1 for s in sequence if s['result'] == 'miss')
    pending = sum(1 for s in sequence if s['result'] == 'pending')
    print(f'  hits={hits} misses={misses} pending={pending}')
    print(f'  cumulative={cumulative_profit:.0f} invested={cumulative_invested:.0f} net={cumulative_profit:.0f}')
    return data
def parse_score(s):
    """Parse score string like '2-0' or '2:0' to [home, away]."""
    if not s: return None
    parts = s.replace(":", "-").split("-")
    if len(parts) != 2: return None
    try:
        return [int(parts[0]), int(parts[1])]
    except:
        return None

def judge_leg_hit(leg, match):
    """Judge whether a plan leg (with type/option) actually hit based on match data."""
    sc = parse_score(match.get("actual_score", ""))
    if not sc: return None
    hg, ag = sc[0], sc[1]
    typ = leg.get("type", "")
    opt = leg.get("option", "")
    hcp = match.get("handicap", 0) or 0

    if typ == "方向":
        if opt == "主胜" or opt == "胜": return hg > ag
        if opt == "客胜" or opt == "负": return hg < ag
        if opt == "平局" or opt == "平": return hg == ag
        adj = hg + hcp - ag
        if opt == "让胜": return adj > 0
        if opt == "让平": return adj == 0
        if opt == "让负": return adj < 0
        return False

    if typ == "方向打包":
        parts = opt.split("/")
        is_hcp = any("让" in p for p in parts)
        for po in parts:
            adj2 = hg + hcp - ag
            if po == "胜" and hg > ag: return True
            if po == "平" and (adj2 == 0 if is_hcp else hg == ag): return True
            if po == "负" and (adj2 < 0 if is_hcp else hg < ag): return True
            if po == "让胜" and adj2 > 0: return True
            if po == "让平" and adj2 == 0: return True
            if po == "让负" and adj2 < 0: return True
        return False

    if typ == "半全场":
        hf = match.get("half_full", "")
        return hf == opt if hf else None

    if typ == "半全场打包":
        hf2 = match.get("half_full", "")
        if not hf2: return None
        if "主不败" in opt: return hf2 in ("胜胜", "平胜")
        if "客不败" in opt: return hf2 in ("负负", "平负")
        return False

    return None

def judge_combo_hit(combo, matches):
    """Judge whether a 2-leg combo hit based on match data."""
    legs = [combo["l1"], combo["l2"]]
    if "l3" in combo: legs.append(combo["l3"])
    any_null = False
    for leg in legs:
        m = matches.get(leg["mid"], {})
        r = judge_leg_hit(leg, m)
        if r is None: any_null = True; continue
        if not r: return False
    return None if any_null else True


if __name__ == '__main__':
    generate()
