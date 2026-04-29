from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .interface import GuardrailClient, GuardrailResponse
from .nemo_input_guard import NemoInputGuard
from .presidio_output_guard import PresidioOutputGuard


@dataclass
class GuardrailsIO:
    blocked_at: Optional[Literal["INPUT", "OUTPUT"]]
    final_output: str
    effective_input: str
    input_guard_response: GuardrailResponse
    pii_redaction_response: GuardrailResponse
    output_guard_response: Optional[GuardrailResponse] = None


class GuardrailsTool:
    def __init__(
        self,
        input_guard: Optional[GuardrailClient] = None,
        output_guard: Optional[GuardrailClient] = None,
    ):
        self.input_guard = input_guard or NemoInputGuard()
        self.output_guard = output_guard or PresidioOutputGuard()

    def apply_input(self, text: str) -> GuardrailResponse:
        return self.input_guard.apply_guardrail("INPUT", text)

    def redact_input_pii(self, text: str) -> GuardrailResponse:
        return self.output_guard.apply_guardrail("INPUT", text)

    def apply_output(self, text: str) -> GuardrailResponse:
        return self.output_guard.apply_guardrail("OUTPUT", text)

    def guard_inference(self, user_input: str, llm_output: Optional[str] = None) -> GuardrailsIO:
        input_guard_response = self.apply_input(user_input)
        if input_guard_response["action"] == "GUARDRAIL_INTERVENED":
            return GuardrailsIO(
                blocked_at="INPUT",
                final_output=input_guard_response["output"][0]["text"],
                effective_input=user_input,
                input_guard_response=input_guard_response,
                pii_redaction_response={"action": "NONE", "output": [{"text": user_input}], "assessments": []},
                output_guard_response=None,
            )

        pii_redaction_response = self.redact_input_pii(user_input)
        effective_input = (
            pii_redaction_response["output"][0]["text"]
            if pii_redaction_response["action"] == "GUARDRAIL_INTERVENED"
            else user_input
        )
        if llm_output is None:
            return GuardrailsIO(
                blocked_at=None,
                final_output="",
                effective_input=effective_input,
                input_guard_response=input_guard_response,
                pii_redaction_response=pii_redaction_response,
                output_guard_response=None,
            )

        output_guard_response = self.apply_output(llm_output)
        if output_guard_response["action"] == "GUARDRAIL_INTERVENED":
            return GuardrailsIO(
                blocked_at="OUTPUT",
                final_output=output_guard_response["output"][0]["text"],
                effective_input=effective_input,
                input_guard_response=input_guard_response,
                pii_redaction_response=pii_redaction_response,
                output_guard_response=output_guard_response,
            )

        return GuardrailsIO(
            blocked_at=None,
            final_output=llm_output,
            effective_input=effective_input,
            input_guard_response=input_guard_response,
            pii_redaction_response=pii_redaction_response,
            output_guard_response=output_guard_response,
        )
