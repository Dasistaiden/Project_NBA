"""下一季場均預測：Marcel 基準 + 梯度提升樹（ML），含回測評估。

Marcel（基準）：近三季依「權重 × 出賽數」加權平均，向聯盟平均回歸
REGRESS_GAMES 場的虛擬量，再乘年齡修正。經典基準模型，可解釋、難打敗。

ML：每項數據一個 HistGradientBoostingRegressor，特徵為前三季各項數據、
年齡、換隊旗標；生涯不足三季的缺值由模型原生處理（不需補值）。

兩者都只對「前一季有出賽紀錄」的球員做預測；新秀無資料，屬 Phase 3。
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from scoring import compute_fantasy_points

PROJECT_STATS = ["pts", "reb", "ast", "stl", "blk", "tov", "min"]
FEATURE_STATS = PROJECT_STATS + ["gp", "fg_pct", "ft_pct", "fg3m"]
MARCEL_WEIGHTS = (5.0, 4.0, 3.0)
REGRESS_GAMES = 30          # 向聯盟平均回歸的虛擬場次
AGE_PEAK, AGE_SLOPE = 27.0, 0.004


def prev_season(season: str, n: int = 1) -> str:
    y = int(season[:4]) - n
    return f"{y}-{str(y + 1)[-2:]}"


def next_season(season: str) -> str:
    y = int(season[:4]) + 1
    return f"{y}-{str(y + 1)[-2:]}"


def _lag(history: pd.DataFrame, target_season: str, n: int) -> pd.DataFrame:
    return history[history["season"] == prev_season(target_season, n)].set_index("player_id")


def _league_mean(lags: list, stat: str) -> float:
    d = pd.concat(lags)
    return float(np.average(d[stat].fillna(0), weights=d["gp"].clip(lower=1)))


def marcel(history: pd.DataFrame, target_season: str) -> pd.DataFrame:
    """回傳 index=player_id 的預測場均（PROJECT_STATS + gp）。"""
    lags = [_lag(history, target_season, n) for n in (1, 2, 3)]
    idx = lags[0].index          # 前一季有出賽者才預測
    proj = pd.DataFrame(index=idx)
    for stat in PROJECT_STATS:
        num = pd.Series(REGRESS_GAMES * _league_mean(lags, stat), index=idx)
        den = pd.Series(float(REGRESS_GAMES), index=idx)
        for w, lag in zip(MARCEL_WEIGHTS, lags):
            gp = lag["gp"].reindex(idx).fillna(0)
            num += w * gp * lag[stat].reindex(idx).fillna(0)
            den += w * gp
        proj[stat] = num / den
    age_next = lags[0]["age"].reindex(idx) + 1
    adj = (1 + AGE_SLOPE * (AGE_PEAK - age_next)).clip(0.85, 1.15).fillna(1.0)
    proj[PROJECT_STATS] = proj[PROJECT_STATS].mul(adj, axis=0)
    proj["gp"] = lags[0]["gp"]   # ponytail: 出賽數沿用上季，Phase 2 健康指數上線後改用風險修正值
    return proj.clip(lower=0).round(2)


def build_features(history: pd.DataFrame, target_season: str) -> pd.DataFrame:
    lags = [_lag(history, target_season, n) for n in (1, 2, 3)]
    idx = lags[0].index
    X = pd.DataFrame(index=idx)
    for n, lag in enumerate(lags, 1):
        for col in FEATURE_STATS:
            X[f"{col}_l{n}"] = lag[col].reindex(idx)
    X["age"] = lags[0]["age"].reindex(idx) + 1
    X["team_changed"] = (
        lags[0]["team"].reindex(idx).ne(lags[1]["team"].reindex(idx))
    ).astype(float)
    return X


def train_ml(history: pd.DataFrame, last_train_season: str) -> dict:
    """以所有 ≤ last_train_season 的賽季為目標訓練；特徵永遠只用目標季之前的資料。"""
    seasons = sorted(history["season"].unique())
    targets = [s for s in seasons[1:] if s <= last_train_season]
    X_parts, y_parts = [], []
    for ts in targets:
        X = build_features(history, ts)
        y = history[history["season"] == ts].set_index("player_id")
        y = y[PROJECT_STATS].reindex(X.index)
        keep = y["pts"].notna()          # 目標季有出賽才是有效樣本
        X_parts.append(X[keep])
        y_parts.append(y[keep])
    X_all, y_all = pd.concat(X_parts), pd.concat(y_parts)
    # 整欄全 NaN 會讓 HistGBM 的 binning 崩潰（歷史賽季太少時的 lag 特徵）；
    # 全缺的欄位本身無資訊量，補 0 無害
    all_nan = [c for c in X_all.columns if X_all[c].isna().all()]
    X_all[all_nan] = 0.0
    return {
        stat: HistGradientBoostingRegressor(random_state=0).fit(X_all, y_all[stat])
        for stat in PROJECT_STATS
    }


def predict_ml(models: dict, history: pd.DataFrame, target_season: str) -> pd.DataFrame:
    X = build_features(history, target_season)
    proj = pd.DataFrame(
        {stat: m.predict(X) for stat, m in models.items()}, index=X.index
    )
    proj["gp"] = _lag(history, target_season, 1)["gp"]
    return proj.clip(lower=0).round(2)


def backtest(
    history: pd.DataFrame, weights: dict,
    test_seasons: tuple = ("2024-25", "2025-26"), min_gp: int = 20,
) -> pd.DataFrame:
    """三模型（naive / marcel / ml）在留出賽季上的 FP 誤差與排名相關性。

    只評估「實際出賽 ≥ min_gp 且模型有預測」的球員；訓練資料嚴格早於測試季。
    """
    rows = []
    for ts in test_seasons:
        past = history[history["season"] < ts]
        actual = history[
            (history["season"] == ts) & (history["gp"] >= min_gp)
        ].set_index("player_id")
        actual_fp = compute_fantasy_points(actual, weights)
        models = train_ml(past, prev_season(ts))
        preds = {
            "naive": _lag(past, ts, 1)[PROJECT_STATS],
            "marcel": marcel(past, ts),
            "ml": predict_ml(models, past, ts),
        }
        for name, proj in preds.items():
            ci = proj.index.intersection(actual.index)
            pfp = compute_fantasy_points(proj.loc[ci], weights)
            diff = pfp - actual_fp.loc[ci]
            rows.append({
                "test_season": ts, "model": name, "n_players": len(ci),
                "FP_MAE": round(diff.abs().mean(), 2),
                "rank_corr": round(pfp.corr(actual_fp.loc[ci], method="spearman"), 3),
            })
    return pd.DataFrame(rows)
