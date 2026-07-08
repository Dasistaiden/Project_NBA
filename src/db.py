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
    age         REAL,               -- 該季當時年齡（年齡曲線用）
    team        TEXT,               -- 該季所屬球隊（換隊特徵用）
    gp          INTEGER,
    min         REAL,
    pts REAL, reb REAL, ast REAL, stl REAL, blk REAL, tov REAL,
    fgm REAL, fga REAL, fg_pct REAL,
    fg3m REAL, fg3a REAL, fg3_pct REAL,
    ftm REAL, fta REAL, ft_pct REAL,
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS projections (
    player_id   INTEGER NOT NULL,
    season      TEXT    NOT NULL,   -- 預測的目標賽季，如 2026-27
    model       TEXT    NOT NULL,   -- marcel / ml
    pts REAL, reb REAL, ast REAL, stl REAL, blk REAL, tov REAL,
    min REAL, gp REAL,
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (player_id, season, model)
);
"""

PLAYER_COLS = ["player_id", "name", "team", "age", "nba_position", "positions"]
STAT_COLS = [
    "player_id", "age", "team", "gp", "min",
    "pts", "reb", "ast", "stl", "blk", "tov",
    "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct",
]
PROJ_COLS = ["player_id", "pts", "reb", "ast", "stl", "blk", "tov", "min", "gp"]


def get_connection(db_path: str) -> sqlite3.Connection:
    parent = Path(db_path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    # 舊資料庫遷移：補上後來新增的欄位
    existing = {row[1] for row in conn.execute("PRAGMA table_info(player_stats)")}
    for col, typ in (("age", "REAL"), ("team", "TEXT")):
        if col not in existing:
            conn.execute(f"ALTER TABLE player_stats ADD COLUMN {col} {typ}")
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


def upsert_projections(
    conn: sqlite3.Connection, df: pd.DataFrame, season: str, model: str
) -> None:
    cols = PROJ_COLS + ["season", "model"]
    df = df.assign(season=season, model=model)
    rows = df[cols].itertuples(index=False, name=None)
    conn.executemany(
        f"INSERT OR REPLACE INTO projections ({','.join(cols)}) "
        f"VALUES ({','.join('?' * len(cols))})",
        rows,
    )
    conn.commit()


def load_projection_board(
    conn: sqlite3.Connection, season: str, model: str
) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT p.player_id, p.name, p.team, p.age, p.positions,
               j.gp, j.min, j.pts, j.reb, j.ast, j.stl, j.blk, j.tov
        FROM projections j JOIN players p ON p.player_id = j.player_id
        WHERE j.season = ? AND j.model = ?
        """,
        conn,
        params=(season, model),
    )


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
