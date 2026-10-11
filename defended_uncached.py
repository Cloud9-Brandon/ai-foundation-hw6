"""Measure the final defended agent with nothing reused from the provider cache (12 practice documents)."""
import json

from agent import OUTPUT_DIR, ROOT, run_agent_detailed
from models import Defenses

rows = []
for doc in sorted((ROOT / "data" / "practice_docs").iterdir()):
    out, calls = run_agent_detailed(doc, use_cache=False, defenses=Defenses.all())
    rows.append({"document": doc.name, "decision": out.decision, "model_calls": len(calls),
                 **{k: sum(c[k] for c in calls) for k in ("input_tokens", "cached_input_tokens", "cache_write_tokens", "output_tokens", "cost_usd")}})
    print(doc.name, rows[-1]["cost_usd"], rows[-1]["cached_input_tokens"], flush=True)
(OUTPUT_DIR / "defended_uncached.json").write_text(json.dumps(rows, indent=2) + "\n")
tot = sum(r["cost_usd"] for r in rows)
print("total", tot, "per doc", tot / 12, "30,000 docs", tot / 12 * 30000, "cached tokens", sum(r["cached_input_tokens"] for r in rows))
