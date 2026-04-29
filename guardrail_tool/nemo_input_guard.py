from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

from .interface import GuardrailClient, GuardrailResponse

CONFIG_PATH = Path(__file__).parent / "nemo_config"


class NemoInputGuard(GuardrailClient):
    def __init__(self, config_path: Path = CONFIG_PATH, rails: Optional[Any] = None):
        self.rails = rails
        if self.rails is None:
            from nemoguardrails import LLMRails, RailsConfig  # type: ignore

            self.rails = LLMRails(RailsConfig.from_path(str(config_path)))

    def apply_guardrail(
        self, source: Literal["INPUT", "OUTPUT"], text: str
    ) -> GuardrailResponse:
        if source != "INPUT":
            return {"action": "NONE", "output": [{"text": text}], "assessments": []}

        result = self.rails.generate(messages=[{"role": "user", "content": text}])
        response_content = (
            result.get("content", "") if isinstance(result, dict) else str(result)
        )
        lowered = response_content.strip().lower()
        answer_is_yes = lowered == "yes" or lowered.startswith("yes")
        answer_is_no = lowered == "no" or lowered.startswith("no")

        triggered_by_history = False
        explain_fn = getattr(self.rails, "explain", None)
        if callable(explain_fn):
            try:
                info = self.rails.explain()
                history = getattr(info, "colang_history", None) or ""
                triggered_by_history = "self check input" in history.lower() or "refuse" in history.lower()
            except Exception:
                triggered_by_history = False

        intervened = triggered_by_history or answer_is_yes or ("sorry" in lowered) or (
            not answer_is_no and "yes" in lowered
        )

        if intervened:
            return {
                "action": "GUARDRAIL_INTERVENED",
                "output": [
                    {
                        "text": "Sorry, the model cannot answer this question. "
                        "It may be off-topic or contain a prompt injection attempt.",
                    }
                ],
                "assessments": [
                    {
                        "inputPolicy": {
                            "triggered_rail": "self_check_input",
                            "nemo_response": response_content[:200],
                        }
                    }
                ],
            }
        return {"action": "NONE", "output": [{"text": text}], "assessments": []}
