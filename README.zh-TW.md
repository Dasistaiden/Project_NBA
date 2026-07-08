# NBA Fantasy 選秀模擬器

[English](README.md) | 繁體中文

輔助 Yahoo Fantasy NBA 選秀決策的本機工具：透過 `nba_api` 抓取全聯盟球員數據，計算可自訂加權的 Fantasy Point，並以多頁 Streamlit 介面呈現——位置排名看板、球員並排比較、拍賣制陣容優化器（整數規劃）與球員百科。

## 為什麼需要它

選秀當下只有幾秒鐘能權衡分散各處的資訊：數據、健康、球隊角色、上升空間。這個工具把它們整合成一個可調整、可比較的分數，讓每一支選擇有數據佐證，而不是憑印象。

## 目前功能

- **資料管線**（`src/update_data.py`）— 全聯盟約 580 名球員的場均數據與名單/位置資料，含 API 節流與逐隊重試；`src/backfill_history.py` 回補 2005-06 起 21 季（約 10,600 筆）作為訓練資料。以冪等 upsert 寫入 SQLite，重跑不會重複。
- **自訂 Fantasy Point**（`src/scoring.py`）— 各項數據權重（PTS/REB/AST/STL/BLK/TOV/命中率）附合理預設值（Yahoo Points League：PTS 1 / REB 1.2 / AST 1.5 / STL 3 / BLK 3 / TOV -1），可在側欄即時調整以符合你的聯盟計分規則。
- **拍賣優化器**（`src/auction.py`）— 以 value-over-replacement 法估算 $200 預算下每名球員的合理標價（附可調的巨星溢價曲線），並用整數規劃（PuLP/CBC）在預算與位置格位限制下求出最佳 13 人陣容（一秒內解出）。
- **下一季預測**（`src/projection.py`）— Marcel 基準模型 + 每項數據一個梯度提升樹，以 2005-06 起 21 季資料訓練，經留出賽季回測驗證（ML 在誤差與排名相關性皆勝出）。看板與模擬選秀可切換「上季實際 / 2026-27 預測」排名依據。
- **Streamlit 介面**（`app/`）：
  1. 選秀看板 — PG/SG/SF/PF/C 五大位置排名，附上季場均數據佐證
  2. 球員比較 — 2-4 名球員並排，逐項標示優劣（失誤反向計）
  3. 模擬選秀 — 全員估價表 + 最佳陣容求解
  4. 球員百科 — 照片、跨季數據、角色定位標籤，與人工維護的球探備註（`config/player_notes.yaml`）

## 快速開始

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 抓取當季 + 歷史賽季資料（可重複執行）
.venv\Scripts\python.exe src\update_data.py

# 啟動看板
.venv\Scripts\python.exe -m streamlit run app\draft_board.py
```

賽季、權重、位置對映與拍賣設定集中在 `config/config.yaml`。

## 測試

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

15 個測試涵蓋計分邏輯（缺欄位、NaN 處理）、upsert 冪等性、位置對映、優化器的預算/格位約束與無解情境，以及預測模組（Marcel 回歸方向、換隊特徵、ML 煙霧測試）。`nba_api` 抓取層以實跑抽查驗證；預測準確度以留出賽季回測驗證（`src/run_projection.py` 會印出報告）。

## 已知限制

- 球員位置由 NBA 官方登錄位置（G/F/C）對映而來，與 Yahoo 實際位置資格可能有出入（如 Dončić 對映為 SG/SF，Yahoo 為 PG/SG）
- 57 名賽季中離隊球員無位置對映，介面標示 `?`
- 傷病狀況與媒體評價為人工維護備註，非自動抓取

## 下次更新（規劃中）

- **Phase 2 — 健康度與角色定位**：以三季出賽紀錄推導傷病風險指數；引入先發場次/使用率細化角色標籤
- **Phase 3 — 新秀與質性分析**：NCAA 數據換算新秀預期產出；質性評分欄位
- **Phase 4 — 選秀日輔助**：標記已被選走球員、剩餘最佳人選即時推薦、互動式競標模擬

詳見 [02_planning.md](02_planning.md)。

## 設計文件

完整規劃文件（價值主張 → 規劃 → 需求 → 架構 → 流程紀錄 → 程式碼索引）在專案根目錄的 `01_*.md` – `06_*.md`，入口為 [`06_index.md`](06_index.md)。
