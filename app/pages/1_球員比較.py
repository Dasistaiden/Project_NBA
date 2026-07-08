"""球員比較頁：2-4 名球員數據並排，FP 數值比對 + 六維雷達圖。"""
import pandas as pd
import plotly.graph_objects as go
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

view = board[board["name"].isin(selected)].set_index("name").loc[selected]

# --- Fantasy Point 數值比對（與最高者的差距）---
best_fp = view["fantasy_point"].max()
cols = st.columns(len(selected))
for col, name in zip(cols, selected):
    fp = view.at[name, "fantasy_point"]
    col.metric(name, f"{fp:.1f}",
               delta=None if fp == best_fp else f"{fp - best_fp:.1f}")

COMPARE_ROWS = ["fantasy_point", "gp", "min", "pts", "reb", "ast",
                "stl", "blk", "tov", "fg_pct", "fg3m", "fg3_pct", "ft_pct"]

comp = view[COMPARE_ROWS].T
comp.index = [common.STAT_LABELS.get(r, r.upper().replace("_", " ")) for r in COMPARE_ROWS]

HIGHLIGHT = "background-color: #1b5e20; color: white"
styler = (
    comp.style.format("{:.2f}")
    .highlight_max(axis=1, props=HIGHLIGHT,
                   subset=pd.IndexSlice[[r for r in comp.index if r != "TOV"], :])
    .highlight_min(axis=1, props=HIGHLIGHT, subset=pd.IndexSlice[["TOV"], :])
)

# --- 六維雷達圖：以全聯盟百分位標準化，消除各項級距差異 ---
RADAR_STATS = ["pts", "reb", "ast", "stl", "blk", "tov"]
RADAR_LABELS = ["PTS", "REB", "AST", "STL", "BLK", "TOV(低佳)"]
norm_pool = board[board["gp"] >= cfg["min_games_default"]]


def pct_rank(stat: str, value: float) -> float:
    """該數值在聯盟中的百分位（0-100）；TOV 反向，越低分越高。"""
    p = (norm_pool[stat] <= value).mean() * 100
    return round(100 - p if stat == "tov" else p, 1)


col_table, col_radar = st.columns([3, 2])
with col_table:
    st.dataframe(styler, width="stretch", height=500)
with col_radar:
    fig = go.Figure()
    for name in selected:
        fig.add_trace(go.Scatterpolar(
            r=[pct_rank(s, view.at[name, s]) for s in RADAR_STATS],
            theta=RADAR_LABELS, fill="toself", name=name,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100], ticksuffix="")),
        legend=dict(orientation="h", y=-0.1), height=500,
        margin=dict(t=30, b=30),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(f"軸值為聯盟百分位（出賽 ≥ {cfg['min_games_default']} 場的球員為母體），"
               "已消除各項數據級距差異；TOV 反向計，越外圈越好。")
