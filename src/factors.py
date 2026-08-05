"""數值外因素（Phase 2）：健康度風險指數 + 球隊角色定位。

對應 02_planning.md M2.2/M2.3。健康度由近三季出勤率加權而成；
角色定位由上場時間 + 使用率（USG%）+ 助攻推導。

規劃偏離說明：原規劃想用先發場次（GS），但 stats.nba.com 的全聯盟
endpoint 不提供 GS（需逐球員呼叫 500+ 次 API），改用 MIN + USG% 作
角色 proxy，詳見 05_processes.md。
"""
import pandas as pd

HEALTH_WEIGHTS = (3.0, 2.0, 1.0)   # 近三季出勤率權重，越近越重


def _prev_season(season: str, n: int = 1) -> str:
    # ponytail: 與 projection.prev_season 相同的三行；不 import 是為了
    # 避免 UI 端因此連帶載入 sklearn（projection 的重依賴）
    y = int(season[:4]) - n
    return f"{y}-{str(y + 1)[-2:]}"


def season_availability(history: pd.DataFrame) -> pd.DataFrame:
    """每季出勤率 = gp / 該季聯盟最大 gp。

    用「該季全聯盟最大出賽數」當分母而非固定 82，縮水賽季
    （2011-12 封館 66 場、2019-20 停賽 ~72 場）自動處理。
    """
    max_gp = history.groupby("season")["gp"].transform("max").clip(lower=1)
    out = history[["player_id", "season"]].copy()
    out["availability"] = (history["gp"] / max_gp).clip(0, 1)
    return out


def health_scores(history: pd.DataFrame, target_season: str) -> pd.DataFrame:
    """對 target_season 的前一季有出賽的球員，算健康分數與風險等級。

    回傳 index=player_id：avail_l1/l2/l3（近三季出勤率）、
    health_score（0-100，加權出勤率）、risk（低/中/高）。

    生涯不足三季者，權重只在「有紀錄的賽季」上重新正規化——新秀不會
    因為三年前還沒進聯盟而被扣分。已知限制：「整季報銷 0 出賽」與
    「還沒進聯盟」在資料上無法區分，前者會被低估風險。
    """
    avail = season_availability(history)
    pivot = avail.pivot(index="player_id", columns="season", values="availability")

    lag_seasons = [_prev_season(target_season, n) for n in (1, 2, 3)]
    if lag_seasons[0] not in pivot.columns:
        return pd.DataFrame(
            columns=["avail_l1", "avail_l2", "avail_l3", "health_score", "risk"]
        )

    out = pd.DataFrame(index=pivot[pivot[lag_seasons[0]].notna()].index)
    num = pd.Series(0.0, index=out.index)
    den = pd.Series(0.0, index=out.index)
    for n, (w, s) in enumerate(zip(HEALTH_WEIGHTS, lag_seasons), 1):
        col = pivot[s].reindex(out.index) if s in pivot.columns else pd.Series(dtype=float)
        col = col.reindex(out.index)
        out[f"avail_l{n}"] = col.round(3)
        num += w * col.fillna(0)
        den += w * col.notna()

    out["health_score"] = (100 * num / den).round(1)
    out["risk"] = out["health_score"].map(
        lambda s: "低" if s >= 85 else ("中" if s >= 70 else "高")
    )
    return out


def role_label(row) -> str:
    """由當季 MIN / USG% / AST 推導角色標籤。usg 缺值時退回純上場時間版本。"""
    m = row.get("min") or 0
    usg = row.get("usg_pct")
    ast = row.get("ast") or 0
    pts = row.get("pts") or 0
    reb = row.get("reb") or 0
    blk = row.get("blk") or 0

    has_usg = pd.notna(usg)
    if m >= 30:
        if has_usg and usg >= 27:
            return "核心主力・進攻核心"
        if ast >= 6:
            return "核心主力・組織發起者"
        return "核心主力"
    if m >= 25:
        if pts < 12 and (reb + blk) >= 9:
            return "先發・藍領內線"
        if has_usg and usg < 16:
            return "先發・功能型角色"
        return "先發 / 主要輪換"
    if m >= 15:
        return "輪換球員"
    return "邊緣 / 深度替補"
