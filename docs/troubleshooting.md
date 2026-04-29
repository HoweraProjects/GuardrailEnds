# Troubleshooting

## `file or directory not found: tests/...`

You are likely in the wrong directory.

Use:

```bash
cd /Users/fromkeytoend/PIIPOC/agentic-ai-guardrails-final-project-poc/guardrail_tool
python3 -m pytest -q tests/test_performance_real_optional.py
```

## `zsh: command not found: guardrail-bench`

The package entrypoint is not installed in the current venv.

```bash
cd /Users/fromkeytoend/PIIPOC/agentic-ai-guardrails-final-project-poc/guardrail_tool
. .venv311/bin/activate
python3 -m pip install -e ".[dev]"
```

Then retry:

```bash
guardrail-bench --runs 3
```

Fallback (without entrypoint):

```bash
python3 -m guardrail_tool.cli --runs 3
```

## NeMo/Ollama errors

### `model ... not found`

Pull the configured model:

```bash
ollama pull qwen2.5:7b
```

### endpoint errors (`404`, connection failure)

- Ensure server is running: `ollama serve`
- Verify endpoint:

```bash
curl -sS http://localhost:11434/api/tags
```

## Too many warnings from dependencies

These are mostly upstream deprecation warnings (NeMo/LangChain/Pydantic).
They do not necessarily mean your test failed.

Hide warnings for cleaner output:

```bash
python3 -m pytest -q -W ignore tests/test_performance_real_optional.py
```

## Slow first run

First run may download spaCy models and initialize runtime caches.
Run once to warm up, then measure again.
