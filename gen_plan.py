#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_plan.py V5.3 - 方向兼容矩阵 + 半全场top2 + 腿类排序 + 3.0档上限5.0"""

import json, math, os, sys
from collections import defaultdict
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ============ 方向兼容矩阵 ============

def _check(pred_type, hcp, leg_type, leg_opt):
    """Check if leg option is compatible with prediction at given handicap.
    Uses the compatibility matrix from analysis."""
    if leg_type == "\u65b9\u5411":
        return _direction_compatible(pred_type, hcp, leg_opt)
    elif leg_type == "\u65b9\u5411\u6253\u5305":
        parts = leg_opt.split("/")
        # Fix: handicap pack uses "\u5e73" but means "\u8ba9\u5e73", "\u8d1f" but means "\u8ba9\u8d1f"
        is_hcp = any("\u8ba9" in p for p in parts)
        mapped = []
        for p in parts:
            if is_hcp:
                if p == "\u5e73":
                    mapped.append("\u8ba9\u5e73")
                elif p == "\u8d1f":
                    mapped.append("\u8ba9\u8d1f")
                else:
                    mapped.append(p)
            else:
                mapped.append(p)
        return any(_direction_compatible(pred_type, hcp, p) for p in mapped)
    return True  # non-direction legs always pass

def _direction_compatible(pred, hcp, opt):
    """Simplified: only filter strict opposite. 平/让平 always pass."""
    # 平/让平 always compatible
    if opt in ("平", "平局", "让平"):
        return True

    # 胜 side: only filter 负
    if pred in ("胜", "让胜"):
        if hcp < 0:
            return opt not in ("负", "客胜")
        else:  # hcp >= 0 (home underdog, rare)
            return opt not in ("负", "客胜", "让负")

    # 负 side: only filter 胜
    if pred in ("负", "让负"):
        if hcp > 0:
            return opt not in ("胜", "主胜")
        else:  # hcp <= 0 (home favorite, rare for 让负)
            return opt not in ("胜", "主胜", "让胜")

    # 平: everything passes
    return True
    return True  # unknown


# ============ 腿类型历史命中率（排序用） ============

LEG_TYPE_RATE = {
    "方向": 0.453,       # direction consistent
    "方向打包": 0.80,     # direction pack consistent
    "半全场": 0.545,      # half-full top2 accuracy
    "半全场打包": 0.545,  # same as top2
}


# ============ 主流程 ============

def generate_plan(output_dir=None, predicted_only=False):
    info_data = load_json(os.path.join(DATA_DIR, "match_info.json"))
    rating_data = load_json(os.path.join(DATA_DIR, "rating_result.json"))
    mc_data = load_json(os.path.join(DATA_DIR, "monte_carlo_result.json"))
    
    import sqlite3
    db_hit = {}
    try:
        conn = sqlite3.connect(os.path.join(BASE_DIR, "framework.db"))
        cur = conn.cursor()
        cur.execute("SELECT match_id, hit FROM matches WHERE hit IS NOT NULL")
        for row in cur.fetchall():
            db_hit[row[0]] = row[1] == 1 or row[1] == "True" or row[1] == True
        conn.close()
    except:
        pass
    
    # Parse fundamental signals
    def parse_fundamental_signals(narrative):
        if not narrative: return [], []
        signals = []; risk_tags = []
        tag_map = {
            "出线形势：双方默契球可携手出线": "mutual_draw",
            "出线形势：已提前出线可轮换": "qualified_rotate",
            "出线形势：已淘汰": "eliminated",
            "出线形势：必须赢球": "must_win",
            "出线形势：双方都必须赢球": "must_win_both",
        }
        for text, tag in tag_map.items():
            if text in narrative:
                risk_tags.append(tag); signals.append(text)
        return signals, risk_tags
    
    fund_map = {}
    fa_path = os.path.join(DATA_DIR, "fundamental_analysis.json")
    if os.path.exists(fa_path):
        for m in load_json(fa_path):
            sig, tags = parse_fundamental_signals(m.get("narrative",""))
            fund_map[m["id"]] = {"signals":sig,"risk_tags":tags}
    
    info_map = {m["id"]:m for m in info_data["matches"]}
    rating_map = {m["id"]:m for m in rating_data["matches"]}
    mc_map = {m["id"]:m for m in mc_data["matches"]}

    all_legs = []
    match_map = {}
    match_warnings = {}
    
    for mid, info in info_map.items():
        if mid not in mc_map or mid not in rating_map: continue
        rat = rating_map[mid]; mc = mc_map[mid]
        direction = rat.get("direction","")
        if not direction: continue
        if predicted_only and rat.get("actual_score"): continue
        
        fit = rat.get("fit_score",0) or 0; rating_val = rat.get("rating","")
        phys = mc.get("physical",{}); lh = mc.get("lambda_h_final",1.0); la = mc.get("lambda_a_final",1.0)
        home = info.get("home",""); away = info.get("away","")
        mstr = f"{home} vs {away}"
        
        mt = rat.get("match_time","") or info.get("time","")
        # Skip future matches (prediction only for today or past)
        if mt and len(mt) >= 10:
            try:
                match_dt = datetime.strptime(mt[:10], "%Y-%m-%d")
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if match_dt > today + timedelta(days=1):
                    continue  # skip matches more than 1 day in the future
            except:
                pass
        # Derive display_date from match_id prefix (竞彩销售日)
        match_date = "unknown"
        if mt and len(mt) >= 10:
            wd_map = {"\u5468\u4e00": 0, "\u5468\u4e8c": 1, "\u5468\u4e09": 2, "\u5468\u56db": 3, "\u5468\u4e94": 4, "\u5468\u516d": 5, "\u5468\u65e5": 6}
            prefix = mid[:2]
            if prefix in wd_map:
                target = wd_map[prefix]
                dt = datetime.strptime(mt[:10], "%Y-%m-%d")
                days_back = (dt.weekday() - target) % 7
                match_date = (dt - timedelta(days=days_back)).strftime("%Y-%m-%d")
            else:
                match_date = mt[:10]
        
        hcp = info.get("jc_handicap", 0) or 0
        match_map[mid] = {
            "home":home,"away":away,"date":match_date,"direction":direction,
            "rating":rating_val,"fit":fit,
            "actual_score":info.get("actual_score",""),
            "half_full":info.get("half_full",""),
            "hit":db_hit.get(mid),
            "handicap":hcp
        }
        
        fund = fund_map.get(mid,{}); risk_tags = fund.get("risk_tags",[]); sig_text = fund.get("signals",[])
        if sig_text: match_warnings[mid] = sig_text
        
        sp_h = info.get("jc_sp_win"); sp_d = info.get("jc_sp_draw"); sp_a = info.get("jc_sp_lose")
        hh_w = info.get("jc_hhad_win"); hh_d = info.get("jc_hhad_draw"); hh_l = info.get("jc_hhad_lose")
        has_sp = sp_h is not None
        hcp_prob = mc.get("jc_handicap_prob",{})
        
        def add_leg(mid, match, match_date, typ, opt, odds, mp, src_mp, fit, rating, comps=None):
            if odds <= 1.0 or mp <= 0: return
            # Direction compatibility filter
            if typ in ("方向", "方向打包"):
                if not _check(direction, hcp, typ, opt): return
            leg = {
                "mid":mid,"match":match,"date":match_date,"type":typ,"option":opt,
                "odds":round(odds,2),"mp":round(mp,4),"src_mp":round(src_mp,4),
                "fit":round(fit,1),"rating":rating
            }
            leg["comps"] = comps if comps else [round(odds,2)]
            all_legs.append(leg)
        
        # ---- direction single legs ----
        if has_sp:
            if sp_h:
                mp = phys.get("home_win",0)
                add_leg(mid,mstr,match_date,"方向","主胜",float(sp_h),mp,mp,fit,rating_val)
            if sp_d:
                mp = phys.get("draw",0)
                add_leg(mid,mstr,match_date,"方向","平局",float(sp_d),mp,mp,fit,rating_val)
            if sp_a:
                mp = phys.get("away_win",0)
                add_leg(mid,mstr,match_date,"方向","客胜",float(sp_a),mp,mp,fit,rating_val)
        if hh_w:
            mp = hcp_prob.get("rang_sheng",0)
            add_leg(mid,mstr,match_date,"方向","让胜",float(hh_w),mp,mp,fit,rating_val)
        if hh_d:
            mp = hcp_prob.get("rang_ping",0)
            add_leg(mid,mstr,match_date,"方向","让平",float(hh_d),mp,mp,fit,rating_val)
        if hh_l:
            mp = hcp_prob.get("rang_fu",0)
            add_leg(mid,mstr,match_date,"方向","让负",float(hh_l),mp,mp,fit,rating_val)
        
        # ---- direction pack legs ----
        if has_sp and sp_h and sp_d:
            mp = phys.get("home_win",0)+phys.get("draw",0); odds = 1.0/(1.0/float(sp_h)+1.0/float(sp_d))
            add_leg(mid,mstr,match_date,"方向打包","胜/平",odds,mp,mp,fit,rating_val,
                    comps=[round(float(sp_h),2),round(float(sp_d),2)])
        if has_sp and sp_a and sp_d:
            mp = phys.get("away_win",0)+phys.get("draw",0); odds = 1.0/(1.0/float(sp_a)+1.0/float(sp_d))
            add_leg(mid,mstr,match_date,"方向打包","负/平",odds,mp,mp,fit,rating_val,
                    comps=[round(float(sp_a),2),round(float(sp_d),2)])
        if hh_w and hh_d:
            mp = hcp_prob.get("rang_sheng",0)+hcp_prob.get("rang_ping",0); odds = 1.0/(1.0/float(hh_w)+1.0/float(hh_d))
            add_leg(mid,mstr,match_date,"方向打包","让胜/平",odds,mp,mp,fit,rating_val,
                    comps=[round(float(hh_w),2),round(float(hh_d),2)])
        if hh_d and hh_l:
            mp = hcp_prob.get("rang_ping",0)+hcp_prob.get("rang_fu",0); odds = 1.0/(1.0/float(hh_d)+1.0/float(hh_l))
            add_leg(mid,mstr,match_date,"方向打包","让平/负",odds,mp,mp,fit,rating_val,
                    comps=[round(float(hh_d),2),round(float(hh_l),2)])
        
        # ---- half-full: from MC top2 ----
        top2_hf = mc.get("top2_half_full", [])
        hafu_odds = info.get("hafu_odds", {})
        if not hafu_odds:
            try:
                raw = _RAW_HAFU_CACHE
            except NameError:
                import json as _j
                rp = os.path.join(DATA_DIR, "raw_jczq.json")
                if os.path.exists(rp):
                    rd = _j.load(open(rp, "r", encoding="utf-8"))
                    _RAW_HAFU_CACHE = {}
                    for day in rd.get("value", {}).get("matchInfoList", []):
                        for m in day.get("subMatchList", []):
                            hf = m.get("hafu", {})
                            if hf:
                                _RAW_HAFU_CACHE[m.get("matchNumStr","")] = {k:float(v) if v and str(v)!="-1" else None for k,v in hf.items() if k in ("hh","hd","ha","dh","dd","da","ah","ad","aa")}
                    raw = _RAW_HAFU_CACHE
                else:
                    raw = {}
            hafu_odds = raw.get(mid, {})
        HAFU_KEY_MAP = {"胜胜":"hh","胜平":"hd","胜负":"ha","平胜":"dh","平平":"dd","平负":"da","负胜":"ah","负平":"ad","负负":"aa"}
        
        if top2_hf and hafu_odds:
            hf_legs_added = []
            for hf_opt in top2_hf:
                key = HAFU_KEY_MAP.get(hf_opt, "")
                if key and key in hafu_odds:
                    od = float(hafu_odds[key])
                    if od > 1.0:
                        mp = 1.0/od
                        add_leg(mid,mstr,match_date,"半全场",hf_opt,od,mp,mp,fit,rating_val)
                        hf_legs_added.append({"opt":hf_opt,"odds":od,"mp":mp})
            
            # Make pack leg from top2
            if len(hf_legs_added) == 2:
                opts = [l["opt"] for l in hf_legs_added]
                # Determine pack name
                if set(opts) == {"胜胜","平胜"}:
                    pack_name = "主不败"
                elif set(opts) == {"负负","平负"}:
                    pack_name = "客不败"
                else:
                    pack_name = None
                
                if pack_name:
                    p_odds = 1.0/sum(1.0/l["odds"] for l in hf_legs_added)
                    p_mp = sum(l["mp"] for l in hf_legs_added)
                    add_leg(mid,mstr,match_date,"半全场打包",pack_name,p_odds,p_mp,p_mp,fit,rating_val,
                            comps=[round(hf_legs_added[0]["odds"],2),round(hf_legs_added[1]["odds"],2)])
    
    
    # ---- substitute redundant pack legs for abs(handicap)==1 ----
    # hcp=-1: 方向打包(让胜/平) ≡ 方向(主胜), replace with 主胜 using 方向打包's hit rate
    # hcp=+1: 方向打包(让平/负) ≡ 方向(客胜), replace with 客胜 using 方向打包's hit rate
        # ---- display-only: substitute pack legs for abs(handicap)==1 ----
    for leg in all_legs:
        mid = leg["mid"]
        hcp = match_map.get(mid, {}).get("handicap", 0) or 0
        if abs(hcp) != 1:
            continue

        if hcp == -1 and leg["type"] == "方向打包" and leg["option"] == "让胜/平":
            for other in all_legs:
                if other["mid"] == mid and other["type"] == "方向" and other["option"] == "主胜":
                    if other["odds"] > leg["odds"]:
                        leg["display_option"] = other["option"]
                        leg["display_odds"] = other["odds"]
                    break

        if hcp == 1 and leg["type"] == "方向打包" and leg["option"] == "让平/负":
            for other in all_legs:
                if other["mid"] == mid and other["type"] == "方向" and other["option"] == "客胜":
                    if other["odds"] > leg["odds"]:
                        leg["display_option"] = other["option"]
                        leg["display_odds"] = other["odds"]
                    break


# ---- group by date ----
    date_groups = defaultdict(list)
    for l in all_legs:
        d = l["date"]
        if d not in date_groups:
            date_groups[d] = {"date":d,"match_ids":[]}
        if l["mid"] not in date_groups[d]["match_ids"]:
            date_groups[d]["match_ids"].append(l["mid"])
    
    dates = sorted(date_groups.keys())
    for d in dates:
        g = date_groups[d]
        m_ids = g["match_ids"]
        legs_for_date = [l for l in all_legs if l["mid"] in m_ids]
        
        combos = []
        for i in range(len(legs_for_date)):
            for j in range(i+1, len(legs_for_date)):
                l1, l2 = legs_for_date[i], legs_for_date[j]
                if l1["mid"] == l2["mid"]: continue
                c1 = l1.get("comps", [l1["odds"]]) if "打包" in l1["type"] else [l1["odds"]]
                c2 = l2.get("comps", [l2["odds"]]) if "打包" in l2["type"] else [l2["odds"]]
                paths = [o1*o2 for o1 in c1 for o2 in c2]
                stake = len(paths)
                min_ret = min(paths)/stake
                max_ret = max(paths)/stake
                
                # Use actual leg mp (DDI-computed hit probability) instead of market-implied
                lr1 = 1.0 / l1["odds"]
                lr2 = 1.0 / l2["odds"]
                type_hitrate = lr1 * lr2
                
                # EV = type_hitrate × average payout per unit stake
                ev = round(type_hitrate * (min_ret + max_ret) / 2, 4)
                min_fit = min(l1["fit"], l2["fit"])
                
                raw_opt_odds = l1["odds"] * l2["odds"]
                combos.append({
                    "l1":l1, "l2":l2,
                    "min_odds":round(min_ret,2), "max_odds":round(max_ret,2),
                    "opt_odds":round(raw_opt_odds,2), "raw_opt_odds":raw_opt_odds,
                    "hitrate":round(type_hitrate,4),
                    "ev":round(ev,4), "min_fit":min_fit
                })

        # 排序：先赔率最接近 2.0（用原始精确值），再保底回报最低，再市场 EV 最高
        combos.sort(key=lambda c: (abs(c["raw_opt_odds"] - 2.0), c["min_odds"], -c["ev"]))

        # plan_2: 逐步放宽赔率区间，直到有方案
        for upper in [2.2, 2.3, 2.4, 2.5]:
            plan_2 = [c for c in combos if 1.9 <= c["opt_odds"] and c["opt_odds"] <= upper]
            if plan_2:
                break
        plan_2 = plan_2[:5]

        # plan_3: 2.5~5.0 (opt_odds), TOP5
        plan_3 = [c for c in combos if 2.5 < c["opt_odds"] and c["opt_odds"] < 5.0][:5]
        
        g["plan_2"] = plan_2
        g["plan_3"] = plan_3
    
    data = {
        "date_groups": [date_groups[d] for d in dates],
        "matches": match_map,
        "legs": all_legs,
        "warnings": match_warnings,
    }
    
    out_path = os.path.join(output_dir or DATA_DIR, "plan_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"已生成: {out_path}")
    print(f"  {len(dates)} 个比赛日, {len(all_legs)} 条腿")
    for g in data["date_groups"]:
        print(f"  {g['date']}: {len(g['match_ids'])} 场, 2.0方案={len(g.get('plan_2',[]))}, 3.0方案={len(g.get('plan_3',[]))}")
    return data

if __name__ == "__main__":
    predicted = "--predicted" in sys.argv
    generate_plan(predicted_only=predicted)
