# Testing and Performance

## Test Strategy

The project uses two layers of tests:

1. **Unit/stub tests (default)**
   - deterministic
   - fast
   - do not require live Ollama/NeMo runtime

2. **Optional real performance test**
   - requires local runtime readiness
   - gated by `GUARDRAILS_RUN_REAL_PERF=1`

## Run All Default Tests

```bash
python3 -m pytest -q
```

## Run Real Performance Test

```bash
GUARDRAILS_RUN_REAL_PERF=1 python3 -m pytest -q tests/test_performance_real_optional.py
```

## Performance Budgets (Defaults)

- `GUARDRAILS_REAL_NEMO_MAX_SEC` default: `12.0`
- `GUARDRAILS_REAL_PRESIDIO_MAX_SEC` default: `5.0`

Set custom budgets:

```bash
GUARDRAILS_RUN_REAL_PERF=1 \
GUARDRAILS_REAL_NEMO_MAX_SEC=15 \
GUARDRAILS_REAL_PRESIDIO_MAX_SEC=8 \
python3 -m pytest -q tests/test_performance_real_optional.py
```

## Why Warm-up Matters

First-run latency can include:
- model loading
- spaCy model initialization/download
- runtime cache misses

The real test includes a warm-up phase before timing to avoid false failures.

## Benchmark CLI

Stub mode:

```bash
guardrail-bench --runs 5
```

Real mode:

```bash
guardrail-bench --real --runs 3
```
