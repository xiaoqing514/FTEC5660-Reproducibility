"""Join the two arms into one comparison table.

    .venv\\Scripts\\python.exe repro\\compare_arms.py

Writes results/comparison.csv and prints the per-cell and aggregate contrast:
decision quality (rating, realised return, alpha) and efficiency (runtime, LLM
calls, tokens).
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


def pct(text: str) -> float | None:
    """Parse a log percentage such as '+1.4%' into 0.014."""
    if not text:
        return None
    try:
        return float(str(text).strip().rstrip("%")) / 100
    except ValueError:
        return None


def num(text: str) -> float | None:
    if text is None or text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load(arm: str) -> dict[tuple[str, str], dict]:
    path = RESULTS / arm / "cells.csv"
    if not path.exists():
        raise SystemExit(f"missing {path}, so run that arm first")
    with path.open(encoding="utf-8-sig") as f:
        return {(r["ticker"], r["date"]): r for r in csv.DictReader(f)}


def fmt(x: float | None, spec: str = "+.2%") -> str:
    return format(x, spec) if x is not None else "n/a"


def main() -> int:
    base, mod = load("baseline"), load("modified")
    cells = sorted(set(base) | set(mod))
    rows = []
    for cell in cells:
        b, m = base.get(cell, {}), mod.get(cell, {})
        ab, am = pct(b.get("alpha", "")), pct(m.get("alpha", ""))
        rb, rm = pct(b.get("raw_return", "")), pct(m.get("raw_return", ""))
        rows.append(
            {
                "ticker": cell[0],
                "date": cell[1],
                "rating_baseline": b.get("rating", ""),
                "rating_modified": m.get("rating", ""),
                "raw_return_baseline": b.get("raw_return", ""),
                "raw_return_modified": m.get("raw_return", ""),
                "alpha_baseline": b.get("alpha", ""),
                "alpha_modified": m.get("alpha", ""),
                "alpha_delta": fmt(am - ab) if (ab is not None and am is not None) else "",
                "runtime_s_baseline": b.get("runtime_s", ""),
                "runtime_s_modified": m.get("runtime_s", ""),
                "llm_calls_baseline": b.get("llm_calls", ""),
                "llm_calls_modified": m.get("llm_calls", ""),
                "tokens_in_baseline": b.get("prompt_tokens", ""),
                "tokens_in_modified": m.get("prompt_tokens", ""),
                "tokens_out_baseline": b.get("completion_tokens", ""),
                "tokens_out_modified": m.get("completion_tokens", ""),
                "rating_agrees": ("yes" if b.get("rating") == m.get("rating") else "no")
                if b.get("rating") and m.get("rating") else "",
            }
        )

    out = RESULTS / "comparison.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def agg(arm_rows: list[dict], arm: str, key: str) -> float | None:
        vals = [num(r[f"{key}_{arm}"]) for r in arm_rows]
        vals = [v for v in vals if v is not None]
        return statistics.mean(vals) if vals else None

    alphas_b = [pct(r["alpha_baseline"]) for r in rows]
    alphas_m = [pct(r["alpha_modified"]) for r in rows]
    alphas_b = [a for a in alphas_b if a is not None]
    alphas_m = [a for a in alphas_m if a is not None]

    print(f"{'cell':<22}{'rating b/m':<16}{'alpha b':>9}{'alpha m':>9}"
          f"{'run b':>8}{'run m':>8}{'calls b':>8}{'calls m':>8}")
    for r in rows:
        print(f"{r['ticker'] + ' ' + r['date']:<22}"
              f"{(r['rating_baseline'] + '/' + r['rating_modified']):<16}"
              f"{r['alpha_baseline']:>9}{r['alpha_modified']:>9}"
              f"{r['runtime_s_baseline']:>8}{r['runtime_s_modified']:>8}"
              f"{r['llm_calls_baseline']:>8}{r['llm_calls_modified']:>8}")

    print("\n--- aggregates ---")
    for label, vals in (("mean alpha baseline", alphas_b), ("mean alpha modified", alphas_m)):
        print(f"{label:<24}{statistics.mean(vals):+.2%}  (n={len(vals)})" if vals else f"{label:<24}n/a")
    if alphas_b and alphas_m:
        print(f"{'mean alpha delta':<24}{statistics.mean(alphas_m) - statistics.mean(alphas_b):+.2%}")
    if len(alphas_b) > 1 and len(alphas_m) > 1:
        print(f"{'sd alpha baseline':<24}{statistics.stdev(alphas_b):.2%}")
        print(f"{'sd alpha modified':<24}{statistics.stdev(alphas_m):.2%}")
    for key, label in (("runtime_s", "mean runtime (s)"), ("llm_calls", "mean LLM calls")):
        b, m = agg(rows, "baseline", key), agg(rows, "modified", key)
        if b is not None and m is not None:
            print(f"{label:<24}{b:8.1f} -> {m:8.1f}  ({(m - b) / b:+.1%})")
    for key in ("tokens_in", "tokens_out"):
        b, m = agg(rows, "baseline", key), agg(rows, "modified", key)
        if b is not None and m is not None:
            print(f"{key:<24}{b:8.0f} -> {m:8.0f}  ({(m - b) / b:+.1%})")
    agree = sum(1 for r in rows if r["rating_agrees"] == "yes")
    print(f"{'rating agreement':<24}{agree}/{len(rows)} cells")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
