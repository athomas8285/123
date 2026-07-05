# pipeline.py
# V3.3.3-Core-Rev1.13 文件监听自动化管道（修正版）
# 将 locked_data.json 和 factor_params.json 放入 data/input/ → 自动分析 → 保存结果
# 即使分析失败也会归档文件，避免无限重试

import json
import os
import sys
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = BASE_DIR / "data" / "input"
OUTPUT_DIR = BASE_DIR / "data" / "output"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATA_DIR = BASE_DIR / "data"

for d in [INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def generate_match_id(data):
    content = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode()).hexdigest()[:8]


def looks_like_locked_data(data):
    return isinstance(data, dict) and 'matches' in data and len(data['matches']) > 0


def looks_like_factors(data):
    if not isinstance(data, dict) or 'matches' not in data:
        return False
    matches = data.get('matches', [])
    if not matches:
        return False
    # 检查是否包含因子关键字段
    first = matches[0]
    return ('motivation_home' in first or 'injury_home' in first)


def process_batch(locked_file, factor_file):
    """处理一批数据：locked_data.json + factor_params.json，失败也会归档"""
    print(f"\n{'='*60}")
    print(f"  检测到新文件:")
    print(f"    数据: {locked_file.name}")
    print(f"    因子: {factor_file.name}")
    print(f"{'='*60}")

    match_id = "unknown"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def archive_files(tag=""):
        """归档输入文件"""
        prefix = f"{tag}_{match_id}_{timestamp}" if tag else f"{match_id}_{timestamp}"
        processed_subdir = PROCESSED_DIR / prefix
        processed_subdir.mkdir(exist_ok=True)
        shutil.move(str(locked_file), str(processed_subdir / locked_file.name))
        shutil.move(str(factor_file), str(processed_subdir / factor_file.name))
        print(f"  [OK] 文件已归档到: {processed_subdir}")
        return processed_subdir

    try:
        # 读取数据
        with open(locked_file, 'r', encoding='utf-8') as f:
            locked_data = json.load(f)
        with open(factor_file, 'r', encoding='utf-8') as f:
            factor_data = json.load(f)

        if not looks_like_locked_data(locked_data):
            print(f"  [ERROR] locked_data 格式不正确")
            archive_files("format_error")
            return False
        if not looks_like_factors(factor_data):
            print(f"  [ERROR] factor_params 格式不正确")
            archive_files("format_error")
            return False

        match_count = len(locked_data.get('matches', []))
        factor_count = len(factor_data.get('matches', []))
        match_id = generate_match_id(locked_data)
        print(f"  比赛ID: {match_id}，共 {match_count} 场，因子 {factor_count} 条")

        # 保存到 data/ 目录
        shutil.copy(locked_file, DATA_DIR / "locked_data.json")
        shutil.copy(factor_file, DATA_DIR / "factor_params.json")
        print(f"  [OK] 数据文件已复制到 data/")

        # 创建 match_info.json
        info_matches = []
        for m in locked_data.get('matches', []):
            info_matches.append({
                "id": m.get('id', ''),
                "home": m.get('home', ''),
                "away": m.get('away', ''),
                "event": m.get('event', ''),
                "time": m.get('time', ''),
                "sp_home": m.get('sp_home'),
                "sp_draw": m.get('sp_draw'),
                "sp_away": m.get('sp_away'),
                "initial_sp_home": m.get('initial_sp_home'),
                "initial_sp_draw": m.get('initial_sp_draw'),
                "initial_sp_away": m.get('initial_sp_away'),
                "asian_handicap": m.get('asian_handicap', 0),
                "handicap_change": m.get('handicap_change', 0),
                "match_type": m.get('match_type', '常规'),
                "is_home_life_death": m.get('is_home_life_death', False),
                "lambda_diff": 0,
                "physical_direction": "home",
                "predicted_direction": "home",
                # ===== 数据置信度分层 (P0) =====
                # data_confidence: "api"=API直接返回, "calc"=推算, "infer"=纯推理
                "h2h_confidence": "api" if not m.get('h2h_missing') else "infer",
                "xg_last3_confidence": "calc" if not m.get('xg_last3_missing') else "infer",
                "xg_season_confidence": "api" if not m.get('xg_season_missing') else "infer",
                "roster_confidence": "api" if not m.get('roster_missing') else "infer",
                "injury_home_confidence": "api" if not m.get('injury_home_missing') else "infer",
                "injury_away_confidence": "api" if not m.get('injury_away_missing') else "infer",
                "injury_source_confidence": "calc" if not m.get('injury_source_unreliable') else "infer",
                "motivation_confidence": "calc" if not m.get('motivation_ambiguous') else "infer",
                # ===== 样本量字段 (P1) =====
                "xg_home_sample": m.get('xg_home_sample', 0),
                "xg_away_sample": m.get('xg_away_sample', 0),
                "xg_last3_home_sample": m.get('xg_last3_home_sample', 0),
                "xg_last3_away_sample": m.get('xg_last3_away_sample', 0),
                # xg数据来源赛事类型（用于跨赛事对比检测）
                "xg_home_source_events": m.get('xg_home_source_events', ''),
                "xg_away_source_events": m.get('xg_away_source_events', ''),
                # ===== 保留原有字段 =====
                "h2h_missing": m.get('h2h_missing', False),
                "xg_last3_missing": m.get('xg_last3_missing', False),
                "xg_season_missing": m.get('xg_season_missing', False),
                "roster_missing": m.get('roster_missing', False),
                "injury_home_missing": m.get('injury_home_missing', False),
                "injury_away_missing": m.get('injury_away_missing', False),
                "injury_source_unreliable": m.get('injury_source_unreliable', False),
                "no_coach_statement": m.get('no_coach_statement', False),
                "motivation_ambiguous": m.get('motivation_ambiguous', False),
                "multi_team_linkage": m.get('multi_team_linkage', False),
                "away_xg_missing": m.get('away_xg_missing', False),
                "home_goals": m.get('home_goals', m.get('home_xg')),
                "home_goals_conceded": m.get('home_goals_conceded', m.get('home_xga')),
                "away_goals": m.get('away_goals', m.get('away_xg')),
                "away_goals_conceded": m.get('away_goals_conceded', m.get('away_xga'))
            })
        with open(DATA_DIR / "match_info.json", 'w', encoding='utf-8') as f:
            json.dump({"matches": info_matches}, f, ensure_ascii=False, indent=2)
        print(f"  [OK] match_info.json 已生成")

        # 创建 ai_judgment.json（占位）
        ai_placeholder = {"matches": [{"id": m['id'], "s7_score": 0, "s7_reason": "",
                                         "opponent_predictability": 1.0, "opponent_reason": "",
                                         "trap_analysis": "", "key_risk": ""} for m in info_matches]}
        with open(DATA_DIR / "ai_judgment.json", 'w', encoding='utf-8') as f:
            json.dump(ai_placeholder, f, ensure_ascii=False, indent=2)
        print(f"  [OK] ai_judgment.json 已生成（占位）")

        # 时序完整性检测 (P4)
        from lambda_calc import validate_temporal_integrity
        for m in locked_data.get('matches', []):
            validate_temporal_integrity(m)
        print(f"  [OK] 时序完整性检测完成")

        # 运行全流程分析
        print(f"  运行全流程分析...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "run_all.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            print(f"  [ERROR] 分析失败: {error_msg[-500:]}")
            archive_files("error")
            return False

        print(f"  [OK] 全流程分析完成")

        # 打印汇总表
        rating_path = DATA_DIR / "rating_result.json"
        if rating_path.exists():
            with open(rating_path, 'r', encoding='utf-8') as f:
                rating = json.load(f)
            print(f"\n  *** SUMMARY TABLE ***")
            for i, r in enumerate(rating['matches'], 1):
                direction = r.get('direction', '')
                fit = r.get('fit_score', 0)
                rating_label = r.get('rating', '')
                vs = f"{r['home']} vs {r['away']}"
                print(f"  {i}. [{r['id']}] {vs} -> {direction} (fit={fit:.1f}, {rating_label})")

        # 保存结果到输出目录
        output_match_dir = OUTPUT_DIR / f"{match_id}_{timestamp}"
        output_match_dir.mkdir(exist_ok=True)
        for fname in ['rating_result.json', 'fit_score_result.json', 'ddi_result.json', 'monte_carlo_result.json']:
            src = DATA_DIR / fname
            if src.exists():
                shutil.copy(src, output_match_dir / fname)
        print(f"\n  [OK] 结果已保存到: {output_match_dir}")

        # 归档输入文件
        archive_files()
        return True

    except Exception as e:
        print(f"  [EXCEPTION] 处理失败: {e}")
        try:
            archive_files("exception")
        except:
            pass
        return False


def monitor():
    """监听 input 文件夹"""
    print("=" * 60)
    print("  V3.3.3-Core-Rev1.13 自动化分析管道")
    print(f"  监听文件夹: {INPUT_DIR}")
    print(f"  将 locked_data.json 和 factor_params.json 放入此文件夹")
    print(f"  按 Ctrl+C 停止")
    print("=" * 60)

    while True:
        locked_files = list(INPUT_DIR.glob("locked_data*.json"))
        factor_files = list(INPUT_DIR.glob("factor_params*.json"))
        processed_this_cycle = set()

        for lf in locked_files:
            if lf.name in processed_this_cycle:
                continue
            # 找对应的 factor_params 文件
            base_name = lf.stem.replace("locked_data", "")
            matching_factor = None
            for ff in factor_files:
                ff_base = ff.stem.replace("factor_params", "")
                if ff_base == base_name or (base_name == "" and ff_base == ""):
                    matching_factor = ff
                    break
            if not matching_factor and factor_files:
                # 取第一个未匹配的
                for ff in factor_files:
                    if ff.name not in processed_this_cycle:
                        matching_factor = ff
                        break

            if matching_factor:
                processed_this_cycle.add(lf.name)
                processed_this_cycle.add(matching_factor.name)
                process_batch(lf, matching_factor)

        time.sleep(3)


if __name__ == "__main__":
    monitor()