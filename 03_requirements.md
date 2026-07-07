# Yahoo NBA Fantasy 選秀模擬器 — Phase 1 MVP 功能需求規格

> 承接 [02_planning.md](02_planning.md) 的 Phase 1 範圍，本文件為可直接依此開發的詳細規格。

## 1. 範圍重申

本文件只涵蓋「資料抓取入庫、Fantasy Point 計算、Streamlit 位置排名介面」，不涉及健康度/角色/新秀/心態四項質性因子（Phase 2/3）。

---

## 2. 資料來源 (Data Sources)

### FR-1.1 資料來源選型
- **唯一資料源（MVP）**：`nba_api` Python 套件（封裝 stats.nba.com）
  - 原因：免費、無需 API Key、資料即 NBA 官方統計、社群成熟
- 不做多資料源整合與備援（比照 finance 專案原則，避免過度設計）

### FR-1.2 使用的 Endpoints 與欄位

| 用途 | Endpoint | 關鍵參數 | 取得欄位 |
|---|---|---|---|
| 球員場均數據 | `LeagueDashPlayerStats` | `season='2025-26'`, `per_mode_detailed='PerGame'` | PLAYER_ID, PLAYER_NAME, TEAM_ABBREVIATION, AGE, GP, MIN, PTS, REB, AST, STL, BLK, TOV, FGM, FGA, FG_PCT, FG3M, FG3A, FG3_PCT, FTM, FTA, FT_PCT |
| 球員位置 | `CommonTeamRoster`（30 隊各呼叫一次） | `season='2025-26'`, `team_id` | PLAYER_ID, POSITION（G/F/C/G-F/F-C/F-G/C-F） |

- 呼叫需節流：每次 API 呼叫間隔 ≥ 0.6 秒（stats.nba.com 頻率限制的社群慣例值）
- 總呼叫次數：1（stats）+ 30（rosters）= 31 次，單次全量更新約 30 秒內完成

### FR-1.3 位置對映規則

NBA 官方位置 → 五大位置（一名球員可對映多個位置）：

| NBA 位置 | 對映 |
|---|---|
| G | PG, SG |
| F | SF, PF |
| C | C |
| G-F / F-G | SG, SF |
| F-C / C-F | PF, C |

- 已知近似（見 02 文件已知限制），對映表放設定檔可調，不寫死程式碼

---

## 3. 更新方式 (Update Strategy)

### FR-2.1 更新頻率
- **手動觸發、一次性全量快照**。2025-26 賽季已結束，數據不再變動，無需排程
- 重跑更新腳本 = 全量覆蓋（upsert），可重複執行無副作用

---

## 4. 資料儲存 (Storage)

### FR-3.1 儲存方式
- **SQLite** 單檔（`data/nba.db`），比照 finance 專案零成本原則

### FR-3.2 Schema 設計

**表：`players`**

| 欄位 | 型別 | 說明 |
|---|---|---|
| player_id | INTEGER PK | NBA 官方球員 ID |
| name | TEXT | 球員姓名 |
| team | TEXT | 球隊縮寫，如 `LAL` |
| age | REAL | 年齡 |
| nba_position | TEXT | NBA 官方登錄位置原值，如 `G-F` |
| positions | TEXT | 對映後的五大位置，逗號分隔，如 `SG,SF` |

**表：`player_stats`**

| 欄位 | 型別 | 說明 |
|---|---|---|
| player_id | INTEGER | 對應 players |
| season | TEXT | 如 `2025-26`（Phase 2 回補歷史季時沿用此表） |
| gp | INTEGER | 出賽場次 |
| min | REAL | 場均上場時間 |
| pts / reb / ast / stl / blk / tov | REAL | 場均六大項 |
| fgm / fga / fg_pct | REAL | 投籃 |
| fg3m / fg3a / fg3_pct | REAL | 三分 |
| ftm / fta / ft_pct | REAL | 罰球 |
| updated_at | DATETIME | 寫入時間 |

- **主鍵**：`(player_id, season)`，upsert 防重複

---

## 5. Fantasy Point 計算 (Scoring)

### FR-4.1 計算公式
```
fantasy_point = Σ (場均數據欄位 × 對應權重)
```

### FR-4.2 預設權重（Yahoo Points League 標準）

| 項目 | 權重 |
|---|---|
| PTS | +1.0 |
| REB | +1.2 |
| AST | +1.5 |
| STL | +3.0 |
| BLK | +3.0 |
| TOV | -1.0 |

- 預設值存 `config/config.yaml`；權重涵蓋的欄位不寫死 — 設定檔中列出的任何 `player_stats` 數值欄位都可參與計算（例如日後想加 `fg3m` 權重，改設定檔即可）

### FR-4.3 介面即時調整
- Streamlit 側欄提供各權重的數字輸入框，初始值 = 設定檔預設值，調整後排名即時重算
- 介面調整只影響當次瀏覽，不回寫設定檔

---

## 6. Streamlit 介面 (UI)

### FR-5.1 頁面結構
- 單頁應用，上方以 tabs 切換 PG / SG / SF / PF / C 五大位置（+ 一個「全部」tab）
- 每個 tab 顯示該位置球員排名表，依 Fantasy Point 降冪排序

### FR-5.2 排名表欄位
`排名、姓名、球隊、位置、Fantasy Point、GP、MIN、PTS、REB、AST、STL、BLK、TOV、FG%、3PM、FT%`

### FR-5.3 側欄功能
- 權重調整（FR-4.3）
- 最低出賽場次過濾（預設 20 場，排除小樣本球員干擾排名）

### FR-5.4 明確排除
- 不做球員詳情頁、圖表視覺化、比較功能（非 MVP）

---

## 7. 錯誤處理 (Error Handling)

### FR-6.1 抓取失敗
- 單一球隊 roster 抓取失敗：重試 1 次，仍失敗則記錄至 stdout 並繼續下一隊，該隊球員位置暫缺（`positions` 為空，仍出現在「全部」tab）
- `LeagueDashPlayerStats` 失敗：整體中止並報錯（無此資料則一切免談）

### FR-6.2 資料缺漏
- 位置缺漏的球員在介面上標示 `?`，不阻擋使用

---

## 8. 非功能需求 (Non-Functional Requirements)

| 項目 | 需求 |
|---|---|
| 執行環境 | 個人電腦（Windows），Python 3.10+ |
| 更新執行時間 | 全量更新 < 2 分鐘（含 API 節流） |
| 相依套件 | `nba_api`, `pandas`, `streamlit`, `pyyaml` |
| 設定管理 | 權重、賽季、位置對映表、DB 路徑集中在 `config/config.yaml` |

---

## 9. 驗收標準 (Acceptance Criteria)

- [ ] 執行更新腳本一次後，`players` 與 `player_stats` 涵蓋 2025-26 全部登錄球員
- [ ] 重複執行更新腳本，資料筆數不變（驗證 upsert）
- [ ] 抽查 3 名不同位置球星，場均數據與 NBA 官網一致
- [ ] Streamlit 五大位置 tab 各自只顯示該位置球員，排序正確
- [ ] 側欄調高 AST 權重後，控球後衛排名明顯上升（權重即時生效驗證)
- [ ] 最低出賽場次過濾生效
