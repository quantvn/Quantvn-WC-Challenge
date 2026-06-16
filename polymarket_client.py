"""
QuantVN Oracle Challenge — Polymarket client
=============================================
Fetch xác suất vô địch World Cup 2026 (implied probability) của từng đội từ
Polymarket "Winner of the 2026 FIFA World Cup" market.

Hàm chính cho người chơi & evaluator:
    build_market_data(teams)  ->  dict

Người chơi KHÔNG cần sửa file này.
"""

import httpx
import json
import time
from typing import Optional

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL  = "https://clob.polymarket.com"

_cache: dict = {}
_cache_ttl = 300  # 5 phút


def _get(url: str, params: dict = {}) -> dict:
    key = url + json.dumps(params, sort_keys=True)
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < _cache_ttl:
        return _cache[key]["data"]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = httpx.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            _cache[key] = {"data": data, "ts": now}
            return data
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)


def _search_winner_markets(limit: int = 100) -> list[dict]:
    """
    Tìm các market 'win 2026 FIFA World Cup'. Mỗi market là 1 câu hỏi dạng
    'Will <Team> win the 2026 FIFA World Cup?' với outcomes Yes/No.

    Trả về list[dict]: { question, group_item_title, outcomes, prices, volume, liquidity, closed }
    """
    data = _get(f"{GAMMA_URL}/public-search", {
        "q": "win 2026 FIFA World Cup",
        "limit_per_type": limit,
    })

    results = []
    for event in data.get("events", []):
        for m in event.get("markets", []):
            try:
                outcomes = json.loads(m.get("outcomes", "[]"))
                prices   = [float(p) for p in json.loads(m.get("outcomePrices", "[]"))]
                results.append({
                    "question":  m.get("question", ""),
                    "group_item_title": m.get("groupItemTitle", ""),
                    "outcomes":  outcomes,
                    "prices":    prices,
                    "volume":    float(m.get("volume") or 0),
                    "liquidity": float(m.get("liquidity") or 0),
                    "closed":    bool(m.get("closed", False)),
                })
            except Exception:
                continue
    return results


def _team_in_text(team: str, text: str) -> bool:
    return team.lower() in (text or "").lower()


def _yes_price(market: dict) -> Optional[float]:
    """Lấy implied probability = giá outcome 'Yes' của market vô địch."""
    for outcome, price in zip(market["outcomes"], market["prices"]):
        if str(outcome).strip().lower() in ("yes", "y"):
            return price
    # fallback: market 2 outcome thì lấy phần tử đầu
    return market["prices"][0] if market["prices"] else None


def build_market_data(teams: list[str]) -> dict:
    """
    Build dict market_data truyền vào predict().

    Parameters
    ----------
    teams : list[str]
        Danh sách 48 đội (key của data/teams.json).

    Returns
    -------
    dict
        {
            "polymarket_probability": { team: implied_prob, ... },   # raw, chưa normalize
            "volume":    { team: usd, ... },
            "liquidity": { team: usd, ... },
            "market_found": bool,          # False nếu không fetch được market nào
            "teams_with_market": int
        }

    Lưu ý: implied_prob là RAW từ thị trường (tổng thường > 1 do overround).
    Đội không tìm thấy trên Polymarket -> prob = 0.0; người chơi tự xử lý fallback.
    """
    prob = {t: 0.0 for t in teams}
    vol  = {t: 0.0 for t in teams}
    liq  = {t: 0.0 for t in teams}
    found = 0

    try:
        markets = _search_winner_markets()
    except Exception:
        markets = []

    for m in markets:
        text = f"{m.get('group_item_title','')} {m.get('question','')}"
        for t in teams:
            if prob[t] == 0.0 and _team_in_text(t, text):
                p = _yes_price(m)
                if p is not None:
                    prob[t] = p
                    vol[t]  = m["volume"]
                    liq[t]  = m["liquidity"]
                    found += 1
                break

    return {
        "polymarket_probability": prob,
        "volume": vol,
        "liquidity": liq,
        "market_found": found > 0,
        "teams_with_market": found,
    }


if __name__ == "__main__":
    teams = list(json.load(open("data/teams.json")).keys())
    md = build_market_data(teams)
    print(f"market_found={md['market_found']} teams_with_market={md['teams_with_market']}")
    top = sorted(md["polymarket_probability"].items(), key=lambda x: -x[1])[:10]
    print("Top 10 implied champion prob:")
    for t, p in top:
        print(f"  {t:<14} {p:.4f}")
