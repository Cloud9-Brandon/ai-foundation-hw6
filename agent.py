"""Vendor desk agent: reads a vendor document and recommends or declines it per the handbook.

Usage: python agent.py <document> [<document> ...]
Needs PORTKEY_API_KEY in the environment or in .env (never committed).
"""
import json
import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from defenses import Rules, enforce
from models import Defenses, VendorDeskDeps, VendorDeskResult
from tools import append_json, approve_payment, now_iso, read_document, send_email

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

MODEL_NAME = "gpt-6-luna"  # the only model this project may call
PORTKEY_BASE_URL = os.environ.get("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
OUTPUT_DIR = Path(os.environ.get("VENDOR_DESK_OUTPUT_DIR", ROOT / "output"))
HANDBOOK = (ROOT / "data" / "shop_handbook.md").read_text()
PROMPT = (ROOT / "prompts" / "prompt.md").read_text()  # layer 3 on
PROMPT_BASELINE = (ROOT / "prompts" / "prompt_baseline.md").read_text()  # layer 3 off (Problem 5 prompt)
RULES = Rules(HANDBOOK)
PRICES = json.loads((ROOT / "data" / "prices.json").read_text())[MODEL_NAME]


def build_model() -> OpenAIResponsesModel:
    headers = {
        "x-portkey-api-key": os.environ["PORTKEY_API_KEY"],
        # Portkey replays stored answers (and their old usage numbers) for identical requests.
        # Force a real model call every time so results and token counts are fresh.
        "x-portkey-cache-force-refresh": "true",
    }
    # Optional Portkey routing, if your Portkey setup needs it.
    if os.environ.get("PORTKEY_PROVIDER"):
        headers["x-portkey-provider"] = os.environ["PORTKEY_PROVIDER"]
    if os.environ.get("PORTKEY_VIRTUAL_KEY"):
        headers["x-portkey-virtual-key"] = os.environ["PORTKEY_VIRTUAL_KEY"]
    client = AsyncOpenAI(base_url=PORTKEY_BASE_URL, api_key="portkey", default_headers=headers)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


CACHE_KEY = "vendor-desk-handbook-v1"


def instructions(ctx: RunContext[VendorDeskDeps]) -> str:
    """Instructions plus the full handbook; re-sent on every model request of a run.

    With caching on, the text is identical on every request so the provider can reuse it.
    With caching off, a fresh random line comes first on every request, so no prefix
    matches an earlier request and nothing can be reused.
    """
    prompt = PROMPT if ctx.deps.defenses.prompt_rules else PROMPT_BASELINE
    text = f"{prompt}\n\n# Shop handbook\n\n{ctx.deps.handbook}"
    if ctx.deps.use_cache:
        return text
    return f"Request id: {uuid.uuid4()}\n\n{text}"


def make_agent(model=None, use_cache: bool = True) -> Agent[VendorDeskDeps, VendorDeskResult]:
    # The prompt cache key groups requests that share a prefix; omitted when caching is off.
    settings = OpenAIResponsesModelSettings(openai_prompt_cache_key=CACHE_KEY) if use_cache else None
    return Agent(
        model or build_model(),
        deps_type=VendorDeskDeps,
        output_type=VendorDeskResult,
        instructions=instructions,
        tools=[read_document, send_email, approve_payment],
        model_settings=settings,
    )


def cost_usd(usage) -> float:
    """Dollar cost from API-reported token counts and prices.json (per 1M tokens)."""
    cached = usage.cache_read_tokens
    written = usage.cache_write_tokens
    fresh = usage.input_tokens - cached - written
    return (
        fresh * PRICES["input_per_1m"]
        + cached * PRICES["cached_input_per_1m"]
        + written * PRICES["cache_write_per_1m"]
        + usage.output_tokens * PRICES["output_per_1m"]
    ) / 1_000_000


def tool_events(messages) -> list[dict]:
    """Pair each tool call with a short version of its result."""
    results = {}
    for m in messages:
        if isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart):
                    results[p.tool_call_id] = str(p.content)
    events = []
    for m in messages:
        if isinstance(m, ModelResponse):
            for p in m.parts:
                if isinstance(p, ToolCallPart):
                    result = results.get(p.tool_call_id, "")
                    events.append(
                        {
                            "tool": p.tool_name,
                            "arguments": p.args_as_dict(),
                            "result": result if len(result) <= 200 else result[:200] + "...",
                        }
                    )
    return events


def call_details(messages) -> list[dict]:
    """API-reported token counts and dollar cost for each model call in a run."""
    calls = []
    for m in messages:
        if isinstance(m, ModelResponse):
            u = m.usage
            calls.append(
                {
                    "input_tokens": u.input_tokens,
                    "cached_input_tokens": u.cache_read_tokens,
                    "cache_write_tokens": u.cache_write_tokens,
                    "output_tokens": u.output_tokens,
                    "cost_usd": round(cost_usd(u), 8),
                }
            )
    return calls


def run_agent(document, agent=None, output_dir: Path = OUTPUT_DIR, use_cache: bool = True,
              defenses: Defenses | None = None) -> VendorDeskResult:
    return run_agent_detailed(document, agent, output_dir, use_cache, defenses)[0]


def run_agent_detailed(
    document, agent=None, output_dir: Path = OUTPUT_DIR, use_cache: bool = True,
    defenses: Defenses | None = None,
) -> tuple[VendorDeskResult, list[dict]]:
    """Run one document. `defenses` defaults to all layers on; pass Defenses.none() for the baseline."""
    defenses = defenses or Defenses.all()
    doc = Path(document).expanduser().resolve()
    agent = agent or make_agent(use_cache=use_cache)
    deps = VendorDeskDeps(
        handbook=HANDBOOK, document_path=doc, output_dir=output_dir, use_cache=use_cache,
        defenses=defenses,
    )
    result = agent.run_sync(f"Process this vendor document: {doc}", deps=deps)
    usage = result.usage
    stamp = now_iso()
    final = result.output
    events = list(deps.scan_events)
    if defenses.agent_design:
        final, design_events = enforce(final, deps.seen_text or "", RULES)
        events += design_events
    append_json(
        output_dir / "usage_log.json",
        {
            "document": str(doc),
            "time": stamp,
            "model": MODEL_NAME,
            "setup": "cached" if use_cache else "uncached",
            "defenses": defenses.label(),
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "cached_input_tokens": usage.cache_read_tokens,
            "cache_write_tokens": usage.cache_write_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": round(cost_usd(usage), 8),
        },
    )
    append_json(
        output_dir / "audit_trail.json",
        {
            "document": str(doc),
            "time": stamp,
            "tool_calls": tool_events(result.all_messages()),
            "model_answer": result.output.model_dump(),
            "defense_events": events,
            "final_answer": final.model_dump(),
        },
    )
    deps.scan_events = events  # lets callers report what the defenses did
    return final, call_details(result.all_messages())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python agent.py <document> [<document> ...]")
    for path in sys.argv[1:]:
        print(f"== {path}")
        print(run_agent(path).model_dump_json(indent=2))
