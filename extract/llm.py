"""Thin LLM dispatch — swap providers with LLM_PROVIDER env var."""

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def call_llm(system: str, user: str) -> str:
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        return _openai(system, user)
    if provider == "anthropic":
        return _anthropic(system, user)
    raise ValueError(f"unknown LLM_PROVIDER: {provider}")


def call_llm_structured(system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Force JSON matching `schema` (JSON Schema object). Returns a parsed dict."""
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        return _openai_structured(system, user, schema)
    if provider == "anthropic":
        return _anthropic_structured(system, user, schema)
    raise ValueError(f"unknown LLM_PROVIDER: {provider}")


def _openai(system: str, user: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def _anthropic(system: str, user: str) -> str:
    from anthropic import Anthropic

    client = Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0.2,
    )
    return resp.content[0].text.strip()


def _openai_structured(system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "extraction",
                "strict": True,
                "schema": schema,
            },
        },
    )
    return json.loads(resp.choices[0].message.content)


def _anthropic_structured(system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    tool_name = "submit_extraction"
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0.0,
        tools=[
            {
                "name": tool_name,
                "description": "Submit the structured extraction result.",
                "input_schema": schema,
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input
    raise RuntimeError("Anthropic did not return a tool_use block for structured output")
