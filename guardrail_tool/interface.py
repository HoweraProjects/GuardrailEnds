from abc import ABC, abstractmethod
from typing import List, Literal, TypedDict


class GuardrailAssessment(TypedDict, total=False):
    topicPolicy: dict
    contentPolicy: dict
    sensitiveInformationPolicy: dict
    wordPolicy: dict
    contextualGroundingPolicy: dict


class GuardrailResponse(TypedDict):
    action: Literal["GUARDRAIL_INTERVENED", "NONE"]
    output: List[dict]
    assessments: List[GuardrailAssessment]


class GuardrailClient(ABC):
    @abstractmethod
    def apply_guardrail(
        self,
        source: Literal["INPUT", "OUTPUT"],
        text: str,
    ) -> GuardrailResponse:
        raise NotImplementedError
