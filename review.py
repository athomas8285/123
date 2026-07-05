# review.py
# V3.3.3-Core-Rev1.13 Step 10: 复盘诊断（含P0-P4置信度分析）
import csv, json, os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
from collections import defaultdict

HISTORY_FILE = "history.csv"


def load_review(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def _check_confidence_issues(row):
    """P0-P2: 基于置信度/样本量字段的诊断"""
    issues = []
    h2h = row.get("h2h_confidence", "")
    xg_s = row.get("xg_season_confidence", "")
    xg_l3 = row.get("xg_last3_confidence", "")
    roster = row.get("roster_confidence", "")
    if h2h == "infer":
        issues.append("数据层：H2H数据为推断（置信度低）")
    if xg_s == "infer":
        issues.append("数据层：赛季xG数据为推断（置信度低）")
    if xg_l3 == "infer":
        issues.append("数据层：近3场xG数据为推断（置信度低）")
    if roster == "infer":
        issues.append("数据层：阵容数据为推断（置信度低）")
    if h2h == "infer" and xg_s == "infer" and xg_l3 == "infer":
        issues.append("数据层：多项核心xG数据均为推断，分析可靠性极低")
    try:
        home_s = int(row.get("xg_home_sample", 0) or 0)
        away_s = int(row.get("xg_away_sample", 0) or 0)
        l3_h = int(row.get("xg_last3_home_sample", 0) or 0)
        l3_a = int(row.get("xg_last3_away_sample", 0) or 0)
        min_s = min(home_s, away_s) if home_s > 0 and away_s > 0 else max(home_s, away_s)
        if 0 < min_s < 5:
            issues.append(f"数据层：xG样本量偏小（{min_s}场），统计可靠性不足")
    except:
        pass
    return issues


def diagnose(row):
    issues = []
    lh = float(row.get("lambda_final_h", 0) or 0)
    la = float(row.get("lambda_final_a", 0) or 0)
    diff = lh - la
    score = row.get("actual_score", "")
    direction = row.get("direction", "")
    if not score or ":" not in score:
        return ["诊断数据不完整"]
    try:
        hg, ag = map(int, score.split(":"))
    except:
        return ["比分解析失败"]
    if row.get("xg_season_missing") == "True":
        issues.append("数据层：赛季xG缺失")
    # P0-P2: 置信度/样本量诊断
    issues.extend(_check_confidence_issues(row))
    if diff > 0.5 and hg <= ag:
        issues.append(f"物理层：λ差{diff:.2f}指向主优，实际主未胜")
    elif diff < -0.3 and hg >= ag:
        issues.append(f"物理层：λ差{diff:.2f}指向客优，实际客未胜")
    elif abs(diff) < 0.3:
        if direction in ["胜", "让胜"] and hg <= ag:
            issues.append(f"物理层：λ差{diff:.2f}无法区分方向")
        elif direction in ["负", "让负"] and hg >= ag:
            issues.append(f"物理层：λ差{diff:.2f}无法区分方向")
    inj_h = float(row.get("injury_home", 0) or 0)
    inj_a = float(row.get("injury_away", 0) or 0)
    mot_h = float(row.get("motivation_home", 0) or 0)
    mot_a = float(row.get("motivation_away", 0) or 0)
    if abs(inj_h) > 0.15: issues.append(f"因子层：主队伤停修正{inj_h:+.0%}幅度偏大")
    if abs(inj_a) > 0.15: issues.append(f"因子层：客队伤停修正{inj_a:+.0%}幅度偏大")
    total_h = inj_h + mot_h
    total_a = inj_a + mot_a
    if abs(total_h) > 0.20: issues.append(f"因子层：主队总修正{total_h:+.0%}接近上限")
    if abs(total_a) > 0.20: issues.append(f"因子层：客队总修正{total_a:+.0%}接近上限")
    if diff < -0.2 and mot_h > 0.05: issues.append(f"因子层：物理面客优但主队战意+{mot_h:+.0%}")
    if diff > 0.2 and mot_a > 0.05: issues.append(f"因子层：物理面主优但客队战意+{mot_a:+.0%}")
    if row.get("pressure_triggered") == "True" and hg > ag: issues.append("因子层：压力型修正触发但主队仍赢球")
    if row.get("slack_triggered") == "True" and hg <= ag: issues.append("因子层：松懈修正触发但主队未受影响")
    ddi_h = float(row.get("ddi_home", 0) or 0)
    ddi_a = float(row.get("ddi_away", 0) or 0)
    if direction in ["胜", "让胜"] and ddi_h < -0.005: issues.append(f"市场层：DDI负值但推荐主队")
    if direction in ["负", "让负"] and ddi_a < -0.005: issues.append(f"市场层：DDI负值但推荐客队")
    fit = float(row.get("fit_score", 0) or 0)
    if fit > 8.0: issues.append(f"贴合度{fit:.1f}高贴合但仍未命中")
    return issues if issues else ["✓ 各层无显著偏差，可能为不可控因素"]


def count_modes(rows_list):
    mc = defaultdict(int)
    for r in rows_list:
        diag = r.get("diagnosis", "")
        if "物理层" in diag: mc["物理层偏差"] += 1
        if "因子层" in diag: mc["因子修正偏差"] += 1
        if "市场层" in diag or "诱盘" in diag: mc["诱盘方向误判"] += 1
        if "数据层" in diag: mc["数据质量不足"] += 1
        if "高贴合" in diag: mc["高贴合仍失败"] += 1
    return mc


def main():
    show_all = "--all" in sys.argv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_path = os.path.join(script_dir, HISTORY_FILE)
    if not os.path.exists(history_path):
        print("  📂 history.csv 不存在")
        return
    with open(history_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    review_path = os.path.join(script_dir, "data", "review.json")
    if not os.path.exists(review_path):
        print("  📂 review.json 不存在")
        return
    review_data = load_review(review_path)
    actual_map = {}
    this_round_keys = set()
    for m in review_data.get("matches", []):
        key = (m["id"], m.get("date", ""), m["home"])
        actual_map[key] = m.get("actual_score", "")
        this_round_keys.add(key)
    for row in rows:
        key = (row["id"], row["date"], row["home"])
        if key in actual_map and actual_map[key]:
            score = actual_map[key]
            row["actual_score"] = score
            if ":" in score:
                try:
                    hg, ag = map(int, score.split(":"))
                except:
                    continue
                direction = row.get("direction", "")
                diff_real = hg - ag
                jc_handicap = int(float(row.get("jc_handicap", 0) or 0))
                if direction in ("让胜", "让平", "让负") and abs(jc_handicap) < 0.001:
                    rid = row.get("id", "?")
                    print(f"  [WARN] [{rid}] direction={direction} but jc_handicap={jc_handicap}")
                if direction == "让胜":
                    hit = (diff_real + jc_handicap) > 0
                elif direction == "让平":
                    hit = (diff_real + jc_handicap) == 0
                elif direction == "让负":
                    hit = (diff_real + jc_handicap) < 0
                elif direction == "胜":
                    hit = hg > ag
                elif direction == "负":
                    hit = hg < ag
                elif direction == "平":
                    hit = hg == ag
                else:
                    hit = False
                row["hit"] = "True" if hit else "False"
                if hit:
                    row["diagnosis"] = "✅ 命中"
                else:
                    issues = diagnose(row)
                    detailed = []
                    for iss in issues:
                        if "物理层" in iss: detailed.append("物理层：λ差指向与实际赛果方向不一致")
                        elif "因子层" in iss: detailed.append("因子层：伤停/战意修正幅度可能不当")
                        elif "市场层" in iss: detailed.append("市场层：DDI负值但推荐该方向")
                        elif "数据层" in iss: detailed.append(f"{iss}")
                        elif "高贴合" in iss: detailed.append("贴合度≥8.0但仍未命中")
                        else: detailed.append(iss)
                    row["diagnosis"] = "；".join(detailed) if detailed else "✅ 命中"
    with open(history_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("=" * 70)
    print("  [[复盘诊断报告]]")
    if not show_all:
        print(f"  （本轮场次，共{len(this_round_keys)}场）")
        print(f"  [提示] 查看全部历史请用: python review.py --all")
    print("=" * 70)
    for row in rows:
        score = row.get("actual_score", "")
        if not score: continue
        key = (row["id"], row["date"], row["home"])
        if not show_all and key not in this_round_keys: continue
        mid, vs = row["id"], f"{row['home']} vs {row['away']}"
        direction = row.get("direction", "")
        hit = row.get("hit", "")
        diag = row.get("diagnosis", "")
        status = "✅ 命中" if hit == "True" else "❌ 未命中"
        print(f"\n  [{mid}] {vs}")
        print(f"      预测: {direction} | 实际: {score} | {status}")
        if hit == "False" and diag:
            for d in diag.split("；"):
                print(f"      → {d}")
    all_scored = [r for r in rows if r.get("actual_score")]
    total = len(all_scored)
    hit_count = sum(1 for r in all_scored if r.get("hit") == "True")
    this_round_rows = [r for r in all_scored if (r["id"], r["date"], r["home"]) in this_round_keys]
    this_total = len(this_round_rows)
    this_hit = sum(1 for r in this_round_rows if r.get("hit") == "True")
    if total > 0 and this_total > 0:
        print(f"\n{'='*70}")
        print(f"  累计统计（{total}场）                  本轮统计（{this_total}场）")
        print(f"{'='*70}")
        print(f"  总命中率：{hit_count}/{total} ({hit_count/total*100:.1f}%)")
        if this_total > 0:
            this_pct = this_hit/this_total*100
            total_pct = hit_count/total*100
            diff_pct = this_pct - total_pct
            diff_str = f"+{diff_pct:.1f}%" if diff_pct >= 0 else f"{diff_pct:.1f}%"
            print(f"                                    本轮命中率：{this_hit}/{this_total} ({this_pct:.1f}%)")
            print(f"                                    累计命中率：{hit_count}/{total} ({total_pct:.1f}%)")
            print(f"                                    本轮vs累计：{diff_str}")
    backup_path = os.path.join(script_dir, "data", "review_done.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(review_data, f, ensure_ascii=False, indent=2)
    
    # 同步更新数据库
    try:
        from database import update_result, get_db
        db = get_db()
        updated_db = 0
        for row in rows:
            score = row.get("actual_score", "").strip()
            if not score: continue
            hit_val = row.get("hit", "")
            if hit_val not in ("True", "False"):
                continue
            # 在 DB 中找匹配的 (match_id, home, away)
            sql = "SELECT run_id FROM matches WHERE match_id=? AND home=? AND away=? AND actual_score IS NULL"
            db_matches = db.execute(sql, (row["id"], row["home"], row["away"])).fetchall()
            for dbm in db_matches:
                update_result(row["id"], dbm["run_id"], score,
                             hit=(hit_val == "True"), diagnosis=row.get("diagnosis", ""))
                updated_db += 1
        db.close()
        if updated_db:
            print(f"  [DB] 已更新 {updated_db} 场比赛结果")
    except Exception as e:
        print(f"  [DB] 更新失败: {e}")
    
    print(f"\n  ✅ 复盘完成")
    if not show_all:
        print(f"  [提示] 查看全部历史请用: python review.py --all")


if __name__ == "__main__":
    main()
