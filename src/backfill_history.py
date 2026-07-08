"""一次性回補歷史賽季場均數據（ML 訓練資料）。python src/backfill_history.py

只寫 player_stats（含各季 age/team），不動 players 名單。可重複執行（upsert）。
"""
import time

import db
import fetcher
from update_data import BASE_DIR, load_config

SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(2005, 2026)]  # 2005-06 .. 2025-26


def main() -> None:
    cfg = load_config()
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    for season in SEASONS:
        for attempt in (1, 2):
            try:
                df = fetcher.fetch_season_stats(season)
                db.upsert_stats(conn, df, season)
                print(f"{season}: {len(df)} rows")
                break
            except Exception as exc:
                if attempt == 2:
                    print(f"{season}: FAILED ({exc})")
                else:
                    time.sleep(3)
        time.sleep(cfg["api_delay_seconds"])


if __name__ == "__main__":
    main()
