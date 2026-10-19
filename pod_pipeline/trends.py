"""Fetch Google Trends data for niche keywords.

Google Trends returns *relative* interest (0-100) within each request, and a
request can hold at most 5 keywords. To compare more than 5 keywords fairly,
every batch includes the same ANCHOR keyword; each batch is then rescaled so
the anchor has the same average in all batches.
"""
from __future__ import annotations

import random
import time

import pandas as pd

MAX_PER_REQUEST = 5


def _client(hl: str = "en-US", tz: int = 330):
    from pytrends.request import TrendReq

    # Note: don't pass retries/backoff_factor to TrendReq - that path breaks
    # with urllib3 2.x. We retry ourselves in _with_retry instead.
    return TrendReq(hl=hl, tz=tz, timeout=(10, 30))


def _with_retry(fn, attempts: int = 4, base_wait: float = 20.0):
    """Google rate-limits pytrends (HTTP 429). Back off and try again."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # pytrends raises several error types
            if i == attempts - 1:
                raise
            wait = base_wait * (2 ** i) + random.uniform(0, 5)
            print(f"  ! Trends request failed ({type(e).__name__}: {e}). Retrying in {wait:.0f}s...")
            time.sleep(wait)


def fetch_interest(
    keywords: list[str],
    anchor: str,
    geo: str = "",
    timeframe: str = "today 12-m",
    gprop: str = "",
    pause: float = 8.0,
) -> pd.DataFrame:
    """Return a DataFrame: index = date, one column per keyword, anchor-normalised."""
    client = _client()
    others = [k for k in keywords if k != anchor]
    batch_size = MAX_PER_REQUEST - 1
    frames = []

    for start in range(0, len(others), batch_size):
        batch = others[start:start + batch_size]
        kw_list = [anchor] + batch
        print(f"  - Trends batch: {', '.join(batch)}")

        def call():
            client.build_payload(kw_list, timeframe=timeframe, geo=geo, gprop=gprop)
            return client.interest_over_time()

        df = _with_retry(call)
        if df is None or df.empty:
            print("    (no data returned for this batch)")
            continue
        df = df.drop(columns=["isPartial"], errors="ignore")

        anchor_mean = df[anchor].mean()
        if anchor_mean > 0:
            df = df * (50.0 / anchor_mean)  # anchor average fixed at 50 everywhere
        frames.append(df)
        time.sleep(pause + random.uniform(0, 3))  # be polite, avoid 429s

    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.join(f.drop(columns=[anchor]), how="outer")
    return merged


def fetch_rising_queries(keyword: str, geo: str = "", timeframe: str = "today 12-m", top_n: int = 5) -> list[str]:
    """Rising related searches - good for discovering new sub-niches."""
    client = _client()

    def call():
        client.build_payload([keyword], timeframe=timeframe, geo=geo)
        return client.related_queries()

    try:
        data = _with_retry(call, attempts=2)
        rising = data.get(keyword, {}).get("rising")
        if rising is None or rising.empty:
            return []
        return rising["query"].head(top_n).tolist()
    except Exception as e:
        print(f"  ! Could not fetch rising queries for '{keyword}': {e}")
        return []


def demo_interest(keywords: list[str], weeks: int = 52, seed: int = 7) -> pd.DataFrame:
    """Synthetic data so you can test the pipeline offline (--demo)."""
    rng = random.Random(seed)
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=weeks, freq="W")
    data = {}
    for kw in keywords:
        base = rng.uniform(5, 70)
        slope = rng.uniform(-0.6, 0.9)
        data[kw] = [max(0.0, base + slope * i + rng.gauss(0, 6)) for i in range(weeks)]
    return pd.DataFrame(data, index=idx)
