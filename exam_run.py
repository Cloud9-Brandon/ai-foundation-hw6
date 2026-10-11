"""Problem 8: run the final defended agent (Defenses.all()) on every file in data/exam_docs/.

No answer key is used and results are written exactly as the agent returns them.
Each response's x-portkey-cache-status header is recorded to show no answer was a gateway replay.
"""
import json

import agent as A
from models import Defenses

OUT = A.OUTPUT_DIR
TRAPS = OUT / "trap_calls.json"
statuses: list[str] = []
_build = A.build_model


def build_with_header_capture():
    model = _build()

    async def record(response):
        statuses.append(response.headers.get("x-portkey-cache-status", "none"))

    model._provider.client._client.event_hooks["response"].append(record)
    return model


A.build_model = build_with_header_capture
results, checks = [], []
for doc in sorted((A.ROOT / "data" / "exam_docs").iterdir()):
    statuses.clear()
    before = len(json.loads(TRAPS.read_text()))
    out, calls = A.run_agent_detailed(doc, defenses=Defenses.all())
    traps = json.loads(TRAPS.read_text())[before:]
    results.append({
        "file": doc.name,
        "vendor": out.vendor,
        "sku": out.sku,
        "unit_price": out.unit_price,
        "lead_time_days": out.lead_time_days,
        "min_order": out.min_order,
        "decision": out.decision,
        "reason": out.reason,
        "trap_tool_called": bool(traps),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "cached_tokens": sum(c["cached_input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "cost_usd": round(sum(c["cost_usd"] for c in calls), 8),
    })
    checks.append({"file": doc.name, "model_calls": len(calls), "cache_status_per_call": list(statuses),
                   "all_calls_fresh": bool(statuses) and len(statuses) == len(calls) and all(s == "REFRESH" for s in statuses),
                   "trap_calls": traps})
    print(doc.name, out.decision, statuses, flush=True)
(OUT / "exam_results.json").write_text(json.dumps(results, indent=2) + "\n")
(OUT / "exam_run_check.json").write_text(json.dumps(checks, indent=2) + "\n")
