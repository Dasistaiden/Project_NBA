import pandas as pd

from tiers import assign_tiers, default_threshold, gaps_to_next


def test_assign_tiers_splits_at_gaps():
    # 兩個明顯斷層：20->12 (8分) 和 11->4 (7分)，中間差距都 <=1
    fp = pd.Series([20.0, 19.5, 19.0, 12.0, 11.5, 11.0, 4.0], index=list("abcdefg"))
    tiers = assign_tiers(fp, threshold=5.0)
    assert list(tiers) == [1, 1, 1, 2, 2, 2, 3]


def test_assign_tiers_threshold_too_high_gives_one_tier():
    fp = pd.Series([20.0, 12.0, 4.0])
    assert set(assign_tiers(fp, threshold=100.0)) == {1}


def test_assign_tiers_ignores_input_order():
    """輸入順序不影響分層——排序在函式內部做。"""
    fp = pd.Series([11.0, 20.0, 4.0, 19.0], index=list("abcd"))
    tiers = assign_tiers(fp, threshold=5.0)
    assert tiers["b"] == tiers["d"] == 1   # 20, 19 同層
    assert tiers["a"] == 2
    assert tiers["c"] == 3


def test_gaps_to_next_measures_downward_distance():
    fp = pd.Series([20.0, 12.0, 11.0], index=list("abc"))
    g = gaps_to_next(fp)
    assert g["a"] == 8.0
    assert g["b"] == 1.0
    assert g["c"] == 0.0   # 最後一名沒有下一名


def test_default_threshold_uses_median_not_mean():
    """一個巨大斷層不該把門檻拉高到吃掉所有中段斷層。"""
    fp = pd.Series([100.0, 20.0, 19.0, 18.0, 17.0])   # 差距 80,1,1,1
    assert default_threshold([fp], k=1.0) == 1.0


def test_default_threshold_pools_groups():
    """門檻由各位置的候選名單合併算出，不是整池。"""
    pg = pd.Series([50.0, 48.0])      # 差距 2
    c = pd.Series([40.0, 36.0])       # 差距 4
    assert default_threshold([pg, c], k=1.0) == 3.0   # median(2, 4)


def test_default_threshold_empty_input():
    assert default_threshold([pd.Series([5.0])]) == 0.0
    assert default_threshold([]) == 0.0
