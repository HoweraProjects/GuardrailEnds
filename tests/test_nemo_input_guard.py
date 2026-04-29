from guardrail_tool.nemo_input_guard import NemoInputGuard


class DummyRails:
    def __init__(self, content: str):
        self._content = content

    def generate(self, messages):
        return {"content": self._content}


def test_nemo_input_guard_blocks_on_yes():
    guard = NemoInputGuard(rails=DummyRails("Yes"))
    resp = guard.apply_guardrail("INPUT", "今天台北天氣如何？")
    assert resp["action"] == "GUARDRAIL_INTERVENED"


def test_nemo_input_guard_allows_on_no():
    guard = NemoInputGuard(rails=DummyRails("No"))
    resp = guard.apply_guardrail("INPUT", "本論文的實驗 F1 是多少？")
    assert resp["action"] == "NONE"


def test_nemo_input_guard_pass_through_on_output_source():
    guard = NemoInputGuard(rails=DummyRails("Yes"))
    resp = guard.apply_guardrail("OUTPUT", "some generated text")
    assert resp["action"] == "NONE"
