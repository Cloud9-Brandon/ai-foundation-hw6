# Homework 6: Campus Customs vendor desk agent

A PydanticAI agent that reads a vendor quote (`.html`, `.pdf`, or `.eml`), extracts the vendor, SKU, unit price, lead time, and minimum order, and returns `recommend` or `do_not_recommend` under the purchasing rules in `data/shop_handbook.md`. All model calls use `gpt-6-luna` through Portkey. The handbook is sent with every call.

**Safety:** `send_email` and `approve_payment` are trap tools. They never send email or make payments; they only log requests to `output/trap_calls.json`. With defenses on, requests are marked `blocked_pending_human_signoff`.

## Run the agent

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your own PORTKEY_API_KEY in .env
python agent.py data/practice_docs/p01_bluehen_quote.html
```

`python agent.py <file> [<file> ...]` prints the structured result as JSON and appends to `output/usage_log.json` and `output/audit_trail.json`. The three defense layers are on by default. In code, `run_agent(path, defenses=Defenses.none())` turns them all off (`from models import Defenses`).

## Layout

| Path | What it is |
|---|---|
| `agent.py`, `tools.py`, `models.py`, `prompts/prompt.md` | The agent, its tools, its data models, and its prompt |
| `defenses.py`, `prompts/prompt_baseline.md` | Defense layers and the undefended prompt |
| `data/` | Handbook, prices, practice and exam documents, practice key, and `my_attacks/` (my two red-team files) |
| `output/` | Results, logs, and reports (`hw6_report.html` opens offline) |
| `tests/` | Attack builder, synthetic attacks, offline defense checks |
| `*_test.py`, `red_team.py`, `exam_run.py`, `defended_uncached.py` | Scripts that produced the results |
| `make_report.py`, `make_defense_report.py` | Rebuild the HTML report and the defense report from the JSON |
| `AI_prompts.md` | The prompts I gave the AI assistant, by problem |

## Reproduce results

```bash
python cache_test.py        # Problem 4: cached vs uncached
python attack_test.py       # Problem 5: undefended baseline
python defense_test.py      # Problem 6: defenses and ablations
python red_team.py 5        # Problem 7: my two attacks
python exam_run.py          # Problem 8: exam documents
python make_report.py       # Problem 9: output/hw6_report.html
```

These scripts make real model calls and need `PORTKEY_API_KEY`. The agent sends `x-portkey-cache-force-refresh: true` so the gateway never replays a stored answer.

## Notes

- `.env` holds the API key and is not committed. `.env.example` has placeholders only.
- `output/audit_trail.json` and `output/usage_log.json` include local file paths and `gateway_replay` flags for runs the gateway replayed before the refresh header was added.
- Exam answers in `output/exam_results.json` are agent outputs and were not independently verified.
