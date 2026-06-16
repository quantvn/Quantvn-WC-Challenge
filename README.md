# ⚽ QuantVN Oracle Challenge — World Cup 2026

> Build the Oracle. Beat the crowd.

Dùng dữ liệu **Polymarket** (prediction market tiền thật) + Elo để dự đoán World Cup 2026.
Đánh giá bằng **Brier Score** — càng thấp càng tốt.

> 📖 **Hướng dẫn đầy đủ:** đọc [docs/GUIDE.pdf](docs/GUIDE.pdf) (hoặc [docs/GUIDE.docx](docs/GUIDE.docx)) — từ giới thiệu, 3 cách tiếp cận theo trình độ, cách tính điểm, đến quy trình nộp bài và FAQ.

---

## Challenge gồm 3 hạng mục

| # | Hạng mục | Deadline | Chấm bằng |
|---|----------|---------|-----------|
| 1 | **Kết quả từng trận** — dự đoán win/draw/loss trước mỗi trận | Trước mỗi trận | Per-match Brier Score |
| 2 | **Đội vô địch** — phân phối xác suất 48 đội | **28/6 23:59 UTC+7** | Champion Brier Score |
| 3 | **Ngựa ô** — 1 đội bạn cược sẽ đi xa hơn kỳ vọng | **28/6 23:59 UTC+7** | 🧨 Chaos Award nếu vào QF+ |

Cả 3 hạng mục nằm trong **1 file Python duy nhất**.

---

## Tham gia trong 3 bước

### Bước 1 — Tải repo

Tải ZIP từ GitHub về máy và giải nén, sau đó cài thư viện:
```bash
pip install -r requirements.txt
```

### Bước 2 — Viết model

Mở `predict_template.py`, điền 3 phần:

```python
# Phần 1 — kết quả từng trận (trước mỗi trận)
def predict(match, teams, market_data) -> dict:
    elo_a = teams[match["team_a"]]["elo"]
    elo_b = teams[match["team_b"]]["elo"]
    # ... logic của bạn ...
    return normalize({"team_a": p_a, "draw": p_draw, "team_b": p_b})

# Phần 2 — xác suất vô địch (lock 28/6)
def predict_champion(teams, market_data) -> dict:
    pm  = market_data["polymarket_probability"]
    raw = {t: pm.get(t, 0.0) for t in teams}
    return normalize(raw)

# Phần 3 — ngựa ô (lock 28/6)
DARK_HORSE: str = "Morocco"
```

Chạy thử:
```bash
python predict_template.py
```

### Bước 3 — Nộp bài

Đổi tên thành `submissions/<tên-bạn>.py`, kiểm tra rồi gửi cho organizer:
```bash
python evaluator.py --test submissions/ten-cua-ban.py
```

---

## Data có sẵn

| File | Nội dung |
|------|---------|
| `data/teams.json` | 48 đội — FIFA rank, Elo rating, confederation |
| `data/matches.json` | 104 trận — lịch, kết quả thực tế (cập nhật liên tục) |
| `polymarket_client.py` | Fetch live Polymarket champion odds |

**`match`** truyền vào `predict()`:
```python
{
    "match_id": "M001", "stage": "Group Stage", "group": "A",
    "team_a": "Mexico", "team_b": "South Africa",
    "datetime_utc7": "2026-06-12 06:00",
    "score_a": null, "score_b": null, "result": null
}
```

**`market_data`** (auto-inject):
```python
{
    "polymarket_probability": {"Brazil": 0.18, "France": 0.14, ...},
    "volume":    {"Brazil": 128400.0, ...},
    "liquidity": {"Brazil": 34200.0,  ...},
    "market_found": True,
    "teams_with_market": 44,
}
```

---

## Scoring

### Per-match Brier Score
```
BS_match = (p_a − o_a)² + (p_draw − o_draw)² + (p_b − o_b)²
Final    = trung bình BS_match trên tất cả các trận
```

| Điểm | Ý nghĩa |
|------|---------|
| 0.00 | Hoàn hảo |
| ~0.25 | Tốt (~60% đặt vào đúng kết quả) |
| ~0.67 | Baseline (đặt đều 1/3) |
| 2.00 | Tệ nhất |

### Champion Brier Score *(lock 28/6)*
```
BS_champion = (1/48) × Σ_team (p_team − outcome_team)²
```
Snapshot interim cập nhật sau mỗi vòng. Final sau Chung kết.

---

## Awards

| Award | Tiêu chí |
|---|---|
| 🏆 **Golden Oracle** | Per-match Brier thấp nhất |
| 🔮 **Prophet** | Champion Brier thấp nhất |
| 🧨 **Chaos Award** | Ngựa ô vào QF+ với Polymarket odds thấp nhất |
| 🎯 **Sharp Eye** | Trận nào cũng đặt xác suất cao nhất vào đúng kết quả |
| 🐐 **GOAT Model** | Model architecture ấn tượng nhất |
| 🌱 **Best Beginner** | Bài phân tích hay nhất không cần ML |

---

## Cấu trúc repo

```
quantvn-oracle-wc2026/
├── predict_template.py      ← bạn viết vào đây
├── evaluator.py             ← organizer dùng để tính điểm
├── polymarket_client.py     ← fetch Polymarket data
├── requirements.txt
├── data/
│   ├── teams.json           ← 48 đội
│   └── matches.json         ← 104 trận + kết quả thực tế
├── submissions/
│   └── example.py           ← xem ví dụ ở đây
├── docs/
│   ├── GUIDE.pdf            ← hướng dẫn đầy đủ (bản đọc)
│   └── GUIDE.docx           ← hướng dẫn đầy đủ (bản chỉnh sửa)
└── README.md                ← tổng quan (file này)
```

---

*Good luck. May your calibration be sharp. ⚽*
