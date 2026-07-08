"""各 Streamlit 頁面共用的載入與側欄元件。"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR / "src") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "src"))

import db  # noqa: E402
from scoring import compute_fantasy_points  # noqa: E402,F401  (供頁面 import)
from update_data import load_config  # noqa: E402,F401

POSITIONS = ["PG", "SG", "SF", "PF", "C"]

STAT_LABELS = {
    "gp": "GP", "min": "MIN", "pts": "PTS", "reb": "REB", "ast": "AST",
    "stl": "STL", "blk": "BLK", "tov": "TOV",
    "fg_pct": "FG%", "fg3m": "3PM", "fg3_pct": "3P%", "ft_pct": "FT%",
}


def require_data(cfg: dict) -> None:
    if not (BASE_DIR / cfg["db_path"]).exists():
        st.warning("找不到資料庫，請先執行： `python src/update_data.py`")
        st.stop()


@st.cache_data
def load_board(season: str) -> pd.DataFrame:
    cfg = load_config()
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    return db.load_board(conn, season)


@st.cache_data
def load_projection_board(season: str, model: str) -> pd.DataFrame:
    cfg = load_config()
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    return db.load_projection_board(conn, season, model)


def _next_season(season: str) -> str:
    y = int(season[:4]) + 1
    return f"{y}-{str(y + 1)[-2:]}"


def select_board(cfg: dict):
    """側欄選擇排名依據（上季實際 / Marcel / ML 預測），回傳 (board, 標籤)。"""
    target = _next_season(cfg["season"])
    options = {
        f"{cfg['season']} 實際": None,
        f"{target} 預測（Marcel）": "marcel",
        f"{target} 預測（ML）": "ml",
    }
    choice = st.sidebar.radio(
        "排名依據", list(options),
        help="預測值由 python src/run_projection.py 產生；新秀無歷史資料不在預測範圍",
    )
    model = options[choice]
    if model is None:
        return load_board(cfg["season"]), choice
    proj = load_projection_board(target, model)
    if proj.empty:
        st.sidebar.warning("尚無預測資料，請先執行 `python src/run_projection.py`。已改用實際數據。")
        return load_board(cfg["season"]), f"{cfg['season']} 實際"
    return proj, choice


@st.cache_data
def load_stats_history() -> pd.DataFrame:
    """全部賽季的 player_stats（球員百科用）。"""
    cfg = load_config()
    conn = db.get_connection(str(BASE_DIR / cfg["db_path"]))
    return pd.read_sql_query(
        "SELECT * FROM player_stats ORDER BY season DESC", conn
    )


def sidebar_weights(cfg: dict) -> dict:
    st.sidebar.header("權重設定")
    return {
        stat: st.sidebar.number_input(
            stat.upper(), value=float(w), step=0.1, format="%.2f"
        )
        for stat, w in cfg["weights"].items()
    }


def sidebar_min_gp(cfg: dict) -> int:
    st.sidebar.header("過濾")
    return st.sidebar.slider("最低出賽場次", 0, 82, cfg["min_games_default"])
