import pandas as pd

import db


def _sample_players():
    return pd.DataFrame([{
        "player_id": 1, "name": "Test Guy", "team": "LAL", "age": 25.0,
        "nba_position": "G", "positions": "PG,SG",
    }])


def _sample_stats():
    row = {c: 1.0 for c in db.STAT_COLS}
    row["player_id"] = 1
    row["gp"] = 50
    return pd.DataFrame([row])


def test_upsert_idempotent(tmp_path):
    conn = db.get_connection(str(tmp_path / "t.db"))
    for _ in range(2):
        db.upsert_players(conn, _sample_players())
        db.upsert_stats(conn, _sample_stats(), "2025-26")
    assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM player_stats").fetchone()[0] == 1


def test_load_board_joins(tmp_path):
    conn = db.get_connection(str(tmp_path / "t.db"))
    db.upsert_players(conn, _sample_players())
    db.upsert_stats(conn, _sample_stats(), "2025-26")
    board = db.load_board(conn, "2025-26")
    assert len(board) == 1
    assert board.iloc[0]["name"] == "Test Guy"
    assert board.iloc[0]["gp"] == 50
    assert db.load_board(conn, "2024-25").empty
