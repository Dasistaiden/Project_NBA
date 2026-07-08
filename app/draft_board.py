"""Streamlit 選秀看板（主頁）。執行：streamlit run app/draft_board.py"""
import streamlit as st

import common
from common import compute_fantasy_points, load_config

st.set_page_config(page_title="NBA Fantasy 選秀看板", layout="wide")

cfg = load_config()
common.require_data(cfg)

board, source_label = common.select_board(cfg)
weights = common.sidebar_weights(cfg)
min_gp = common.sidebar_min_gp(cfg)

board = board[board["gp"] >= min_gp].copy()
board["fantasy_point"] = compute_fantasy_points(board, weights)
board["positions"] = board["positions"].replace("", "?")

DISPLAY_COLS = [
    c for c in [
        "name", "team", "positions", "fantasy_point", "gp", "min",
        "pts", "reb", "ast", "stl", "blk", "tov", "fg_pct", "fg3m", "ft_pct",
    ] if c in board.columns
]

st.title(f"NBA Fantasy 選秀看板 — {source_label}")

tabs = st.tabs(["全部"] + common.POSITIONS)
for tab, pos in zip(tabs, [None] + common.POSITIONS):
    with tab:
        view = board if pos is None else board[
            board["positions"].str.split(",").map(lambda ps: pos in ps)
        ]
        view = view.sort_values("fantasy_point", ascending=False).reset_index(drop=True)
        view.index += 1  # 排名從 1 開始
        st.dataframe(view[DISPLAY_COLS], width="stretch", height=600)
