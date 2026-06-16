"""
QuantVN Oracle Challenge — World Cup 2026
==========================================
File này có 3 phần bạn cần điền:

  1. predict()         — dự đoán kết quả từng trận (win/draw/loss), trước mỗi trận
  2. predict_champion() — dự đoán xác suất vô địch 48 đội, deadline trước 28/6 23:59 UTC+7
  3. DARK_HORSE        — tên 1 đội "ngựa ô" bạn cược sẽ gây bất ngờ, cùng deadline

Hướng dẫn:
  1. Đọc docstring từng hàm bên dưới
  2. Viết logic trong phần # YOUR MODEL HERE
  3. Chạy thử: python predict_template.py
  4. Đổi tên thành <tên-bạn>.py và submit

Không được sửa:
  - Tên hàm predict() / predict_champion()
  - Kiểu dữ liệu input / output
"""

import json

# ── Bạn có thể thêm import ở đây ──────────────────────────────────────────
# import math
# import numpy as np
# ──────────────────────────────────────────────────────────────────────────


def normalize(probs: dict) -> dict:
    """Chuẩn hoá để tổng xác suất = 1.0."""
    total = sum(probs.values())
    if total <= 0:
        return {k: 1.0 / len(probs) for k in probs}
    return {k: v / total for k, v in probs.items()}


def predict(match: dict, teams: dict, market_data: dict) -> dict:
    """
    Dự đoán xác suất kết quả 1 trận đấu.

    Parameters
    ----------
    match : dict
        Thông tin trận đấu (từ data/matches.json), ví dụ:
        {
            "match_id": "M001",
            "stage": "Group Stage",
            "group": "A",
            "team_a": "Mexico",
            "team_b": "South Africa",
            "datetime_utc7": "2026-06-12 06:00",
            "score_a": null,      ← luôn null lúc dự đoán (chưa đá)
            "score_b": null,
            "result": null
        }

    teams : dict
        Thông tin tĩnh của các đội (từ data/teams.json):
        {
            "Brazil": {"fifa_rank": 4, "elo": 2078, "confederation": "CONMEBOL"},
            "France": {"fifa_rank": 2, "elo": 2005, ...},
            ...
        }

    market_data : dict
        Dữ liệu live từ Polymarket — xác suất vô địch toàn giải của mỗi đội
        (dùng làm tín hiệu sức mạnh tương đối):
        {
            "polymarket_probability": { "Brazil": 0.18, "France": 0.14, ... },
            "volume":    { "Brazil": 128400.0, ... },
            "liquidity": { "Brazil": 34200.0, ... },
            "market_found": True,
            "teams_with_market": 44,
        }

    Returns
    -------
    dict
        Xác suất 3 kết quả (Group Stage) hoặc 2 kết quả (Knockout — bỏ "draw" = 0):
        {
            "team_a": 0.45,   ← xác suất team_a thắng
            "draw":   0.28,   ← xác suất hoà (Group Stage); 0.0 ở Knockout
            "team_b": 0.27,   ← xác suất team_b thắng
        }
        Tổng phải = 1.0 (evaluator tự normalize nếu lệch nhỏ).

    Notes
    -----
    - Knockout stages (Round of 32 trở đi): kết quả thực tế không bao giờ là "draw"
      (ai thua thì bị loại, dù qua extra-time/penalties). Đặt draw = 0.0 ở knockout.
    - Đội "TBD" ở knockout chưa xác định → evaluator sẽ bỏ qua trận đó.
    """
    team_a = match["team_a"]
    team_b = match["team_b"]
    stage  = match["stage"]

    is_knockout = stage != "Group Stage"

    # ── YOUR MODEL HERE ───────────────────────────────────────────────────
    #
    # 🟢 Beginner — dùng Elo để ước lượng sức mạnh tương đối:
    #
    import math
    elo_a = teams.get(team_a, {}).get("elo", 1500)
    elo_b = teams.get(team_b, {}).get("elo", 1500)
    #
    # Công thức Elo win probability:
    win_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    win_b = 1 / (1 + 10 ** ((elo_a - elo_b) / 400))
    #
    # Ước lượng tỉ lệ hoà dựa trên Elo gần nhau (đội cân sức → hoà nhiều hơn):
    elo_diff = abs(elo_a - elo_b)
    draw_base = 0.28 * math.exp(-elo_diff / 600)   # khoảng 10–28%
    #
    raw = {
        "team_a": win_a * (1 - draw_base),
        "draw":   draw_base,
        "team_b": win_b * (1 - draw_base),
    }
    #
    # 🟡 Intermediate — blend Elo với Polymarket champion odds:
    # pm = market_data["polymarket_probability"]
    # p_a = pm.get(team_a, 0.0)
    # p_b = pm.get(team_b, 0.0)
    # if p_a + p_b > 0:
    #     market_win_a = p_a / (p_a + p_b)
    #     market_win_b = p_b / (p_a + p_b)
    #     elo_win_a    = win_a / (win_a + win_b)
    #     blended_a    = 0.6 * market_win_a + 0.4 * elo_win_a
    #     blended_b    = 1 - blended_a
    #     raw = {"team_a": blended_a * (1 - draw_base),
    #            "draw":   draw_base,
    #            "team_b": blended_b * (1 - draw_base)}
    #
    # ──────────────────────────────────────────────────────────────────────

    if is_knockout:
        raw["draw"] = 0.0

    return normalize(raw)


# ══════════════════════════════════════════════════════════════════════════
# PHẦN 2 — Dự đoán đội vô địch (deadline: 28/6/2026 23:59 UTC+7)
# ══════════════════════════════════════════════════════════════════════════

def predict_champion(teams: dict, market_data: dict) -> dict:
    """
    Dự đoán xác suất vô địch World Cup 2026 cho cả 48 đội.
    Lock trước khi vòng bảng kết thúc (28/6/2026 23:59 UTC+7).

    Parameters
    ----------
    teams : dict       — như predict() ở trên
    market_data : dict — như predict() ở trên

    Returns
    -------
    dict
        Xác suất vô địch của TẤT CẢ 48 đội, tổng = 1.0:
        {"Argentina": 0.195, "Brazil": 0.210, "France": 0.110, ...}
    """
    pm = market_data["polymarket_probability"]

    # ── YOUR MODEL HERE ───────────────────────────────────────────────────
    #
    # 🟢 Beginner — dùng thẳng Polymarket champion odds:
    #     raw = {t: pm.get(t, 0.0) for t in teams}
    #
    # 🟡 Intermediate — blend Polymarket với Elo prior:
    #     import math
    #     elo_prior = normalize({t: math.exp(info["elo"] / 200)
    #                            for t, info in teams.items()})
    #     raw = {t: 0.7 * pm.get(t, 0.0) + 0.3 * elo_prior[t] for t in teams}
    #
    raw = {t: pm.get(t, 0.0) for t in teams}
    # ──────────────────────────────────────────────────────────────────────

    return normalize(raw)


# ══════════════════════════════════════════════════════════════════════════
# PHẦN 3 — Ngựa ô (deadline: 28/6/2026 23:59 UTC+7)
# ══════════════════════════════════════════════════════════════════════════

# Tên 1 đội bạn cho là "ngựa ô" — sẽ đi xa hơn kỳ vọng thị trường.
# Nếu đội này vào Tứ kết trở lên → bạn được xét giải 🧨 Chaos Award.
# Đổi thành tên đội của bạn, ví dụ: "Morocco", "Japan", "Ivory Coast"
DARK_HORSE: str = "Japan"


# ── Test nhanh khi chạy trực tiếp ─────────────────────────────────────────
if __name__ == "__main__":
    from polymarket_client import build_market_data

    teams       = json.load(open("data/teams.json"))
    matches     = json.load(open("data/matches.json"))
    print("Fetching live Polymarket data...")
    market_data = build_market_data(list(teams.keys()))

    # ── Test predict() — 5 trận đầu ───────────────────────────────────────
    print("\n── Test predict() — 5 trận đầu ──────────────────────────")
    for m in matches[:5]:
        if m["team_a"] == "TBD":
            continue
        pred = predict(m, teams, market_data)
        print(f"\n{m['match_id']} [{m['stage']}]  {m['team_a']} vs {m['team_b']}")
        print(f"  {m['team_a']:<20} {pred['team_a']*100:5.1f}%")
        print(f"  {'draw':<20} {pred['draw']*100:5.1f}%")
        print(f"  {m['team_b']:<20} {pred['team_b']*100:5.1f}%")
        print(f"  Tổng: {sum(pred.values()):.4f}")

    # ── Test predict_champion() ────────────────────────────────────────────
    print("\n── Test predict_champion() — Top 10 ─────────────────────")
    champ = predict_champion(teams, market_data)
    print(f"Tổng xác suất: {sum(champ.values()):.4f} (phải ≈ 1.0)")
    for t, p in sorted(champ.items(), key=lambda x: -x[1])[:10]:
        print(f"  {t:<18} {p*100:5.2f}%")

    # ── Test DARK_HORSE ────────────────────────────────────────────────────
    print(f"\n── Ngựa ô của bạn: {DARK_HORSE} ──────────────────────────")
    if DARK_HORSE not in teams:
        print(f"  ⚠️  '{DARK_HORSE}' không có trong danh sách 48 đội!")
