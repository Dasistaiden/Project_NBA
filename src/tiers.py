"""分層：把同位置的球員依 Fantasy Point 斷層切成層級。

拍賣制的實戰重點不是「誰比較好」，是「斷層在哪」——從第 3 名掉到第 4 名
若只差 0.5 分，就沒有理由為了第 3 名多花 $15；若差 8 分，那就該搶。
"""
import pandas as pd


def gaps_to_next(fp: pd.Series) -> pd.Series:
    """每名球員與「排在他後面那一名」的 FP 差距。最後一名為 0。"""
    ranked = fp.sort_values(ascending=False)
    return (-ranked.diff()).shift(-1).fillna(0.0).reindex(fp.index)


def default_threshold(groups: list, k: float = 2.5) -> float:
    """預設斷層門檻 = 各組相鄰差距合併後的中位數 × k。

    必須餵「實際會被分層的那些人」（各位置的候選名單），不能餵整池：
    整池 400 人的相鄰差距中位數只有 0.04，用它當門檻會讓每個人自成一層。

    用中位數而非平均：少數幾個巨大斷層（榜首與其他人的差距）會把平均拉高，
    導致所有中段斷層都被門檻吃掉。
    """
    diffs = [-g.sort_values(ascending=False).diff().dropna() for g in groups]
    diffs = pd.concat(diffs) if diffs else pd.Series(dtype=float)
    return round(float(diffs.median() * k), 1) if len(diffs) else 0.0


def assign_tiers(fp: pd.Series, threshold: float) -> pd.Series:
    """依 FP 由高到低，相鄰差距超過 threshold 就切一層。回傳層號（1 起）。"""
    ranked = fp.sort_values(ascending=False)
    breaks = (-ranked.diff().fillna(0)) > threshold
    return breaks.cumsum().add(1).reindex(fp.index)
