from __future__ import annotations

import argparse
import os
import statistics
import time
from typing import Callable, List

from .nemo_input_guard import NemoInputGuard
from .presidio_output_guard import PresidioOutputGuard


class C:
    """ANSI palette aligned with `settings_tui` (slate + cyan + indigo accents)."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    # Foreground
    SLATE = "\033[38;5;252m"
    MUTED = "\033[38;5;245m"
    CYAN = "\033[38;5;117m"  # ~#7dd3fc
    SKY = "\033[38;5;81m"  # brighter cyan
    INDIGO = "\033[38;5;147m"  # ~lavender labels
    BLUE = "\033[38;5;75m"
    GREEN = "\033[38;5;114m"
    YELLOW = "\033[38;5;221m"
    RED = "\033[38;5;203m"
    MAGENTA = "\033[38;5;213m"


ASCII_BANNER = r"""
   _____                     _           _ _   ______            _
  / ____|                   | |         (_) | |  ____|          | |
 | |  __ _   _  __ _ _ __ __| |_ __ __ _ _| | | |__   _ __   __| |__
 | | |_ | | | |/ _` | '__/ _` | '__/ _` | | | |  __| | '_ \ / _` / __|
 | |__| | |_| | (_| | | | (_| | | | (_| | | | | |____| | | | (_| \__ \
  \_____|\__,_|\__,_|_|  \__,_|_|  \__,_|_|_| |______|_| |_|\__,_|___/
"""


def _supports_color() -> bool:
    return os.getenv("TERM", "dumb") != "dumb"


def _paint(text: str, *styles: str) -> str:
    if not _supports_color():
        return text
    return "".join(styles) + text + C.RESET


def _latency_stats(samples: List[float]) -> tuple[float, float, float]:
    avg = statistics.mean(samples) if samples else 0.0
    p95 = sorted(samples)[max(0, int(len(samples) * 0.95) - 1)] if samples else 0.0
    mx = max(samples) if samples else 0.0
    return avg, p95, mx


def _run_bench(label: str, fn: Callable[[], None], runs: int) -> dict:
    latencies_ms: List[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    avg, p95, mx = _latency_stats(latencies_ms)
    return {"label": label, "avg_ms": avg, "p95_ms": p95, "max_ms": mx, "samples": latencies_ms}


def _sparkline(samples: List[float]) -> str:
    if not samples:
        return ""
    ticks = "▁▂▃▄▅▆▇█"
    low = min(samples)
    high = max(samples)
    if high - low < 1e-9:
        return ticks[0] * len(samples)
    out = []
    for x in samples:
        idx = int((x - low) / (high - low) * (len(ticks) - 1))
        out.append(ticks[idx])
    return "".join(out)


def _status_badge(ms: float) -> str:
    if ms <= 400:
        return _paint("FAST", C.GREEN, C.BOLD)
    if ms <= 1200:
        return _paint("OK", C.YELLOW, C.BOLD)
    return _paint("SLOW", C.RED, C.BOLD)


def _rule(width: int, heavy: bool = False) -> str:
    ch = "━" if heavy else "─"
    line = ch * width
    return _paint(line, C.MUTED, C.DIM)


def _subtitle_line(mode: str, runs: int) -> str:
    left = _paint("guardrail-bench", C.INDIGO, C.BOLD)
    meta = _paint(
        f"  ·  mode={mode}  ·  runs={runs}  ·  latency in ms",
        C.MUTED,
        C.DIM,
    )
    return left + meta


def main() -> None:
    parser = argparse.ArgumentParser(prog="guardrail-bench")
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    mode = "real" if args.real else "stub"
    print(_paint(ASCII_BANNER, C.SKY, C.BOLD))
    print(_paint("Guardrail studio · benchmark", C.CYAN, C.BOLD))
    print(_subtitle_line(mode, args.runs))

    if args.real:
        try:
            nemo = NemoInputGuard()
            presidio = PresidioOutputGuard()
            nemo_result = _run_bench(
                "NeMo INPUT",
                lambda: nemo.apply_guardrail("INPUT", "本論文的實驗 F1 是多少？"),
                args.runs,
            )
            presidio_result = _run_bench(
                "Presidio OUTPUT",
                lambda: presidio.apply_guardrail("OUTPUT", "Contact me at test.author@example.com"),
                args.runs,
            )
        except Exception as e:
            print(_paint(f"✖ benchmark failed: {e}", C.RED, C.BOLD))
            raise SystemExit(1)
    else:
        class _DummyRails:
            def generate(self, messages):
                return {"content": "No"}

        class _DummyAnalyzer:
            def analyze(self, text, entities, language):
                return []

        class _DummyAnonymizer:
            def anonymize(self, text, analyzer_results, operators):
                return type("Anon", (), {"text": text})()

        nemo = NemoInputGuard(rails=_DummyRails())
        presidio = PresidioOutputGuard(analyzer=_DummyAnalyzer(), anonymizer=_DummyAnonymizer())
        nemo_result = _run_bench("NeMo INPUT (stub)", lambda: nemo.apply_guardrail("INPUT", "safe"), args.runs)
        presidio_result = _run_bench(
            "Presidio OUTPUT (stub)", lambda: presidio.apply_guardrail("OUTPUT", "safe"), args.runs
        )

    header = f"{'Guardrail':<24} {'avg(ms)':>10} {'p95(ms)':>10} {'max(ms)':>10}  {'status':<8}  trend"
    print(_rule(88, heavy=True))
    print(_paint(header, C.SLATE, C.BOLD))
    print(_rule(88))

    for result in (nemo_result, presidio_result):
        trend = _sparkline(result["samples"])
        label = _paint(f"{result['label']:<22}", C.SLATE)
        mark = _paint("✓", C.GREEN, C.BOLD)
        nums = f"{result['avg_ms']:>10.1f} {result['p95_ms']:>10.1f} {result['max_ms']:>10.1f}  "
        badge = _status_badge(result["p95_ms"])
        spark = _paint(trend, C.SKY)
        row = f"{mark} {label} {nums}{badge}  {spark}"
        print(row)

    print(_rule(88, heavy=True))
    print(
        _paint("Done. ", C.MUTED)
        + _paint("Stay safe, ship fast.", C.CYAN, C.BOLD)
        + _paint("  ·  try ", C.MUTED, C.DIM)
        + _paint("guardrail-tui", C.INDIGO, C.BOLD)
        + _paint(" for config.", C.MUTED, C.DIM)
    )


if __name__ == "__main__":
    main()
