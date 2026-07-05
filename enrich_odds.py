# -*- coding: utf-8 -*-
"""
enrich_odds.py - Enrich match_info.json and locked_data.json with real odds
from the 竞彩网 API raw data (raw_jczq.json).

Adds these fields when available:
  - jc_sp_win / jc_sp_draw / jc_sp_lose   (from had pool)
  - jc_hhad_win / jc_hhad_draw / jc_hhad_lose  (from hhad pool)
  - jc_handicap (goalLine, int)
  - ttg_odds (dict of goal-count->odds)
  - crs_odds (dict of scoreline->odds)
  - hafu_odds (dict of htft_code->odds)

Usage:
    python enrich_odds.py [--data-dir DIR]
"""

import json
import os
import re
import sys


def _data_dir():
    if len(sys.argv) > 1 and sys.argv[1] == "--data-dir" and len(sys.argv) > 2:
        return sys.argv[2]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "data")


def extract_match_id(match_num_str):
    return match_num_str


def build_jczq_map(raw_data):
    jczq_map = {}
    for day in raw_data.get("value", {}).get("matchInfoList", []):
        for sub in day.get("subMatchList", []):
            mid = sub.get("matchNumStr", "")
            if mid:
                jczq_map[mid] = sub
    return jczq_map


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return default


def enrich_match(match, jczq_entry):
    had = jczq_entry.get("had", {})
    if had.get("h") is not None:
        match["jc_sp_win"] = _safe_float(had["h"])
        match["jc_sp_draw"] = _safe_float(had["d"])
        match["jc_sp_lose"] = _safe_float(had["a"])

    hhad = jczq_entry.get("hhad", {})
    if hhad.get("h") is not None:
        match["jc_hhad_win"] = _safe_float(hhad["h"])
        match["jc_hhad_draw"] = _safe_float(hhad["d"])
        match["jc_hhad_lose"] = _safe_float(hhad["a"])

    gl = jczq_entry.get("goalLine")
    if gl is not None:
        match["jc_handicap"] = int(gl)
    elif jczq_entry.get("hhad", {}).get("goalLine"):
        match["jc_handicap"] = int(jczq_entry["hhad"]["goalLine"])

    _meta_keys = {"goalLine", "goalLineValue", "updateDate", "updateTime", "id"}

    def _odds_only(d):
        return {k: _safe_float(v) for k, v in d.items()
                if not k.endswith("f") and k not in _meta_keys and _safe_float(v)}

    ttg = jczq_entry.get("ttg", {})
    if ttg:
        match["ttg_odds"] = _odds_only(ttg)

    crs = jczq_entry.get("crs", {})
    if crs:
        match["crs_odds"] = _odds_only(crs)

    hafu = jczq_entry.get("hafu", {})
    if hafu:
        match["hafu_odds"] = _odds_only(hafu)
def enrich_file(filepath, jczq_map, in_place=True):
    if not os.path.exists(filepath):
        print(f"  [SKIP] file not found: {filepath}")
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched_count = 0
    for match in data.get("matches", []):
        mid = match.get("id", "")
        if mid in jczq_map:
            enrich_match(match, jczq_map[mid])
            enriched_count += 1

    if in_place and enriched_count > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] {os.path.basename(filepath)}: enriched {enriched_count}/{len(data.get('matches', []))} matches")
    return data


def main():
    ddir = _data_dir()
    raw_path = os.path.join(ddir, "raw_jczq.json")

    if not os.path.exists(raw_path):
        print(f"[ERROR] raw_jczq.json not found at {raw_path}")
        print("  Run fetch_jczq.py first to download 竞彩网 data.")
        sys.exit(1)

    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    jczq_map = build_jczq_map(raw_data)
    print(f"Loaded {len(jczq_map)} matches from 竞彩网 API")

    for fname in ("match_info.json", "locked_data.json"):
        enrich_file(os.path.join(ddir, fname), jczq_map)

    print("[OK] Enrichment complete")


if __name__ == "__main__":
    main()

