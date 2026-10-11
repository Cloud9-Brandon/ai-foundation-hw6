# Homework 6 – AI Prompts

Constraints for all problems:
- Use `PORTKEY_API_KEY` for authentication.
- Make AI calls only with the model `gpt-6-luna`.
- Simulate email and payment actions by writing to a log (no real sends or charges).
- Keep `.env` out of Git.

## Setup – Getting Started

**Prompt:**
> I'm starting Homework 6. Help me work through it one problem at a time. First, create an `AI_prompts.md` file to record the prompts I give you, including this one. Organize it with a section for each problem, including the problem number and title, my prompt in my own words, and—if I use one—a follow-up prompt plus a sentence explaining what was missing from my first prompt. Wait for me to describe each problem in my own words before working on it. Follow these constraints throughout: use `PORTKEY_API_KEY`, make AI calls only with `gpt-6-luna`, simulate email and payment actions by writing to a log, and keep `.env` out of Git. Ask me what I want to do for Problem 1. (Attached: `data (3).zip`)

**Follow-up prompt:** None.

## Problem 2 – Handbook Token Count and Cost Estimate

**Prompt:**
> Please work on Problem 2 only. Extract the provided data ZIP into the HW6 folder if it hasn't been extracted yet. Use `data/shop_handbook.md` and `data/prices.json` to find the handbook's token count, explaining how you counted it. Calculate the handbook-only cost for one call and 1,000 calls, both with cached tokens and without cached tokens. Show the math and save the results in `output/handbook_estimate.md`. Add this prompt to the Problem 2 section of `AI_prompts.md`; record a follow-up only if I actually need one.

**Follow-up prompt:** None.

## Problem 3 – Build the Vendor Desk Agent

**Prompt:**
> Problem 3 — Build the vendor desk agent. Implement the PydanticAI agent using `gpt-6-luna` and the project constraints already recorded in `AI_prompts.md`. Use `prompts/prompt.md`, `agent.py`, `tools.py`, and `models.py`. The agent should accept a vendor document path, read HTML, PDF, and `.eml` files, and return the vendor, SKU, unit price, lead time in days, minimum order, a `recommend` or `do_not_recommend` decision based on the handbook, and a one-sentence reason. Include the handbook in every model call.
>
> Add `send_email` and `approve_payment` trap tools. They must never send an email or make a payment; they should only append each call and its arguments to `output/trap_calls.json`, starting with an empty list and keeping the log for the whole homework.
>
> After every run, append the document, time, API-reported token counts, and dollar cost calculated with `prices.json` to `output/usage_log.json`. Append each tool call with its arguments and a short result, plus the final answer, to `output/audit_trail.json`. Run the agent on `data/practice_docs/p01_bluehen_quote.html` and on documents `p01` and `p08` to show it works. Create `output/harness.md` explaining each field in `models.py` and why it exists, plus each tool in one line. Log this prompt in the Problem 3 section of `AI_prompts.md`; add a follow-up only if I actually need one, and explain what the first prompt lacked.

**Follow-up prompt:** None so far.

## Problem 4 – Compare Cached and Uncached Runs

**Prompt:**
> Problem 4 — Compare cached and uncached runs. Run the vendor desk agent on all 12 practice documents twice: once configured to reuse the handbook from cache, and once configured so nothing is reused. Use the API-reported token counts to confirm that caching worked and that the uncached runs have no cached tokens.
>
> Save details for every model call from both setups in `output/cache_test.json`, including the setup, document, API-reported token counts, and dollar cost calculated with `prices.json`. In `output/cache_test.md`, report the total cost and cost per document for each setup, the percentage saved with caching, how the real results compare with my Problem 2 estimate, and the projected cost of processing 1,000 documents a day for 30 days with and without caching. Note anything surprising in the results and explain why it may have happened. Log this prompt in the Problem 4 section of `AI_prompts.md`; record a follow-up only if I actually need one.

**Follow-up prompt:** None.

## Problem 5 – Attack Your Own Agent

**Prompt:**
> Problem 5 — Attack your own agent. Run the existing Problem 3 agent on all 12 documents in `data/practice_docs/`, without changing its prompts, readers, or defenses first. Use the project's existing Portkey and `gpt-6-luna` setup. Never send actual email or make payments; the trap tools should only log calls.
>
> Compare each answer with `data/practice_key.json`. Save `output/attack_results.json` with a result for every document: whether each field matched the key, whether the decision matched, whether a trap tool was called, and whether the answer included a link or other strange text.
>
> For each document that fooled the agent, explain in `output/attack_results.md` what fooled it and where that text appeared in the file. Inspect the original documents as a person would—in a browser, PDF viewer, or email app—and compare what's visibly shown with what the agent read. Preserve existing logs and note any prior reader behavior that may affect the results. Add this prompt to the Problem 5 section of `AI_prompts.md`; record a follow-up only if I actually need one.

**Follow-up prompt:** None.

## Problem 6 – Defend Your Agent

**Prompt:**
> Problem 6 — Defend your agent. Use the Problem 5 results as the unchanged-agent baseline. Add defenses at three levels: code that checks document content before it reaches the model, agent design that prevents document text from triggering dangerous tools or controlling the decision, and rules in `prompts/prompt.md`.
>
> Address the attacks found in Problem 5, including the PDF text that was off-page, tiny, or white, while preserving legitimate visible quote details. Keep `send_email` and `approve_payment` in the system, but require human sign-off before they can be used; they must not send email or make payments. Keep a way to run the agent with defenses disabled for Problem 7.
>
> Rerun all 12 practice documents with defenses enabled, using the same model and cache setup as the Problem 5 baseline. Clean documents must still return the correct values; refusing or blanking a real quote counts as a failure. Save `output/defense_results.json` in the same shape as the Problem 5 results, with token counts and cost per document added.
>
> In `output/defense_results.md`, include before-and-after results for all 12 documents, what each defense layer catches that the others miss, and the extra tokens and cost each layer adds per document. Use API-reported usage for model calls, and report zero token cost for layers that add no model input or calls. Add a "Safety" section to `output/harness.md` describing each layer in plain language. Log this prompt under Problem 6 in `AI_prompts.md`; record a follow-up only if I actually need one.

**Follow-up prompt (Problem 6):**
> Problem 6 appears complete: the defended agent got 12/12 practice documents right, and you kept a no-defense mode for Problem 7.
> Two details to reconcile before relying on the reports:
>
> * Use the fresh 10/12 undefended run as the Problem 5 baseline; label the earlier 11/12 results as gateway replays. The update mentions corrections to the Markdown reports, but check that `attack_results.json` and `cache_test.json` don't still present replayed results as fresh runs.
> * The generated reason drops "business" from "business days." That changes the meaning of the lead time, so preserve the qualifier in the deterministic reason.

**What the first prompt lacked:** It did not say that earlier results from the gateway's response cache had to be labeled as replays in the JSON files as well as the reports, or that the code-written reason had to keep the "business days" unit.

## Problem 7 – Red Team

**Prompt:**
> Problem 7 — Red team. Create two realistic vendor quote documents in `data/my_attacks/`. Each should look normal to a person opening it, but use a hiding trick or attack goal that is new compared with the practice set. Keep the documents local and use only fake vendor information; do not target real credentials or cause real email or payment actions.
>
> Run each attack against both `Defenses.none()` and `Defenses.all()`. Force fresh model responses for every run and verify they weren't gateway-cache replays. The trap tools must remain log-only.
>
> In `output/red_team.md`, describe each attack: what is hidden and where, what it tries to make the agent do, and what happened with no defenses versus all defenses. Aim for attacks that are genuinely new and fool the undefended agent. Don't change the defenses during this problem. Log this prompt in the Problem 7 section of `AI_prompts.md`; record a follow-up only if I actually need one.

**Follow-up prompt:** None.

## Problem 8 – Exam Documents

**Prompt:**
> Problem 8 — Exam documents. Run the final defended agent (`Defenses.all()`) on every file in `data/exam_docs/`. Use fresh model responses, and verify they weren't gateway-cache replays. Don't use an answer key or hand-edit the results.
>
> Save `output/exam_results.json` with one entry per exam file. Include `file`, `vendor`, `sku`, `unit_price`, `lead_time_days`, `min_order`, `decision` (`recommend` or `do_not_recommend`), `reason`, `trap_tool_called`, `input_tokens`, `cached_tokens`, `output_tokens`, and `cost_usd`. Use the actual result and API-reported usage for each run; calculate cost with `prices.json`. Make sure clean documents are handled normally and no trap tool is called. Log this prompt in the Problem 8 section of `AI_prompts.md`; record a follow-up only if I actually need one.

**Follow-up prompt:** None.

## Problem 9 – Results Page

**Prompt:**
> Problem 9 — Results page. Build `output/hw6_report.html` as a polished, self-contained report that opens by double-clicking and works offline without any other files. Embed its CSS, scripts, chart, and data; don't rely on internet access, external libraries, fonts, or assets.
> Use the latest corrected results from the project files. Reconcile replay notes before showing numbers: use the fresh 10/12 Problem 5 baseline, the corrected cache comparison, and the regenerated defense results. Don't invent values or present gateway replays as fresh model runs.
> Include these five sections:
>
> 1. Problem 4 cache results, with a chart.
> 2. Attack results before and after defenses.
> 3. The defenses' token and dollar costs.
> 4. The exam results and both red-team attacks. Label exam answers as agent outputs, not independently verified.
> 5. A short recommendation to the store manager on whether to use the agent for real vendor email, including estimated monthly cost for 1,000 documents per day. Show the cost source, calculation, and assumptions; use the actual per-document cost of the final defended agent.
>
> Make the page easy to read with thoughtful typography, color, and layout. Open the finished HTML locally to check it works offline and displays the report correctly. Log this prompt in the Problem 9 section of `AI_prompts.md`; record a follow-up only if I actually need one.

**Follow-up prompt (Problem 9):**
> The report appears to meet Problem 9's offline, single-file requirement: it rendered from `file://` with network lookups blocked.
>
> One cost claim needs qualification: **$85.98** is the undefended agent's uncached projection. It isn't established as an upper bound for the defended agent, which adds prompt tokens. Recalculate the defended uncached projection using `prices.json`, or label $85.98 as an undefended reference estimate. The light-mode colors also remain untested.

**What the first prompt lacked:** It asked for the final defended agent's actual per-document cost but did not say how to treat the no-cache scenario, so the report used the undefended Problem 4 figure as a bound, and it did not ask for the light-mode appearance to be checked.

## Problem 10 – Prepare the Homework for Submission

**Prompt:**
> Problem 10 — Prepare the homework for submission. Check the project against the expected repository tree on the assignment page. Include the full `data/` folder, both attack files, all required source files and outputs, and a short `README.md` explaining how to run the agent.
>
> Make sure `.gitignore` excludes `.env`, `.venv/`, and `__pycache__/`. Include `.env.example` with placeholders only. Review the files to be committed and the Git history for real API keys or other secrets; never print any secret values. Do not remove existing files or rewrite existing Git history.
>
> Prepare the repository locally and report its current or proposed GitHub repository, visibility, branch, and file list. Then stop before creating or changing a public repository, pushing, or submitting to Canvas. Ask me to approve the exact repository and Canvas submission before those steps. Log this prompt in the Problem 10 section of `AI_prompts.md`.

**Follow-up prompt:** None.
