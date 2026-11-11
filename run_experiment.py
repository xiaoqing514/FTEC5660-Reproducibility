"""Run one arm of the debate-round experiment and record per-cell evidence.

Usage (from the repro/ directory, with the venv python):

    python run_experiment.py --arm baseline --dates 2026-10-15 2026-10-22 2026-10-29

The arm only changes ``max_debate_rounds``: baseline uses the repository default
(1), modified uses 0. Everything else -- models, temperature, analysts, ticker,
dates, data vendors -- is identical between arms.

Evidence written under ``results/<arm>/``:
    cells.csv        one row per (ticker, date) cell: runtime, LLM calls, tokens,
                     rating, realized return, alpha
    cells.json       the same rows plus the raw final decision text
    summary.txt      the repository's own ``summarize()`` rendering
    runs/<run_id>/   the backtest run dir, including trading_memory.md
    run_config.json  the exact config the arm ran with
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import traceback
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


def load_env() -> None:
    """Load repro/.env (or the process env) before importing tradingagents."""
    env_path = HERE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env()

from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402


class UsageCounter(BaseCallbackHandler):
    """Count model calls and tokens across the whole process, and log each call."""

    def __init__(self) -> None:
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._starts: dict = {}

    def snapshot(self) -> tuple[int, int, int]:
        return (self.calls, self.prompt_tokens, self.completion_tokens)

    def on_chat_model_start(self, serialized, messages, *, run_id=None, **kwargs):
        self._starts[run_id] = time.perf_counter()

    def on_llm_start(self, serialized, prompts, *, run_id=None, **kwargs):
        self._starts.setdefault(run_id, time.perf_counter())

    def on_llm_end(self, response, *, run_id=None, **kwargs):  # noqa: D102
        self.calls += 1
        prompt = completion = 0
        try:
            msg = response.generations[0][0].message
            usage = getattr(msg, "usage_metadata", None) or {}
            prompt = int(usage.get("input_tokens") or 0)
            completion = int(usage.get("output_tokens") or 0)
            self.prompt_tokens += prompt
            self.completion_tokens += completion
        except Exception:  # a provider that reports nothing still counts as one call
            pass
        elapsed = time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        print(f"    [llm #{self.calls}] {elapsed:6.1f}s in={prompt} out={completion}", flush=True)


COUNTER = UsageCounter()
CELL_RECORDS: list[dict] = []


def patch_instrumentation() -> None:
    """Attach the counter to every LLM client and time each propagate() call."""
    import tradingagents.graph.trading_graph as tg

    original_create = tg.create_tier_client

    def create_with_callbacks(config, tier, **extra):
        cbs = list(extra.pop("callbacks", None) or [])
        cbs.append(COUNTER)
        # A per-request ceiling keeps one slow provider call from stalling the
        # whole cell; the SDK's default (10 min) plus its own retries is too long
        # for a 6-cell experiment. Identical in both arms.
        extra.setdefault("timeout", float(os.environ.get("TA_TIMEOUT", "240")))
        extra.setdefault("max_retries", int(os.environ.get("TA_MAX_RETRIES", "1")))
        return original_create(config, tier, callbacks=cbs, **extra)

    tg.create_tier_client = create_with_callbacks

    original_propagate = tg.TradingAgentsGraph.propagate

    def timed_propagate(self, company_name, trade_date, *args, **kwargs):
        before = COUNTER.snapshot()
        started = time.perf_counter()
        error = ""
        final_state, signal = None, None
        try:
            final_state, signal = original_propagate(self, company_name, trade_date, *args, **kwargs)
        except Exception as exc:  # record, then re-raise so run_backtest logs the failure
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            elapsed = time.perf_counter() - started
            after = COUNTER.snapshot()
            CELL_RECORDS.append(
                {
                    "ticker": str(company_name),
                    "date": str(trade_date),
                    "runtime_s": round(elapsed, 1),
                    "llm_calls": after[0] - before[0],
                    "prompt_tokens": after[1] - before[1],
                    "completion_tokens": after[2] - before[2],
                    "signal": signal,
                    "error": error,
                    "final_trade_decision": (
                        (final_state or {}).get("final_trade_decision", "")
                        if isinstance(final_state, dict)
                        else ""
                    ),
                }
            )

    tg.TradingAgentsGraph.propagate = timed_propagate


def build_config(arm: str, rounds: int) -> dict:
    from tradingagents.default_config import build_default_config

    cfg = build_default_config()
    model = os.environ.get("TA_MODEL", "deepseek-chat")
    out = RESULTS / arm
    cfg.update(
        {
            "llm_provider": "deepseek",
            "quick_think_provider": None,
            "deep_think_provider": None,
            "quick_think_llm": model,
            "deep_think_llm": model,
            "backend_url": None,
            "temperature": float(os.environ.get("TA_TEMPERATURE", "0.0")),
            "max_debate_rounds": rounds,
            "max_risk_discuss_rounds": 1,
            # Bounded so a model that keeps retrying a keyless vendor (the macro
            # tools have no FRED key here) cannot burn the whole run. Identical
            # in both arms, so the A/B comparison is unaffected.
            "max_tool_rounds": int(os.environ.get("TA_MAX_TOOL_ROUNDS", "8")),
            "output_language": "English",
            "benchmark_ticker": "SPY",
            "holding_period_days": 5,
            "results_dir": str(out / "runs"),
            "memory_log_path": str(out / "trading_memory.md"),
            "data_cache_dir": str(RESULTS / "_cache"),
            # Keyless vendors only: no FRED / Alpha Vantage / SEC contact is
            # configured, so the keyless categories are the honest choice. A
            # category set to "" falls back to every vendor of that method
            # (router.py:216-225), so macro_data keeps its "fred" default and
            # simply degrades to "unavailable" when the key is missing.
            "data_vendors": {
                "core_stock_apis": "yfinance",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
                "macro_data": "fred",
                "prediction_markets": "polymarket",
            },
        }
    )
    return cfg


def read_memory_log(path: Path) -> list[dict]:
    """Parse settled/pending entries out of a trading memory log."""
    from tradingagents.memory import TradingMemoryLog

    entries = TradingMemoryLog({"memory_log_path": str(path)}).load_entries()
    return entries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["baseline", "modified"])
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--dates", nargs="+", required=True)
    ap.add_argument("--ticker", default="AAPL")
    ap.add_argument("--analysts", nargs="+", default=["market", "news", "fundamentals"])
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    rounds = args.rounds if args.rounds is not None else (1 if args.arm == "baseline" else 0)
    cfg = build_config(args.arm, rounds)
    out = RESULTS / args.arm
    out.mkdir(parents=True, exist_ok=True)

    run_id = args.run_id or f"{args.arm}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_config = {
        **{k: v for k, v in cfg.items() if k != "data_cache_dir"},
        "run_id": run_id,
        "arm": args.arm,
        "dates": args.dates,
        "ticker": args.ticker,
        "analysts": args.analysts,
        "model": cfg["quick_think_llm"],
        "rounds": rounds,
    }
    (out / "run_config.json").write_text(json.dumps(run_config, indent=2, default=str), encoding="utf-8")

    print(f"[{datetime.now():%H:%M:%S}] arm={args.arm} rounds={rounds} model={cfg['quick_think_llm']} "
          f"ticker={args.ticker} dates={args.dates} run_id={run_id}", flush=True)

    from tradingagents.backtest import run_backtest, summarize

    patch_instrumentation()

    started = time.perf_counter()
    status = "ok"
    try:
        result = run_backtest(
            [args.ticker],
            args.dates,
            cfg,
            selected_analysts=tuple(args.analysts),
            run_id=run_id,
            progress=lambda i, n, t, d: print(f"  cell {i}/{n}: {t} {d}", flush=True),
        )
    except Exception:
        status = "failed"
        traceback.print_exc()
        raise
    finally:
        elapsed = time.perf_counter() - started

    entries = read_memory_log(Path(result.log_path)) if Path(result.log_path).exists() else []
    by_cell = {(e["ticker"], e["date"]): e for e in entries}

    rows = []
    for rec in CELL_RECORDS:
        entry = by_cell.get((rec["ticker"], rec["date"]), {})
        rows.append(
            {
                **{k: rec[k] for k in ("ticker", "date", "runtime_s", "llm_calls",
                                       "prompt_tokens", "completion_tokens", "signal")},
                "rating": entry.get("rating", ""),
                "pending": entry.get("pending", ""),
                "raw_return": entry.get("raw") or "",
                "alpha": entry.get("alpha") or "",
                "holding": entry.get("holding") or "",
                "error": rec["error"],
            }
        )

    # A resumed arm (same run_id, more dates) must not lose the cells an earlier
    # process already measured, so merge with whatever cells.csv already holds.
    csv_path = out / "cells.csv"
    merged: dict[tuple[str, str], dict] = {}
    if csv_path.exists():
        with csv_path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                merged[(row["ticker"], row["date"])] = row
    for row in rows:
        merged[(row["ticker"], row["date"])] = {k: ("" if v is None else v) for k, v in row.items()}
    rows = [merged[k] for k in sorted(merged)]

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["ticker"])
        w.writeheader()
        w.writerows(rows)
    (out / "cells.json").write_text(
        json.dumps({"arm": args.arm, "rounds": rounds, "run_id": run_id,
                    "wall_clock_s": round(elapsed, 1), "rows": rows,
                    "raw": CELL_RECORDS}, indent=2),
        encoding="utf-8",
    )

    summary_text = ""
    if Path(result.log_path).exists():
        summary_text = summarize(result).render()
        (out / "summary.txt").write_text(
            f"arm={args.arm} rounds={rounds} model={cfg['quick_think_llm']}\n"
            f"run_id={run_id} wall_clock_s={elapsed:.1f}\n"
            f"llm_calls={COUNTER.calls} prompt_tokens={COUNTER.prompt_tokens} "
            f"completion_tokens={COUNTER.completion_tokens}\n\n{summary_text}\n",
            encoding="utf-8",
        )
    print("\n" + summary_text, flush=True)
    print(f"[{datetime.now():%H:%M:%S}] wall_clock_s={elapsed:.1f} llm_calls={COUNTER.calls} "
          f"tokens_in={COUNTER.prompt_tokens} tokens_out={COUNTER.completion_tokens}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
