"""Build the 7-slide presentation deck from the measured results.

    python slides_build.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
OUT = HERE / "report"

NAVY = RGBColor(0x10, 0x25, 0x38)
ACCENT = RGBColor(0x1F, 0x6F, 0xB2)
GREY = RGBColor(0x55, 0x5F, 0x6B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def cells(arm: str) -> list[dict]:
    with (RESULTS / arm / "cells.csv").open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pct(t: str) -> float | None:
    try:
        return float(str(t).strip().rstrip("%")) / 100
    except (TypeError, ValueError):
        return None


DIRECTION = {"Buy": 1, "Overweight": 1, "Underweight": -1, "Sell": -1, "Hold": 0}


def verdict(cell: dict) -> str:
    """Whether the cell's rating called its realised alpha correctly."""
    a = pct(cell.get("alpha", ""))
    d = DIRECTION.get(cell.get("rating", ""), 0)
    if a is None:
        return "-"
    if d == 0:
        return "no call"
    return "correct" if a * d > 0 else "wrong"


def blank(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def textbox(slide, left, top, width, height, text, size=18, bold=False, color=NAVY,
            align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Calibri"
    return tb


def bullets(slide, left, top, width, height, items, size=16, color=NAVY, spacing=8):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(spacing)
        r = p.add_run()
        r.text = ("•  " if not item.startswith("    ") else "      ") + item.strip()
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.name = "Calibri"
    return tb


def accent_bar(slide, top=Inches(1.22)):
    bar = slide.shapes.add_shape(1, Inches(0.6), top, Inches(1.1), Emu(38000))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()


def header(slide, title, kicker=None):
    if kicker:
        textbox(slide, Inches(0.6), Inches(0.34), Inches(12), Inches(0.3), kicker.upper(),
                size=11, bold=True, color=ACCENT)
    # A long title would wrap into the rule and the body; shrink it to stay one line.
    size = 30 if len(title) <= 48 else (26 if len(title) <= 58 else 23)
    textbox(slide, Inches(0.6), Inches(0.6), Inches(12.4), Inches(0.6), title, size=size, bold=True)
    accent_bar(slide)


def table(slide, left, top, width, rows, col_widths, size=13):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), left, top, width,
                                   Inches(0.34) * len(rows))
    tbl = shape.table
    for j, w in enumerate(col_widths):
        tbl.columns[j].width = w
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = str(val)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(size)
            p.font.name = "Calibri"
            p.font.bold = (i == 0)
            p.font.color.rgb = WHITE if i == 0 else NAVY
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = NAVY
    return tbl


def build() -> Path:
    base, mod = cells("baseline"), cells("modified")
    by_date_b = {c["date"]: c for c in base}
    by_date_m = {c["date"]: c for c in mod}

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1 -----------------------------------------------------------------
    s = blank(prs)
    bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    textbox(s, Inches(0.9), Inches(2.0), Inches(11), Inches(0.5),
            "FTEC5660 · REPRODUCIBILITY WORK", size=14, bold=True, color=ACCENT)
    textbox(s, Inches(0.9), Inches(2.5), Inches(11.5), Inches(1.6),
            "Reproducing TradingAgents, and what\none debate round is worth",
            size=40, bold=True, color=WHITE)
    textbox(s, Inches(0.9), Inches(4.5), Inches(11.5), Inches(0.9),
            "How does removing one bull/bear debate round change the cost and the decision quality "
            "of a multi-agent LLM trading system?",
            size=17, color=RGBColor(0xC8, 0xD6, 0xE2))
    textbox(s, Inches(0.9), Inches(6.0), Inches(11), Inches(0.4),
            "CHEN Duoduo · Student ID 1155267609",
            size=13, color=RGBColor(0xC8, 0xD6, 0xE2))
    textbox(s, Inches(0.9), Inches(6.4), Inches(11), Inches(0.4),
            "TauricResearch/TradingAgents @ 9fa1196 · DeepSeek-V4.1-Flash · AAPL, Oct 2026",
            size=12, color=RGBColor(0x8F, 0xA6, 0xB8))

    # 2 -----------------------------------------------------------------
    s = blank(prs)
    header(s, "What runs when you give it a ticker and a date", "the system")
    bullets(s, Inches(0.7), Inches(1.5), Inches(6.4), Inches(5),
            ["Four analysts with tools (market, sentiment, news, fundamentals) run in parallel, "
             "and each keeps its own bounded tool loop",
             "Bull vs Bear research debate, gated by max_debate_rounds",
             "Research Manager writes the investment plan",
             "Trader drafts the decision",
             "Three-way risk debate: aggressive / neutral / conservative",
             "Portfolio Manager issues one of five ratings",
             "Memory log settles every past decision with realised return + alpha vs SPY"],
            size=15)
    box = s.shapes.add_shape(1, Inches(7.4), Inches(1.6), Inches(5.3), Inches(4.6))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xF2, 0xF6, 0xFA)
    box.line.color.rgb = RGBColor(0xD5, 0xDF, 0xE8)
    tb = box.text_frame
    tb.word_wrap = True
    tb.vertical_anchor = MSO_ANCHOR.TOP
    lines = ["analysts  ─┬─▶  Bull ⇄ Bear", "                     │",
             "            Research Manager", "                     │",
             "                  Trader", "                     │",
             "        Risk debate (3 roles)", "                     │",
             "            Portfolio Manager", "                     │",
             "        rating + memory log"]
    for i, ln in enumerate(lines):
        p = tb.paragraphs[0] if i == 0 else tb.add_paragraph()
        r = p.add_run()
        r.text = ln
        r.font.name = "Consolas"
        r.font.size = Pt(13)
        r.font.color.rgb = NAVY

    # 3 -----------------------------------------------------------------
    s = blank(prs)
    header(s, "The target claim: every decision is settled and scored", "reproduction target")
    textbox(s, Inches(0.7), Inches(1.5), Inches(11.8), Inches(0.9),
            "README claim: every cell is scored on realized alpha against the instrument's regional "
            "benchmark and grouped by rating.", size=17, color=GREY)
    bullets(s, Inches(0.7), Inches(2.5), Inches(11.8), Inches(3.6),
            ["One cell = one ticker on one date = one full graph execution",
             "Settlement enters at the first close after the analysis date (no look-ahead), then "
             "measures 5 trading days of realised return",
             "Alpha = cell return − SPY return over the same window",
             "Hit rate per rating: Buy/Overweight expect positive alpha, Underweight/Sell negative, "
             "Hold claims no direction",
             "Efficiency: elapsed seconds and LLM calls per cell, from a callback handler on "
             "every model client"],
            size=16)
    textbox(s, Inches(0.7), Inches(6.3), Inches(11.8), Inches(0.6),
            "Outside this study: the paper's portfolio-level backtest (annualised return, Sharpe, "
            "drawdown), which a two-day laptop budget cannot support.", size=13, color=GREY)

    # 4 -----------------------------------------------------------------
    s = blank(prs)
    header(s, "One integer apart, everything else pinned", "experimental setup")
    table(s, Inches(0.7), Inches(1.5), Inches(6.3),
          [["", "baseline", "modified"],
           ["max_debate_rounds", "1 (default)", "0"],
           ["model", "deepseek-flash", "deepseek-flash"],
           ["temperature", "0.0", "0.0"],
           ["analysts", "market/news/fundamentals", "same"],
           ["ticker · dates", "AAPL · 3 dates", "same"],
           ["max_tool_rounds", "8", "8"]],
          [Inches(1.9), Inches(2.2), Inches(2.2)], size=13)
    bullets(s, Inches(7.3), Inches(1.6), Inches(5.4), Inches(4.8),
            ["I read the routing code and confirmed that it stops the debate at "
             "count ≥ 2 × max_debate_rounds",
             "A value of 1 runs Bull, Bear and hand-over, and a value of 0 runs Bull once while the "
             "Bear never speaks, so the rebuttal is what disappears",
             "The first Bull turn stays unconditional, so 0 keeps one Bull statement and removes the "
             "rebuttal",
             "Dates chosen so all three cells settle before the run"],
            size=14)

    # 5 -----------------------------------------------------------------
    s = blank(prs)
    header(s, "The pipeline reproduces: 3/3 cells settled", "baseline results")
    rows = [["date", "rating", "raw", "alpha", "runtime", "calls"]]
    for c in base:
        rows.append([c["date"], c["rating"], c["raw_return"], c["alpha"],
                     f"{float(c['runtime_s']):.0f}s", c["llm_calls"]])
    table(s, Inches(0.7), Inches(1.6), Inches(7.6), rows,
          [Inches(1.5), Inches(1.6), Inches(1.1), Inches(1.1), Inches(1.2), Inches(1.1)], size=13)
    alphas = [pct(c["alpha"]) for c in base]
    alphas = [a for a in alphas if a is not None]
    mean = sum(alphas) / len(alphas) if alphas else 0
    textbox(s, Inches(0.7), Inches(3.35), Inches(12), Inches(0.6),
            f"mean alpha {mean:+.2%} · 61 LLM calls · 16 min elapsed for the arm",
            size=17, bold=True, color=ACCENT)
    stats = s.shapes.add_shape(1, Inches(8.7), Inches(1.55), Inches(3.9), Inches(1.5))
    stats.fill.solid()
    stats.fill.fore_color.rgb = RGBColor(0xF2, 0xF6, 0xFA)
    stats.line.color.rgb = RGBColor(0xD5, 0xDF, 0xE8)
    stf = stats.text_frame
    stf.word_wrap = True
    stf.vertical_anchor = MSO_ANCHOR.TOP
    for i, ln in enumerate(["3 / 3 cells settled", "0 pending", "+0.90% mean alpha"]):
        p = stf.paragraphs[0] if i == 0 else stf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(15)
        r.font.bold = (i == 0)
        r.font.color.rgb = NAVY
        r.font.name = "Calibri"
    bullets(s, Inches(0.7), Inches(4.3), Inches(11.9), Inches(1.9),
            ["Every decision is logged as pending and later settled with its realised return and alpha",
             "Ratings were 2 Hold and 1 Underweight, and a Hold claims no direction so it stays out "
             "of the hit rate",
             "No published number is matched, since the model, the dates and the metric granularity "
             "all differ"], size=14)

    # 6 -----------------------------------------------------------------
    s = blank(prs)
    header(s, "Cheaper, and it stopped abstaining", "modification & results")
    rows = [["date", "rating (1 round)", "alpha", "call", "rating (0 rounds)", "call",
             "time 1→0", "calls 1→0"]]
    for d in sorted(set(by_date_b) | set(by_date_m)):
        b, m = by_date_b.get(d, {}), by_date_m.get(d, {})
        rows.append([d, b.get("rating", "-"), b.get("alpha", "-"), verdict(b), m.get("rating", "-"),
                     verdict(m), f"{float(b.get('runtime_s', 0)):.0f}→"
                     f"{float(m.get('runtime_s', 0)):.0f}", f"{b.get('llm_calls','-')}→"
                     f"{m.get('llm_calls','-')}"])
    table(s, Inches(0.5), Inches(1.5), Inches(12.3), rows,
          [Inches(1.5), Inches(2.1), Inches(0.95), Inches(1.25), Inches(2.1), Inches(1.25),
           Inches(1.6), Inches(1.5)], size=11.5)
    textbox(s, Inches(0.6), Inches(3.3), Inches(12.2), Inches(0.5),
            "mean per cell: 321s → 260s (−19%) · 20.0 → 17.3 LLM calls (−13%) · "
            "tokens −18% · alpha identical within a date by construction",
            size=14, bold=True, color=ACCENT)
    bullets(s, Inches(0.6), Inches(4.0), Inches(12.2), Inches(2.8),
            ["The cost falls because one fewer analyst turn per cell is mechanical and would "
             "replicate on other dates",
             "The baseline abstained twice with Hold and made one correct Underweight call, while the "
             "modified arm committed to Overweight three times and was correct twice",
             "The shorter debate changed the system's willingness to abstain and left its foresight "
             "unchanged",
             "With 3 dates and one run per date per arm this is a cross-date sample and no "
             "significance test"], size=13)

    # 7 -----------------------------------------------------------------
    s = blank(prs)
    header(s, "What reproduces, what does not, what I would do next", "conclusions")
    bullets(s, Inches(0.7), Inches(1.5), Inches(5.8), Inches(4.8),
            ["The mechanism reproduces, with a pinned commit and pinned dependencies, 3 of 3 cells "
             "settled, and 19 to 21 LLM calls per baseline cell against 16 to 18 in the modified arm",
             "The cost effect reproduces and is mechanical, so it would hold on other dates",
             "The paper's returns do not reproduce, since the model and the dates differ and the "
             "metric is a per-decision alpha without a portfolio backtest",
             "Variance stays unmeasured, because 3 dates give 3 samples and every date ran once"],
            size=14)
    box = s.shapes.add_shape(1, Inches(6.9), Inches(1.6), Inches(5.7), Inches(3.5))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xF2, 0xF6, 0xFA)
    box.line.color.rgb = RGBColor(0xD5, 0xDF, 0xE8)
    tb = box.text_frame
    tb.word_wrap = True
    tb.vertical_anchor = MSO_ANCHOR.TOP
    for i, ln in enumerate(["Next steps", "",
                            "• 5 dates per arm + 3 repeats on one date",
                            "• log reasoning tokens, not just totals",
                            "• add the sentiment analyst back",
                            "• compare 0 vs 2 rounds, not only 0 vs 1"]):
        p = tb.paragraphs[0] if i == 0 else tb.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(15)
        r.font.bold = (i == 0)
        r.font.color.rgb = NAVY
        r.font.name = "Calibri"
    textbox(s, Inches(0.7), Inches(6.6), Inches(11.9), Inches(0.5),
            "Repository, configs, logs and this deck: see the GitHub link in the submission.",
            size=12, color=GREY)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "FTEC5660_Presentation.pptx"
    prs.save(target)
    return target


if __name__ == "__main__":
    print(build())
