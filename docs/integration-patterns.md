# Integration Patterns

## Pattern A: Wrapper Around Existing Model Call

Use this when you already have a single function that sends prompts to a model.

```python
from guardrail_tool import GuardrailsTool

guard = GuardrailsTool()

def guarded_answer(user_input: str) -> str:
    pre = guard.guard_inference(user_input=user_input, llm_output=None)
    if pre.blocked_at == "INPUT":
        return pre.final_output

    raw_output = call_llm(pre.effective_input)
    post = guard.guard_inference(user_input=user_input, llm_output=raw_output)
    return post.final_output
```

## Pattern B: Agent Toolchain Stage

Use this in multi-step agents:

1. `INPUT` gate before planning/tool selection
2. Redacted prompt to model/tools
3. `OUTPUT` gate before final response

This prevents:
- jailbreak prompts from influencing agent planning
- accidental PII echo from context/tool outputs

## Pattern C: RAG Pipeline

Recommended order:

1. `NeMo INPUT` check
2. `Presidio INPUT` redaction
3. retrieval + generation with redacted query
4. `Presidio OUTPUT` guard before returning answer

## Pattern D: FastAPI Endpoint

```python
@app.post("/chat")
def chat(req: ChatRequest):
    pre = guard.guard_inference(req.user_input, None)
    if pre.blocked_at == "INPUT":
        return {"reply": pre.final_output, "blocked_at": "INPUT"}

    raw = call_llm(pre.effective_input)
    post = guard.guard_inference(req.user_input, raw)

    return {"reply": post.final_output, "blocked_at": post.blocked_at}
```

## Observability Tip

Persist selected fields from `GuardrailsIO`:

- `blocked_at`
- `input_guard_response["action"]`
- `output_guard_response["action"]` (if available)
- timing per stage

This makes debugging false positives and performance regressions much easier.
