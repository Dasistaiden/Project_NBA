"""球員百科：照片、歷年數據、球隊定位、人工備註（狀況/媒體評價）。"""
from urllib.parse import quote_plus

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


def role_label(row) -> str:
    """ponytail: 純場均數據啟發式；Phase 2 引入先發場次/USG% 後再細化"""
    if row["min"] >= 32 and row["ast"] >= 6:
        return "核心主力・主要進攻發起者"
    if row["min"] >= 32:
        return "核心主力"
    if row["min"] >= 25:
        if row["pts"] < 12 and (row["reb"] + row["blk"]) >= 9:
            return "先發・藍領內線"
        return "先發 / 主要輪換"
    if row["min"] >= 15:
        return "輪換球員"
    return "邊緣 / 深度替補"


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
