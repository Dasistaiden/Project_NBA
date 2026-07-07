"""Fantasy Point 計算。對應 03_requirements.md FR-4。"""
import pandas as pd


def compute_fantasy_points(df: pd.DataFrame, weights: dict) -> pd.Series:
    """各欄位 × 權重加總。weights 中 df 沒有的欄位直接忽略（欄位可擴充）。"""
    total = pd.Series(0.0, index=df.index)
    for col, weight in weights.items():
        if col in df.columns:
            total = total + df[col].fillna(0) * weight
    return total.round(2)
