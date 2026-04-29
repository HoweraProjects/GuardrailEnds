# Quickstart

## 1) Go to the sub-repo

```bash
cd /Users/fromkeytoend/PIIPOC/agentic-ai-guardrails-final-project-poc/guardrail_tool
```

## 2) Create/activate a virtual environment

```bash
python3.11 -m venv .venv311
. .venv311/bin/activate
```

## 3) Install package + dev dependencies

```bash
python3 -m pip install -e ".[dev]"
```

## 4) Ensure local Ollama is ready (for real NeMo checks)

```bash
ollama serve
ollama pull qwen2.5:7b
```

The default NeMo config in this project uses:

- endpoint: `http://localhost:11434`
- model: `qwen2.5:7b`

## 5) Minimal usage

```python
from guardrail_tool import GuardrailsTool

guard = GuardrailsTool()

# Input stage
pre = guard.guard_inference(user_input="What is the F1 score?", llm_output=None)
if pre.blocked_at == "INPUT":
    print(pre.final_output)
    raise SystemExit(0)

# Replace this with your own model call
raw_output = "The reported F1 score is 0.801."

# Output stage
post = guard.guard_inference(user_input="What is the F1 score?", llm_output=raw_output)
print(post.final_output)
```

## 5.5) One-command Ollama client integration

If your app already calls Ollama endpoints (`/api/chat` or `/api/generate`), run:

```bash
guardrail-ollama-proxy --listen-port 11435 --upstream http://127.0.0.1:11434
```

Then switch your client base URL from:

- `http://127.0.0.1:11434`

to:

- `http://127.0.0.1:11435`

No application code changes are required beyond base URL update.

## 6) Run tests

```bash
python3 -m pytest -q
```

Optional real performance test:

```bash
GUARDRAILS_RUN_REAL_PERF=1 python3 -m pytest -q tests/test_performance_real_optional.py
```
