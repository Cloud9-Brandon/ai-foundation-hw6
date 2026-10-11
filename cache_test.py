"""Problem 4: run all 12 practice documents with and without prompt caching."""
import json
from pathlib import Path

from models import Defenses
from agent import OUTPUT_DIR, ROOT, run_agent_detailed
from tools import now_iso

DOCS = sorted((ROOT / "data" / "practice_docs").iterdir())
KEY = {r["file"]: r for r in json.loads((ROOT / "data" / "practice_key.json").read_text())}
FIELDS = ("vendor", "sku", "unit_price", "lead_time_days", "min_order", "decision")

records = []
for setup, use_cache in (("cached", True), ("uncached", False)):
    for doc in DOCS:
        output, calls = run_agent_detailed(doc, use_cache=use_cache, defenses=Defenses.none())
        key = KEY[doc.name]
        match = all(getattr(output, f) == key[f] for f in FIELDS)
        print(setup, doc.name, output.decision, "key-match" if match else "KEY MISMATCH", flush=True)
        for i, call in enumerate(calls, 1):
            records.append(
                {"setup": setup, "document": doc.name, "call": i, "time": now_iso(), **call,
                 "matches_key": match}
            )
(OUTPUT_DIR / "cache_test.json").write_text(json.dumps(records, indent=2) + "\n")
