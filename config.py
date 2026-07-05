# config.py
# V3.3.3-Core-Rev1.12 全局配置文件

# ============================================
# 联赛平均 xGA（预期失球）参考值
# ============================================
LEAGUE_AVG_XGA = {
    "英超": 1.40,
    "西甲": 1.35,
    "阿甲": 1.25,
    "巴拉圭甲": 1.15,
    "玻利维亚甲": 1.20,
    "巴甲": 1.30,
    "乌甲": 1.15,
    "哥伦甲": 1.30,
    "委内瑞拉超": 1.45,
    "厄瓜多尔甲": 1.20,
    "秘鲁甲": 1.35,
    "智利甲": 1.30,
    "墨超": 1.30,
    "美职联": 1.45,
    "法甲": 1.30,
    "德甲": 1.35,
    "意甲": 1.25,
    "葡超": 1.25,
    "葡甲": 1.30,
    "荷甲": 1.45,
    "苏超": 1.35,
    "瑞典超": 1.40,
    "挪超": 1.45,
    "芬超": 1.35,
    "日职": 1.35,
    "韩K": 1.25,
    "澳超": 1.50,
    "默认": 1.35
}

# ============================================
# 跨联赛兑换系数（基于2024+2025+2026解放者杯280场）
# ============================================
LEAGUE_EXCHANGE_RATE = {
    "巴甲": 0.89,
    "阿甲": 0.94,
    "智利甲": 1.05,
    "秘鲁甲": 1.09,
    "巴拉圭甲": 1.01,
    "玻利维亚甲": 1.14,
    "厄瓜多尔甲": 1.02,
    "乌甲": 0.96,
    "委内瑞拉超": 1.08,
    "哥伦甲": 0.97,
}

# ============================================
# 蒙特卡洛模拟参数
# ============================================
MONTE_CARLO_RUNS = 2000
HALF_TIME_RATIO = 0.44

# ============================================
# DDI 校准参数
# ============================================
D_KELLY_DEFAULT = 0.05
VBAL_DEFAULT = 0.15              # 资金流偏差默认值（Rev1.13：修复DDI归零问题）
DDI_TRIGGER_THRESHOLD = 0.08
DDI_AMPLITUDE_CAP = 0.05
DDI_AMPLITUDE_RATIO = 0.3
AWAY_COLD_TREATMENT = 0.08
DDI_MISCALIBRATION_THRESHOLD = 0.005

# ============================================
# 战意修正硬上限
# ============================================
MOTIVATION_CAP_PLAYOFF = 0.05
MOTIVATION_CAP_REGULAR = 0.15

# ============================================
# 因子修正约束
# ============================================
INJURY_CORE_MAX = 0.20
INJURY_ROTATION_MAX = 0.05
SLACK_PENALTY = 0.08
ALTITUDE_BONUS = 0.15
ALTITUDE_THRESHOLD = 2500

# ============================================
# 贴合度评分参数
# ============================================
FIT_SCORE_THRESHOLD_MELTDOWN = 4.0
FIT_SCORE_THRESHOLD_BACKUP = 6.0
OPPONENT_PREDICTABILITY_MIN = 0.90

# ============================================
# 风控降级参数
# ============================================
DEEP_HANDICAP_THRESHOLD = 2.0
MID_HANDICAP_MIN = 1.0
MID_HANDICAP_MAX = 1.25
MID_HANDICAP_LAMBDA_DIFF = 0.5





# ============================================
# World Cup extensions (V3.3.3-Core-Rev1.15)
# ============================================


# ============================================
# ??????? (V3.3.3-Core-Rev1.15)
# ============================================

# ???? - ?????????
CONFED_DEFLATION = {
    "UEFA": 1.0,
    "CONMEBOL": 0.92,
    "CONCACAF": 0.78,
    "CAF": 0.72,
    "AFC": 0.75,
    "OFC": 0.55,
}

# ??????? league_avg_xGA
CONFED_DEFAULT_XGA = {
    "UEFA": 1.35,
    "CONMEBOL": 1.30,
    "CONCACAF": 1.20,
    "CAF": 1.15,
    "AFC": 1.20,
    "OFC": 1.10,
}

# ???????
WORLD_CUP_AVG_XGA = 1.35
KNOCKOUT_LAMBDA_FACTOR = 0.90

# ?????? lambda ????
GROUP_MATCHDAY_FACTOR = {1: 0.97, 2: 1.0, 3: 1.03}

# ?????????????
KEY_PLAYER_INJURY_BOOST = 0.10
INJURY_WORLD_CUP_MAX = 0.35

# ??????
NEUTRAL_VENUE_HOME_ADVANTAGE = 0.0
NEUTRAL_VENUE_ALTITUDE_FACTOR = 0.0

# FIFA??????
FIFA_RANK_DIFF_THRESHOLD = 30
FIFA_RANK_CLOSE_THRESHOLD = 10


# Negative binomial dispersion
DISPERSION_ALPHA = 0.35
