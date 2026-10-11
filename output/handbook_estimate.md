# Handbook Cost Estimate (`gpt-6-luna`)

Scope: the handbook (`data/shop_handbook.md`) as input only. No user question and no output tokens are included.

## 1. Token count

**Handbook size: 10,058 tokens.**

How I counted:
- I read `data/shop_handbook.md` (28,903 characters, 6,127 words) and tokenized it with the `tiktoken` library using the `o200k_base` encoding.
- The tokenizer for `gpt-6-luna` isn't published, so `o200k_base` (OpenAI's current-generation encoding) is a proxy.
- Cross-checks: `cl100k_base` gives 10,184 tokens, and the rule of thumb of about 4 characters per token gives 28,903 / 4 ≈ 7,226. The tokenizer count is the most reliable, so I use it.

## 2. Prices (`data/prices.json`, per 1M tokens)

| Item | Price |
|---|---|
| Input (uncached) | $0.10 |
| Cached input (read) | $0.01 |
| Cache write | $0.125 |

## 3. Without caching

Every call pays the full input price.

- 1 call: 10,058 × $0.10 / 1,000,000 = **$0.0010058**
- 1,000 calls: 1,000 × $0.0010058 = **$1.0058**

## 4. With caching

Assumption: the handbook is the same prefix on every call. Call 1 writes it to the cache. Calls 2–1,000 read it from the cache.

- Cache write (call 1): 10,058 × $0.125 / 1,000,000 = $0.00125725
- Cached read (each later call): 10,058 × $0.01 / 1,000,000 = $0.00010058

| | Cost |
|---|---|
| 1 call, first call (cache write) | **$0.00125725** |
| 1 call, steady state (cache hit) | **$0.00010058** |
| 1,000 calls | $0.00125725 + 999 × $0.00010058 = $0.00125725 + $0.10047942 = **$0.10173667** |

## 5. Comparison

| | 1 call | 1,000 calls |
|---|---|---|
| No cache | $0.0010058 | $1.0058 |
| Cached | $0.00010058 (hit) / $0.00125725 (first write) | $0.10173667 |

For 1,000 calls, caching cuts the handbook cost from $1.0058 to about $0.1017, a saving of about $0.904 (about 90%). The first-call write premium (25% over the normal input price) is paid back on the second call.
