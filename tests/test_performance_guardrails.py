import os
import time

from guardrail_tool.nemo_input_guard import NemoInputGuard
from guardrail_tool.presidio_output_guard import PresidioOutputGuard


class DummyRails:
    def generate(self, messages):
        return {"content": "No"}


class DummyAnalyzer:
    def analyze(self, text, entities, language):
        return []


class DummyAnonymizer:
    def anonymize(self, text, analyzer_results, operators):
        return type("Anon", (), {"text": text})()


def test_guardrails_stubs_are_fast():
    max_sec = float(os.getenv("GUARDRAILS_PERF_MAX_SEC", "2.0"))
    n = int(os.getenv("GUARDRAILS_PERF_ITERS", "1000"))

    nemo = NemoInputGuard(rails=DummyRails())
    presidio = PresidioOutputGuard(analyzer=DummyAnalyzer(), anonymizer=DummyAnonymizer())

    t0 = time.perf_counter()
    for _ in range(n):
        nemo.apply_guardrail("INPUT", "safe query")
    for _ in range(n):
        presidio.apply_guardrail("OUTPUT", "safe output")
    elapsed = time.perf_counter() - t0
    assert elapsed < max_sec
