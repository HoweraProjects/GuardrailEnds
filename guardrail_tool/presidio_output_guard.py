from __future__ import annotations

from typing import Literal, Optional

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from .interface import GuardrailClient, GuardrailResponse

TW_NATIONAL_ID = PatternRecognizer(
    supported_entity="TW_NATIONAL_ID",
    name="TW National ID",
    patterns=[Pattern(name="tw_id", regex=r"\b[A-Z][12]\d{8}\b", score=0.95)],
    supported_language="zh",
)
TW_MOBILE = PatternRecognizer(
    supported_entity="TW_MOBILE",
    name="TW Mobile",
    patterns=[Pattern(name="tw_mobile", regex=r"09\d{2}[- ]?\d{3}[- ]?\d{3}", score=0.9)],
    supported_language="zh",
)
TW_STUDENT_ID = PatternRecognizer(
    supported_entity="TW_STUDENT_ID",
    name="TW Student ID",
    patterns=[Pattern(name="tw_sid", regex=r"\b1\d{8}\b", score=0.85)],
    supported_language="zh",
)

DEFAULT_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "TW_NATIONAL_ID",
    "TW_MOBILE",
    "TW_STUDENT_ID",
]


def _build_analyzer() -> AnalyzerEngine:
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": "zh", "model_name": "zh_core_web_lg"},
            {"lang_code": "en", "model_name": "en_core_web_sm"},
        ],
    }
    try:
        provider = NlpEngineProvider(nlp_configuration=nlp_config)
        nlp_engine = provider.create_engine()
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["zh", "en"])
    except Exception:
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "zh", "model_name": "zh_core_web_lg"}],
            }
        )
        analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["zh"])
    for r in (TW_NATIONAL_ID, TW_MOBILE, TW_STUDENT_ID):
        analyzer.registry.add_recognizer(r)
    return analyzer


class PresidioOutputGuard(GuardrailClient):
    def __init__(
        self,
        pii_action: Literal["BLOCK", "ANONYMIZE"] = "ANONYMIZE",
        entities: Optional[list] = None,
        language: str = "zh",
        analyzer: Optional[AnalyzerEngine] = None,
        anonymizer: Optional[AnonymizerEngine] = None,
    ):
        self.analyzer = analyzer
        self.anonymizer = anonymizer
        self.pii_action = pii_action
        self.entities = entities or DEFAULT_ENTITIES
        self.language = language

    def _ensure_initialized(self) -> None:
        if self.analyzer is None:
            self.analyzer = _build_analyzer()
        if self.anonymizer is None:
            self.anonymizer = AnonymizerEngine()

    def apply_guardrail(
        self, source: Literal["INPUT", "OUTPUT"], text: str
    ) -> GuardrailResponse:
        self._ensure_initialized()
        results = self.analyzer.analyze(text=text, entities=self.entities, language=self.language)
        if not results:
            return {"action": "NONE", "output": [{"text": text}], "assessments": []}

        if self.pii_action == "BLOCK":
            output_text = "Sorry, the response contains sensitive information and was blocked."
        else:
            operators = {
                "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE_REDACTED]"}),
                "TW_NATIONAL_ID": OperatorConfig("replace", {"new_value": "[TW_NATIONAL_ID_REDACTED]"}),
                "TW_MOBILE": OperatorConfig("replace", {"new_value": "[TW_MOBILE_REDACTED]"}),
                "TW_STUDENT_ID": OperatorConfig("replace", {"new_value": "[TW_STUDENT_ID_REDACTED]"}),
            }
            anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)
            output_text = anonymized.text

        assessment = {
            "sensitiveInformationPolicy": {
                "source": source,
                "piiEntities": [
                    {
                        "type": r.entity_type,
                        "match": text[r.start : r.end],
                        "score": r.score,
                        "action": self.pii_action,
                    }
                    for r in results
                ],
            }
        }
        return {"action": "GUARDRAIL_INTERVENED", "output": [{"text": output_text}], "assessments": [assessment]}
