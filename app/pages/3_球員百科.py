"""球員百科：照片、歷年數據、球隊定位、健康度、人工備註（狀況/媒體評價）。"""
from urllib.parse import quote_plus

import pandas as pd
import yaml
import streamlit as st

import common
from common import BASE_DIR, compute_fantasy_points, load_config

st.set_page_config(page_title="球員百科", layout="wide")

cfg = load_config()
common.require_data(cfg)

board = common.load_board(cfg["season"])
board["fantasy_point"] = compute_fantasy_points(board, cfg["weights"])
board = board.sort_values("fantasy_point", ascending=False)

NOTES_PATH = BASE_DIR / "config" / "player_notes.yaml"


def load_notes() -> dict:
    if NOTES_PATH.exists():
        with open(NOTES_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


# Phase 2：角色邏輯移到 src/factors.py（加入 USG% 判斷），此處只 import
from factors import role_label  # noqa: E402

st.title("球員百科")

name = st.selectbox("搜尋球員（依 Fantasy Point 排序）", board["name"].tolist())
player = board[board["name"] == name].iloc[0]

col_photo, col_info = st.columns([1, 2])
with col_photo:
    st.image(
        f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player['player_id']}.png",
        width="stretch",
    )
with col_info:
    st.header(player["name"])
    c1, c2, c3 = st.columns(3)
    c1.metric("球隊", player["team"] or "—")
    c2.metric("位置", player["positions"] or "?")
    c3.metric("年齡", f"{player['age']:.0f}")
    c1.metric("Fantasy Point", f"{player['fantasy_point']:.1f}")
    c2.metric("球隊定位", role_label(player))
    c3.metric("出賽", f"{player['gp']:.0f} 場")

# Phase 2：健康度
phase2 = common.load_phase2()
mine = phase2[phase2["player_id"] == player["player_id"]]
if not mine.empty and pd.notna(mine.iloc[0]["health_score"]):
    h = mine.iloc[0]
    st.subheader("健康度（近三季出勤加權）")
    c1, c2 = st.columns(2)
    c1.metric("健康分數", f"{h['health_score']:.0f} / 100")
    c2.metric("風險等級", h["risk"])

st.subheader("年度數據")
history = common.load_stats_history()
history = history[history["player_id"] == player["player_id"]]
SEASON_COLS = ["season", "gp", "min", "pts", "reb", "ast", "stl", "blk", "tov",
               "fg_pct", "fg3m", "fg3_pct", "ft_pct"]
st.dataframe(
    history[SEASON_COLS].reset_index(drop=True),
    width="stretch",
)

st.subheader("目前狀況與媒體評價")
note = load_notes().get(name)
if note:
    if note.get("status"):
        st.markdown(f"**目前狀況：** {note['status']}")
    if note.get("media"):
        st.markdown(f"**媒體評價：** {note['media']}")
else:
    st.info(
        "此球員尚無人工備註（編輯 `config/player_notes.yaml` 加入 "
        f'`"{name}":` 的 status / media 欄位即可顯示）。'
    )

news_q = quote_plus(f'"{name}" NBA')
st.markdown(
    f"最新消息：[Google 新聞搜尋](https://news.google.com/search?q={news_q}) ｜ "
    f"[RotoWire 傷病動態](https://www.rotowire.com/basketball/injury-report.php)"
)
