"""Design briefs for the top niches.

If ANTHROPIC_API_KEY is set (and the `anthropic` package is installed), briefs
are written by Claude. Otherwise a ready-to-paste prompt file is produced, which
you can paste into Claude.ai or any chatbot for free.
"""
from __future__ import annotations

import os

import pandas as pd

DEFAULT_MODEL = os.environ.get("POD_BRIEF_MODEL", "claude-sonnet-5-5")

PROMPT_TEMPLATE = """You are helping a print-on-demand seller plan T-shirt / sticker / mug designs.

Niche: "{niche}"
Trend data: recent interest {recent_interest} (anchor-relative), growth {growth_pct}% vs earlier months, peaks in {peak_month}.
Rising related searches: {rising}

Write {n} distinct design ideas for this niche. For each, give:
1. Text / phrase on the design (original wording - no song lyrics, brand names, slogans or characters that could be trademarked)
2. Visual style (e.g. retro sunset, minimal line art, bold typography)
3. Colour palette (2-4 colours, and whether it suits light or dark garments)
4. Target buyer (who buys it, and as a gift for whom)
5. Best products (tee, sticker, mug, tote...)

Keep it practical: designs one person can make in Canva or Kittl in under 30 minutes.
"""


def build_prompt(row: pd.Series, n: int = 5) -> str:
    rising = row.get("rising_queries") or "n/a"
    return PROMPT_TEMPLATE.format(
        niche=row["niche"],
        recent_interest=row["recent_interest"],
        growth_pct=row["growth_pct"],
        peak_month=row["peak_month"],
        rising=rising,
        n=n,
    )


def generate_briefs(top: pd.DataFrame, out_path: str, n: int = 5) -> str:
    """Write briefs (or prompts) to a Markdown file. Returns the mode used."""
    use_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
    client = None
    if use_api:
        try:
            import anthropic
            client = anthropic.Anthropic()
        except ImportError:
            print("  ! ANTHROPIC_API_KEY is set but `anthropic` isn't installed (pip install anthropic). Writing prompts instead.")
            use_api = False

    sections = ["# Design briefs\n"]
    for _, row in top.iterrows():
        prompt = build_prompt(row, n)
        sections.append(f"## {row['niche']}  (score {row['score']}, {row['verdict']})\n")
        if use_api:
            print(f"  - Writing briefs for '{row['niche']}'...")
            try:
                msg = client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}],
                )
                sections.append("".join(b.text for b in msg.content if b.type == "text") + "\n")
                continue
            except Exception as e:
                print(f"  ! API call failed ({e}); saving the prompt instead.")
        sections.append("Paste this into Claude (or any chatbot):\n\n```\n" + prompt + "```\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))
    return "api" if use_api else "prompts"
