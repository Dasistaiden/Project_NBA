"""回測：選秀當下的預測模型，能不能在便宜球員裡挑出爆發者？

這是「便宜球員預測」這條路線的量尺——任何模型改動都該先跑這支，
看 top-N 相對池子平均的提升有沒有變好，否則就是在憑感覺調參數。

執行：python src/draft_backtest.py
"""
import warnings

import pandas as pd

import db
import draft_history as dh
from projection import marcel, predict_ml, prev_season, train_ml
from scoring import compute_fantasy_points
from update_data import BASE_DIR, load_config

# 選秀年 -> 該次選秀要預測的賽季
DRAFT_SEASONS = {2024: "2024-25", 2025: "2025-26"}
CHEAP_MAX = 10      # 「便宜」的定義：成交價 $10 以下
TOP_N = 8           # 假設你打算從便宜池裡挑幾個人


def _projected_totals(history: pd.DataFrame, target: str, weights: dict) -> pd.DataFrame:
    """兩個模型對 target 季的預測「整季總產出」= 場均 FP × 預測出賽數。

    用總產出而非場均：便宜球員的風險有一半在出勤，只比場均會高估玻璃人。
    """
    past = history[history["season"] < target]
    mar = marcel(past, target)
    ml = predict_ml(train_ml(past, prev_season(target)), past, target)
    return pd.DataFrame({
        "marcel": compute_fantasy_points(mar, weights) * mar["gp"],
        "ml": compute_fantasy_points(ml, weights) * ml["gp"],
    })


def run_year(year: int, history: pd.DataFrame, draft: pd.DataFrame,
             weights: dict) -> tuple:
    """回傳 (摘要 dict, 便宜池 DataFrame)。"""
    target = DRAFT_SEASONS[year]
    actual = history[history["season"] == target].set_index("player_id")
    actual_total = (compute_fantasy_points(actual, weights) * actual["gp"]).rename("actual")

    pool = (draft[draft["year"] == year].set_index("player_id")
            .join(_projected_totals(history, target, weights))
            .join(actual_total)
            .dropna(subset=["actual", "marcel"]))
    cheap = pool[pool["spend"] <= CHEAP_MAX]
    baseline = cheap["actual"].mean()

    summary = {"year": year, "池內人數": len(cheap), "池平均產出": round(baseline)}
    for model in ("marcel", "ml"):
        top = cheap.nlargest(TOP_N, model)
        summary[f"{model}_相關"] = round(
            cheap[model].corr(cheap["actual"], method="spearman"), 3
        )
        summary[f"{model}_top{TOP_N}提升"] = round(top["actual"].mean() / baseline - 1, 3)
    return summary, cheap


def main() -> None:
    warnings.filterwarnings("ignore")
    cfg = load_config()
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    history = pd.read_sql_query("SELECT * FROM player_stats", conn)
    draft = dh.load()

    rows = []
    for year in DRAFT_SEASONS:
        summary, cheap = run_year(year, history, draft, cfg["weights"])
        rows.append(summary)
        print(f"\n=== {year} 選秀 → {DRAFT_SEASONS[year]}（${CHEAP_MAX} 以下，"
              f"{summary['池內人數']} 人）===")
        for label, col in (("模型挑的", "marcel"), ("事後最強", "actual")):
            picks = cheap.nlargest(TOP_N, col)
            print(f"  {label}：" + ", ".join(
                f"{r.player}(${r.spend}→{r.actual:.0f})" for r in picks.itertuples()
            ))
    print("\n" + pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
