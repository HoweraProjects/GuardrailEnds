# Guardrail Tool / Library

Standalone guardrail library/tool extracted from the project.

Detailed documentation is available in [`docs/`](./docs/README.md).

Includes:
- `NemoInputGuard` for prompt-injection / off-topic input checks
- `PresidioOutputGuard` for PII detection + anonymization/blocking
- `GuardrailsTool` orchestration helper for agent integration

## NeMo Setup (Local Ollama)

Default model is `qwen2.5:7b` in `guardrail_tool/nemo_config/config.yml`.

```bash
ollama serve
ollama pull qwen2.5:7b
curl -sS http://localhost:11434/api/tags
curl -sS http://localhost:11434/api/chat -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"reply with No"}],"stream":false}'
```

## Performance Targets (Pragmatic)

- NeMo input guard: <= 12s/request
- Presidio guard: <= 5s/request

## Run Tests

```bash
python3 -m pytest
```

Optional real perf test:

```bash
GUARDRAILS_RUN_REAL_PERF=1 python3 -m pytest tests/test_performance_real_optional.py
```

## Benchmark CLI (ASCII + colors)

```bash
guardrail-bench --runs 5
guardrail-bench --real --runs 3
```

## One-Command Ollama Integration (Client-Side)

Run a local proxy that sits in front of your existing Ollama and applies guardrails automatically:

```bash
guardrail-ollama-proxy --listen-port 11435 --upstream http://127.0.0.1:11434
```

Then point your client to:

- Base URL: `http://127.0.0.1:11435`

Supported endpoints:
- `/api/chat`
- `/api/generate`

Notes:
- The proxy enforces NeMo input checks + Presidio input/output protections.
- For compatibility, streaming requests are handled as single final NDJSON event (not token-by-token passthrough).
