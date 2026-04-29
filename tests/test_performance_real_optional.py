import os
import time

import pytest

from guardrail_tool.nemo_input_guard import NemoInputGuard
from guardrail_tool.presidio_output_guard import PresidioOutputGuard

RUN_REAL = os.getenv("GUARDRAILS_RUN_REAL_PERF", "0") == "1"


@pytest.mark.skipif(
    not RUN_REAL,
    reason="Set GUARDRAILS_RUN_REAL_PERF=1 to run real (non-stub) performance checks.",
)
def test_real_guardrail_latency_budget():
    nemo_budget_sec = float(os.getenv("GUARDRAILS_REAL_NEMO_MAX_SEC", "12.0"))
    presidio_budget_sec = float(os.getenv("GUARDRAILS_REAL_PRESIDIO_MAX_SEC", "5.0"))

    try:
        nemo = NemoInputGuard()
        presidio = PresidioOutputGuard()
    except Exception as e:
        pytest.skip(f"Runtime unavailable: {e}")

    # Warm-up to avoid counting first-run model downloads/initializations.
    try:
        nemo.apply_guardrail("INPUT", "warmup")
    except Exception:
        pass
    try:
        presidio.apply_guardrail("OUTPUT", "warmup@example.com")
    except Exception:
        pass

    t0 = time.perf_counter()
    try:
        nemo.apply_guardrail("INPUT", "本論文的實驗 F1 是多少？")
    except Exception as e:
        pytest.skip(f"NeMo/Ollama unavailable: {e}")
    nemo_elapsed = time.perf_counter() - t0

    t1 = time.perf_counter()
    try:
        presidio.apply_guardrail("OUTPUT", "Contact me at test.author@example.com")
    except Exception as e:
        pytest.skip(f"Presidio unavailable: {e}")
    presidio_elapsed = time.perf_counter() - t1

    assert nemo_elapsed <= nemo_budget_sec
    assert presidio_elapsed <= presidio_budget_sec
