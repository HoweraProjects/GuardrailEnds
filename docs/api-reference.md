# API Reference

## `GuardrailClient`

Base interface for all guardrail implementations.

```python
apply_guardrail(source: Literal["INPUT", "OUTPUT"], text: str) -> GuardrailResponse
```

## `GuardrailResponse`

Typed dictionary with fields:

- `action`: `"NONE"` or `"GUARDRAIL_INTERVENED"`
- `output`: `list[dict]`, expected shape: `[{"text": "..."}]`
- `assessments`: `list[dict]` with policy metadata

---

## `NemoInputGuard`

```python
NemoInputGuard(config_path: Path = CONFIG_PATH, rails: Optional[Any] = None)
```

### Notes

- `config_path` points to NeMo Guardrails config directory.
- `rails` supports dependency injection for tests (avoids requiring live NeMo runtime).
- For non-`INPUT` source, it returns pass-through (`action="NONE"`).

---

## `PresidioOutputGuard`

```python
PresidioOutputGuard(
    pii_action: Literal["BLOCK", "ANONYMIZE"] = "ANONYMIZE",
    entities: Optional[list] = None,
    language: str = "zh",
    analyzer: Optional[AnalyzerEngine] = None,
    anonymizer: Optional[AnonymizerEngine] = None,
)
```

### Behavior

- Detects entities from `entities` (default includes email/phone/Taiwan IDs).
- If no PII detected: returns `action="NONE"`.
- If PII detected:
  - `BLOCK`: returns a blocked message.
  - `ANONYMIZE`: returns redacted text.

---

## `GuardrailsTool`

Main orchestration class.

### Constructor

```python
GuardrailsTool(
    input_guard: Optional[GuardrailClient] = None,
    output_guard: Optional[GuardrailClient] = None,
)
```

### Methods

- `apply_input(text: str) -> GuardrailResponse`
- `redact_input_pii(text: str) -> GuardrailResponse`
- `apply_output(text: str) -> GuardrailResponse`
- `guard_inference(user_input: str, llm_output: Optional[str] = None) -> GuardrailsIO`

### `GuardrailsIO`

- `blocked_at`: `"INPUT"`, `"OUTPUT"`, or `None`
- `final_output`: what you should return to user
- `effective_input`: sanitized input to send to model
- plus raw responses from each guard stage for observability/debugging
