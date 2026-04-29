from typing import Literal

from guardrail_tool.tool import GuardrailsTool


class DummyGuard:
    def __init__(self, fn):
        self.fn = fn

    def apply_guardrail(self, source: Literal["INPUT", "OUTPUT"], text: str):
        return self.fn(source, text)


def test_guardrails_tool_blocks_at_input():
    input_guard = DummyGuard(
        lambda source, text: {
            "action": "GUARDRAIL_INTERVENED",
            "output": [{"text": "blocked at input"}],
            "assessments": [],
        }
    )
    output_guard = DummyGuard(
        lambda source, text: {"action": "NONE", "output": [{"text": text}], "assessments": []}
    )
    tool = GuardrailsTool(input_guard=input_guard, output_guard=output_guard)
    res = tool.guard_inference(user_input="off-topic", llm_output="x")
    assert res.blocked_at == "INPUT"


def test_guardrails_tool_blocks_at_output():
    input_guard = DummyGuard(
        lambda source, text: {"action": "NONE", "output": [{"text": text}], "assessments": []}
    )

    def out_fn(source, text):
        if source == "INPUT":
            return {"action": "NONE", "output": [{"text": text}], "assessments": []}
        return {"action": "GUARDRAIL_INTERVENED", "output": [{"text": "blocked"}], "assessments": []}

    tool = GuardrailsTool(input_guard=input_guard, output_guard=DummyGuard(out_fn))
    res = tool.guard_inference(user_input="safe", llm_output="sensitive")
    assert res.blocked_at == "OUTPUT"
