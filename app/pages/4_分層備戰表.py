"""分層備戰表：選秀前印出來的那張紙。

各位置依 Fantasy Point 切層，標出斷層在哪、每層剩幾個人、估價多少。
選秀當下不需要同步任何資料——看 Yahoo 螢幕就知道各層還剩誰。
"""
import streamlit as st

import common
from common import compute_fantasy_points, load_config
from auction import estimate_prices
from tiers import assign_tiers, default_threshold, gaps_to_next

st.set_page_config(page_title="分層備戰表", layout="wide")

cfg = load_config()
common.require_data(cfg)

board, source_label = common.select_board(cfg)
weights = common.sidebar_weights(cfg)
min_gp = common.sidebar_min_gp(cfg)

teams, star_premium = common.sidebar_auction(cfg)
slots = common.sidebar_slots(cfg)

pool = board[(board["gp"] >= min_gp) & (board["positions"] != "")].copy()
pool["fantasy_point"] = compute_fantasy_points(pool, weights)
pool["price"] = estimate_prices(
    pool["fantasy_point"], cfg["auction"]["budget"], teams, len(slots), star_premium
)
pool = pool.merge(common.load_phase2(), on="player_id", how="left")

st.sidebar.header("分層")
depth = st.sidebar.slider("每個位置列出人數", 10, 60, 30, 5)


def eligible(pos: str):
    return pool[pool["positions"].str.split(",").apply(lambda p: pos in p)]


# 門檻由「各位置實際列出的那些人」的差距算出，不是整池
auto = default_threshold([
    eligible(pos).nlargest(depth, "fantasy_point")["fantasy_point"]
    for pos in common.POSITIONS
])
threshold = st.sidebar.slider(
    "斷層門檻（FP）", 0.5, 15.0, max(0.5, float(auto)), 0.5,
    help=f"與下一名差距超過此值就切一層。預設 {auto} = 各位置候選名單相鄰差距中位數 × 2.5",
)
print_mode = st.sidebar.checkbox("全部展開（列印用）")

st.title(f"分層備戰表（依 {source_label}）")
st.caption(
    "拍賣制的決策不是「誰比較好」，是「斷層在哪」：同層之內的球員價值接近，"
    "為了層內排名多花錢不划算；該搶的是每一層的最後一個。"
)

COLS = {
    "tier": "層", "name": "球員", "team": "隊", "positions": "位置",
    "price": "估價", "fantasy_point": "FP", "gap": "距下一名",
    "health_score": "健康", "risk": "風險", "role": "角色",
}


def render_position(pos: str) -> None:
    view = eligible(pos).copy()
    if view.empty:
        st.info(f"{pos} 無符合條件的球員")
        return
    view = view.nlargest(depth, "fantasy_point")
    view["tier"] = assign_tiers(view["fantasy_point"], threshold)
    view["gap"] = gaps_to_next(view["fantasy_point"])

    counts = view.groupby("tier").size()
    st.caption(
        f"{pos}：{len(counts)} 層 — "
        + "、".join(f"第 {t} 層 {n} 人" for t, n in counts.items())
    )

    view = view.sort_values("fantasy_point", ascending=False)
    show = view[[c for c in COLS if c in view.columns]].rename(columns=COLS)
    show.index = range(1, len(show) + 1)
    st.dataframe(
        # 隔層淡底，讓斷層在紙上一眼看得出來
        show.style.apply(
            lambda r: ["background-color: rgba(128,128,128,0.15)"
                       if r["層"] % 2 == 0 else ""] * len(r),
            axis=1,
        ).format({"FP": "{:.1f}", "距下一名": "{:.1f}", "健康": "{:.0f}"}),
        width="stretch",
        height=min(38 * len(show) + 40, 900),
    )


if print_mode:
    for pos in common.POSITIONS:
        st.subheader(pos)
        render_position(pos)
else:
    for tab, pos in zip(st.tabs(common.POSITIONS), common.POSITIONS):
        with tab:
            render_position(pos)
