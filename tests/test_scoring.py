import pandas as pd

from scoring import compute_fantasy_points


def test_weighted_sum():
    df = pd.DataFrame({"pts": [10.0], "ast": [4.0], "tov": [2.0]})
    fp = compute_fantasy_points(df, {"pts": 1.0, "ast": 1.5, "tov": -1.0})
    assert fp.iloc[0] == 10 + 6 - 2


def test_missing_column_ignored():
    df = pd.DataFrame({"pts": [10.0]})
    fp = compute_fantasy_points(df, {"pts": 1.0, "nonexistent": 99.0})
    assert fp.iloc[0] == 10.0


def test_nan_treated_as_zero():
    df = pd.DataFrame({"pts": [float("nan")], "reb": [5.0]})
    fp = compute_fantasy_points(df, {"pts": 1.0, "reb": 1.2})
    assert fp.iloc[0] == 6.0
