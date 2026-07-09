# run_all.py锛圧ev1.13 瀹屾暣鐗埪峰惈鏈潵鍑芥暟妫€娴嬶級
import subprocess, sys, os, json, datetime
from lambda_calc import calc_initial_lambda, calc_initial_lambda_alt, calc_initial_lambda_wc, validate_temporal_integrity
from monte_carlo import MonteCarloEngine
from config import MONTE_CARLO_RUNS, SLACK_PENALTY


def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_factors(lambda_h, lambda_a, factor_params):
    fp = factor_params
    diff = lambda_h - lambda_a
    
    # World Cup extensions
    round_type = fp.get('round_type', 'group')
    matchday = fp.get('matchday', 0)
    neutral_venue = fp.get('neutral_venue', False)
    key_player_missing_h = fp.get('key_player_missing_home', False)
    key_player_missing_a = fp.get('key_player_missing_away', False)
    from config import (SLACK_PENALTY, KEY_PLAYER_INJURY_BOOST,
                        INJURY_WORLD_CUP_MAX, NEUTRAL_VENUE_HOME_ADVANTAGE,
                        NEUTRAL_VENUE_ALTITUDE_FACTOR, GROUP_MATCHDAY_FACTOR,
                        KNOCKOUT_LAMBDA_FACTOR)
    
    mot_h_reverse = (fp['motivation_home'] > 0 and diff < -0.3) or (fp['motivation_home'] < 0 and diff > 0.3)
    mot_a_reverse = (fp['motivation_away'] > 0 and diff > 0.3) or (fp['motivation_away'] < 0 and diff < -0.3)
    
    # Injury: use World Cup max if applicable
    injury_max = INJURY_WORLD_CUP_MAX if round_type in ('group', 'knockout') else fp.get('injury_home_max', 0.20)
    lh = lambda_h * (1 + min(fp['injury_home'], injury_max))
    la = lambda_a * (1 + min(fp.get('injury_away', 0), injury_max))
    
    # Key player missing boost (World Cup specific)
    if key_player_missing_h: lh *= (1 - KEY_PLAYER_INJURY_BOOST)
    if key_player_missing_a: la *= (1 - KEY_PLAYER_INJURY_BOOST)
    
    if fp.get('injury_home_boost', 0) != 0: lh *= (1 + fp['injury_home_boost'])
    if fp.get('injury_away_boost', 0) != 0: la *= (1 + fp.get('injury_away_boost', 0))
    
    mot_h, mot_a = fp['motivation_home'], fp['motivation_away']
    if mot_h_reverse and abs(diff) > 0.3: mot_h /= 2
    if mot_a_reverse and abs(diff) > 0.3: mot_a /= 2
    if fp.get('pressure_home', False) and mot_h > 0: mot_h /= 2
    if fp.get('pressure_away', False) and mot_a > 0: mot_a /= 2
    lh *= (1 + mot_h); la *= (1 + mot_a)
    
    if fp.get('slack_home', False): lh *= (1 - SLACK_PENALTY)
    if fp.get('slack_away', False): la *= (1 - SLACK_PENALTY)
    
    # Neutral venue: cancel home advantage and altitude effects
    if neutral_venue:
        altitude_h = NEUTRAL_VENUE_ALTITUDE_FACTOR
        altitude_a = NEUTRAL_VENUE_ALTITUDE_FACTOR
    else:
        altitude_h = fp.get('altitude_home', 0)
        altitude_a = fp.get('altitude_away', 0)
    
    if altitude_h > 0: lh *= (1 + altitude_h)
    if altitude_a > 0: la *= (1 + altitude_a)
    
    # Matchday adjustment (group stage only)
    if round_type == 'group' and matchday in GROUP_MATCHDAY_FACTOR:
        md_factor = GROUP_MATCHDAY_FACTOR[matchday]
        lh *= md_factor
        la *= md_factor
    
    # Knockout adjustment
    if round_type == 'knockout':
        lh *= KNOCKOUT_LAMBDA_FACTOR
        la *= KNOCKOUT_LAMBDA_FACTOR
    
    return round(lh, 4), round(la, 4)


def generate_monte_carlo(match_ids=None):
    data_dir = os.environ.get('BACKTEST_DATA_DIR')
    if not data_dir:
        script_dir = os.environ.get('BACKTEST_TMPDIR', os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(script_dir, 'data')
    locked = load_json(os.path.join(data_dir, 'locked_data.json'))
    factors = load_json(os.path.join(data_dir, 'factor_params.json'))
    match_info = load_json(os.path.join(data_dir, 'match_info.json'))
    factor_map = {m['id']: m for m in factors['matches']}
    info_map = {m['id']: m for m in match_info['matches']}
    results = []
    matches_to_process = locked['matches']
    if match_ids:
        matches_to_process = [m for m in locked['matches'] if m['id'] in match_ids]
        skipped_locked = len(locked['matches']) - len(matches_to_process)
        if skipped_locked > 0:
            print(f'[FILTER] --match-ids: processing {len(matches_to_process)}/{len(locked["matches"])} matches (not in locked: {skipped_locked})')
        # Log match_ids not found in locked_data
        locked_ids = {m['id'] for m in locked['matches']}
        missing = [mid for mid in match_ids if mid not in locked_ids]
        if missing:
            print(f'[FILTER] match_ids NOT in locked_data (will be skipped): {missing}')
    for match in matches_to_process:
        mid, home, away = match['id'], match['home'], match['away']
        if not home or not away:
            print('  [%s] data incomplete (home/away missing), skipped' % mid)
            continue
        if not match.get('jc_sp_win') and not match.get('jc_hhad_win'):
            if match.get('sp_missing'):
                print('  [%s] no SP odds (sp_missing=True), skipped' % mid)
                continue
        
        validate_temporal_integrity(match)
        
        print()
        print('-' * 60)
        print('  [%s] %s vs %s' % (mid, home, away))
        
        try:
            round_type = match.get('round_type', 'group')
            neutral_venue = match.get('neutral_venue', False)
            h_xg = match.get('home_xg'); h_xga = match.get('home_xga')
            a_xg = match.get('away_xg'); a_xga = match.get('away_xga')
            
            # Pre-tournament detection: if xG data is missing and teams exist in squad profiles,
            # use FIFA rank + squad value instead of traditional lambda calculation
            xg_missing = (h_xg is None and h_xga is None and a_xg is None and a_xga is None)
            if xg_missing and round_type in ('group', 'knockout'):
                from squad_power import estimate_match
                sq_result = estimate_match(
                    home, away,
                    round_type=round_type,
                    neutral_venue=neutral_venue)
                if sq_result is not None:
                    lh_raw = sq_result['lambda_h']
                    la_raw = sq_result['lambda_a']
                    pre_tournament = True
                    print('  [SQUAD-POWER] %s vs %s: λ=(%.4f, %.4f)' % (home, away, lh_raw, la_raw))
                else:
                    # Fallback to stats-based calculation if squad profiles unavailable
                    pre_tournament = False
                    lh_raw, la_raw = calc_initial_lambda_wc(0, 0, 0, 0,
                        match.get('home_league', ''), match.get('away_league', ''),
                        neutral_venue, match.get('home_confed'), match.get('away_confed'))
            else:
                pre_tournament = False
                # Use WC-specific calculation for World Cup matches
                if round_type in ('group', 'knockout'):
                    h_g = match.get('home_goals', 0) or 0
                    h_ga = match.get('home_goals_conceded', 0) or 0
                    a_g = match.get('away_goals', 0) or 0
                    a_ga = match.get('away_goals_conceded', 0) or 0
                    lh_raw, la_raw = calc_initial_lambda_wc(
                        home_xg=h_g, home_xga=h_ga,
                        away_xg=a_g, away_xga=a_ga,
                        home_league=match.get('home_league', ''),
                        away_league=match.get('away_league', ''),
                        neutral_venue=neutral_venue,
                        home_confed=match.get('home_confed'),
                        away_confed=match.get('away_confed'))
                elif None in [h_xg, h_xga, a_xg, a_xga]:
                    h_g = match.get('home_goals'); h_ga = match.get('home_goals_conceded')
                    a_g = match.get('away_goals'); a_ga = match.get('away_goals_conceded')
                    lh_raw, la_raw = calc_initial_lambda_alt(
                        home_goals=h_g, home_goals_conceded=h_ga,
                        away_goals=a_g, away_goals_conceded=a_ga,
                        home_league=match.get('home_league', ''), away_league=match.get('away_league', ''))
                else:
                    lh_raw, la_raw = calc_initial_lambda(
                        home_xg=h_xg, home_xga=h_xga, away_xg=a_xg, away_xga=a_xga,
                        home_league=match.get('home_league', ''), away_league=match.get('away_league', ''))
        except ValueError as e:
            print('  data missing: %s' % e)
            continue
        
        if mid in factor_map:
            lh_final, la_final = apply_factors(lh_raw, la_raw, factor_map[mid])
        else:
            lh_final, la_final = lh_raw, la_raw
        
        lambda_diff = round(lh_final - la_final, 4)
        if mid in info_map:
            info_map[mid]['lambda_diff'] = lambda_diff
        
        from validate import cross_validate, validate_wc_scenario, validate_fifa_rank
        cross_validate(match, lh_final, la_final, factor_map.get(mid, {}))
        
        # World Cup-specific validation
        if factor_map.get(mid, {}):
            wc_warnings = validate_wc_scenario(match, factor_map[mid], lh_final, la_final)
            for w in wc_warnings:
                print('  [WC-VALIDATE] ' + w)
        
        # FIFA rank validation (if available)
        fifa_h = match.get('fifa_rank_home')
        fifa_a = match.get('fifa_rank_away')
        if fifa_h and fifa_a:
            rank_warnings = validate_fifa_rank(fifa_h, fifa_a, lh_final, la_final)
            for w in rank_warnings:
                print('  [FIFA-RANK] ' + w)
        
        jc = match.get('jc_handicap', -1)
        engine = MonteCarloEngine(lambda_h=lh_final, lambda_a=la_final, jc_handicap=jc, runs=MONTE_CARLO_RUNS)
        result = engine.run()
        p, jp = result['physical'], result['jc_handicap']
        
        results.append({
            'id': mid, 'home': home, 'away': away,
            'lambda_raw_h': round(lh_raw, 4), 'lambda_raw_a': round(la_raw, 4),
            'lambda_h_final': lh_final, 'lambda_a_final': la_final, 'lambda_diff': lambda_diff,
            'jc_handicap': jc,
            'physical': {'home_win': round(p['home_win'], 4), 'draw': round(p['draw'], 4), 'away_win': round(p['away_win'], 4)},
            'jc_handicap_prob': {'rang_sheng': round(jp['rang_sheng'], 4), 'rang_ping': round(jp['rang_ping'], 4), 'rang_fu': round(jp['rang_fu'], 4)},
            'top2_total_goals': result['top2_total_goals'], 'top2_half_full': result['top2_half_full'], 'top3_scores': result['top3_scores']
        })
    
    valid_ids = {m['id'] for m in results}
    # Merge with existing MC results (don't destroy data when using --match-ids)
    mc_path = os.path.join(data_dir, 'monte_carlo_result.json')
    if match_ids and os.path.exists(mc_path):
        old_mc = load_json(mc_path)
        old_map = {m['id']: m for m in old_mc['matches']}
        for r in results:
            old_map[r['id']] = r
        save_json({'matches': list(old_map.values())}, mc_path)
    else:
        save_json({'matches': results}, mc_path)
    # Merge: update lambda_diff for processed matches, keep unprocessed entries
    for m in match_info['matches']:
        if m['id'] in valid_ids and m['id'] in info_map:
            ld = info_map[m['id']].get('lambda_diff')
            if ld is not None:
                m['lambda_diff'] = ld
    save_json(match_info, os.path.join(data_dir, 'match_info.json'))
    # Do NOT overwrite factor_params.json or ai_judgment.json -- keep all entries for future processing


def run_step(script_name, description):
    script_dir = os.environ.get('BACKTEST_TMPDIR', os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run([sys.executable, os.path.join(script_dir, script_name)], capture_output=False, cwd=script_dir)
    if result.returncode != 0:
        raise Exception('%s failed' % script_name)


def save_to_database():
    from database import insert_run, insert_match
    
    data_dir = os.environ.get('BACKTEST_DATA_DIR')
    if not data_dir:
        script_dir = os.environ.get('BACKTEST_TMPDIR', os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(script_dir, 'data')
    
    required = ['locked_data.json', 'factor_params.json', 'match_info.json',
                'monte_carlo_result.json', 'ddi_result.json',
                'fit_score_result.json', 'rating_result.json', 'ai_judgment.json']
    for f in required:
        if not os.path.exists(os.path.join(data_dir, f)):
            print('  [DB] skip: missing ' + f)
            return
    
    locked = load_json(os.path.join(data_dir, 'locked_data.json'))
    factors = load_json(os.path.join(data_dir, 'factor_params.json'))
    mc = load_json(os.path.join(data_dir, 'monte_carlo_result.json'))
    ddi = load_json(os.path.join(data_dir, 'ddi_result.json'))
    fit = load_json(os.path.join(data_dir, 'fit_score_result.json'))
    rating = load_json(os.path.join(data_dir, 'rating_result.json'))
    ai = load_json(os.path.join(data_dir, 'ai_judgment.json'))
    
    fm = {m['id']: m for m in factors['matches']}
    mm = {m['id']: m for m in mc['matches']}
    dm = {m['id']: m for m in ddi['matches']}
    fim = {m['id']: m for m in fit['matches']}
    rm = {m['id']: m for m in rating['matches']}
    am = {m['id']: m for m in ai['matches']}
    lm = {m['id']: m for m in locked['matches']}
    
    valid = set(mm.keys()) & set(dm.keys()) & set(fim.keys()) & set(rm.keys())
    if not valid:
        print('  [DB] no valid matches')
        return
    
    ds = locked['matches'][0].get('time', '')[:10] if locked['matches'] else ''
    run_id = insert_run(ds, run_type='live', prediction_date=datetime.date.today().strftime('%Y-%m-%d'))
    
    # Carry over actual_score/hit/diagnosis from previous runs
    import sqlite3 as _sql
    _db = _sql.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "framework.db"))
    _db.row_factory = _sql.Row
    _prev = {}
    for _r in _db.execute("SELECT match_id, actual_score, hit, diagnosis, half_full, half_time_score, jc_sp_home, jc_sp_draw, jc_sp_away, jc_hhad_win, jc_hhad_draw, jc_hhad_lose, jc_handicap FROM matches WHERE actual_score IS NOT NULL AND actual_score != '' ORDER BY run_id DESC").fetchall():
        if _r["match_id"] not in _prev:
            _prev[_r["match_id"]] = dict(_r)
    _db.close()

    # Load match_info.json for SP odds (field names: sp_home/sp_draw/sp_away)
    mi_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "match_info.json")
    _mi_map = {}
    if os.path.exists(mi_path):
        _mi_data = load_json(mi_path)
        for _m in _mi_data.get("matches", []):
            _mi_map[_m["id"]] = _m

    for mid in sorted(valid):
        lk = lm[mid]; md = mm[mid]; dd = dm[mid]; fd = fim[mid]['fit_score']; rd = rm[mid]; ad = am[mid]
        # SP odds: prefer match_info.json, fallback to previous DB run
        _misp = _mi_map.get(mid, {})
        _prv = _prev.get(mid, {})
        _sp_home = _misp.get("sp_home") or _prv.get("jc_sp_home")
        _sp_draw = _misp.get("sp_draw") or _prv.get("jc_sp_draw")
        _sp_away = _misp.get("sp_away") or _prv.get("jc_sp_away")
        _hhad_w = _misp.get("jc_hhad_win") or _prv.get("jc_hhad_win")
        _hhad_d = _misp.get("jc_hhad_draw") or _prv.get("jc_hhad_draw")
        _hhad_l = _misp.get("jc_hhad_lose") or _prv.get("jc_hhad_lose")
        _jc_hcp = _misp.get("jc_handicap") or _prv.get("jc_handicap") or lk.get("jc_handicap")
        m = {
            'match_id': mid, 'home': lk['home'], 'away': lk['away'],
            'event': lk.get('event', ''), 'match_time': lk.get('time', ''),
            'match_type': lk.get('match_type', ''), 'league': lk.get('home_league', ''),
            'asian_handicap': lk.get('asian_handicap'), 'jc_handicap': _jc_hcp,
            'handicap_change': lk.get('handicap_change'),
            'lambda_h_final': md.get('lambda_h_final'), 'lambda_a_final': md.get('lambda_a_final'),
            'lambda_diff': md.get('lambda_diff'),
            'physical_home_win': md['physical']['home_win'],
            'physical_draw': md['physical']['draw'],
            'physical_away_win': md['physical']['away_win'],
            'market_home_win': dd.get('market', {}).get('home_win'),
            'market_draw': dd.get('market', {}).get('draw'),
            'market_away_win': dd.get('market', {}).get('away_win'),
            'ddi_home_win': dd['ddi']['home_win'], 'ddi_draw': dd['ddi']['draw'], 'ddi_away_win': dd['ddi']['away_win'],
            'protection_triggered': dd.get('protection_triggered', False),
            'sp_missing': dd.get('sp_missing', True),
            'fit_score': fd['final_total'], 'rating': rd['rating'], 'direction': rd['direction'],
            'direction_warning': rd.get('direction_warning', False),
            'downgrade_count': rd.get('downgrade_count', 0), 'meltdown': rd.get('meltdown', False),
            'scenario_type': rd.get('scenario_type', ''),
            'top2_total_goals': md.get('top2_total_goals', []),
            'top2_half_full': md.get('top2_half_full', []),
            'top3_scores': md.get('top3_scores', []),
            's7_score': ad.get('s7_score'), 's7_reason': ad.get('s7_reason', ''),
            'trap_analysis': ad.get('trap_analysis', ''), 'key_risk': ad.get('key_risk', ''),
            'actual_score': _prev.get(mid, {}).get('actual_score'),
            'half_time_score': _prev.get(mid, {}).get('half_time_score'),
            'half_full': _prev.get(mid, {}).get('half_full'),
            'hit': _prev.get(mid, {}).get('hit'),
            'diagnosis': _prev.get(mid, {}).get('diagnosis'),
            # SP odds fields (NEW: prevent NULL overwrite)
            'jc_sp_home': _sp_home, 'jc_sp_draw': _sp_draw, 'jc_sp_away': _sp_away,
            'jc_hhad_win': _hhad_w, 'jc_hhad_draw': _hhad_d, 'jc_hhad_lose': _hhad_l,
        }
        # Auto-calculate hit for matches that already have actual_score but no hit
        if m['actual_score'] and m['hit'] is None and m['direction']:
            try:
                score = m['actual_score']
                if ':' in score:
                    hg, ag = map(int, score.split(':'))
                    hcp = m.get('jc_handicap') or 0
                    adj = hg + hcp - ag
                    dr = m['direction']
                    if dr == '让胜':    m['hit'] = 1 if adj > 0 else 0
                    elif dr == '让平':  m['hit'] = 1 if adj == 0 else 0
                    elif dr == '让负':  m['hit'] = 1 if adj < 0 else 0
                    elif dr == '胜':    m['hit'] = 1 if hg > ag else 0
                    elif dr == '负':    m['hit'] = 1 if hg < ag else 0
                    elif dr == '平':    m['hit'] = 1 if hg == ag else 0
                    m['diagnosis'] = '命中' if m['hit'] == 1 else '未命中'
            except:
                pass
        insert_match(run_id, m)
    
    print('  [DB] saved %d matches (run_id=%d)' % (len(valid), run_id))



def _merge_step_output(data_dir, match_ids, filename):
    '''After a pipeline step overwrites the output file, restore non-targeted matches from backup.
    Call BEFORE running the step to save backup, and AFTER to merge.'''
    import shutil
    path = os.path.join(data_dir, filename)
    bak = path + '.bak'
    if not os.path.exists(bak):
        # First call: save backup
        if os.path.exists(path):
            shutil.copy2(path, bak)
    else:
        # Second call: merge backup entries with new results
        if os.path.exists(path) and os.path.exists(bak):
            new_data = load_json(path)
            old_data = load_json(bak)
            new_map = {m['id']: m for m in new_data['matches']}
            old_map = {m['id']: m for m in old_data['matches']}
            # Restore entries for non-targeted matches
            for mid, entry in old_map.items():
                if mid not in match_ids:
                    new_map[mid] = entry
            save_json({'matches': list(new_map.values())}, path)
            os.remove(bak)

def main(match_ids=None):
    data_dir = os.environ.get('BACKTEST_DATA_DIR')
    if not data_dir:
        script_dir = os.environ.get('BACKTEST_TMPDIR', os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(script_dir, 'data')
    for f in ['locked_data.json', 'factor_params.json', 'match_info.json']:
        if not os.path.exists(os.path.join(data_dir, f)):
            print('[ERROR] missing ' + f)
            return
    generate_monte_carlo(match_ids=match_ids)
    if match_ids:
        _merge_step_output(data_dir, match_ids, 'ddi_result.json')
    run_step('ddi.py', 'DDI')
    if match_ids:
        _merge_step_output(data_dir, match_ids, 'ddi_result.json')
        _merge_step_output(data_dir, match_ids, 'fit_score_result.json')
    # Ensure ai_judgment.json has entries for all matches in ddi_result (fill missing with defaults)
    _ai_path = os.path.join(data_dir, 'ai_judgment.json')
    if os.path.exists(_ai_path):
        _ai_data = load_json(_ai_path)
        _ai_map = {m['id']: m for m in _ai_data['matches']}
        _ddi_data = load_json(os.path.join(data_dir, 'ddi_result.json'))
        _changed = False
        for _m in _ddi_data['matches']:
            if _m['id'] not in _ai_map:
                _ai_map[_m['id']] = {
                    'id': _m['id'], 's7_score': 5.0, 's7_reason': '缺省默认值',
                    'opponent_predictability': 0.5, 'opponent_reason': '',
                    'trap_analysis': '', 'key_risk': ''
                }
                _changed = True
        if _changed:
            _ai_data['matches'] = list(_ai_map.values())
            save_json(_ai_data, _ai_path)
            print('  [FILL] ai_judgment.json: total', len(_ai_data['matches']), 'entries')
    run_step('fit_score.py', 'Fit Score')
    if match_ids:
        _merge_step_output(data_dir, match_ids, 'fit_score_result.json')
        _merge_step_output(data_dir, match_ids, 'rating_result.json')
    run_step('rating.py', 'Rating')
    if match_ids:
        _merge_step_output(data_dir, match_ids, 'rating_result.json')
    run_step('save_history.py', 'History')
    save_to_database()
    print('[OK] All steps complete')


if __name__ == '__main__':
    import sys as _sys
    _match_ids = None
    if '--match-ids' in _sys.argv:
        idx = _sys.argv.index('--match-ids')
        if idx + 1 < len(_sys.argv):
            _match_ids = set(_sys.argv[idx + 1].split(','))
    main(match_ids=_match_ids)
