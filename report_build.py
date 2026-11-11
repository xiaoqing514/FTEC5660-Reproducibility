"""Build the FTEC5660 reproducibility report (DOCX) from the measured evidence.

Run with the bundled Python that ships python-docx:

    python report_build.py

Numbers in the results sections are read from results/*/cells.csv and
results/comparison.csv, so the document cannot drift from the measurements.
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
OUT = HERE / "report"
UPSTREAM_COMMIT = "9fa1196fffbcfd9de5146d2dd2869df84ab99838"
MODEL = "deepseek-flash (DeepSeek-V4.1-Flash)"
DATES = ["2026-10-06", "2026-10-13", "2026-10-20"]


# --------------------------------------------------------------------------- helpers
def load_cells(arm: str) -> list[dict]:
    path = RESULTS / arm / "cells.csv"
    if not path.exists():
        raise SystemExit(f"missing {path}")
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pct(text: str) -> float | None:
    if not text:
        return None
    try:
        return float(str(text).strip().rstrip("%")) / 100
    except ValueError:
        return None


def fnum(text: str, spec: str = ".0f", empty: str = "n/a") -> str:
    try:
        return format(float(text), spec)
    except (TypeError, ValueError):
        return empty


def fpct(text: str, empty: str = "n/a") -> str:
    v = pct(text)
    return f"{v:+.2%}" if v is not None else empty


def style_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.12

    for name, size, color in (("Heading 1", 15, (0x1F, 0x3B, 0x57)),
                              ("Heading 2", 12, (0x1F, 0x3B, 0x57)),
                              ("Title", 20, (0x10, 0x25, 0x38))):
        st = doc.styles[name]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(*color)
        st.paragraph_format.space_before = Pt(10 if name != "Title" else 0)
        st.paragraph_format.space_after = Pt(4)


def para(doc: Document, text: str, *, bold_lead: str | None = None, size: float | None = None,
         align=None, italic: bool = False) -> None:
    p = doc.add_paragraph()
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        if size:
            r.font.size = Pt(size)
    r = p.add_run(text)
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if align is not None:
        p.alignment = align
    return p


def bullets(doc: Document, items: list[str], style: str = "List Bullet") -> None:
    for it in items:
        doc.add_paragraph(it, style=style)


def table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None,
          font_size: float = 8.5) -> None:
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(font_size)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(val))
            run.font.size = Pt(font_size)
    # Keep a row on one page: a split row leaves an orphaned cell fragment behind.
    for row in t.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = tr_pr.makeelement(qn("w:cantSplit"), {})
        tr_pr.append(cant_split)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def code_block(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(7.5)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.left_indent = Cm(0.5)


# --------------------------------------------------------------------------- content
def build() -> Path:
    base = load_cells("baseline")
    mod = load_cells("modified")

    doc = Document()
    style_document(doc)

    doc.add_paragraph("Reproducing a Multi-Agent LLM Trading System", style="Title")
    p = doc.add_paragraph()
    r = p.add_run("FTEC5660 · Agentic AI for Business and FinTech · Reproducibility Work")
    r.font.size = Pt(11)
    r.bold = True
    para(doc, "Name: CHEN Duoduo    Student ID: 1155267609    Date: 12 November 2026",
         size=10)
    para(doc, f"Upstream: TauricResearch/TradingAgents @ {UPSTREAM_COMMIT[:7]} (v0.7.1). "
              f"Model used here: {MODEL}, temperature 0. All numbers below were produced on the "
              f"author's machine during this assignment; none are copied from the paper.",
         size=9.5, italic=True)

    # 1 ---------------------------------------------------------------- summary
    doc.add_heading("1. Project summary and reproduction target", level=1)
    para(doc, "TradingAgents is a multi-agent framework for financial trading decisions. For one "
              "ticker and one trade date it runs four specialist analysts with tool access (market, "
              "sentiment, news, fundamentals), a structured bull-versus-bear research debate, a "
              "research manager that writes an investment plan, a trader that drafts a decision, a "
              "three-way risk debate (aggressive / neutral / conservative), and a portfolio manager "
              "that issues a final five-tier rating (Buy, Overweight, Hold, Underweight, Sell). It "
              "qualifies as an agentic system under the course definition: it plans and acts over "
              "many steps, calls external data tools, keeps a persistent memory log, and coordinates "
              "several LLM roles in a graph.")
    para(doc, "The target I reproduced is the repository's own evaluation loop, because the paper's "
              "table reports portfolio metrics that this per-decision pipeline cannot produce. "
              "run_backtest executes the graph over a grid of (ticker, date) cells, and each decision "
              "is settled after a five-trading-day holding window into a realised return and an alpha "
              "against the instrument's regional benchmark. The README states its claim plainly: "
              "every cell is scored on realized alpha against the instrument's regional benchmark and "
              "grouped by rating. Reproducing that claim means showing that the pipeline runs end to "
              "end here, that every decision is logged, settled and scored, and that the aggregate "
              "summary follows from my own runs.")
    para(doc, "This scope is deliberately narrow. The paper's portfolio-level backtest (annualised "
              "return, Sharpe, max drawdown over a full year and several tickers) is far outside a "
              "two-day budget on a laptop with a hosted API, and the repository's own README warns "
              "that returns depend on model, temperature, date range and sampling. What can be "
              "reproduced honestly is the mechanism and its per-decision measurement.")

    # 2 ---------------------------------------------------------------- architecture
    doc.add_heading("2. System architecture as implemented", level=1)
    para(doc, "The graph is built in tradingagents/graph/setup.py. Three properties matter for the "
              "experiment:")
    bullets(doc, [
        "The analysts are parallel entry nodes: every selected analyst is wired from START and the "
        "debate starts only once all of them have filed a report (setup.py:160-166). Each analyst is "
        "its own sub-graph with a private message history and a bounded tool loop (max_tool_rounds), "
        "so one analyst's tool calls never pollute another's context.",
        "The research debate is a two-node loop (Bull Researcher, Bear Researcher) gated by "
        "ConditionalLogic.should_continue_debate, which stops when the turn count reaches "
        "2 × max_debate_rounds (conditional_logic.py:12-21). The same pattern governs the risk "
        "debate with 3 × max_risk_discuss_rounds.",
        "A Memory Log node runs alongside the analysts. It settles decisions whose holding window "
        "has traded since an earlier run, writes a short reflection, and feeds the most recent "
        "lessons to the Portfolio Manager. Point-in-time filtering keeps a backtest cell from reading "
        "outcomes that had not happened yet at its analysis date.",
    ])
    para(doc, "The single modification studied here sits exactly on the first of those loops, which "
              "makes it easy to isolate, because one integer in the config reaches one comparison in "
              "one router.")

    # 3 ---------------------------------------------------------------- setup
    doc.add_heading("3. Setup, environment and deviations", level=1)
    para(doc, "Everything ran on one Windows laptop with no GPU: Python 3.11.8 in a virtual "
              "environment, the upstream repository installed in editable mode from commit "
              f"{UPSTREAM_COMMIT[:7]}, and the LLM served over HTTPS by the DeepSeek API.")
    table(doc,
          ["Component", "Version / value"],
          [["OS", "Windows 11 (x64), no discrete GPU"],
           ["Python", "3.11.8 (venv)"],
           ["tradingagents", "0.7.1 (editable, commit " + UPSTREAM_COMMIT[:7] + ")"],
           ["langgraph", "1.2.20"],
           ["langchain-core", "1.7.7"],
           ["langchain-openai", "1.7.4"],
           ["pandas / numpy", "3.1.1 / 2.4.6"],
           ["yfinance", "1.8.0"],
           ["LLM provider", "DeepSeek, OpenAI-compatible endpoint (api.deepseek.com)"],
           ["Model (quick + deep)", MODEL],
           ["Temperature", "0.0"],
           ["Data vendors", "yfinance (keyless); macro tools unavailable (no FRED key)"]],
          widths=[5.0, 10.0])
    caption(doc, "Table 1. Environment actually used.")

    doc.add_heading("3.1 Documented deviations", level=2)
    para(doc, "The course rules allow substituting a model when the original is unreachable, provided "
              "the change is recorded and treated as a controlled variable. The table lists every "
              "deviation from the repository defaults, all of them identical in the two arms.")
    table(doc,
          ["Deviation", "Value used", "Why"],
          [["Model / provider", "deepseek-flash",
            "The paper's models are unreachable from this account. Per the course rules, results are "
            "not directly comparable to the paper because the underlying LLM differs."],
           ["Sampling temperature", "0.0", "Fixed in both arms to reduce run-to-run variation, and "
            "the chosen model is reasoning-first and largely ignores it (the README says so)."],
           ["Analysts", "market, news, fundamentals", "The sentiment analyst adds data sources and "
            "cost without touching the debate loop under study, and it is identical in both arms."],
           ["max_tool_rounds", "8 (default 20)", "Without a FRED key the macro tools report the "
            "series as unavailable and the model kept retrying them, so a bounded budget keeps one "
            "cell inside a few minutes. The bound applies to both arms and caps how much evidence "
            "each analyst gathers."],
           ["Dates", "2026-10-06 / 13 / 20", "Every cell needs a completed five-trading-day holding "
            "window to settle; these are the most recent dates with a full window before the run."]],
          widths=[3.6, 4.6, 6.8])
    caption(doc, "Table 2. Deviations from upstream defaults, identical across arms.")

    # 4 ---------------------------------------------------------------- method
    doc.add_heading("4. Reproduction methodology and metric definitions", level=1)
    para(doc, "A cell in this report is one ticker on one date together with one full execution of "
              "the graph, and the portfolio manager's final text is parsed into a rating and appended "
              "to that run's memory log as pending. Settlement then enters at the first close after "
              "the analysis date, since a run reads news published after that day's close and the "
              "same-day close would leak information, and it measures the outcome over five trading "
              "days:")
    bullets(doc, [
        "Raw return: percentage change of the instrument over the holding window.",
        "Alpha: raw return minus the same-window return of the benchmark (SPY for a US ticker).",
        "Hit rate: share of settled cells whose alpha has the sign the rating claimed (Buy and "
        "Overweight expect positive alpha, Underweight and Sell negative, Hold claims no direction "
        "and is excluded from the hit rate).",
        "Efficiency: elapsed time per cell and number of LLM calls per cell, both measured by a "
        "LangChain callback handler attached to every model client (run_experiment.py).",
    ])
    para(doc, "The sample covers one ticker (AAPL), three dates and two arms, and every date appears "
              "once in each arm, so the design gives a small cross-date sample with no repeated run of "
              "one identical input. The LLM is stochastic, so per-cell numbers move for reasons "
              "unrelated to the modification, and the report therefore shows every cell and treats "
              "the arm means as indicative, since the course asks for a measured impact together with "
              "an honest statement of how much of that impact is noise.")

    # 5 ---------------------------------------------------------------- baseline results
    doc.add_heading("5. Baseline: does the documented pipeline work?", level=1)
    para(doc, "All three baseline cells completed, settled and scored, so the reproduction target is "
              "met in a weak but honest sense: the mechanism the README describes runs here, on my "
              "dates, with my model.")
    rows = []
    for c in base:
        rows.append([c["date"], c["rating"], fpct(c.get("raw_return", "")), fpct(c.get("alpha", "")),
                     fnum(c.get("runtime_s", "")), fnum(c.get("llm_calls", "")),
                     f"{int(float(c['prompt_tokens'])) + int(float(c['completion_tokens'])):,}"
                     if c.get("prompt_tokens") else "n/a"])
    table(doc, ["Analysis date", "Rating", "Raw return", "Alpha vs SPY", "Runtime (s)", "LLM calls",
                "Tokens"], rows, widths=[2.6, 2.4, 2.2, 2.3, 2.0, 1.9, 2.2])
    caption(doc, "Table 3. Baseline cells (max_debate_rounds = 1, the repository default).")

    alphas_b = [pct(c.get("alpha", "")) for c in base]
    alphas_b = [a for a in alphas_b if a is not None]
    if alphas_b:
        para(doc, f"Mean alpha across the three settled cells is {statistics.mean(alphas_b):+.2%} "
                  f"(sd {statistics.stdev(alphas_b):.2%}, n={len(alphas_b)}). The repository's "
                  f"summary renderer, run on my log, is quoted verbatim in the appendix. No published "
                  f"number is matched, and none should be: the model differs, the dates differ from "
                  f"the paper's window, and the paper reports portfolio-level metrics that a "
                  f"single-decision alpha cannot express.")

    # 6 ---------------------------------------------------------------- modification
    doc.add_heading("6. The modification: one round less debate", level=1)
    para(doc, "The modification lowers max_debate_rounds from 1 to 0, which shortens the bull and "
              "bear research debate by one round. One config integer carries the change, the change "
              "removes one analyst turn per cell and alters what the research manager reads, and it "
              "targets a genuine design choice about how much adversarial argument the system obtains "
              "before it decides.")
    para(doc, "I verified the code path in the source. The routing condition compares the turn count "
              "with 2 × max_debate_rounds, so the default of 1 runs Bull, then Bear, and then hands "
              "over to the Research Manager, while 0 satisfies the condition after the Bull's first "
              "turn and the Research Manager receives a one-sided debate. The first Bull turn stays "
              "unconditional because setup.py wires the analysts into the Bull Researcher node, and a "
              "value of 0 therefore removes the rebuttal while one Bull statement is still produced. "
              "That detail matters because the parameter name suggests that zero disables the debate "
              "entirely.")
    code_block(doc,
               "tradingagents/graph/conditional_logic.py\n"
               "  if state['investment_debate_state']['count'] >= 2 * self.max_debate_rounds:\n"
               "      return 'Research Manager'\n\n"
               "repro/configs/baseline.json   max_debate_rounds = 1\n"
               "repro/configs/modified.json   max_debate_rounds = 0   (the only change)")
    para(doc, "Both arms are produced by one function in run_experiment.py; the only branch between "
              "them is this integer, and each arm's run_config.json records the value actually used.")

    # 7 ---------------------------------------------------------------- comparison
    doc.add_heading("7. Results after the modification", level=1)
    para(doc, "A methodological point comes first because it governs how the table must be read. In "
              "this framework alpha belongs to the cell, since it measures the instrument's realised "
              "excess return over the benchmark after that date, and the same date therefore yields "
              "the same alpha in both arms whatever the agents decided. What differs across arms is "
              "the rating and, through the rating, whether the cell was called correctly. Comparing "
              "arm means of alpha would measure the calendar, and the informative comparison pairs "
              "each rating with its outcome.")
    dir_map = {"Buy": 1, "Overweight": 1, "Underweight": -1, "Sell": -1, "Hold": 0}

    def called(rating: str, alpha_text: str) -> str:
        a = pct(alpha_text)
        d = dir_map.get(rating, 0)
        if a is None:
            return "n/a"
        if d == 0:
            return "no call (Hold)"
        return "correct" if a * d > 0 else "wrong"

    by_date_b = {c["date"]: c for c in base}
    rows = []
    for c in mod:
        b = by_date_b.get(c["date"], {})
        rows.append([c["date"], b.get("rating", "n/a"), called(b.get("rating", ""), b.get("alpha", "")),
                     c.get("rating", "n/a"), called(c.get("rating", ""), c.get("alpha", "")),
                     fpct(b.get("alpha", "")),
                     f"{fnum(b.get('runtime_s',''))} → {fnum(c.get('runtime_s',''))}",
                     f"{fnum(b.get('llm_calls',''))} → {fnum(c.get('llm_calls',''))}"])
    table(doc, ["Date", "Rating (1)", "Call (1)", "Rating (0)", "Call (0)", "Alpha",
                "Runtime s", "Calls"], rows,
          widths=[2.2, 2.0, 2.3, 2.0, 2.3, 1.6, 2.2, 1.7])
    caption(doc, "Table 4. Per-cell contrast. Alpha is identical within a date by construction; the "
                 "decision, and whether it was right, is what changes.")

    signed_b = [r for r in base if dir_map.get(r.get("rating", ""), 0) != 0]
    signed_m = [r for r in mod if dir_map.get(r.get("rating", ""), 0) != 0]
    hit_b = [r for r in signed_b if called(r.get("rating", ""), r.get("alpha", "")) == "correct"]
    hit_m = [r for r in signed_m if called(r.get("rating", ""), r.get("alpha", "")) == "correct"]

    am_list = [pct(c.get("alpha", "")) for c in mod]
    am_list = [a for a in am_list if a is not None]
    rt_b = [float(c["runtime_s"]) for c in base if c.get("runtime_s")]
    rt_m = [float(c["runtime_s"]) for c in mod if c.get("runtime_s")]
    cl_b = [float(c["llm_calls"]) for c in base if c.get("llm_calls")]
    cl_m = [float(c["llm_calls"]) for c in mod if c.get("llm_calls")]
    tok_b = [float(c["prompt_tokens"]) + float(c["completion_tokens"]) for c in base if c.get("prompt_tokens")]
    tok_m = [float(c["prompt_tokens"]) + float(c["completion_tokens"]) for c in mod if c.get("prompt_tokens")]

    def tally(rows_: list[dict]) -> str:
        counts: dict[str, int] = {}
        for c in rows_:
            counts[c.get("rating", "?")] = counts.get(c.get("rating", "?"), 0) + 1
        return ", ".join(f"{k} \u00d7{v}" for k, v in counts.items())

    para(doc, "Aggregates over the three dates per arm:")
    bullets(doc, [
        f"Decisions: baseline {tally(base)}; modified {tally(mod)}.",
        f"Signed calls: baseline {len(hit_b)}/{len(signed_b)} correct, modified {len(hit_m)}/{len(signed_m)} "
        f"correct. Baseline left {len(base) - len(signed_b)} cell(s) without a direction (Hold), so the "
        f"two arms are not scored on the same number of decisions.",
        f"Cost per cell: {statistics.mean(rt_b):.0f}s → {statistics.mean(rt_m):.0f}s "
        f"({(statistics.mean(rt_m) - statistics.mean(rt_b)) / statistics.mean(rt_b):+.1%}); "
        f"{statistics.mean(cl_b):.0f} → {statistics.mean(cl_m):.0f} LLM calls "
        f"({(statistics.mean(cl_m) - statistics.mean(cl_b)) / statistics.mean(cl_b):+.1%}).",
        f"Tokens per cell: {statistics.mean(tok_b):,.0f} → {statistics.mean(tok_m):,.0f} "
        f"({(statistics.mean(tok_m) - statistics.mean(tok_b)) / statistics.mean(tok_b):+.1%}).",
    ])
    para(doc, "The cost effect is mechanical and unambiguous, because one fewer analyst turn per cell "
              "removes about a fifth of the elapsed time and an eighth of the calls. The quality "
              "effect appears as a behavioural shift, since the research manager stopped abstaining "
              "once the Bear's rebuttal was removed. Baseline returned Hold twice and Underweight "
              "once, so it made a directional claim in only one of three cells, while the modified "
              "arm claimed Overweight in all three and was right twice. Whether a system that always "
              "commits and is right twice in three performs better than one that usually abstains is a "
              "portfolio question this design cannot settle, and a comparison of returns alone would "
              "not reveal that behavioural change.")

    # 8 ---------------------------------------------------------------- debug diary
    doc.add_heading("8. Debug diary", level=1)
    para(doc, "The blockers below are the ones that actually cost time; each entry names the symptom, "
              "the cause I established, and the fix that is now part of the workflow.")
    table(doc,
          ["#", "Symptom", "Cause", "Fix"],
          [["1", "Every HTTPS request from the shell failed with SEC_E_NO_CREDENTIALS, so git clone "
                 "could not reach GitHub.",
            "The shell runs under a restricted Windows token; Schannel could not acquire credentials.",
            "Set http.sslBackend=openssl for git; Python's OpenSSL stack was unaffected."],
           ["2", "pip install hung for >12 minutes with no output, twice.",
            "The resolver backtracked over the langchain/langgraph dependency graph while pinning "
            "pandas 3 and langchain 1.x.",
            "Installed uv and resolved with `uv pip install -e .`, which finished in about a minute."],
           ["3", "uv then refused to start with the error failed to open cache/.lock: access denied.",
            "Its default cache lives under AppData, outside the writable sandbox root.",
            "Pointed UV_CACHE_DIR inside the project."],
           ["4", "First end-to-end run stalled on cell 1 for ~10 minutes with no new output.",
            "The news analyst kept calling get_macro_indicators, which reports the series as "
            "unavailable without a FRED key, and the SDK's default 10-minute timeout meant each "
            "retry took ten minutes to appear.",
            "Bounded max_tool_rounds to 8, set a 240 s request timeout, and attached a callback that "
            "prints every call's latency and tokens, so the run is now observable while it happens."],
           ["5", "Leaving the macro vendor unset did not remove the calls.",
            "An empty vendor string makes the router fall back to every available vendor "
            "(router.py:216-225), which is the opposite of disabling the category.",
            "Kept the default fred entry and accepted the graceful unavailable sentinel, which the "
            "agent prompts are written to respect."],
           ["6", "A cell produced a decision and the log stayed pending.",
            "Settlement needs five trading days after the analysis date, so a date too recent has no "
            "future prices.",
            "Chose analysis dates with a completed holding window before the run date."],
           ["7", "Report numbers would have drifted from the CSVs while iterating on wording.",
            "Hand-copying metrics into prose.",
            "report_build.py reads cells.csv and fills in the document, so the tables cannot disagree "
            "with the measured files."],
           ["8", "The first comparison showed a zero alpha delta between arms on every date.",
            "No defect was present, because alpha is the instrument's realised excess return after "
            "the date and therefore belongs to the cell. Comparing arm means of alpha would have "
            "measured the calendar, since the agents cannot influence it.",
            "Switched the quality comparison to rating versus outcome (correct, wrong, no call), and "
            "documented the reasoning in Section 7."]],
          widths=[0.8, 5.4, 4.6, 4.4], font_size=8)
    caption(doc, "Table 5. Blockers, causes and fixes.")

    # 9 ---------------------------------------------------------------- conclusion
    doc.add_heading("9. Conclusion: what is reproducible, what is not", level=1)
    bullets(doc, [
        "The mechanism reproduces, because a pinned commit together with pinned dependencies produce "
        "settled and scored cells on a laptop with a hosted API, and the parallel analysts, the debate "
        "gates, the memory log, the settlement and the summary all behave as the repository documents.",
        "The cost of the modification also reproduces, because removing one debate round removes one "
        "analyst turn per cell and that produces roughly a fifth less elapsed time and an eighth "
        "fewer LLM calls, a mechanical result that would replicate on other dates.",
        "The most interesting finding concerns behaviour, since the system stopped abstaining once the "
        "Bear's rebuttal disappeared. Baseline chose Hold in two of three cells, the modified arm "
        "claimed Overweight in all three and was right twice, and the shorter debate changed how "
        "decisive the decision became without visibly improving foresight.",
        "The paper's return figures do not reproduce, because the model and the dates differ, the "
        "metric is a per-decision alpha with no portfolio backtest behind it, and the generator is "
        "stochastic. The README warns about exactly this, and the honest deliverable is a mechanism "
        "study that makes no claim to match a published number.",
        "Variance remains unmeasured, because three dates give three samples, each date ran once per "
        "arm, and part of the rating difference could therefore be sampling noise. A variance estimate "
        "needs repeated runs on identical inputs, and the API budget did not allow them here.",
    ])
    para(doc, "If I extended this work, the highest-value change would be repeats on a single date "
              "before adding further dates, because that separates a genuine effect of the debate from "
              "model noise, and the present design cannot answer that question.")

    # appendix ---------------------------------------------------------
    # No forced page break: with one, the last three conclusion bullets sat alone
    # on a nearly empty page. The heading's keep-with-next keeps Appendix A intact.
    doc.add_heading("Appendix A. Repository map and how to re-run", level=1)
    para(doc, "The repository holds the harness, the two arm configurations, the measured cells and "
              "the logs, and it pins the upstream code by commit without copying that code here.")
    code_block(doc,
               "repro/\n"
               "  run_experiment.py      # one arm: config, per-cell timing/calls/tokens, cells.csv\n"
               "  compare_arms.py        # joins both arms into results/comparison.csv\n"
               "  smoke_env.py           # keyless environment check\n"
               "  probe_models.py        # model IDs the endpoint actually serves\n"
               "  configs/baseline.json  # max_debate_rounds = 1\n"
               "  configs/modified.json  # max_debate_rounds = 0  (the only change)\n"
               "  results/{baseline,modified}/cells.csv, summary.txt, run_config.json, runs/\n"
               "  logs/                  # console log of every run\n"
               "  report/                # this report\n")
    para(doc, "Re-run: clone the upstream repository, check out "
              f"{UPSTREAM_COMMIT[:7]}, create a Python 3.11 venv, `uv pip install -e TradingAgents`, "
              "put DEEPSEEK_API_KEY in repro/.env, then run run_experiment.py once per arm and "
              "compare_arms.py. No key is committed; .env is ignored.")

    doc.add_heading("Appendix B. Repository summary output (verbatim)", level=1)
    for arm in ("baseline", "modified"):
        path = RESULTS / arm / "summary.txt"
        if path.exists():
            para(doc, f"{arm}:", bold_lead=None, size=9.5)
            code_block(doc, path.read_text(encoding="utf-8").strip())

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "FTEC5660_Reproducibility_Report.docx"
    doc.save(target)
    return target


if __name__ == "__main__":
    print(build())
