# Project_NBA — Fantasy Draft Simulator

Yahoo Fantasy NBA 選秀工具：nba_api → SQLite → 自訂 Fantasy Points → Streamlit 看板 + 拍賣 ILP 最佳化（詳見 README.md / README.zh-TW.md）。獨立 git repo（github.com/Dasistaiden/Project_NBA）。與使用者溝通用繁體中文。

## 面試敘事（所有對外文件與功能取捨對齊這段）

- **假設我是**：球團 front office 的 analyst，要在固定預算（$200 薪資帽）與位置格位限制下，組出預期產出最大的陣容。
- **決策問題**：每名球員值多少錢？該對誰出價、出到多少就停？
- **商業轉譯**：這是「約束條件下的人才定價與資源配置」——value-over-replacement 估價 + 整數規劃求解，同樣框架適用招募薪資談判、採購預算分配、廣告版位競價。預測模組（Marcel + GBT、留出賽季回測）示範「baseline 先行、ML 要贏過 baseline 才上」的紀律。
- 講這個專案時：先講預算配置問題，再講估價與優化，最後講已知限制（位置對映與 Yahoo 有出入、傷病靠人工備註）。

## 結構

- `src/` — `update_data.py`（資料抓取入口）、`scoring.py`、`auction.py`、`projection.py`、`backfill_history.py`
- `tests/` — pytest，改 `src/` 後必跑對應測試，沒過不准說完成
- `app/` — Streamlit 多頁看板（入口 `app\draft_board.py`）
- `config/` — config.yaml（賽季/權重/位置）、player_notes.yaml（手動球探筆記，勿覆蓋）
- 規劃文件 01–06 在專案根目錄，動大功能前先讀對應那份

## 硬規則

1. 環境用本專案 `.venv`：`.venv\Scripts\python.exe`、`.venv\Scripts\pip`。不用全域 Python。
2. 永不讀取 `.venv/`、`__pycache__/`、`.pytest_cache/`；資料庫檔案不整份讀。
3. 不 import 或參照 workspace 其他專案的程式碼（隔離原則）。
4. 抓資料的節流（throttling）與 per-team retry 不可移除——nba_api 會封鎖高頻請求。
5. PowerShell 5.1：無 `&&`；跑測試：`.venv\Scripts\python.exe -m pytest tests\ -q`。
