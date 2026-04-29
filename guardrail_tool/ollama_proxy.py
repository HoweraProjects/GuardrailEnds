from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import error, request

from .tool import GuardrailsTool


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _jsonl_response(handler: BaseHTTPRequestHandler, payload: dict) -> None:
    line = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/x-ndjson")
    handler.send_header("Content-Length", str(len(line)))
    handler.end_headers()
    handler.wfile.write(line)


def _extract_user_input_chat(body: dict) -> str:
    messages = body.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


def _replace_last_user_message(messages: list, new_content: str) -> list:
    out = list(messages)
    for i in range(len(out) - 1, -1, -1):
        msg = out[i]
        if isinstance(msg, dict) and msg.get("role") == "user":
            replaced = dict(msg)
            replaced["content"] = new_content
            out[i] = replaced
            return out
    return out


def _build_handler(upstream_base: str, guard: GuardrailsTool):
    upstream_base = upstream_base.rstrip("/")

    class OllamaProxyHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path not in ("/api/chat", "/api/generate"):
                _json_response(self, 404, {"error": f"Unsupported path: {self.path}"})
                return

            content_len = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_len)
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                _json_response(self, 400, {"error": "Invalid JSON body"})
                return

            stream = bool(body.get("stream", False))
            if self.path == "/api/chat":
                user_input = _extract_user_input_chat(body)
            else:
                user_input = str(body.get("prompt", ""))

            pre = guard.guard_inference(user_input=user_input, llm_output=None)
            if pre.blocked_at == "INPUT":
                if self.path == "/api/chat":
                    blocked_payload = {
                        "model": body.get("model", ""),
                        "created_at": "",
                        "message": {"role": "assistant", "content": pre.final_output},
                        "done": True,
                        "done_reason": "stop",
                    }
                else:
                    blocked_payload = {
                        "model": body.get("model", ""),
                        "created_at": "",
                        "response": pre.final_output,
                        "done": True,
                        "done_reason": "stop",
                    }
                if stream:
                    _jsonl_response(self, blocked_payload)
                else:
                    _json_response(self, 200, blocked_payload)
                return

            forward_body = dict(body)
            # Keep behavior simple and deterministic: do a non-stream upstream call,
            # then optionally return as single-line NDJSON if client requested stream.
            forward_body["stream"] = False
            if self.path == "/api/chat":
                forward_body["messages"] = _replace_last_user_message(
                    body.get("messages", []), pre.effective_input
                )
            else:
                forward_body["prompt"] = pre.effective_input

            upstream_url = f"{upstream_base}{self.path}"
            req = request.Request(
                upstream_url,
                data=json.dumps(forward_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=300) as resp:
                    resp_data = resp.read()
                    status_code = resp.getcode()
            except error.HTTPError as e:
                body_bytes = e.read()
                try:
                    payload = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    payload = {"error": body_bytes.decode("utf-8", errors="replace")}
                _json_response(self, e.code, payload)
                return
            except Exception as e:
                _json_response(self, 502, {"error": f"Upstream connection failed: {e}"})
                return

            try:
                upstream_payload = json.loads(resp_data.decode("utf-8"))
            except Exception:
                _json_response(
                    self, 502, {"error": "Upstream returned non-JSON response."}
                )
                return

            if self.path == "/api/chat":
                raw_output = str(
                    upstream_payload.get("message", {}).get("content", "")
                )
            else:
                raw_output = str(upstream_payload.get("response", ""))

            post = guard.guard_inference(user_input=user_input, llm_output=raw_output)
            final_output = post.final_output
            if self.path == "/api/chat":
                msg = dict(upstream_payload.get("message", {}))
                msg["content"] = final_output
                upstream_payload["message"] = msg
            else:
                upstream_payload["response"] = final_output

            if stream:
                _jsonl_response(self, upstream_payload)
            else:
                _json_response(self, status_code, upstream_payload)

        def log_message(self, fmt: str, *args: Any) -> None:
            # Keep output clean for CLI UX.
            return

    return OllamaProxyHandler


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="guardrail-ollama-proxy",
        description="Run a local Ollama-compatible proxy with NeMo+Presidio guardrails.",
    )
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=11435)
    parser.add_argument("--upstream", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    guard = GuardrailsTool()
    handler = _build_handler(args.upstream, guard)
    server = ThreadingHTTPServer((args.listen_host, args.listen_port), handler)

    print(
        f"[guardrail-ollama-proxy] listening on http://{args.listen_host}:{args.listen_port}"
    )
    print(f"[guardrail-ollama-proxy] upstream={args.upstream}")
    print(
        "[guardrail-ollama-proxy] point your Ollama client/base_url to this proxy endpoint."
    )
    print("[guardrail-ollama-proxy] Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
