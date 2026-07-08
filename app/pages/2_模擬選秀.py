"""模擬選秀頁：$200 拍賣制，估算球員標價並求出預算內最佳陣容。"""
import streamlit as st

import common
from common import compute_fantasy_points, load_config
from auction import estimate_prices, optimize_roster

st.set_page_config(page_title="模擬選秀", layout="wide")

cfg = load_config()
common.require_data(cfg)

board, source_label = common.select_board(cfg)
weights = common.sidebar_weights(cfg)
min_gp = common.sidebar_min_gp(cfg)

st.sidebar.header("拍賣設定")
budget = st.sidebar.number_input("我的總預算 ($)", 50, 500, cfg["auction"]["budget"])
teams = st.sidebar.number_input("聯盟隊伍數", 8, 20, cfg["auction"]["league_teams"])
star_premium = st.sidebar.slider(
    "巨星溢價", 1.0, 2.5, float(cfg["auction"]["star_premium"]), 0.1,
    help="模擬真實市場：越高則頂級球員越貴、中後段越接近 $1。1.0 = 純線性估價",
)

slots = cfg["auction"]["roster_slots"]

# 只用有位置對映且達最低出賽的球員估價
pool = board[(board["gp"] >= min_gp) & (board["positions"] != "")].copy()
pool["fantasy_point"] = compute_fantasy_points(pool, weights)
pool["price"] = estimate_prices(
    pool["fantasy_point"], cfg["auction"]["budget"], teams, len(slots), star_premium
)

st.title(f"模擬選秀 — $200 拍賣制（{len(slots)} 人陣容，依 {source_label}）")
st.caption(
    "標價由 Fantasy Point 以 value-over-replacement 法推算，並以「巨星溢價」"
    "貼近真實拍賣的價格曲線；優化器在預算內求總 Fantasy Point 最大的可行陣容。"
    "同樣的權重與設定下，結果是固定的（精確解）；結果改變代表某個設定變了。"
)

if st.button("計算最佳陣容", type="primary"):
    with st.spinner("求解中..."):
        # ponytail: 只取前 250 名餵優化器，其餘不可能入選；降低 ILP 規模
        candidates = pool.nlargest(250, "fantasy_point")
        try:
            roster = optimize_roster(candidates, slots, cfg["slot_eligibility"], budget)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

    c1, c2, c3 = st.columns(3)
    c1.metric("總花費", f"${int(roster['price'].sum())} / ${budget}")
    c2.metric("剩餘預算", f"${budget - int(roster['price'].sum())}")
    c3.metric("陣容總 Fantasy Point", f"{roster['fantasy_point'].sum():.1f}")

    show = roster[["slot", "name", "team", "positions", "price", "fantasy_point",
                   "gp", "min", "pts", "reb", "ast", "stl", "blk", "tov"]]
    st.dataframe(show.reset_index(drop=True), width="stretch", height=500)

with st.expander("全球員估價表（練習出價時參考行情）"):
    price_list = pool.sort_values("fantasy_point", ascending=False)[
        ["name", "team", "positions", "price", "fantasy_point", "gp", "pts", "reb", "ast"]
    ].reset_index(drop=True)
    price_list.index += 1
    st.dataframe(price_list, width="stretch", height=400)
