"""SQLite 連線、schema、upsert、查詢。對應 04_architecture.md §3-4。"""
import sqlite3
from datetime import date, timedelta
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
    usg_pct REAL,               -- 使用率（Phase 2 角色定位用）
    ts_pct  REAL,               -- 真實命中率（Phase 2 角色定位用）
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

-- 逐場 box score（賽季中的每日更新、滾動窗口排行用）
-- 刻意不存 fg_pct/ft_pct：窗口命中率必須是 SUM(fgm)/SUM(fga)，
-- 存了每場的百分比遲早有人拿去平均，那是錯的。
CREATE TABLE IF NOT EXISTS game_logs (
    player_id   INTEGER NOT NULL,
    game_id     TEXT    NOT NULL,
    game_date   TEXT    NOT NULL,   -- 'YYYY-MM-DD'，字串比較即可做區間查詢
    season      TEXT    NOT NULL,
    team        TEXT,               -- 該場所屬球隊（賽季中被交易會變）
    min  REAL,
    pts  REAL, reb REAL, ast REAL, stl REAL, blk REAL, tov REAL,
    fgm  REAL, fga REAL,
    fg3m REAL, fg3a REAL,
    ftm  REAL, fta REAL,
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (player_id, game_id)
);

CREATE INDEX IF NOT EXISTS idx_game_logs_window
    ON game_logs (season, game_date);

-- 聯盟裡誰擁有誰。沒有列 = 自由球員（不另外存自由球員名單）
CREATE TABLE IF NOT EXISTS rosters (
    player_id   INTEGER NOT NULL PRIMARY KEY,
    league_team TEXT    NOT NULL,
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);
"""

PLAYER_COLS = ["player_id", "name", "team", "age", "nba_position", "positions"]
STAT_COLS = [
    "player_id", "age", "team", "gp", "min",
    "pts", "reb", "ast", "stl", "blk", "tov",
    "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct",
]
PROJ_COLS = ["player_id", "pts", "reb", "ast", "stl", "blk", "tov", "min", "gp"]
GAME_LOG_COLS = [
    "player_id", "game_id", "game_date", "team", "min",
    "pts", "reb", "ast", "stl", "blk", "tov",
    "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
]


def get_connection(db_path: str) -> sqlite3.Connection:
    parent = Path(db_path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    # 舊資料庫遷移：補上後來新增的欄位
    existing = {row[1] for row in conn.execute("PRAGMA table_info(player_stats)")}
    for col, typ in (("age", "REAL"), ("team", "TEXT"),
                     ("usg_pct", "REAL"), ("ts_pct", "REAL")):
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


def update_advanced(conn: sqlite3.Connection, df: pd.DataFrame, season: str) -> None:
    """把進階數據（usg_pct/ts_pct）補進既有的 player_stats 列。

    用 UPDATE 而非 INSERT OR REPLACE：進階數據是「補欄位」，
    必須先 upsert_stats 建好該季的列，才輪得到這裡。
    """
    rows = [
        (usg, ts, pid, season)
        for pid, usg, ts in df[["player_id", "usg_pct", "ts_pct"]]
        .itertuples(index=False, name=None)
    ]
    conn.executemany(
        "UPDATE player_stats SET usg_pct = ?, ts_pct = ? "
        "WHERE player_id = ? AND season = ?",
        rows,
    )
    conn.commit()


def upsert_game_logs(conn: sqlite3.Connection, df: pd.DataFrame, season: str) -> None:
    """寫入逐場 box score。以 (player_id, game_id) 為鍵，重抓同一天不會重複。"""
    cols = GAME_LOG_COLS + ["season"]
    df = df.assign(season=season)
    rows = df[cols].itertuples(index=False, name=None)
    conn.executemany(
        f"INSERT OR REPLACE INTO game_logs ({','.join(cols)}) "
        f"VALUES ({','.join('?' * len(cols))})",
        rows,
    )
    conn.commit()


def last_game_date(conn: sqlite3.Connection, season: str) -> str | None:
    """已入庫的最後一場比賽日期，增量更新的起點。無資料回傳 None。"""
    return conn.execute(
        "SELECT MAX(game_date) FROM game_logs WHERE season = ?", (season,)
    ).fetchone()[0]


def load_window(
    conn: sqlite3.Connection, season: str, days: int = 14, end_date: str | None = None
) -> pd.DataFrame:
    """近 N 天的場均數據（動態排行用）。end_date 預設為庫中最後一場比賽日。

    命中率用 SUM(makes)/SUM(attempts) 而非每場百分比的平均——後者會讓
    出手兩次進一球的替補看起來像神射手。
    """
    end = end_date or last_game_date(conn, season) or ""
    # 無資料時 start=end="" 讓查詢自然落空，仍回傳帶正確欄位的空表
    start = "" if not end else (
        date.fromisoformat(end) - timedelta(days=days - 1)
    ).isoformat()
    return pd.read_sql_query(
        """
        SELECT g.player_id, p.name, p.team, p.positions,
               COUNT(*) AS gp,
               AVG(g.min) AS min, AVG(g.pts) AS pts, AVG(g.reb) AS reb,
               AVG(g.ast) AS ast, AVG(g.stl) AS stl, AVG(g.blk) AS blk,
               AVG(g.tov) AS tov, AVG(g.fg3m) AS fg3m,
               SUM(g.fgm) / NULLIF(SUM(g.fga), 0) AS fg_pct,
               SUM(g.ftm) / NULLIF(SUM(g.fta), 0) AS ft_pct
        FROM game_logs g JOIN players p ON p.player_id = g.player_id
        WHERE g.season = ? AND g.game_date BETWEEN ? AND ?
        GROUP BY g.player_id
        """,
        conn,
        params=(season, start, end),
    )


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
               s.ftm, s.fta, s.ft_pct, s.usg_pct, s.ts_pct
        FROM players p
        JOIN player_stats s ON p.player_id = s.player_id
        WHERE s.season = ?
        """,
        conn,
        params=(season,),
    )
