# TradingAgents reproducibility study (FTEC5660)

Reproduction of a documented capability of **TradingAgents: Multi-Agents LLM Financial Trading
Framework** (TauricResearch), plus one isolated modification: **shortening the bull/bear research
debate by one round**.

- Upstream: <https://github.com/TauricResearch/TradingAgents>
- Pinned commit: `9fa1196fffbcfd9de5146d2dd2869df84ab99838` (tag `v0.7.1` + one README commit)
- Paper: <https://arxiv.org/abs/2412.20138>

Upstream code is **not vendored** here: it is fetched from GitHub at the pinned commit, so the
upstream LICENSE and authorship stay with the upstream repository. This repository holds only the
harness described below, the two arm configurations, the measured cells and the report.

## What is reproduced

The repository's documented evaluation loop (`tradingagents.backtest.run_backtest` +
`summarize`): the graph analyses a ticker on a date, the Portfolio Manager emits one of five
ratings, the decision is appended to a memory log as *pending*, and once the 5-trading-day holding
window has traded the run settles it with the realised return and the alpha against the regional
benchmark (SPY here). `summarize` then reports, per rating, `n`, directional hit rate and mean alpha.

Target claim, quoted from the repository README section on backtesting: every cell is scored on
realized alpha against the instrument's regional benchmark and grouped by rating. The reproduction
checks that this pipeline runs end to end on this machine and produces settled and scored cells, and
it makes no claim about matching any published return figure, since the README itself warns that
returns do not form a replicable fixed number.

## What is modified

| | baseline | modified |
|---|---|---|
| `max_debate_rounds` | `1` (repository default) | `0` |

The provider, the model, the temperature, the analysts, the ticker, the dates and the vendors stay
identical across arms; `run_experiment.py` builds both configs from one function, and this value is
the only branch inside it.

Semantics, verified in `tradingagents/graph/conditional_logic.py:12-21`: the debate continues while
`count < 2 * max_debate_rounds`, so the default (1) yields one Bull turn and one Bear turn before
the Research Manager. With 0 the router sends the graph to the Research Manager immediately after
the Bull's single turn, so the bear rebuttal disappears. (The Bull's first turn is unconditional:
`setup.py:166` wires the analysts straight into `Bull Researcher`.)

## Experiment design

- Ticker: `AAPL`; dates: 2026-10-06, 2026-10-13, 2026-10-20 (all with a completed 5-day holding
  window before the run date, so every cell settles).
- Analysts: `market`, `news`, `fundamentals` (the `social` analyst is left out to keep the run
  inside the time budget; identical in both arms).
- Model: `deepseek-flash` (DeepSeek API, OpenAI-compatible) for both the quick and deep tiers;
  `temperature = 0.0`. This is a documented substitution for the paper's models, per the course
  rules: results are **not directly comparable** to the paper because the underlying LLM differs.
- `max_tool_rounds = 8` in both arms. Rationale: the macro tools need a FRED key that is not
  configured here, and the model otherwise spends most of its tool budget retrying them. Bounding
  it is symmetric, so the A/B contrast is unaffected; it is a deviation from the default 20 and is
  reported as such.
- Data: keyless vendors only (`yfinance`); macro indicators therefore degrade to an unavailability
  notice inside the prompts, and the agents are instructed to report that notice without estimating
  a value.

## Results

Three settled cells per arm (all 3/3 resolved, none pending), one run per cell:

| date | rating (1 round) | alpha | call | rating (0 rounds) | call | runtime 1→0 | calls 1→0 |
|---|---|---|---|---|---|---|---|
| 2026-10-06 | Hold | +2.80% | no call | Overweight | correct | 355 → 256 s | 20 → 16 |
| 2026-10-13 | Underweight | -0.20% | correct | Overweight | wrong | 320 → 299 s | 21 → 18 |
| 2026-10-20 | Hold | +0.10% | no call | Overweight | correct | 287 → 226 s | 19 → 18 |

Aggregates: mean runtime per cell 321 s → 260 s (-18.9%), LLM calls 20.0 → 17.3 (-13.3%), tokens
-18.9%. Alpha is identical within a date, because it measures the instrument's realised excess return
after that date and therefore belongs to the cell, so the informative comparison pairs every rating
with its outcome: the baseline made a directional call in 1 of 3 cells and was correct, while the
modified arm made a directional call in 3 of 3 cells and was correct twice.

Reading: removing the Bear's rebuttal changes cost mechanically and changes the decisions
behaviourally, since the system stopped abstaining and gained no visible foresight. With 3 dates and
one run per date per arm this is a cross-date sample, and it carries no significance test.

Full evidence: `results/comparison.csv`, `results/*/cells.csv`, `results/*/summary.txt`,
`logs/`, and the report in `report/`.

```
results/
  baseline/  cells.csv, cells.json, summary.txt, run_config.json, runs/<run_id>/
  modified/  cells.csv, cells.json, summary.txt, run_config.json, runs/<run_id>/
  comparison.csv
```

## Reproduce

```bash
# 1. upstream code, pinned
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents && git checkout 9fa1196fffbcfd9de5146d2dd2869df84ab99838 && cd ..

# 2. environment (Python 3.11)
python -m venv .venv
.venv/Scripts/python -m pip install -U pip uv
.venv/Scripts/uv pip install -e TradingAgents

# 3. credentials
cp repro/.env.example repro/.env      # then set DEEPSEEK_API_KEY

# 4. run both arms (each cell is one full multi-agent analysis; ~3-8 min per cell)
cd repro
../.venv/Scripts/python run_experiment.py --arm baseline --dates 2026-10-06 2026-10-13 2026-10-20
../.venv/Scripts/python run_experiment.py --arm modified --dates 2026-10-06 2026-10-13 2026-10-20

# 5. side-by-side table
../.venv/Scripts/python compare_arms.py
```

No API key is committed: `.env` is git-ignored, and `results/` keeps only model outputs and
timings.

## Files

| path | purpose |
|---|---|
| `run_experiment.py` | runs one arm: config, per-cell timing + LLM call/token counting, writes `cells.csv` / `summary.txt` |
| `compare_arms.py` | joins the two arms into `results/comparison.csv` and prints the deltas |
| `smoke_env.py` | keyless environment check (imports, config, Yahoo data, tool routing) |
| `probe_models.py` | lists the model IDs the DeepSeek endpoint actually serves |
| `configs/*.json` | the two arm configurations, as run |
| `logs/` | console logs of every run (evidence for the debug diary) |
