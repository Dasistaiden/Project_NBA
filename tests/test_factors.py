import pandas as pd

from factors import health_scores, role_label, season_availability


def _row(pid, season, gp, **kw):
    base = dict(player_id=pid, season=season, gp=gp, min=30.0, pts=15.0,
                reb=5.0, ast=4.0, blk=0.5, usg_pct=20.0)
    base.update(kw)
    return base


def test_availability_uses_league_max_as_denominator():
    # 模擬縮水賽季：該季最大出賽 66 場（2011-12 封館）
    history = pd.DataFrame([
        _row(1, "2011-12", 66),   # 全勤 → 1.0
        _row(2, "2011-12", 33),   # 出一半 → 0.5
    ])
    avail = season_availability(history)
    assert avail.loc[avail["player_id"] == 1, "availability"].iloc[0] == 1.0
    assert avail.loc[avail["player_id"] == 2, "availability"].iloc[0] == 0.5


def test_health_scores_weighted_and_risk():
    history = pd.DataFrame([
        # player 1：三季全勤 → 100 分、低風險
        _row(1, "2023-24", 82), _row(1, "2024-25", 82), _row(1, "2025-26", 82),
        # player 2：越來越常缺席 → 低分、高風險
        _row(2, "2023-24", 82), _row(2, "2024-25", 41), _row(2, "2025-26", 20),
    ])
    scores = health_scores(history, "2026-27")
    assert scores.at[1, "health_score"] == 100.0
    assert scores.at[1, "risk"] == "低"
    # player 2 加權：(3*20/82 + 2*41/82 + 1*82/82) / 6 ≈ 0.456 → 45.6 分
    assert scores.at[2, "health_score"] < 50
    assert scores.at[2, "risk"] == "高"


def test_health_scores_rookie_not_penalized():
    # 新秀只有一季（全勤），權重重新正規化 → 100 分而不是 100/6
    history = pd.DataFrame([
        _row(1, "2025-26", 82),
        _row(9, "2023-24", 82), _row(9, "2024-25", 82), _row(9, "2025-26", 82),
    ])
    scores = health_scores(history, "2026-27")
    assert scores.at[1, "health_score"] == 100.0


def test_health_scores_requires_last_season():
    # 前一季（2025-26）沒出賽的球員不在結果裡
    history = pd.DataFrame([_row(1, "2024-25", 82)])
    scores = health_scores(history, "2026-27")
    assert 1 not in scores.index


def test_role_label_usg_branches():
    core = dict(min=34.0, usg_pct=31.0, ast=4.0, pts=28.0, reb=6.0, blk=1.0)
    assert role_label(pd.Series(core)) == "核心主力・進攻核心"

    playmaker = dict(min=33.0, usg_pct=22.0, ast=8.0, pts=15.0, reb=4.0, blk=0.3)
    assert role_label(pd.Series(playmaker)) == "核心主力・組織發起者"

    blue_collar = dict(min=26.0, usg_pct=14.0, ast=1.5, pts=9.0, reb=10.0, blk=1.5)
    assert role_label(pd.Series(blue_collar)) == "先發・藍領內線"

    bench = dict(min=12.0, usg_pct=18.0, ast=1.0, pts=5.0, reb=2.0, blk=0.2)
    assert role_label(pd.Series(bench)) == "邊緣 / 深度替補"


def test_role_label_without_usg():
    # usg 缺值（NaN）退回上場時間邏輯，不噴錯
    row = pd.Series(dict(min=34.0, usg_pct=float("nan"), ast=7.0,
                         pts=20.0, reb=5.0, blk=0.5))
    assert role_label(row) == "核心主力・組織發起者"