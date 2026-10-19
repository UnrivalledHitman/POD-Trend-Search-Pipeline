"""Summarise your own sales log - the data that matters most in Phase 2."""
from __future__ import annotations

import pandas as pd

COLUMNS = ["date_listed", "design_name", "niche", "platform", "product",
           "views", "favorites", "sales", "royalty_inr"]


def summarise(path: str) -> None:
    df = pd.read_csv(path)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Tracker is missing columns: {missing}")
    for c in ["views", "favorites", "sales", "royalty_inr"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if df.empty:
        print("Tracker is empty - log your designs as you list them.")
        return

    by_niche = df.groupby("niche").agg(
        designs=("design_name", "count"),
        views=("views", "sum"),
        favorites=("favorites", "sum"),
        sales=("sales", "sum"),
        earnings_inr=("royalty_inr", "sum"),
    )
    by_niche["sales_per_design"] = (by_niche["sales"] / by_niche["designs"]).round(2)
    by_niche["fav_rate_%"] = (100 * by_niche["favorites"] / by_niche["views"].replace(0, pd.NA)).round(1)
    by_niche = by_niche.sort_values("sales_per_design", ascending=False)

    print("\n=== Niches ranked by sales per design ===")
    print(by_niche.to_string())

    winners = df[df["sales"] >= 2].sort_values("sales", ascending=False)
    print("\n=== Winners - make 5-10 variations of each ===")
    print(winners[["design_name", "niche", "platform", "sales"]].to_string(index=False) if not winners.empty else "None yet.")

    days = (pd.Timestamp.today() - pd.to_datetime(df["date_listed"], errors="coerce")).dt.days
    dead = df[(days >= 30) & (df["views"] < 20) & (df["sales"] == 0)]
    print("\n=== Listed 30+ days, under 20 views, no sales - rethink title/tags or drop ===")
    print(dead[["design_name", "niche", "platform"]].to_string(index=False) if not dead.empty else "None.")
    print(f"\nTotal: {int(df['sales'].sum())} sales, Rs {df['royalty_inr'].sum():,.0f} earned from {len(df)} listings.")
