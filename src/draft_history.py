"""歷史競標資料：讀 data/history_draft.xlsx，把球員姓名比對成 player_id。

每張工作表是一年，欄位 Pick / Player / Spend / Team。
球員一年後可能換隊，所以姓名是唯一的比對依據，不看 Team。
聯盟規模（幾隊、每隊幾人）由資料本身推導，不另外設定。
"""
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd
from nba_api.stats.static import players as static_players

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PATH = BASE_DIR / "data" / "history_draft.xlsx"


def _norm(name: str) -> str:
    """去掉變音符號並轉小寫：'Alperen Şengün' -> 'alperen sengun'。

    Excel 裡的姓名帶變音符號，nba_api 的名單不帶，直接比對會漏掉。
    """
    stripped = unicodedata.normalize("NFKD", str(name))
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower().strip()


@lru_cache(maxsize=1)
def _name_lookup() -> dict:
    """正規化姓名 -> player_id。用 nba_api 的靜態名單（含退役球員，不打 API）。

    不能用資料庫的 players 表：那裡只有現役球員，兩年前選秀名單中已退役
    或長期缺陣的人（Damian Lillard、Kyrie Irving 等）會比對不到。
    """
    return {_norm(p["full_name"]): p["id"] for p in static_players.get_players()}


def attach_player_ids(df: pd.DataFrame, name_col: str = "Player") -> pd.DataFrame:
    """新增 player_id 欄。比對不到的留 NA，由呼叫端決定怎麼處理。"""
    out = df.copy()
    out["player_id"] = out[name_col].map(_norm).map(_name_lookup())
    return out


def load(path: Path | str = DEFAULT_PATH) -> pd.DataFrame:
    """讀取全部年份，回傳 year / pick / player / spend / team / player_id /
    n_teams / roster_size。

    n_teams 與 roster_size 由該年的資料推導（隊伍數 = 相異隊名數，
    每隊人數 = 總筆數 / 隊伍數），因為聯盟規模每年不同。
    """
    sheets = pd.read_excel(path, sheet_name=None)
    frames = []
    # 只取以年份命名的工作表；其餘（如 2024_rank）由 load_standings 處理
    for year, raw in sheets.items():
        if not year.isdigit():
            continue
        d = attach_player_ids(raw).rename(columns=str.lower)
        d["year"] = int(year)
        d["n_teams"] = d["team"].nunique()
        d["roster_size"] = len(d) // d["n_teams"]
        frames.append(d)
    cols = ["year", "pick", "player", "spend", "team", "player_id",
            "n_teams", "roster_size"]
    return pd.concat(frames, ignore_index=True)[cols].sort_values(["year", "pick"])


def load_standings(path: Path | str = DEFAULT_PATH) -> pd.DataFrame:
    """讀 `<年份>_rank` 工作表，回傳 year / rank / team / pct / pts / moves。

    rank 是季後賽最終名次（原始值帶 `*` 表示晉級季後賽），與例行賽戰績不同。
    W-L-T 欄不取：Excel 會把 "6-12-1" 自動判讀成日期，pct 欄才是可靠的戰績來源。
    """
    sheets = pd.read_excel(path, sheet_name=None)
    frames = []
    for name, raw in sheets.items():
        if not name.endswith("_rank"):
            continue
        d = raw.rename(columns=str.lower)
        d["year"] = int(name.split("_")[0])
        d["rank"] = d["rank"].astype(str).str.lstrip("*").astype(int)
        frames.append(d[["year", "rank", "team", "pct", "pts", "moves"]])
    return pd.concat(frames, ignore_index=True).sort_values(["year", "rank"])
