"""SQLite 連線、schema、upsert、查詢。對應 04_architecture.md §3-4。"""
import sqlite3
from pathlib import Path

import pandas as pd

DDL = """
CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    team          TEXT,
    age           REAL,
    nba_position  TEXT,
    positions     TEXT
);

CREATE TABLE IF NOT EXISTS player_stats (
    player_id   INTEGER NOT NULL,
    season      TEXT    NOT NULL,
    gp          INTEGER,
    min         REAL,
    pts REAL, reb REAL, ast REAL, stl REAL, blk REAL, tov REAL,
    fgm REAL, fga REAL, fg_pct REAL,
    fg3m REAL, fg3a REAL, fg3_pct REAL,
    ftm REAL, fta REAL, ft_pct REAL,
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (player_id, season)
);
"""

PLAYER_COLS = ["player_id", "name", "team", "age", "nba_position", "positions"]
STAT_COLS = [
    "player_id", "gp", "min", "pts", "reb", "ast", "stl", "blk", "tov",
    "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct",
]


def get_connection(db_path: str) -> sqlite3.Connection:
    parent = Path(db_path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    return conn


def upsert_players(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    rows = df[PLAYER_COLS].itertuples(index=False, name=None)
    conn.executemany(
        f"INSERT OR REPLACE INTO players ({','.join(PLAYER_COLS)}) "
        f"VALUES ({','.join('?' * len(PLAYER_COLS))})",
        rows,
    )
    conn.commit()


def upsert_stats(conn: sqlite3.Connection, df: pd.DataFrame, season: str) -> None:
    cols = STAT_COLS + ["season"]
    df = df.assign(season=season)
    rows = df[cols].itertuples(index=False, name=None)
    conn.executemany(
        f"INSERT OR REPLACE INTO player_stats ({','.join(cols)}) "
        f"VALUES ({','.join('?' * len(cols))})",
        rows,
    )
    conn.commit()


def load_board(conn: sqlite3.Connection, season: str) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT p.player_id, p.name, p.team, p.age, p.nba_position, p.positions,
               s.gp, s.min, s.pts, s.reb, s.ast, s.stl, s.blk, s.tov,
               s.fgm, s.fga, s.fg_pct, s.fg3m, s.fg3a, s.fg3_pct,
               s.ftm, s.fta, s.ft_pct
        FROM players p
        JOIN player_stats s ON p.player_id = s.player_id
        WHERE s.season = ?
        """,
        conn,
        params=(season,),
    )
