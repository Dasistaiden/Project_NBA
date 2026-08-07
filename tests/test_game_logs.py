import pandas as pd
import pytest

import db
import fetcher


def _log(player_id, game_id, game_date, **stats):
    row = {c: 0.0 for c in db.GAME_LOG_COLS}
    row.update(
        player_id=player_id, game_id=game_id, game_date=game_date, team="LAL", **stats
    )
    return row


@pytest.fixture
def conn(tmp_path):
    c = db.get_connection(str(tmp_path / "t.db"))
    db.upsert_players(c, pd.DataFrame([{
        "player_id": 1, "name": "Test Guy", "team": "LAL", "age": 25.0,
        "nba_position": "G", "positions": "PG,SG",
    }]))
    return c


def test_reupsert_same_game_does_not_duplicate(conn):
    logs = pd.DataFrame([_log(1, "0022500001", "2025-11-01", pts=20)])
    db.upsert_game_logs(conn, logs, "2025-26")
    db.upsert_game_logs(conn, logs, "2025-26")   # 日更從最後一天重抓的情境
    assert conn.execute("SELECT COUNT(*) FROM game_logs").fetchone()[0] == 1


def test_last_game_date(conn):
    assert db.last_game_date(conn, "2025-26") is None
    db.upsert_game_logs(conn, pd.DataFrame([
        _log(1, "0022500001", "2025-11-01"),
        _log(1, "0022500002", "2025-11-05"),
    ]), "2025-26")
    assert db.last_game_date(conn, "2025-26") == "2025-11-05"


def test_window_pct_is_summed_not_averaged(conn):
    """兩場 1/1 與 1/10：正確答案 2/11=.182，錯的平均法會給 (1.0+0.1)/2=.55"""
    db.upsert_game_logs(conn, pd.DataFrame([
        _log(1, "0022500001", "2025-11-01", fgm=1, fga=1),
        _log(1, "0022500002", "2025-11-02", fgm=1, fga=10),
    ]), "2025-26")
    row = db.load_window(conn, "2025-26", days=30).iloc[0]
    assert row["fg_pct"] == pytest.approx(2 / 11, abs=1e-4)


def test_window_respects_cutoff(conn):
    db.upsert_game_logs(conn, pd.DataFrame([
        _log(1, "0022500001", "2025-11-01", pts=40),
        _log(1, "0022500002", "2025-11-20", pts=10),
    ]), "2025-26")
    recent = db.load_window(conn, "2025-26", days=7)   # 錨在 11-20，只含後者
    assert recent.iloc[0]["gp"] == 1
    assert recent.iloc[0]["pts"] == 10
    assert db.load_window(conn, "2025-26", days=30).iloc[0]["gp"] == 2


def test_window_empty_db_has_columns(conn):
    out = db.load_window(conn, "2025-26")
    assert out.empty
    assert "fg_pct" in out.columns   # 空表仍要能餵給下游而不 KeyError


def test_api_date_format():
    assert fetcher._api_date("2025-10-22") == "10/22/2025"
    assert fetcher._api_date(None) == ""
