"""回測三模型並產出下一季預測寫入 projections 表。python src/run_projection.py"""
import pandas as pd

import db
from projection import backtest, marcel, next_season, predict_ml, train_ml
from update_data import BASE_DIR, load_config


def main() -> None:
    cfg = load_config()
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    history = pd.read_sql_query("SELECT * FROM player_stats", conn)
    n_seasons = history["season"].nunique()
    print(f"History: {len(history)} rows, {n_seasons} seasons")
    if n_seasons < 6:
        print("歷史賽季不足，請先執行 python src/backfill_history.py")
        return

    print("\n=== Backtest（留出賽季驗證，FP 以預設權重計）===")
    print(backtest(history, cfg["weights"]).to_string(index=False))

    target = next_season(cfg["season"])
    print(f"\nGenerating {target} projections...")
    db.upsert_projections(conn, marcel(history, target).reset_index(), target, "marcel")
    models = train_ml(history, cfg["season"])
    db.upsert_projections(
        conn, predict_ml(models, history, target).reset_index(), target, "ml"
    )
    n = conn.execute(
        "SELECT model, COUNT(*) FROM projections WHERE season = ? GROUP BY model",
        (target,),
    ).fetchall()
    print(f"Done: {n}")


if __name__ == "__main__":
    main()
