# Guardrail Tool Documentation

This documentation explains how to use the `guardrail_tool` package as a standalone safety layer for AI applications.

## Contents

- [Quickstart](./quickstart.md)
- [Architecture](./architecture.md)
- [API Reference](./api-reference.md)
- [Integration Patterns](./integration-patterns.md)
- [Testing and Performance](./testing-and-performance.md)
- [Troubleshooting](./troubleshooting.md)

## What This Library Does

`guardrail_tool` provides a practical dual-gate guardrail design:

1. **Input Gate (NeMo):**
   - Blocks prompt injection / jailbreak attempts
   - Blocks off-topic requests based on the configured policy prompt

2. **PII Protection (Presidio):**
   - Optionally redacts PII from user input before model/retrieval
   - Redacts or blocks PII in model output as a final safety net

## Design Goals

- Keep integration simple for agent and RAG pipelines
- Preserve a stable response schema (`GuardrailResponse`)
- Offer unit-testable behavior without requiring live LLM runtime
- Support optional real-runtime performance checks
