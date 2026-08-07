"""nba_api 封裝：場均數據 + 30 隊 roster。對應 04_architecture.md §4。"""
import time

import pandas as pd
from nba_api.stats.endpoints import (
    commonteamroster,
    leaguedashplayerstats,
    playergamelogs,
)
from nba_api.stats.static import teams

# LeagueDashPlayerStats 欄位 -> player_stats/players 欄位
STAT_RENAME = {
    "PLAYER_ID": "player_id", "PLAYER_NAME": "name",
    "TEAM_ABBREVIATION": "team", "AGE": "age",
    "GP": "gp", "MIN": "min",
    "PTS": "pts", "REB": "reb", "AST": "ast",
    "STL": "stl", "BLK": "blk", "TOV": "tov",
    "FGM": "fgm", "FGA": "fga", "FG_PCT": "fg_pct",
    "FG3M": "fg3m", "FG3A": "fg3a", "FG3_PCT": "fg3_pct",
    "FTM": "ftm", "FTA": "fta", "FT_PCT": "ft_pct",
}


def fetch_season_stats(season: str) -> pd.DataFrame:
    """全聯盟球員場均數據。失敗直接 raise（FR-6.1：無此資料則中止）。"""
    df = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season, per_mode_detailed="PerGame"
    ).get_data_frames()[0]
    return df[list(STAT_RENAME)].rename(columns=STAT_RENAME)


def fetch_advanced_stats(season: str) -> pd.DataFrame:
    """全聯盟球員進階數據：使用率 USG%、真實命中率 TS%。

    與 fetch_season_stats 同一個 endpoint，只是 measure_type 換成 Advanced。
    """
    df = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season, per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced",
    ).get_data_frames()[0]
    df = df[["PLAYER_ID", "USG_PCT", "TS_PCT"]].rename(columns={
        "PLAYER_ID": "player_id", "USG_PCT": "usg_pct", "TS_PCT": "ts_pct",
    })
    # ponytail: stats.nba.com 的百分比量級不固定（0.28 或 28.0 皆出現過），統一成 0-100
    if df["usg_pct"].max() <= 1:
        df["usg_pct"] = df["usg_pct"] * 100
    if df["ts_pct"].max() <= 1:
        df["ts_pct"] = df["ts_pct"] * 100
    return df


# PlayerGameLogs 欄位 -> game_logs 欄位（不取 *_PCT，見 db.py DDL 註解）
GAMELOG_RENAME = {
    "PLAYER_ID": "player_id", "GAME_ID": "game_id", "GAME_DATE": "game_date",
    "TEAM_ABBREVIATION": "team", "MIN": "min",
    "PTS": "pts", "REB": "reb", "AST": "ast",
    "STL": "stl", "BLK": "blk", "TOV": "tov",
    "FGM": "fgm", "FGA": "fga", "FG3M": "fg3m", "FG3A": "fg3a",
    "FTM": "ftm", "FTA": "fta",
}


def fetch_game_logs(season: str, date_from: str | None = None) -> pd.DataFrame:
    """全聯盟逐場 box score。date_from（'YYYY-MM-DD'）之後的比賽，None 代表整季。

    一次呼叫拿全聯盟，不需要逐球員迴圈——這是能做每日更新的關鍵。
    """
    df = playergamelogs.PlayerGameLogs(
        season_nullable=season,
        date_from_nullable=_api_date(date_from),
        # 不指定的話季後賽也會混進來；fantasy 聯盟只跑例行賽
        season_type_nullable="Regular Season",
    ).get_data_frames()[0]
    df = df[list(GAMELOG_RENAME)].rename(columns=GAMELOG_RENAME)
    # API 回傳 '2025-10-22T00:00:00'，只留日期部分
    df["game_date"] = df["game_date"].str[:10]
    return df


def _api_date(iso_date: str | None) -> str:
    """'2025-10-22' -> '10/22/2025'（stats.nba.com 的日期格式）。None -> 空字串。"""
    if not iso_date:
        return ""
    y, m, d = iso_date.split("-")
    return f"{m}/{d}/{y}"


def fetch_positions(season: str, delay: float = 0.6) -> pd.DataFrame:
    """30 隊 roster 的球員位置。單隊失敗重試 1 次，仍失敗則跳過（FR-6.1）。"""
    frames = []
    for team in teams.get_teams():
        for attempt in (1, 2):
            try:
                roster = commonteamroster.CommonTeamRoster(
                    team_id=team["id"], season=season
                ).get_data_frames()[0]
                frames.append(roster[["PLAYER_ID", "POSITION"]])
                break
            except Exception as exc:  # nba_api 可能丟各種網路/JSON 錯誤
                if attempt == 2:
                    print(f"WARN: roster failed for {team['abbreviation']}: {exc}")
                else:
                    time.sleep(delay)
        time.sleep(delay)
    if not frames:
        return pd.DataFrame(columns=["player_id", "nba_position"])
    out = pd.concat(frames, ignore_index=True)
    return out.rename(columns={"PLAYER_ID": "player_id", "POSITION": "nba_position"})


def map_positions(nba_position: str, mapping: dict) -> str:
    """'G-F' -> 'SG,SF'。未知/空位置回傳空字串（FR-6.2）。"""
    return ",".join(mapping.get(nba_position, []))
