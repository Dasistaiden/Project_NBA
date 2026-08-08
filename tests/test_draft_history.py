import pandas as pd
import pytest

import draft_history as dh


def test_norm_strips_diacritics():
    assert dh._norm("Alperen Şengün") == "alperen sengun"
    assert dh._norm("Jonas Valančiūnas") == "jonas valanciunas"
    assert dh._norm("  Luka Dončić ") == "luka doncic"


def test_attach_player_ids_matches_diacritics_and_retired():
    """變音符號要能對上；已退役球員也要能對上（資料庫的 players 表沒有他們）。"""
    df = pd.DataFrame({"Player": [
        "Alperen Şengün",       # 變音符號
        "Damian Lillard",       # 已非現役，players 表查不到
        "Nikola Jokić",
        "Not A Real Person",    # 對不到
    ]})
    out = dh.attach_player_ids(df)
    assert out["player_id"].notna().sum() == 3
    assert pd.isna(out.iloc[3]["player_id"])


@pytest.mark.skipif(not dh.DEFAULT_PATH.exists(), reason="需要 history_draft.xlsx")
def test_load_real_file_matches_every_name():
    """真實檔案應該 100% 比對成功——有漏就是姓名比對邏輯退步了。"""
    d = dh.load()
    unmatched = d[d["player_id"].isna()]["player"].tolist()
    assert not unmatched, f"比對不到：{unmatched}"


@pytest.mark.skipif(not dh.DEFAULT_PATH.exists(), reason="需要 history_draft.xlsx")
def test_load_derives_league_size_per_year():
    """聯盟規模每年不同，必須從資料推導而非寫死。"""
    d = dh.load()
    sizes = d.groupby("year")[["n_teams", "roster_size"]].first()
    assert sizes.loc[2024].tolist() == [8, 13]
    assert sizes.loc[2025].tolist() == [10, 10]
    # 每隊花費不得超過 $200 預算
    assert d.groupby(["year", "team"])["spend"].sum().max() <= 200
