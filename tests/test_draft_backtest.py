import warnings

import pandas as pd
import pytest

import db
import draft_backtest as bt
import draft_history as dh
from update_data import BASE_DIR, load_config

pytestmark = pytest.mark.skipif(
    not dh.DEFAULT_PATH.exists()
    or not (BASE_DIR / load_config()["db_path"]).exists(),
    reason="需要 history_draft.xlsx 與 nba.db",
)


@pytest.fixture(scope="module")
def fixtures():
    warnings.filterwarnings("ignore")
    cfg = load_config()
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    return (pd.read_sql_query("SELECT * FROM player_stats", conn),
            dh.load(), cfg["weights"])


@pytest.mark.parametrize("year", list(bt.DRAFT_SEASONS))
def test_models_beat_the_cheap_pool_average(year, fixtures):
    """模型挑的前 N 名要贏過便宜池的平均，否則這條路線就沒有立足點。

    這是量尺測試：改動預測模型後若這裡退步，就是改壞了。
    """
    history, draft, weights = fixtures
    summary, cheap = bt.run_year(year, history, draft, weights)
    assert summary["池內人數"] >= 30
    for model in ("marcel", "ml"):
        assert summary[f"{model}_相關"] > 0, f"{model} 對便宜池毫無排序能力"
        assert summary[f"{model}_top{bt.TOP_N}提升"] > 0, f"{model} 挑的人不如隨機"


def test_backtest_never_sees_the_target_season(fixtures):
    """特徵只能用目標季之前的資料——洩漏會讓回測數字全部失真。"""
    history, draft, weights = fixtures
    target = bt.DRAFT_SEASONS[2024]
    trimmed = history[history["season"] < target]
    # 把目標季整個抽掉後仍能產生預測，代表預測端沒有偷看目標季
    proj = bt._projected_totals(
        pd.concat([trimmed, history[history["season"] == target]]), target, weights
    )
    proj_blind = bt._projected_totals(trimmed, target, weights)
    common = proj.index.intersection(proj_blind.index)
    assert len(common) > 100
    pd.testing.assert_series_equal(
        proj.loc[common, "marcel"], proj_blind.loc[common, "marcel"]
    )
