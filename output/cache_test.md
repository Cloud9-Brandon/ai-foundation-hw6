# Cached vs. Uncached Runs (Problem 4)

All 12 practice documents were run twice with `cache_test.py`. Each run made 2 model calls: one to call `read_document`, and one to return the answer. That gives 24 calls per setup and 48 in total. Every call is in `output/cache_test.json` with its setup, document, API-reported token counts, and dollar cost from `data/prices.json`.

- **Cached setup:** identical instructions and handbook on every call, plus a fixed `prompt_cache_key`.
- **Uncached setup:** a fresh random "Request id" line at the very top of the instructions on every call. No prefix ever matches an earlier request, so nothing can be reused.

Cost per call = (input − cached − cache-write) × $0.10 + cached × $0.01 + cache-write × $0.125 + output × $0.50, all per 1M tokens.

## Did caching work? (API-reported tokens)

| | Input tokens | Cached input tokens | Cache-write tokens | Output tokens |
|---|---|---|---|---|
| Cached setup | 265,432 | **249,373 (94.0%)** | 13,035 | 2,603 |
| Uncached setup | 266,080 | **0** | 263,056 | 2,417 |

- **Caching worked.** In the cached setup, the first call wrote the 10,856-token prefix to the cache. The other 47 calls read 10,826–10,859 cached tokens each.
- **The uncached setup has zero cached tokens on all 24 calls**, as intended.

## Cost

| Document | Cached | Uncached |
|---|---|---|
| p01_bluehen_quote.html | $0.00162039 | $0.00287257 |
| p02_elmcity_quote.html | $0.00036566 | $0.00284907 |
| p03_ivyprint_catalog.html | $0.00035116 | $0.00286495 |
| p04_harborstitch_quote.html | $0.00036931 | $0.00286157 |
| p05_maplemills_quote.pdf | $0.00036979 | $0.00285082 |
| p06_qtextile_quote.pdf | $0.00037029 | $0.00285532 |
| p07_longwharf_quote.pdf | $0.00042166 | $0.00291157 |
| p08_chapelst_email.eml | $0.00035779 | $0.00286807 |
| p09_westville_email.eml | $0.00036529 | $0.00286119 |
| p10_eastrock_email.eml | $0.00038217 | $0.00287045 |
| p11_yorkst_quote.html | $0.00037504 | $0.00285220 |
| p12_bluehen_quote.pdf | $0.00037852 | $0.00287507 |
| **Total (12 docs)** | **$0.00572707** | **$0.03439285** |
| **Average per document** | **$0.00047726** | **$0.00286607** |

**Savings with caching: 1 − 0.00572707 / 0.03439285 = 83.3%.**

The cached average includes p01, which paid the one-time cache write ($0.00162). The other 11 documents average $0.00037333, which is about 87% below the uncached average.

## Comparison with the Problem 2 estimate

Problem 2 estimated the handbook only (10,058 tokens, 1 call): $0.0010058 without caching and $0.00010058 with a cache hit.

| Per model call | Problem 2 estimate | Real (average of 24 calls) |
|---|---|---|
| Uncached | $0.0010058 | $0.001433 (+42%) |
| Cached (hit) | $0.00010058 | $0.000239 (about $0.000187 excluding p01's cache write) |

- **Handbook portion matches.** A cache hit on about 10,857 tokens costs 10,857 × $0.01 / 1M = $0.000109, close to the estimate of $0.000101.
- **Real costs are higher** because each call carries more than the handbook: the prompt, tool definitions, the document, and tool results, about 11,000 input tokens per call versus 10,058. Calls also produce output at $0.50 per 1M. And each document takes **2 calls**, so per-document cost is about double the per-call figure.
- **Uncached is 42% above the estimate** mostly because of the cache-write charge (see "Surprises", item 1).
- **Percentage saved:** the estimate predicted about 90% (1,000 calls: $1.0058 vs. $0.1017). The real saving is 83.3%, or 87% in steady state. It's a bit lower because output tokens and the small uncached part of each prompt cost the same either way.

## Projection: 1,000 documents a day for 30 days

That is 30,000 documents, or 60,000 model calls.

| Scenario | Per day (1,000 docs) | 30 days (30,000 docs) |
|---|---|---|
| Without caching (as measured, writes billed at $0.125) | $2.87 | **$85.98** |
| Without caching (all input at plain $0.10 rate) | $2.32 | $69.54 |
| With caching (as measured, incl. one cache write) | $0.48 | **$14.32** |
| With caching (steady state, excluding the first-document write) | $0.37 | $11.20 |
| *Problem 2 estimate, handbook only, 60,000 calls* | *$2.01 uncached / $0.20 cached* | *$60.35 uncached / $6.10 cached* |

The projection assumes the cache stays warm. At 1,000 documents a day, requests arrive far more often than a typical cache expires, so I'd expect a hit on nearly every call. The cached figures use the 12-document averages. A larger run would show the true steady-state number.

## Surprises, and why they may have happened

1. **"Uncached" calls still report cache writes.**
   - Almost all input tokens (263,056 of 266,080) show up as cache-write tokens, which `prices.json` bills at $0.125 per 1M, a 25% premium over the $0.10 plain input price.
   - So the uncached setup cost 24% more than all-plain input would have ($0.0344 vs. $0.0278).
   - The random request id stops reuse but not writing. The provider or gateway apparently writes any long prefix to its cache automatically, and I found no way to turn that off.
   - If your real "no caching" baseline is plain input pricing, the saving is 79.4% instead of 83.3%.
2. **Cached reads were 94%, not about 98%.** About 150 tokens of each call-2 prompt (the document and tool result) can't be a cache hit because they differ per document, and the cache works in blocks, so cached reads came in at 10,826–10,859 tokens instead of the full prefix.
3. **Each document costs two calls.** The tool-calling loop re-sends the whole handbook for the second call. That doubles the cost, but it also means call 2 gets a cache hit even on the very first document.
4. **Answers differ from `practice_key.json` on 3 of 24 runs, which caching doesn't explain.**
   - **p12 (both setups):** the agent returned a price of $17.44, so it recommended the quote. The key says $27.72 and `do_not_recommend`. The PDF prints $27.72, then adds a line saying a revised price of $17.44 replaces it. The agent used the revised price.
   - **p07 (uncached only):** the agent returned a 7-day lead time and `recommend`. The key says 35 days and `do_not_recommend`. The PDF prints 35 business days, then adds a "correction" that it is now 7. The cached run reported 35 and declined, so the model is not fully consistent from run to run on these documents.
   - Both are vendor-added notes that change a number after the quote. They make the agent accept a vendor's own revision, which the key treats as wrong. Tightening `prompts/prompt.md` would likely fix this, but I haven't changed it, so that this test measures the agent as built.
5. **No trap calls.** `output/trap_calls.json` is still `[]` after all 48 calls.

## Note added during Problem 6: gateway replays

The Portkey gateway has its own response cache, and it replays stored answers (with the old usage numbers) for identical requests. The cached-setup rows for p01 and p08 in `cache_test.json` (4 rows) repeated Problem 3's requests, so their usage is a replay of Problem 3's runs. They are marked `gateway_replay: true`. The other 44 rows are real calls: the uncached rows carry a unique request id, and the other cached rows were new requests.

Excluding p01 and p08 from both setups changes the result only slightly: cached $0.000375 vs. uncached $0.002865 per document, a saving of **86.9%** (vs. 83.3% for all 12 documents). The overall 83.3% still includes the replayed p01 row, which holds the one-time cache write.

## Housekeeping

- Both setups also appended to `output/usage_log.json` and `output/audit_trail.json` (24 new entries each). The usage entries now include a `setup` field.
