import pandas as pd

from projection import (
    build_features, marcel, next_season, predict_ml, prev_season, train_ml,
)


def _row(pid, season, age, team, pts, gp=70):
    return dict(
        player_id=pid, season=season, age=age, team=team, gp=gp, min=30.0,
        pts=pts, reb=5.0, ast=5.0, stl=1.0, blk=1.0, tov=2.0,
        fgm=8.0, fga=16.0, fg_pct=0.5, fg3m=2.0, fg3a=5.0, fg3_pct=0.4,
        ftm=4.0, fta=5.0, ft_pct=0.8,
    )


def _history():
    rows = []
    for i, (season, age) in enumerate([("2023-24", 25), ("2024-25", 26), ("2025-26", 27)]):
        rows.append(_row(1, season, age, "AAA", pts=24.0))
        # player 2：低產出、2025-26 換隊
        rows.append(_row(2, season, age, "BBB" if i < 2 else "CCC", pts=8.0))
    return pd.DataFrame(rows)


def test_season_math():
    assert prev_season("2025-26") == "2024-25"
    assert prev_season("2025-26", 3) == "2022-23"
    assert next_season("2025-26") == "2026-27"
    assert prev_season("2000-01") == "1999-00"


def test_marcel_regresses_toward_league_mean():
    proj = marcel(_history(), "2026-27")
    league_pts = 16.0  # 兩名球員 gp 相同 → 聯盟均值 (24+8)/2
    assert league_pts < proj.at[1, "pts"] < 24.0   # 高產出被拉回
    assert 8.0 < proj.at[2, "pts"] < league_pts    # 低產出被拉高
    assert (proj["pts"] >= 0).all()


def test_team_changed_flag():
    X = build_features(_history(), "2026-27")
    assert X.at[2, "team_changed"] == 1.0
    assert X.at[1, "team_changed"] == 0.0


def test_ml_smoke():
    # GBM 需要合理樣本數，合成 40 名球員 × 3 季
    rows = []
    for pid in range(1, 41):
        for season, age in [("2023-24", 22 + pid % 10), ("2024-25", 23 + pid % 10),
                            ("2025-26", 24 + pid % 10)]:
            rows.append(_row(pid, season, age, f"T{pid % 6}", pts=5.0 + pid * 0.5))
    history = pd.DataFrame(rows)
    models = train_ml(history, "2025-26")
    proj = predict_ml(models, history, "2026-27")
    assert len(proj) == 40
    assert "pts" in proj.columns and "gp" in proj.columns
    assert (proj["pts"] >= 0).all()
