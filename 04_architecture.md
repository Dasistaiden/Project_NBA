# Yahoo NBA Fantasy 選秀模擬器 — Phase 1 系統架構設計

> 承接 [03_requirements.md](03_requirements.md) 的功能需求，轉換為具體技術設計。**本文件是後續程式實作的核心依據**，模組、檔名、函式介面皆以此為準。

---

## 1. 架構總覽

單機、單一 Python 專案、SQLite 儲存、手動觸發更新、Streamlit 呈現。不採用 ORM、不採用排程框架 — 對應規劃文件的 MVP 範圍。

```
[手動執行]
    │
    ▼
[update_data.py]  ← 資料更新進入點（一次性全量）
    │
    ├─→ 讀取 config/config.yaml
    ├─→ fetcher.py   （nba_api 封裝：場均數據 + 30 隊 roster）
    └─→ db.py        （upsert 至 SQLite）

[app/draft_board.py]  ← Streamlit 進入點，只讀
    │
    ├─→ db.py        （讀取 players + player_stats）
    └─→ scoring.py   （fantasy point 計算，權重來自側欄）
```

---

## 2. 目錄結構

```
project_nba/
├── config/
│   └── config.yaml           # 賽季、預設權重、位置對映、DB 路徑、過濾預設
├── data/
│   └── nba.db                # SQLite（執行後產生，不進版控）
├── src/
│   ├── db.py                 # Schema 定義、連線、upsert、查詢
│   ├── fetcher.py            # nba_api 封裝（含節流、重試）
│   ├── scoring.py            # fantasy point 計算
│   └── update_data.py        # 全量更新主流程（唯一寫入進入點）
├── app/
│   └── draft_board.py        # Streamlit 主頁
├── docs/                     # 本系列文件
├── tests/
└── requirements.txt          # nba_api, pandas, streamlit, pyyaml, pytest
```

---

## 3. 資料庫設計 (DDL)

```sql
CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    team          TEXT,
    age           REAL,
    nba_position  TEXT,
    positions     TEXT           -- 逗號分隔，如 'SG,SF'；未知則空字串
);

CREATE TABLE IF NOT EXISTS player_stats (
    player_id   INTEGER NOT NULL,
    season      TEXT    NOT NULL,
    gp          INTEGER,
    min         REAL,
    pts REAL, reb REAL, ast REAL, stl REAL, blk REAL, tov REAL,
    fgm REAL, fga REAL, fg_pct REAL,
    fg3m REAL, fg3a REAL, fg3_pct REAL,
    ftm REAL, fta REAL, ft_pct REAL,
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (player_id, season)
);
```

---

## 4. 模組介面 (Function Signatures)

```python
# src/db.py
get_connection(db_path: str) -> sqlite3.Connection      # 含建表
upsert_players(conn, df: pd.DataFrame) -> None
upsert_stats(conn, df: pd.DataFrame, season: str) -> None
load_board(conn, season: str) -> pd.DataFrame           # players JOIN player_stats

# src/fetcher.py
fetch_season_stats(season: str) -> pd.DataFrame          # LeagueDashPlayerStats PerGame
fetch_positions(season: str) -> pd.DataFrame             # 30 隊 CommonTeamRoster，含節流與單隊重試
map_positions(nba_position: str, mapping: dict) -> str   # 'G-F' -> 'SG,SF'

# src/scoring.py
compute_fantasy_points(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series
    # weights key = player_stats 欄位名，僅計算 df 中存在的欄位

# src/update_data.py
run(season: str | None = None) -> None                   # 讀 config → fetch → upsert
```

---

## 5. config.yaml 結構

```yaml
season: "2025-26"
db_path: "data/nba.db"
min_games_default: 20
api_delay_seconds: 0.6

weights:            # Yahoo Points League 預設（FR-4.2）
  pts: 1.0
  reb: 1.2
  ast: 1.5
  stl: 3.0
  blk: 3.0
  tov: -1.0

position_mapping:   # FR-1.3
  "G":   [PG, SG]
  "F":   [SF, PF]
  "C":   [C]
  "G-F": [SG, SF]
  "F-G": [SG, SF]
  "F-C": [PF, C]
  "C-F": [PF, C]
```

---

## 6. Streamlit 頁面設計 (app/draft_board.py)

- `st.tabs(["全部", "PG", "SG", "SF", "PF", "C"])`
- 側欄：`st.number_input` × 6 個權重（初始值來自 config）+ `st.slider` 最低出賽場次
- 主表：`st.dataframe`，欄位依 FR-5.2，依 fantasy_point 降冪
- 資料載入用 `@st.cache_data` 快取（DB 讀取一次即可，權重計算在快取外執行以便即時反應）
- 位置過濾：`positions` 欄位字串包含該 tab 位置即顯示；空字串者只出現在「全部」tab 並標示 `?`

---

## 7. 錯誤處理策略

| 情境 | 處理 |
|---|---|
| `LeagueDashPlayerStats` 失敗 | 中止並報錯（FR-6.1） |
| 單隊 roster 失敗 | 重試 1 次，仍失敗印警告後繼續，該隊球員 positions 留空 |
| Streamlit 啟動時 DB 不存在 | 頁面顯示提示「請先執行 python src/update_data.py」，不噴 traceback |

---

## 8. 測試範圍（最小集）

| 檔案 | 涵蓋 |
|---|---|
| `tests/test_scoring.py` | 權重計算正確性、缺欄位容忍、負權重（TOV） |
| `tests/test_db.py` | upsert 冪等性、load_board JOIN 正確 |
| `tests/test_positions.py` | 位置對映表各分支 |

- `fetcher.py` 不寫自動化測試（依賴外部 API），以更新腳本實跑 + 驗收標準抽查代替
