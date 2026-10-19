"""Turn trend curves + competition counts into one niche score (0-100)."""
from __future__ import annotations

import math

import pandas as pd

# How much each signal matters. Tune these once you have real sales data.
WEIGHTS = {"demand": 0.40, "growth": 0.35, "competition": 0.25}


def trend_features(interest: pd.DataFrame, recent_weeks: int = 12) -> pd.DataFrame:
    """Per keyword: average demand, recent demand, growth, and peak month.

    "Recent" is a time window, not a row count, because Google returns daily,
    weekly or monthly rows depending on the timeframe. For short timeframes the
    window shrinks to the last quarter of the data.
    """
    rows = []
    for kw in interest.columns:
        s = interest[kw].dropna()
        if s.empty:
            continue
        span = s.index.max() - s.index.min()
        window = min(pd.Timedelta(weeks=recent_weeks), span / 4)
        is_recent = s.index >= s.index.max() - window  # always includes the last point
        recent = s[is_recent].mean()
        earlier = s[~is_recent].mean() if (~is_recent).any() else s.mean()
        growth = (recent - earlier) / max(earlier, 1.0)  # +0.30 = 30% more interest lately
        rows.append({
            "niche": kw,
            "avg_interest": round(s.mean(), 1),
            "recent_interest": round(recent, 1),
            "growth_pct": round(growth * 100, 1),
            "peak_month": s.idxmax().strftime("%b"),
        })
    return pd.DataFrame(rows)


def _minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)


def score_niches(features: pd.DataFrame, competition: dict[str, float]) -> pd.DataFrame:
    df = features.copy()
    df["competition"] = df["niche"].map(lambda n: competition.get(n))

    demand = _minmax(df["recent_interest"])
    growth = _minmax(df["growth_pct"].clip(-100, 200))

    has_comp = df["competition"].notna() & (df["competition"] >= 0)  # 0 listings = wide open
    if has_comp.any():
        # log scale: 500 vs 5,000 listings matters more than 50k vs 55k
        log_comp = df.loc[has_comp, "competition"].apply(lambda c: math.log10(c + 1))
        comp_score = pd.Series(0.5, index=df.index)  # neutral if unknown
        comp_score.loc[has_comp] = 1 - _minmax(log_comp)
        w = WEIGHTS
    else:
        comp_score = pd.Series(0.0, index=df.index)
        total = WEIGHTS["demand"] + WEIGHTS["growth"]
        w = {"demand": WEIGHTS["demand"] / total, "growth": WEIGHTS["growth"] / total, "competition": 0.0}

    df["score"] = (100 * (w["demand"] * demand + w["growth"] * growth + w["competition"] * comp_score)).round(1)
    df["verdict"] = df.apply(_verdict, axis=1)
    return df.sort_values("score", ascending=False).reset_index(drop=True)


def _verdict(row) -> str:
    if row["score"] >= 65:
        return "Design now"
    if row["score"] >= 45:
        return "Test a few"
    if row["growth_pct"] < -25:
        return "Fading - skip"
    return "Low priority"
