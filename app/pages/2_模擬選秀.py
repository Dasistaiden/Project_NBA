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

teams, star_premium = common.sidebar_auction(cfg)
budget = st.sidebar.number_input(
    "我的總預算 ($)", 50, 500, cfg["auction"]["budget"],
    help="優化器可花的錢。估價本身用聯盟標準預算計算，不受此值影響。",
)
slots = common.sidebar_slots(cfg)

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
        # ponytail: 只取「全聯盟會被選走的人數」餵優化器，其餘不可能入選；
        # 隨陣容人數縮放，否則大陣容聯盟會把可行解切掉
        candidates = pool.nlargest(max(250, teams * len(slots)), "fantasy_point")
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
