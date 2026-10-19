# POD Trend Search Pipeline

A lean Phase 1 tool for print-on-demand sellers: it ranks niche ideas using Google Trends data and your own competition counts, then writes design briefs for the best ones. A small sales tracker tells you which niches and designs are actually earning.

It doesn't guarantee sales. It helps you decide what to design next, and gets smarter once your own sales data comes in.

## What it does

1. Reads your niche ideas from `data/keywords.csv`
2. Pulls 12 months of Google Trends interest for each one (anchor-normalised, so more than 5 keywords compare fairly)
3. Scores each niche on **demand**, **growth** and **competition** (0-100) and gives a verdict: *Design now*, *Test a few*, *Low priority*, *Fading - skip*
4. Writes design briefs for the top niches (with Claude if you have an API key, otherwise ready-to-paste prompts)
5. `track` mode summarises your sales log: best niches, winning designs to make variations of, and dead listings

## Setup

```bash
git clone https://github.com/<your-username>/pod-trend-search-pipeline.git
cd pod-trend-search-pipeline
uv sync                       # installs Python 3.12 + dependencies into .venv (https://docs.astral.sh/uv/)
```

Then run the commands below with `uv run`, e.g. `uv run python run_pipeline.py --demo`.
Without uv: `python -m venv .venv`, activate it, then `pip install -r requirements.txt`.

## Usage

```bash
python run_pipeline.py --demo            # test offline with fake data first
python run_pipeline.py                   # real data, worldwide
python run_pipeline.py --geo IN          # India only (IN-WB = West Bengal, US, GB...)
python run_pipeline.py --gprop froogle   # Google Shopping searches = buyer intent
python run_pipeline.py --rising          # add rising related searches (new sub-niche ideas)
python run_pipeline.py track             # summarise data/sales_tracker.csv
```

Outputs go to `output/`: `niche_ranking_<date>.csv`, `trend_curves_<date>.csv` and `design_briefs_<date>.md`.

### Adding competition counts

Search each niche on Redbubble or Etsy and put the result count in the `competition` column of `data/keywords.csv`. Lower competition raises the score. If the column is blank, scoring uses demand and growth only.

### AI-written briefs (optional)

```bash
uv sync --extra briefs              # or: pip install anthropic
export ANTHROPIC_API_KEY=...        # Windows: set ANTHROPIC_API_KEY=...
```

Without a key, `design_briefs_<date>.md` contains prompts you can paste into Claude.ai for free. Change the model with the `POD_BRIEF_MODEL` environment variable.

### Sales tracker

Add one row per listing to `data/sales_tracker.csv` and update views, favorites and sales weekly:

```
date_listed,design_name,niche,platform,product,views,favorites,sales,royalty_inr
2026-10-20,Chai Over Everything,chai lover,Redbubble,tee,240,12,4,900
```

## Notes and limits

- Google Trends gives **relative** interest (0-100), not search counts. Scores compare your niches to each other, not to the whole market.
- `pytrends` is an unofficial library and Google rate-limits it. The script pauses between requests and retries automatically. If it keeps failing, wait an hour or use fewer keywords.
- Always check design phrases against trademark databases (USPTO, tmhunt.com) before listing.
- Tune `WEIGHTS` in `pod_pipeline/score.py` once you know which signals predict your sales.

## Roadmap

- **Phase 2:** use tracker data to re-weight scoring
- **Phase 3:** Etsy API competition counts, Printify auto-listing, image generation
