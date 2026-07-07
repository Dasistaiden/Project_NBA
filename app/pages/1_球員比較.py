"""球員比較頁：2-4 名球員數據並排，逐項標示優劣。"""
import pandas as pd
import streamlit as st

import common
from common import compute_fantasy_points, load_config

st.set_page_config(page_title="球員比較", layout="wide")

cfg = load_config()
common.require_data(cfg)

board = common.load_board(cfg["season"])
weights = common.sidebar_weights(cfg)

board["fantasy_point"] = compute_fantasy_points(board, weights)
board = board.sort_values("fantasy_point", ascending=False)

st.title("球員比較")

selected = st.multiselect(
    "選擇 2-4 名球員（依 Fantasy Point 排序）",
    options=board["name"].tolist(),
    default=board["name"].head(2).tolist(),
    max_selections=4,
)

if len(selected) < 2:
    st.info("請至少選擇 2 名球員")
    st.stop()

COMPARE_ROWS = ["fantasy_point", "gp", "min", "pts", "reb", "ast",
                "stl", "blk", "tov", "fg_pct", "fg3m", "fg3_pct", "ft_pct"]

view = board[board["name"].isin(selected)].set_index("name")
comp = view[COMPARE_ROWS].T
comp.index = [common.STAT_LABELS.get(r, r.upper().replace("_", " ")) for r in COMPARE_ROWS]

# 每項數據標示最佳者（TOV 越低越好，其餘越高越好）
HIGHLIGHT = "background-color: #1b5e20; color: white"
styler = (
    comp.style.format("{:.2f}")
    .highlight_max(axis=1, props=HIGHLIGHT,
                   subset=pd.IndexSlice[[r for r in comp.index if r != "TOV"], :])
    .highlight_min(axis=1, props=HIGHLIGHT, subset=pd.IndexSlice[["TOV"], :])
)

col_table, col_chart = st.columns([3, 2])
with col_table:
    st.dataframe(styler, width="stretch", height=500)
with col_chart:
    st.caption("Fantasy Point")
    st.bar_chart(view["fantasy_point"])
    st.caption("六大項並排")
    st.bar_chart(view[["pts", "reb", "ast", "stl", "blk", "tov"]].T, stack=False)
