"""
QuantVN Oracle Challenge — Evaluator
=====================================
Chấm 3 hạng mục trong 1 file submission:

  1. predict()          — Brier Score trung bình theo từng trận
  2. predict_champion() — Brier Score dự đoán vô địch (lock 28/6 23:59 UTC+7)
  3. DARK_HORSE         — Ghi nhận ngựa ô (award, không tính điểm số)

Cách chấm per-match
-------------------
    BS_match = (p_a - o_a)² + (p_draw - o_draw)² + (p_b - o_b)²
    Final per-match = trung bình BS_match trên tất cả trận đã có kết quả
    Thấp hơn = tốt hơn  (0 = hoàn hảo, ~0.667 = baseline đặt đều)

Cách chấm champion
------------------
    BS_champion = (1/48) × Σ_team (p_team - outcome_team)²
    outcome_team = 1 nếu đội đó vô địch, 0 nếu không
    Snapshot interim (đội đã loại = outcome 0) cập nhật giữa giải.
    Final chỉ biết sau Chung kết.

Lưu ý lock time
---------------
  - per-match  : commit trước datetime_utc7 của từng trận
  - champion   : commit trước 2026-06-28 23:59 UTC+7
  - dark_horse : cùng deadline champion
  Organizer kiểm tra git log.

Usage:
    python evaluator.py --test submissions/example.py
    python evaluator.py
"""

import argparse
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Optional

from polymarket_client import build_market_data

TEAMS_PATH   = Path("data/teams.json")
MATCHES_PATH = Path("data/matches.json")

# Deadline lock champion/dark-horse (UTC+7)
CHAMPION_LOCK = "2026-06-28 23:59"

# ── Organizer cập nhật sau Chung kết ─────────────────────────────────────
CHAMPION: Optional[str] = None   # vd: "Argentina"

# Các đội đã bị loại (cho snapshot interim champion Brier)
ELIMINATED: dict[str, str] = {
    # "Saudi Arabia": "Group Stage",
}


def load_teams() -> dict:
    return json.loads(TEAMS_PATH.read_text())


def load_matches() -> list:
    return json.loads(MATCHES_PATH.read_text())


def load_submission(path: str):
    spec = importlib.util.spec_from_file_location("submission", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "predict"):
        raise AttributeError(f"{path} không có hàm predict()")
    return mod


def normalize(probs: dict) -> dict:
    total = sum(probs.values())
    if total <= 0:
        return {k: 1.0 / len(probs) for k in probs}
    return {k: v / total for k, v in probs.items()}


# ── Per-match scoring ─────────────────────────────────────────────────────

def brier_match(pred: dict, result: str) -> float:
    outcomes = {"team_a": 0.0, "draw": 0.0, "team_b": 0.0}
    outcomes[result] = 1.0
    return sum((pred.get(k, 0.0) - outcomes[k]) ** 2 for k in outcomes)


def score_per_match(mod, teams: dict, matches: list, market_data: dict) -> dict:
    played  = [m for m in matches if m.get("result") and m["team_a"] != "TBD"]
    scored  = []
    errors  = []
    total   = 0.0

    for m in played:
        try:
            raw  = mod.predict(m, teams, market_data)
            pred = normalize({k: float(raw.get(k, 0.0))
                              for k in ("team_a", "draw", "team_b")})
            bs   = brier_match(pred, m["result"])
            scored.append({
                "match_id": m["match_id"],
                "match":    f"{m['team_a']} vs {m['team_b']}",
                "result":   m["result"],
                "pred":     {k: round(v, 4) for k, v in pred.items()},
                "bs":       round(bs, 6),
            })
            total += bs
        except Exception as e:
            errors.append({"match_id": m["match_id"], "error": str(e)})
            total += 2.0

    n    = len(played)
    avg  = round(total / n, 6) if n > 0 else None
    return {"matches_scored": len(scored), "avg_brier": avg,
            "details": scored, "errors": errors}


# ── Champion scoring ──────────────────────────────────────────────────────

def score_champion(mod, teams: dict, market_data: dict) -> dict:
    if not hasattr(mod, "predict_champion"):
        return {"error": "không có hàm predict_champion()", "champion_brier": None}
    try:
        raw   = mod.predict_champion(teams, market_data)
        probs = normalize({t: float(raw.get(t, 0.0)) for t in teams})
    except Exception as e:
        return {"error": str(e), "champion_brier": None}

    n = len(probs)
    if CHAMPION is not None:
        bs = sum((p - (1.0 if t == CHAMPION else 0.0)) ** 2
                 for t, p in probs.items()) / n
        return {"type": "final", "champion_brier": round(bs, 6),
                "champion": CHAMPION,
                "top5": [(t, round(p, 4))
                         for t, p in sorted(probs.items(), key=lambda x: -x[1])[:5]]}

    # snapshot interim
    interim = sum(probs[t] ** 2 for t in ELIMINATED if t in probs) / n
    return {"type": "snapshot", "champion_brier_interim": round(interim, 6),
            "eliminated_count": len([t for t in ELIMINATED if t in probs]),
            "top5": [(t, round(p, 4))
                     for t, p in sorted(probs.items(), key=lambda x: -x[1])[:5]]}


# ── Dark horse ────────────────────────────────────────────────────────────

def get_dark_horse(mod, teams: dict) -> Optional[str]:
    dh = getattr(mod, "DARK_HORSE", None)
    if not isinstance(dh, str):
        return None
    return dh if dh in teams else f"INVALID: {dh}"


# ── Full evaluation ───────────────────────────────────────────────────────

def evaluate_one(mod, teams: dict, matches: list, market_data: dict) -> dict:
    match_result    = score_per_match(mod, teams, matches, market_data)
    champion_result = score_champion(mod, teams, market_data)
    dark_horse      = get_dark_horse(mod, teams)
    return {
        "per_match":  match_result,
        "champion":   champion_result,
        "dark_horse": dark_horse,
    }


def run_evaluation(submissions_dir: str = "submissions") -> dict:
    teams       = load_teams()
    matches     = load_matches()
    market_data = build_market_data(list(teams.keys()))
    sub_files   = sorted(Path(submissions_dir).glob("*.py"))

    if not sub_files:
        print(f"Không tìm thấy file nào trong {submissions_dir}/")
        return {}

    leaderboard = {}
    for sub_file in sub_files:
        name = sub_file.stem
        try:
            mod = load_submission(str(sub_file))
        except Exception as e:
            print(f"  ❌ {name}: load lỗi: {e}")
            leaderboard[name] = {"error": str(e)}
            continue
        result = evaluate_one(mod, teams, matches, market_data)
        leaderboard[name] = result
        pm = result["per_match"]
        cm = result["champion"]
        dh = result["dark_horse"]
        bs_m = pm.get("avg_brier")
        bs_c = cm.get("champion_brier") or cm.get("champion_brier_interim")
        print(f"  ✅ {name}: match={bs_m}  champion={bs_c}  dark_horse={dh}")
    return leaderboard


def print_leaderboard(leaderboard: dict):
    if not leaderboard:
        return
    # Sắp xếp theo per-match Brier (primary)
    ranked = sorted(
        leaderboard.items(),
        key=lambda x: x[1].get("per_match", {}).get("avg_brier") or 9999,
    )
    played = max(
        (v.get("per_match", {}).get("matches_scored", 0) for v in leaderboard.values()),
        default=0,
    )
    print("\n" + "═" * 68)
    print(f"  🏆  QUANTVN ORACLE — LEADERBOARD  ({played} trận đã chấm)")
    print("═" * 68)
    print(f"  {'Rank':<5} {'Name':<22} {'PerMatch':>9}  {'Champion':>10}  {'NgựaÔ'}")
    print("─" * 68)
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, stats) in enumerate(ranked):
        if stats.get("error"):
            print(f"  {'❌':<5} {name:<22}  {'ERROR':>9}")
            continue
        medal  = medals[i] if i < 3 else f"  {i+1}."
        bs_m   = stats.get("per_match", {}).get("avg_brier")
        cm     = stats.get("champion", {})
        bs_c   = cm.get("champion_brier") or cm.get("champion_brier_interim")
        dh     = stats.get("dark_horse") or "—"
        bs_m_s = f"{bs_m:.6f}" if bs_m is not None else "—"
        bs_c_s = f"{bs_c:.6f}" if bs_c is not None else "—"
        print(f"  {medal:<5} {name:<22} {bs_m_s:>9}  {bs_c_s:>10}  {dh}")
    print("═" * 68)
    print("  Brier Score thấp hơn = tốt hơn\n")


def save_leaderboard(leaderboard: dict, out: str = "leaderboard.json"):
    Path(out).write_text(json.dumps(leaderboard, indent=2, ensure_ascii=False))
    print(f"Saved → {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QuantVN Oracle Evaluator")
    parser.add_argument("--submissions", default="submissions")
    parser.add_argument("--out", default="leaderboard.json")
    parser.add_argument("--test", help="test 1 file submission cụ thể")
    args = parser.parse_args()

    teams   = load_teams()
    matches = load_matches()
    played  = [m for m in matches if m.get("result") and m["team_a"] != "TBD"]
    print(f"Matches có kết quả: {len(played)}/{len(matches)}")
    print(f"Champion lock: {CHAMPION_LOCK} UTC+7  |  "
          f"Nhà vô địch: {CHAMPION or '(chưa xác định)'}")

    if args.test:
        try:
            mod         = load_submission(args.test)
            market_data = build_market_data(list(teams.keys()))
            print(f"\n✅ Loaded: {args.test}\n")

            result = evaluate_one(mod, teams, matches, market_data)

            # Per-match
            pm = result["per_match"]
            print(f"── Per-match Brier: {pm['avg_brier']}  "
                  f"({pm['matches_scored']} trận) ──────────────")
            for d in pm["details"]:
                p = d["pred"]
                print(f"  {d['match_id']}  {d['match']:<36}  "
                      f"result={d['result']:<8}  BS={d['bs']:.4f}  "
                      f"[{p['team_a']:.2f}/{p['draw']:.2f}/{p['team_b']:.2f}]")
            if pm["errors"]:
                for e in pm["errors"]:
                    print(f"  ❌ {e['match_id']}: {e['error']}")

            # Champion
            cm = result["champion"]
            print(f"\n── Champion Brier: {cm} ──────────────────────────────")
            if "top5" in cm:
                for t, p in cm["top5"]:
                    print(f"  {t:<18} {p*100:5.2f}%")

            # Dark horse
            print(f"\n── Ngựa ô: {result['dark_horse']} ──────────────────────")

        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()
        sys.exit(0)

    leaderboard = run_evaluation(args.submissions)
    print_leaderboard(leaderboard)
    save_leaderboard(leaderboard, args.out)
