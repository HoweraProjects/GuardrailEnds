# Architecture

## High-Level Flow

```text
User Input
   |
   v
[NeMo Input Guard]
   |-- block --> return refusal
   |
   v
[Presidio Input Redaction]
   |
   v
Model / Agent / RAG Inference
   |
   v
[Presidio Output Guard]
   |-- redact/block --> return guarded output
   |
   v
Final Output
```

## Components

- `NemoInputGuard`:
  - Uses NeMo Guardrails `self_check_input` flow
  - Interprets policy response (`Yes`/`No`) to decide intervention
  - Intended for **INPUT** checks

- `PresidioOutputGuard`:
  - Uses Presidio Analyzer + Anonymizer
  - Supports **INPUT** and **OUTPUT** via `source` parameter
  - Includes custom Taiwan-specific recognizers (`TW_NATIONAL_ID`, `TW_MOBILE`, `TW_STUDENT_ID`)

- `GuardrailsTool`:
  - Orchestrates both guards in sequence
  - Exposes a single integration point for agent pipelines

## Response Contract

All guards return a Bedrock-like structure:

- `action`: `"NONE"` or `"GUARDRAIL_INTERVENED"`
- `output`: list with text payload (`[{"text": "..."}]`)
- `assessments`: structured metadata (policy details, detected entities, etc.)

This stable contract makes it easy to swap internals while preserving integration behavior.

## Why This Split?

- Input safety and output privacy are different problems.
- Prompt-injection/off-topic control is better handled by an LLM judge (NeMo policy prompt).
- PII detection/masking is better handled by specialized recognizers (Presidio).
