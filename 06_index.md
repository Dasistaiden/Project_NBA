# Yahoo NBA Fantasy 選秀模擬器 — 索引與目錄

> **活文件（living document）**。每次程式碼或資料庫結構變動後，更新對應章節並在第 5 節附加一筆紀錄（只增不改）。

---

## 1. 程式碼目錄索引 (Code Index)

| 檔案 | 職責 | 對應文件 |
|---|---|---|
| `src/db.py` | SQLite 連線、schema、upsert、`load_board` JOIN 查詢 | [04](04_architecture.md) §3-4 |
| `src/fetcher.py` | `nba_api` 封裝（場均數據、30 隊 roster、位置對映），含節流與單隊重試 | 04 §4, §7 |
| `src/scoring.py` | Fantasy Point 加權計算 | 03 FR-4 |
| `src/auction.py` | $200 拍賣估價（value-over-replacement）與 ILP 陣容優化（pulp/CBC） | — |
| `src/update_data.py` | 全量更新主流程（唯一寫入進入點），含歷史賽季回補 | 04 §1 |
| `app/common.py` | 各頁共用：config/board 載入（cached）、側欄權重與過濾元件 | — |
| `app/draft_board.py` | 主頁：位置排名看板 | 04 §6 |
| `app/pages/1_球員比較.py` | 2-4 名球員數據並排，逐項標示優劣（TOV 反向） | — |
| `app/pages/2_模擬選秀.py` | 估價表 + 預算內最佳 13 人陣容求解 | — |
| `app/pages/3_球員百科.py` | 照片（NBA CDN）、歷年數據、角色定位啟發式、人工備註 | — |
| `config/config.yaml` | 賽季、歷史賽季、權重、位置對映、拍賣設定、格位資格 | 04 §5 |
| `config/player_notes.yaml` | 人工維護的球員備註（status/media），百科頁讀取 | — |
| `data/nba.db` | SQLite 資料庫（執行後產生，不進版控） | — |

### 函式簽名索引

```python
# db.py
get_connection(db_path: str) -> sqlite3.Connection        # 含建表
upsert_players(conn, df: pd.DataFrame) -> None
upsert_stats(conn, df: pd.DataFrame, season: str) -> None
load_board(conn, season: str) -> pd.DataFrame             # players JOIN player_stats

# fetcher.py
fetch_season_stats(season: str) -> pd.DataFrame           # 失敗直接 raise
fetch_positions(season: str, delay: float = 0.6) -> pd.DataFrame
map_positions(nba_position: str, mapping: dict) -> str    # 'G-F' -> 'SG,SF'，未知回空字串

# scoring.py
compute_fantasy_points(df: pd.DataFrame, weights: dict) -> pd.Series  # 缺欄位忽略

# update_data.py
load_config(base_dir: Path = BASE_DIR) -> dict
run(season: str | None = None) -> None      # 另回補 config.history_seasons

# auction.py
estimate_prices(fp: pd.Series, budget: int, teams: int, roster_size: int) -> pd.Series
optimize_roster(df, slots: list, eligibility: dict, budget: int) -> pd.DataFrame  # 無解 raise ValueError

# app/common.py
load_board(season) / load_stats_history()   # @st.cache_data
sidebar_weights(cfg) / sidebar_min_gp(cfg)
require_data(cfg)                            # DB 不存在則 st.stop
```

---

## 2. 資料字典 (Data Catalog)

### 表：`players`

| 欄位 | 型別 | 說明 | 範例 |
|---|---|---|---|
| `player_id` | INTEGER PK | NBA 官方球員 ID | `203999` |
| `name` | TEXT | 姓名（含變音符號，UTF-8） | `Nikola Jokić` |
| `team` | TEXT | 球隊縮寫 | `DEN` |
| `age` | REAL | 年齡 | `31.0` |
| `nba_position` | TEXT | NBA 官方登錄位置原值 | `C` |
| `positions` | TEXT | 對映後五大位置，逗號分隔；未知為空字串 | `PF,C` |

### 表：`player_stats`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `player_id`, `season` | 複合 PK | season 格式 `2025-26`，Phase 2 回補歷史季沿用此表 |
| `gp`, `min` | INTEGER / REAL | 出賽場次、場均時間 |
| `pts` `reb` `ast` `stl` `blk` `tov` | REAL | 場均六大項（權重計算來源） |
| `fgm` `fga` `fg_pct` / `fg3m` `fg3a` `fg3_pct` / `ftm` `fta` `ft_pct` | REAL | 投籃/三分/罰球 |
| `updated_at` | DATETIME | 寫入時間（UTC） |

### 資料快照（2026-07-05，非即時）

- `players`：582 筆（525 筆有位置對映）
- `player_stats`：2025-26 × 582、2024-25 × 569、2023-24 × 572 筆

---

## 3. CLI / 介面

| 指令 | 用途 |
|---|---|
| `.venv\Scripts\python.exe src\update_data.py` | 全量更新（可重複執行，upsert） |
| `.venv\Scripts\python.exe -m streamlit run app\draft_board.py` | 啟動選秀看板（localhost:8501） |

無 HTTP API。權重調整在 Streamlit 側欄，僅影響當次瀏覽，預設值在 `config/config.yaml`。

---

## 4. 測試索引

| 檔案 | 涵蓋 |
|---|---|
| `tests/test_scoring.py` | 加權計算、缺欄位容忍、NaN 視為 0 |
| `tests/test_db.py` | upsert 冪等性、load_board JOIN、season 過濾 |
| `tests/test_positions.py` | 位置對映各分支、未知位置回空字串 |
| `tests/test_auction.py` | 估價替補水準 $1、優化器預算/格位約束與最佳性、無解 raise |

執行：`.venv\Scripts\python.exe -m pytest tests/ -v` — 最近一次：10 passed。
`fetcher.py` 無自動化測試（外部 API），以實跑抽查代替（見 [05_processes.md](05_processes.md) §4）。

---

## 5. 更新日誌 (Changelog)

> 只增不改。格式：`日期 | 變動內容 | 影響範圍`

| 日期 | 變動內容 | 影響範圍 |
|---|---|---|
| 2026-07-05 | 初版建立：完成 Phase 1 MVP（資料抓取入庫 + Fantasy Point + Streamlit 五位置看板），7 測試通過，582 名球員實跑入庫驗證成功 | 全新建立 |
| 2026-07-05 | 擴充為多頁應用：新增球員比較、模擬選秀（$200 拍賣估價 + pulp ILP 陣容優化）、球員百科（NBA CDN 照片 + 歷年數據 + 人工備註檔）三頁；回補 2024-25、2023-24 歷史賽季；新依賴 `pulp`；10 測試通過，優化器實跑 0.7s 解出 $200/433FP 陣容 | `app/`（多頁重構 + common.py）、`src/auction.py`、`src/update_data.py`、`config/`（auction 設定 + player_notes.yaml） |

### 下次更新此文件時的檢查清單
- [ ] `src/` / `app/` 有檔案增刪改名？→ 更新第 1 節
- [ ] Schema 有新欄位/表？→ 更新第 2 節
- [ ] CLI 或介面行為變動？→ 更新第 3 節
- [ ] 測試增減？→ 更新第 4 節
- [ ] 第 5 節附加一筆變動紀錄
