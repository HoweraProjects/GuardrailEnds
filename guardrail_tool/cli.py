from __future__ import annotations

import argparse
import os
import statistics
import time
from typing import Callable, List

from .nemo_input_guard import NemoInputGuard
from .presidio_output_guard import PresidioOutputGuard


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="guardrail-bench")
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    mode = "real" if args.real else "stub"
    print(_paint(ASCII_BANNER, C.MAGENTA, C.BOLD))
    print(_paint("Guardrail Performance Benchmark", C.CYAN, C.BOLD))
    print(
        _paint(
            f"mode={mode} | runs={args.runs} | renderer=ascii+ansi",
            C.BLUE,
            C.DIM,
        )
    )
    print(_paint("─" * 88, C.DIM))

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
            print(_paint(f"✖ Benchmark failed: {e}", C.RED, C.BOLD))
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
    print(_paint(header, C.BOLD))
    print(_paint("─" * len(header), C.DIM))

    for result in (nemo_result, presidio_result):
        trend = _sparkline(result["samples"])
        print(
            f"{_paint('✓', C.GREEN, C.BOLD)} "
            f"{result['label']:<22} "
            f"{result['avg_ms']:>10.1f} "
            f"{result['p95_ms']:>10.1f} "
            f"{result['max_ms']:>10.1f}  "
            f"{_status_badge(result['p95_ms']):<8}  "
            f"{_paint(trend, C.CYAN)}"
        )

    print(_paint("─" * len(header), C.DIM))
    print(_paint("Done. Stay safe, ship fast.", C.CYAN, C.BOLD))


if __name__ == "__main__":
    main()
