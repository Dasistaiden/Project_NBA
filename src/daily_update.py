"""賽季中的每日增量更新：只抓上次之後的比賽。手動執行：python src/daily_update.py

與 update_data.py 的差別：那支是季前/整季重建（全聯盟場均 + 位置 + 進階數據，
30+ 次 API 呼叫）；這支是賽季中天天跑的，一次呼叫拿完新比賽。
"""
from pathlib import Path

import db
import fetcher
from update_data import load_config

BASE_DIR = Path(__file__).resolve().parents[1]


def run(season: str | None = None) -> None:
    cfg = load_config()
    season = season or cfg["season"]
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))

    since = db.last_game_date(conn, season)
    # 從最後一天「當天」重抓而非隔天：當晚可能還有比賽未結束就跑過更新。
    # PK 是 (player_id, game_id)，重抓同一場只會覆寫，不會長出重複列。
    print(f"Fetching game logs for {season}" + (f" since {since}..." if since else " (full season)..."))
    logs = fetcher.fetch_game_logs(season, since)
    if logs.empty:
        print("No new games.")
        return

    db.upsert_game_logs(conn, logs, season)
    print(f"Done. {len(logs)} game logs upserted, latest {db.last_game_date(conn, season)}.")


if __name__ == "__main__":
    run()
