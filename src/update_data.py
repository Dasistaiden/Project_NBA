"""全量更新主流程（唯一寫入進入點）。手動執行：python src/update_data.py"""
import time
from pathlib import Path

import yaml

import db
import fetcher

BASE_DIR = Path(__file__).resolve().parents[1]


def load_config(base_dir: Path = BASE_DIR) -> dict:
    with open(base_dir / "config" / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(season: str | None = None) -> None:
    cfg = load_config()
    season = season or cfg["season"]
    print(f"Fetching {season} per-game stats...")
    stats = fetcher.fetch_season_stats(season)
    print(f"  {len(stats)} players")

    print("Fetching team rosters for positions...")
    positions = fetcher.fetch_positions(season, cfg["api_delay_seconds"])

    players = stats[["player_id", "name", "team", "age"]].merge(
        positions, on="player_id", how="left"
    )
    players["nba_position"] = players["nba_position"].fillna("")
    players["positions"] = players["nba_position"].map(
        lambda p: fetcher.map_positions(p, cfg["position_mapping"])
    )

    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    db.upsert_players(conn, players)
    db.upsert_stats(conn, stats, season)
    n_pos = (players["positions"] != "").sum()
    print(f"Done. {len(players)} players upserted, {n_pos} with mapped positions.")

    # 歷史賽季只回補 stats（players 名單以當前賽季為準）
    for hist_season in cfg.get("history_seasons", []):
        time.sleep(cfg["api_delay_seconds"])
        print(f"Backfilling {hist_season} per-game stats...")
        hist = fetcher.fetch_season_stats(hist_season)
        db.upsert_stats(conn, hist, hist_season)
        print(f"  {len(hist)} rows")


if __name__ == "__main__":
    run()
