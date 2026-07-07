"""$200 auction 估價與最佳陣容優化。

估價採標準 value-over-replacement 法：聯盟可上名單的最後一名球員值 $1，
其餘依「超出替補水準的價值」按比例分配剩餘預算池。
陣容優化以整數規劃（pulp/CBC）求精確解：填滿全部格位、總價不超預算、
最大化總 Fantasy Point。
"""
import pandas as pd
import pulp


def estimate_prices(fp: pd.Series, budget: int, teams: int, roster_size: int) -> pd.Series:
    """由 Fantasy Point 推算每名球員的合理拍賣標價（整數，最低 $1）。"""
    n_rostered = teams * roster_size
    ranked = fp.sort_values(ascending=False)
    replacement = ranked.iloc[n_rostered] if len(ranked) > n_rostered else ranked.min()
    value = (fp - replacement).clip(lower=0)
    pool = budget * teams - n_rostered  # 每個名單位保底 $1，剩餘依價值分配
    total_value = value.sum()
    if total_value <= 0:
        return pd.Series(1, index=fp.index)
    return (1 + value * pool / total_value).round().clip(lower=1).astype(int)


def optimize_roster(
    df: pd.DataFrame, slots: list, eligibility: dict, budget: int
) -> pd.DataFrame:
    """求最佳陣容。df 需含 name, positions, fantasy_point, price 欄。

    回傳選中球員（含 slot 欄），依 slots 順序排列。
    無可行解（預算/格位過緊）時 raise ValueError。
    """
    players = df.reset_index(drop=True)
    x = {}  # (player_idx, slot_idx) -> 二元變數，只建可指派的組合
    for i, pos_str in enumerate(players["positions"]):
        pos = set(str(pos_str).split(","))
        for s, slot in enumerate(slots):
            if pos & set(eligibility[slot]):
                x[(i, s)] = pulp.LpVariable(f"x_{i}_{s}", cat="Binary")

    prob = pulp.LpProblem("auction_roster", pulp.LpMaximize)
    prob += pulp.lpSum(players.at[i, "fantasy_point"] * v for (i, _), v in x.items())
    for s in range(len(slots)):
        prob += pulp.lpSum(v for (i, s2), v in x.items() if s2 == s) == 1
    for i in players.index:
        prob += pulp.lpSum(v for (i2, _), v in x.items() if i2 == i) <= 1
    prob += pulp.lpSum(players.at[i, "price"] * v for (i, _), v in x.items()) <= budget

    status = prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if pulp.LpStatus[status] != "Optimal":
        raise ValueError("無可行解：預算或格位設定過緊")

    picks = sorted(
        ((s, i) for (i, s), v in x.items() if v.value() == 1), key=lambda t: t[0]
    )
    out = players.loc[[i for _, i in picks]].copy()
    out.insert(0, "slot", [slots[s] for s, _ in picks])
    return out
