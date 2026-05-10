from __future__ import annotations

import os
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Literal, Optional

from .interface import GuardrailClient, GuardrailResponse

CONFIG_PATH = Path(__file__).parent / "nemo_config"
DEFAULT_BLOCK_MESSAGE = (
    "Sorry, the model cannot answer this question. "
    "It may be off-topic or contain a prompt injection attempt."
)
_SAFE_PATTERN = re.compile(r"^[\w\s\.,;:!?\-()'\"/]+$", re.UNICODE)


class NemoInputGuard(GuardrailClient):
    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        rails: Optional[Any] = None,
        cache_size: Optional[int] = None,
        quick_allow_chars: Optional[int] = None,
    ):
        self.rails = rails
        self.cache_size = cache_size if cache_size is not None else int(os.getenv("GUARDRAILS_NEMO_CACHE_SIZE", "512"))
        self.quick_allow_chars = (
            quick_allow_chars
            if quick_allow_chars is not None
            else int(os.getenv("GUARDRAILS_NEMO_QUICK_ALLOW_CHARS", "40"))
        )
        self._cache: OrderedDict[str, GuardrailResponse] = OrderedDict()
        if self.rails is None:
            from nemoguardrails import LLMRails, RailsConfig  # type: ignore

            self.rails = LLMRails(RailsConfig.from_path(str(config_path)))

    def _cache_get(self, key: str) -> Optional[GuardrailResponse]:
        cached = self._cache.get(key)
        if cached is None:
            return None
        self._cache.move_to_end(key)
        return cached

    def _cache_set(self, key: str, value: GuardrailResponse) -> None:
        if self.cache_size <= 0:
            return
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def _quick_allow(self, text: str) -> bool:
        # Fast-path: short, plain-language queries are usually safe and do not
        # need an expensive LLM guard pass.
        return len(text) <= self.quick_allow_chars and bool(_SAFE_PATTERN.match(text))

    def apply_guardrail(
        self, source: Literal["INPUT", "OUTPUT"], text: str
    ) -> GuardrailResponse:
        if source != "INPUT":
            return {"action": "NONE", "output": [{"text": text}], "assessments": []}

        if self._quick_allow(text):
            return {"action": "NONE", "output": [{"text": text}], "assessments": []}

        cache_key = text.strip()
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

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
            response = {
                "action": "GUARDRAIL_INTERVENED",
                "output": [
                    {
                        "text": DEFAULT_BLOCK_MESSAGE,
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
            self._cache_set(cache_key, response)
            return response

        response = {"action": "NONE", "output": [{"text": text}], "assessments": []}
        self._cache_set(cache_key, response)
        return response
