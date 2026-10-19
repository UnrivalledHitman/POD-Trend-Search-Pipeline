#!/usr/bin/env python3
"""POD Trend Search Pipeline - Phase 1 (lean build).

Examples:
  python run_pipeline.py --demo                      # offline test with fake data
  python run_pipeline.py                             # worldwide, last 12 months
  python run_pipeline.py --geo IN --top 5            # India only
  python run_pipeline.py --gprop froogle             # Google Shopping searches
  python run_pipeline.py --rising                    # also fetch rising related searches
  python run_pipeline.py track                       # summarise your sales tracker
"""
from __future__ import annotations

import argparse
import os
from datetime import date

import pandas as pd

from pod_pipeline import briefs, score, trends, tracker


def load_keywords(path: str) -> tuple[list[str], dict[str, float]]:
    df = pd.read_csv(path, comment="#").dropna(subset=["niche"])
    df["niche"] = df["niche"].astype(str).str.strip()
    df = df[df["niche"] != ""].drop_duplicates("niche")
    comp = {}
    if "competition" in df.columns:
        for n, c in zip(df["niche"], pd.to_numeric(df["competition"], errors="coerce")):
            if pd.notna(c):
                comp[n] = float(c)
    return df["niche"].tolist(), comp


def run(args) -> None:
    keywords, competition = load_keywords(args.keywords)
    if len(keywords) < 2:
        raise SystemExit("Add at least 2 niches to the keywords file.")
    anchor = args.anchor or keywords[0]
    anchor_only = anchor not in keywords  # reference keyword, not a niche to rank
    if anchor_only:
        keywords.insert(0, anchor)
    print(f"Analysing {len(keywords)} niches (anchor: '{anchor}', geo: {args.geo or 'worldwide'}, {args.timeframe})")

    if args.demo:
        interest = trends.demo_interest(keywords)
    else:
        interest = trends.fetch_interest(keywords, anchor, geo=args.geo,
                                         timeframe=args.timeframe, gprop=args.gprop)
    if interest.empty:
        raise SystemExit("No trend data came back. Try again later (Google may be rate-limiting) or use --demo.")

    niches = interest.drop(columns=[anchor]) if anchor_only else interest
    feats = score.trend_features(niches)
    ranked = score.score_niches(feats, competition)

    top = ranked.head(args.top).copy()
    top["rising_queries"] = ""
    if args.rising and not args.demo:
        print("Fetching rising related searches for top niches...")
        rising = trends.fetch_rising(top["niche"].tolist(), geo=args.geo,
                                     timeframe=args.timeframe, gprop=args.gprop)
        top["rising_queries"] = [", ".join(rising[n]) for n in top["niche"]]
    ranked = ranked.merge(top[["niche", "rising_queries"]], on="niche", how="left").fillna({"rising_queries": ""})

    os.makedirs(args.out, exist_ok=True)
    stamp = date.today().isoformat()
    ranked_path = os.path.join(args.out, f"niche_ranking_{stamp}.csv")
    curves_path = os.path.join(args.out, f"trend_curves_{stamp}.csv")
    briefs_path = os.path.join(args.out, f"design_briefs_{stamp}.md")
    ranked.to_csv(ranked_path, index=False)
    interest.round(1).to_csv(curves_path)

    print("\n=== Niche ranking ===")
    cols = ["niche", "score", "verdict", "recent_interest", "growth_pct", "competition", "peak_month"]
    print(ranked[cols].to_string(index=False))

    if not args.no_briefs:
        mode = briefs.generate_briefs(ranked.head(args.top), briefs_path, n=args.ideas)
        note = {"api": "written by Claude",
                "mixed": "partly written by Claude, the rest as prompts"}.get(mode, "prompts to paste into Claude")
        print(f"\nDesign briefs ({note}): {briefs_path}")
    print(f"Ranking: {ranked_path}\nTrend curves: {curves_path}")
    if args.demo:
        print("\n(DEMO MODE - numbers are synthetic. Run without --demo for real Google Trends data.)")


def main() -> None:
    p = argparse.ArgumentParser(description="Rank POD niches with Google Trends and generate design briefs.")
    sub = p.add_subparsers(dest="cmd")
    t = sub.add_parser("track", help="Summarise your sales tracker CSV")
    t.add_argument("--file", default="data/sales_tracker.csv")

    p.add_argument("--keywords", default="data/keywords.csv", help="CSV with columns: niche, competition (optional)")
    p.add_argument("--anchor", help="Keyword included in every batch for fair comparison (default: first niche)")
    p.add_argument("--geo", default="", help="Country code, e.g. IN, US, GB, or IN-WB for West Bengal. Blank = worldwide")
    p.add_argument("--timeframe", default="today 12-m", help="e.g. 'today 12-m', 'today 3-m', 'today 5-y'")
    p.add_argument("--gprop", default="", choices=["", "froogle", "youtube", "images", "news"],
                   help="froogle = Google Shopping searches (buyer intent)")
    p.add_argument("--top", type=int, default=5, help="How many top niches get design briefs")
    p.add_argument("--ideas", type=int, default=5, help="Design ideas per niche")
    p.add_argument("--rising", action="store_true", help="Fetch rising related searches for top niches")
    p.add_argument("--no-briefs", action="store_true", help="Skip the design-brief step")
    p.add_argument("--out", default="output", help="Output folder")
    p.add_argument("--demo", action="store_true", help="Use synthetic data (no internet needed)")
    args = p.parse_args()

    if args.cmd == "track":
        tracker.summarise(args.file)
    else:
        run(args)


if __name__ == "__main__":
    main()
