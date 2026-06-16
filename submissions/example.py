"""
Example submission — Intermediate level

Approach:
  - predict()          : blend 60% Polymarket champion odds + 40% Elo
  - predict_champion() : blend 70% Polymarket + 30% Elo prior
  - DARK_HORSE         : Morocco (đi sâu nhờ tổ chức tốt và phong độ ổn định)
"""

import math


def normalize(probs: dict) -> dict:
    total = sum(probs.values())
    if total <= 0:
        return {k: 1.0 / len(probs) for k in probs}
    return {k: v / total for k, v in probs.items()}


def predict(match: dict, teams: dict, market_data: dict) -> dict:
    team_a      = match["team_a"]
    team_b      = match["team_b"]
    is_knockout = match["stage"] != "Group Stage"

    elo_a = teams.get(team_a, {}).get("elo", 1500)
    elo_b = teams.get(team_b, {}).get("elo", 1500)
    pm    = market_data["polymarket_probability"]
    pm_a  = pm.get(team_a, 0.0)
    pm_b  = pm.get(team_b, 0.0)

    elo_str_a = math.exp(elo_a / 400)
    elo_str_b = math.exp(elo_b / 400)
    elo_win_a = elo_str_a / (elo_str_a + elo_str_b)

    if pm_a + pm_b > 0:
        pm_win_a = pm_a / (pm_a + pm_b)
        win_a    = 0.6 * pm_win_a + 0.4 * elo_win_a
    else:
        win_a = elo_win_a

    win_b     = 1 - win_a
    elo_diff  = abs(elo_a - elo_b)
    draw_prob = 0.27 * math.exp(-elo_diff / 700)

    raw = {
        "team_a": win_a * (1 - draw_prob),
        "draw":   draw_prob,
        "team_b": win_b * (1 - draw_prob),
    }
    if is_knockout:
        raw["draw"] = 0.0
    return normalize(raw)


def predict_champion(teams: dict, market_data: dict) -> dict:
    pm        = market_data["polymarket_probability"]
    elo_prior = normalize({t: math.exp(info["elo"] / 200)
                           for t, info in teams.items()})
    blended   = {}
    for t in teams:
        p_market = pm.get(t, 0.0)
        if p_market > 0:
            blended[t] = 0.7 * p_market + 0.3 * elo_prior[t]
        else:
            blended[t] = elo_prior[t]
    return normalize(blended)


# Ngựa ô: Morocco — phong độ tốt, tổ chức kỷ luật, dễ gây bất ngờ
DARK_HORSE: str = "Morocco"
