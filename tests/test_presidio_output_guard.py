import dataclasses

from guardrail_tool.presidio_output_guard import PresidioOutputGuard


@dataclasses.dataclass
class DummyResult:
    entity_type: str
    start: int
    end: int
    score: float = 0.9


class DummyAnalyzer:
    def __init__(self, results):
        self._results = results
        self.calls = 0

    def analyze(self, text, entities, language):
        self.calls += 1
        return self._results


class DummyAnonymizer:
    def anonymize(self, text, analyzer_results, operators):
        out = text
        for r in sorted(analyzer_results, key=lambda x: x.start, reverse=True):
            op = operators.get(r.entity_type) or operators.get("DEFAULT")
            new_value = (
                getattr(op, "new_value", None)
                or getattr(op, "arguments", {}).get("new_value")
                or getattr(op, "params", {}).get("new_value")
                or getattr(op, "config", {}).get("new_value")
            )
            out = out[: r.start] + new_value + out[r.end :]
        return dataclasses.make_dataclass("Anon", [("text", str)])(out)


def test_presidio_output_guard_no_pii():
    guard = PresidioOutputGuard(analyzer=DummyAnalyzer([]), anonymizer=DummyAnonymizer())
    resp = guard.apply_guardrail("OUTPUT", "hello world")
    assert resp["action"] == "NONE"


def test_presidio_output_guard_anonymize_email():
    text = "Contact: test.author@example.com"
    email = "test.author@example.com"
    start = text.index(email)
    end = start + len(email)
    guard = PresidioOutputGuard(
        analyzer=DummyAnalyzer([DummyResult(entity_type="EMAIL_ADDRESS", start=start, end=end)]),
        anonymizer=DummyAnonymizer(),
    )
    resp = guard.apply_guardrail("INPUT", text)
    assert resp["action"] == "GUARDRAIL_INTERVENED"
    assert "[EMAIL_REDACTED]" in resp["output"][0]["text"]


def test_presidio_output_guard_block():
    guard = PresidioOutputGuard(
        analyzer=DummyAnalyzer([DummyResult(entity_type="EMAIL_ADDRESS", start=0, end=1)]),
        anonymizer=DummyAnonymizer(),
        pii_action="BLOCK",
    )
    resp = guard.apply_guardrail("OUTPUT", "x")
    assert resp["action"] == "GUARDRAIL_INTERVENED"


def test_presidio_output_guard_cache_reuses_previous_analysis():
    analyzer = DummyAnalyzer([DummyResult(entity_type="EMAIL_ADDRESS", start=0, end=1)])
    guard = PresidioOutputGuard(analyzer=analyzer, anonymizer=DummyAnonymizer(), quick_skip_chars=0)
    guard.apply_guardrail("OUTPUT", "x")
    guard.apply_guardrail("OUTPUT", "x")
    assert analyzer.calls == 1


def test_presidio_output_guard_quick_skip_short_safe_text():
    analyzer = DummyAnalyzer([DummyResult(entity_type="EMAIL_ADDRESS", start=0, end=1)])
    guard = PresidioOutputGuard(analyzer=analyzer, anonymizer=DummyAnonymizer(), quick_skip_chars=120)
    resp = guard.apply_guardrail("OUTPUT", "safe short sentence")
    assert resp["action"] == "NONE"
    assert analyzer.calls == 0
