import pandas as pd
import pytest

from auction import estimate_prices, optimize_roster

ELIGIBILITY = {
    "G": ["PG", "SG"], "C": ["C"],
    "UTIL": ["PG", "SG", "SF", "PF", "C"],
}


def test_prices_replacement_level_is_one_dollar():
    # 4 隊 × 2 人 = 8 個名單位；第 9 名以後應為 $1
    fp = pd.Series([50, 45, 40, 35, 30, 25, 20, 15, 10, 5])
    prices = estimate_prices(fp, budget=100, teams=4, roster_size=2)
    assert prices.iloc[-1] == 1
    assert prices.iloc[0] > prices.iloc[1]  # 越強越貴
    assert (prices >= 1).all()


def test_optimizer_respects_budget_and_slots():
    df = pd.DataFrame([
        {"name": "StarG", "positions": "PG,SG", "fantasy_point": 60.0, "price": 50},
        {"name": "MidG", "positions": "PG", "fantasy_point": 30.0, "price": 10},
        {"name": "StarC", "positions": "C", "fantasy_point": 55.0, "price": 45},
        {"name": "CheapC", "positions": "C", "fantasy_point": 20.0, "price": 1},
        {"name": "Wing", "positions": "SF", "fantasy_point": 40.0, "price": 20},
    ])
    roster = optimize_roster(df, ["G", "C", "UTIL"], ELIGIBILITY, budget=60)
    assert len(roster) == 3
    assert roster["price"].sum() <= 60
    assert set(roster["slot"]) == {"G", "C", "UTIL"}
    # 預算 60 下最佳解：StarG(50) + CheapC(1) + 不超過 9 元的 UTIL 不存在
    # → 實際最佳為 MidG + CheapC + StarC = 105 FP / $56
    assert roster["fantasy_point"].sum() == 105.0


def test_optimizer_infeasible_raises():
    df = pd.DataFrame([
        {"name": "OnlyG", "positions": "PG", "fantasy_point": 10.0, "price": 99},
    ])
    with pytest.raises(ValueError):
        optimize_roster(df, ["G", "C"], ELIGIBILITY, budget=200)
