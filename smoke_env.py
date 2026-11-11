"""Environment smoke test: package import, config overrides, Yahoo data access.

Runs without any LLM API key. Usage:
    .venv\\Scripts\\python.exe repro\\smoke_env.py
"""

from __future__ import annotations

import os
import sys
import traceback


def section(name: str) -> None:
    print(f"\n=== {name} ===", flush=True)


def main() -> int:
    section("python / package")
    print(sys.version)
    import tradingagents
    from tradingagents.default_config import DEFAULT_CONFIG, build_default_config

    print("tradingagents version:", getattr(tradingagents, "__version__", "?"))
    print("package file:", tradingagents.__file__)

    section("config")
    cfg = build_default_config()
    for k in ("llm_provider", "deep_think_llm", "quick_think_llm",
              "max_debate_rounds", "max_risk_discuss_rounds", "holding_period_days",
              "benchmark_ticker", "data_vendors"):
        print(f"{k} = {cfg.get(k)!r}")
    print("DEFAULT max_debate_rounds:", DEFAULT_CONFIG["max_debate_rounds"])

    section("env keys seen")
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "FRED_API_KEY", "SEC_EDGAR_USER_AGENT"):
        v = os.environ.get(k)
        print(f"{k}: {'set' if v else 'unset'}" + (f" (len {len(v)})" if v else ""))

    section("yfinance ohlcv")
    try:
        import yfinance as yf
        df = yf.download("AAPL", start="2026-09-25", end="2026-11-11", progress=False, auto_adjust=False)
        print("rows:", len(df))
        print(df.tail(3).to_string())
    except Exception:
        traceback.print_exc()
        return 1

    section("dataflows router (get_stock_data)")
    try:
        from tradingagents.dataflows.router import route_to_vendor
        out = route_to_vendor("get_stock_data", "AAPL", "2026-10-01", "2026-10-31")
        print(str(out)[:600])
    except Exception:
        traceback.print_exc()
        return 1

    section("graph construction (no LLM calls)")
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        print("TradingAgentsGraph importable:", bool(TradingAgentsGraph))
    except Exception:
        traceback.print_exc()
        return 1

    print("\nSMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
