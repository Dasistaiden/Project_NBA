"""nba_api 封裝：場均數據 + 30 隊 roster。對應 04_architecture.md §4。"""
import time

import pandas as pd
from nba_api.stats.endpoints import commonteamroster, leaguedashplayerstats
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
