"""Read/write NeMo `config.yml` and parse/build `self_check_input` prompt text."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

CONFIG_DIR = Path(__file__).resolve().parent / "nemo_config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yml"

PURPOSE_PREFIX = "You are the safety gatekeeper for this agent: "
ON_TOPIC_HDR = "\n\nValid user input MUST be on-topic. On-topic means:\n"
BLOCK_HDR = "\n\nReject the user input if ANY of the following applies:\n"
EXC_HDR = (
    "\n\nExceptions — always ALLOW these (do not reject for the rules above):\n"
)
USER_LINE = 'User input: "{{ user_input }}"'


def config_path(explicit: Optional[Path] = None) -> Path:
    return explicit if explicit is not None else DEFAULT_CONFIG_PATH


def load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("config.yml must parse to a mapping")
    return data


def extract_connection(data: dict[str, Any]) -> tuple[str, str]:
    models = data.get("models")
    if not models or not isinstance(models, list):
        raise ValueError("config.yml: missing models list")
    main = models[0]
    if not isinstance(main, dict):
        raise ValueError("config.yml: models[0] must be a mapping")
    model = str(main.get("model", "")).strip()
    params = main.get("parameters") or {}
    base_url = str(params.get("base_url", "")).strip()
    return model, base_url


def extract_self_check_content(data: dict[str, Any]) -> str:
    prompts = data.get("prompts")
    if not isinstance(prompts, list):
        return ""
    for p in prompts:
        if isinstance(p, dict) and p.get("task") == "self_check_input":
            c = p.get("content")
            return str(c).strip() if c is not None else ""
    return ""


@dataclass
class ParsedPrompt:
    purpose: str
    on_topic: str
    block_rules: str
    exceptions: str


def parse_self_check_prompt(content: str) -> Optional[ParsedPrompt]:
    """Parse prompt text produced by `build_self_check_prompt` / setup.sh. Returns None if unknown shape."""
    c = content.strip()
    if USER_LINE not in c:
        return None
    head, _, tail = c.partition(USER_LINE)
    head = head.rstrip()
    tail = tail.lstrip()
    if not tail:
        return None
    yes_no = (
        'If the input should be REJECTED, reply with exactly "Yes" and nothing else.'
        in tail
        and 'If the input should be ALLOWED, reply with exactly "No" and nothing else.'
        in tail
    )
    if not yes_no:
        return None

    if not head.startswith(PURPOSE_PREFIX):
        return None
    rest = head[len(PURPOSE_PREFIX) :]
    if ON_TOPIC_HDR not in rest or BLOCK_HDR not in rest:
        return None
    purpose, rest = rest.split(ON_TOPIC_HDR, 1)
    purpose = purpose.strip()
    on_topic, rest = rest.split(BLOCK_HDR, 1)
    on_topic = on_topic.strip()
    if EXC_HDR in rest:
        block_rules, exceptions = rest.split(EXC_HDR, 1)
    else:
        block_rules = rest
        exceptions = ""
    block_rules = block_rules.strip()
    exceptions = exceptions.strip()
    if not purpose or not on_topic:
        return None
    return ParsedPrompt(
        purpose=purpose,
        on_topic=on_topic,
        block_rules=block_rules,
        exceptions=exceptions,
    )


def build_self_check_prompt(
    purpose: str,
    on_topic: str,
    block_rules: str,
    exceptions: str,
) -> str:
    lines = [
        f"{PURPOSE_PREFIX}{purpose.strip()}",
        "",
        "Valid user input MUST be on-topic. On-topic means:",
        on_topic.strip(),
        "",
        "Reject the user input if ANY of the following applies:",
        block_rules.rstrip("\n"),
        "",
    ]
    if exceptions.strip():
        lines.extend(
            [
                "Exceptions — always ALLOW these (do not reject for the rules above):",
                exceptions.strip(),
                "",
            ]
        )
    lines.extend(
        [
            USER_LINE,
            "",
            'If the input should be REJECTED, reply with exactly "Yes" and nothing else.',
            'If the input should be ALLOWED, reply with exactly "No" and nothing else.',
        ]
    )
    return "\n".join(lines)


def render_config_yaml(model: str, base_url: str, prompt_content: str) -> str:
    model_q = json.dumps(model.strip())
    base_q = json.dumps(base_url.strip())
    out: list[str] = []
    out.append("models:")
    out.append("  - type: main")
    out.append("    engine: ollama")
    out.append(f"    model: {model_q}")
    out.append("    parameters:")
    out.append(f"      base_url: {base_q}")
    out.append("")
    out.append("rails:")
    out.append("  input:")
    out.append("    flows:")
    out.append("      - self check input")
    out.append("")
    out.append("prompts:")
    out.append("  - task: self_check_input")
    out.append("    content: |")
    for line in prompt_content.split("\n"):
        out.append("      " + line)
    out.append("")
    out.append("streaming: false")
    out.append("")
    return "\n".join(out)


def backup_config(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    bak = path.with_name(f"{path.name}.bak.{ts}")
    shutil.copy2(path, bak)
    return bak


def save_config(
    path: Path,
    model: str,
    base_url: str,
    prompt_content: str,
    *,
    backup: bool = True,
) -> Optional[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    bak: Optional[Path] = None
    if backup and path.is_file():
        bak = backup_config(path)
    text = render_config_yaml(model, base_url, prompt_content)
    path.write_text(text, encoding="utf-8")
    return bak
