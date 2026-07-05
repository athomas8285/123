# monte_carlo.py
# V3.3.3-Core-Rev1.13 Step 6：泊松蒙特卡洛模拟（收敛验证版）

import numpy as np
from collections import Counter
from config import MONTE_CARLO_RUNS, HALF_TIME_RATIO, DISPERSION_ALPHA


class MonteCarloEngine:
    def __init__(self, lambda_h, lambda_a, jc_handicap, runs=None, random_seed=42, dispersion_alpha=None):
        self.lh = lambda_h
        self.la = lambda_a
        self.handicap = jc_handicap
        self.base_runs = runs if runs else MONTE_CARLO_RUNS
        self.seed = random_seed
        np.random.seed(self.seed)
        self.max_runs = 10000  # 上限
        self.convergence_std = 0.01  # 收敛标准差阈值
        self.dispersion_alpha = DISPERSION_ALPHA if dispersion_alpha is None else dispersion_alpha

    def run(self):
        """带收敛验证的蒙特卡洛模拟"""
        runs = self.base_runs
        converged = False

        while runs <= self.max_runs and not converged:
            n_r = 1.0 / self.dispersion_alpha
            p_h = n_r / (n_r + self.lh)
            p_a = n_r / (n_r + self.la)
            home_goals = np.random.negative_binomial(n_r, p_h, runs)
            away_goals = np.random.negative_binomial(n_r, p_a, runs)
            diff = home_goals - away_goals

            home_win = np.sum(diff > 0) / runs
            draw = np.sum(diff == 0) / runs
            away_win = np.sum(diff < 0) / runs

            # 检查收敛性：用Bootstrap抽样估计标准差
            if runs >= self.base_runs:
                boot_home = []
                for _ in range(100):
                    idx = np.random.choice(runs, runs, replace=True)
                    boot_home.append(np.sum(diff[idx] > 0) / runs)
                std_home = np.std(boot_home)
                if std_home < self.convergence_std:
                    converged = True
                elif not converged:
                    runs = min(runs + 500, self.max_runs)
            else:
                runs = min(runs + 500, self.max_runs)

        # 置信区间（Bootstrap方法）
        boot_home = []
        boot_draw = []
        boot_away = []
        for _ in range(200):
            idx = np.random.choice(runs, runs, replace=True)
            boot_home.append(np.sum(diff[idx] > 0) / runs)
            boot_draw.append(np.sum(diff[idx] == 0) / runs)
            boot_away.append(np.sum(diff[idx] < 0) / runs)

        ci_home = (np.percentile(boot_home, 2.5), np.percentile(boot_home, 97.5))
        ci_draw = (np.percentile(boot_draw, 2.5), np.percentile(boot_draw, 97.5))
        ci_away = (np.percentile(boot_away, 2.5), np.percentile(boot_away, 97.5))

        # 竞彩让球盘概率
        jc_score = diff + self.handicap
        rang_sheng = np.sum(jc_score > 0) / runs
        rang_ping = np.sum(jc_score == 0) / runs
        rang_fu = np.sum(jc_score < 0) / runs

        # 总进球TOP2
        total_goals = home_goals + away_goals
        goal_counter = Counter(total_goals)
        top2_total = [f"{g}球" for g, _ in goal_counter.most_common(2)]

        # 半全场TOP2
        n_r_ht = 1.0 / self.dispersion_alpha
        p_h_ht = n_r_ht / (n_r_ht + self.lh * HALF_TIME_RATIO)
        p_a_ht = n_r_ht / (n_r_ht + self.la * HALF_TIME_RATIO)
        half_h = np.random.negative_binomial(n_r_ht, p_h_ht, runs)
        half_a = np.random.negative_binomial(n_r_ht, p_a_ht, runs)
        half_diff = half_h - half_a
        half_result = np.where(half_diff > 0, '胜', np.where(half_diff == 0, '平', '负'))
        full_result = np.where(diff > 0, '胜', np.where(diff == 0, '平', '负'))
        ht_ft_labels = [f"{h}{f}" for h, f in zip(half_result, full_result)]
        ht_ft_counter = Counter(ht_ft_labels)
        top2_half_full = [label for label, _ in ht_ft_counter.most_common(2)]

        # 比分TOP3
        score_labels = [f"{h}-{a}" for h, a in zip(home_goals, away_goals)]
        score_counter = Counter(score_labels)
        top3_scores = [f"{s}" for s, _ in score_counter.most_common(3)]

        return {
            "physical": {
                "home_win": round(home_win, 4),
                "draw": round(draw, 4),
                "away_win": round(away_win, 4),
                "ci_home": f"{ci_home[0]*100:.1f}%-{ci_home[1]*100:.1f}%",
                "ci_draw": f"{ci_draw[0]*100:.1f}%-{ci_draw[1]*100:.1f}%",
                "ci_away": f"{ci_away[0]*100:.1f}%-{ci_away[1]*100:.1f}%",
                "converged": converged,
                "runs_used": runs
            },
            "jc_handicap": {
                "rang_sheng": round(rang_sheng, 4),
                "rang_ping": round(rang_ping, 4),
                "rang_fu": round(rang_fu, 4)
            },
            "top2_total_goals": top2_total,
            "top2_half_full": top2_half_full,
            "top3_scores": top3_scores,
            "lambda_params": {
                "lambda_h": self.lh,
                "lambda_a": self.la,
                "jc_handicap": self.handicap,
                "runs": runs,
                "converged": converged,
                "dispersion_alpha": self.dispersion_alpha
            }
        }