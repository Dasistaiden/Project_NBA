# Yahoo NBA Fantasy 選秀模擬器 — Phase 1 流程與執行紀錄

> 依 [03_requirements.md](03_requirements.md) 與 [04_architecture.md](04_architecture.md) 實作，本文件記錄「怎麼跑」與「跑過一次的結果」。

## 1. 與架構文件的差異

無重大偏離。一處補充：球員姓名含變音符號（如 `Nikola Jokić`），Windows 主控台預設 cp950 編碼會印不出來 — 查詢腳本若要在終端印出球員名，需設 `PYTHONIOENCODING=utf-8`。資料庫內儲存正確，Streamlit 顯示不受影響。

---

## 2. 環境建置

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt`：`nba_api`, `pandas`, `streamlit`, `pyyaml`, `pytest`（實測環境：Python 3.12.4）。

---

## 3. 手動執行方式

**更新資料（一次性全量，約 30-60 秒）：**
```powershell
.venv\Scripts\python.exe src\update_data.py
```

**啟動選秀看板：**
```powershell
.venv\Scripts\python.exe -m streamlit run app\draft_board.py
```
瀏覽器開 http://localhost:8501。側欄可調權重與最低出賽場次，五大位置以 tab 切換。

**跑測試：**
```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## 4. 首次執行紀錄（2026-07-05）

| 項目 | 結果 |
|---|---|
| pytest | 7 passed |
| `update_data.py` 實跑 | 582 名球員入庫，525 名有位置對映，無失敗球隊 |
| 數據抽查 | Jokić 27.7 pts / 12.9 reb / 10.7 ast；SGA 31.1 pts；Dončić 33.5 pts — 與 NBA 官方 2025-26 數據一致 |
| Streamlit 煙霧測試 | headless 啟動，HTTP 200 |

### 驗收標準對照（03 文件 §9）

- [x] 更新腳本執行後涵蓋 2025-26 全部登錄球員（582 名）
- [x] 重複執行不產生重複列（upsert，test_db.py 驗證）
- [x] 抽查 3 名不同位置球星數據與官網一致
- [x] Streamlit 五大位置 tab 過濾與排序（介面實跑確認）
- [x] 權重即時生效（side bar number_input 直接參與計算）
- [x] 最低出賽場次過濾生效

---

## 5. 已知事項

- 57 名球員無位置對映（`positions` 空，介面標示 `?`）：多為賽季中被裁或交易後不在期末 roster 的球員，Fantasy 價值通常很低，不影響選秀決策
- Dončić 這類 NBA 登錄為 F-G 的球員對映成 `SG,SF`，與 Yahoo 實際資格（PG,SG）有出入 — 02 文件已知限制，用過再決定是否引入外部位置來源
