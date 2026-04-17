# Agent Researcher Internals

Pipeline: parallel source fetch (30-item cap per source) -> URL validation -> dedup/freshness filter -> cross-day history filter -> Sonnet prefilter (fast ranking, top 50) -> Opus deep scoring (comedy angles, semantic dedup, 3 retries with exponential backoff) -> Markdown brief + optional Notion delivery. Single `anthropic.Anthropic` client shared across prefilter and scorer.

## Sources (9 total, 3 tiers)

| Source | Tier | Auth | Module |
|--------|------|------|--------|
| Hacker News (Algolia API) | validation | None | `sources/hackernews.py` |
| Lobsters (JSON API) | validation | None | `sources/lobsters.py` |
| RSS (arXiv cs.AI/cs.RO/cs.CE/eess/q-bio, bioRxiv, medRxiv) | context | None | `sources/rss.py` |
| News RSS (BBC, Reuters, Guardian, NPR, AP, Ars Technica) | discovery | None | `sources/news_rss.py` |
| Manifold Markets (prediction markets) | validation | None | `sources/prediction_markets.py` |
| X/Twitter (xAI Grok with `web_search`) | discovery | `XAI_API_KEY` | `sources/xai.py` |
| Reddit (r/LocalLLaMA, r/technology, r/engineering, r/medicine, r/science, r/Futurology, r/worldnews, r/nottheonion, r/news via PRAW) | discovery | `REDDIT_CLIENT_ID` + `SECRET` | `sources/reddit.py` |
| Product Hunt (GraphQL + OAuth) | discovery | `PRODUCT_HUNT_API_KEY` + `SECRET` | `sources/producthunt.py` |
| Bluesky (AT Protocol search) | discovery | `BLUESKY_HANDLE` + `APP_PASSWORD` | `sources/bluesky.py` |

Tier freshness cutoffs: discovery/validation = 24h, context = 48h.

All sources must return items with valid URLs. Items with empty URLs are filtered out at source level and as a safety net in the runner before dedup.

## Key modules

- **Source Protocol** (`sources/base.py`): synchronous `fetch() -> list[RawItem]`. Runner parallelizes via `asyncio.to_thread()`.
- **Dedup** (`dedup.py`): URL normalization + `rapidfuzz` title similarity (threshold 85). Merges multi-source items rather than discarding. Empty URLs are excluded from URL dedup to prevent false collisions. `filter_already_covered()` provides cross-day dedup by scanning previous brief JSON sidecars (7-day lookback) and dropping items that match by normalized URL or fuzzy title.
- **Prefilter** (`prefilter.py`): fast pre-screening via `claude-opus-4-7`. Rates items on comedy/broad appeal/visual potential (single 0-10 score per item), returns top 50 by rank. 2 retries with 3s backoff. Falls back to raw score sorting if API unavailable. Caps input at 200 items. Accepts optional `client` parameter (shared Anthropic client from runner).
- **Scorer** (`scorer.py`): streams to `claude-opus-4-7` with adaptive thinking, 32k max tokens, 50-item cap (fed by prefilter). Accepts optional `client` parameter (shared Anthropic client from runner). Retries up to 3 times with exponential backoff (5s, 10s, 20s) on API or JSON parse failures. Rewrites titles for clarity, generates comedy explanations for every item. Falls back to raw score sorting (with visible warning) if all retries exhausted or API key missing. `comedy_angle` uses enriched three-part format: structural contradiction (what's said vs what's happening), double emotional hit (two contradictory emotions), and one-liner joke seed. This propagates to all downstream script prompts. Five scoring criteria with weighted total: comedy_potential (weight 2.0), cultural_resonance/broad resonance (1.0), freshness (1.0), visual_comedy_potential (1.5), emotional_range (1.0). Weights defined in `SCORE_WEIGHTS` module-level constant. Semantic dedup via `duplicate_of` field: Claude flags items covering the same event, Python code merges sources into the canonical item and drops duplicates before ranking. Detects max_tokens truncation and triggers batch splitting without retrying (retrying the same batch would hit the same limit).
- **xAI source** (`sources/xai.py`): uses `grok-4.20-beta-latest-non-reasoning` with `web_search(allowed_domains=["x.com"])` tool for live X data.
- **Delivery** (`delivery/`): local `.md` file (always) + Notion page (if `NOTION_API_KEY` configured).
- **Alerts** (`alerts.py`): Slack webhook notifications on success/failure. Gated on `SLACK_WEBHOOK_URL`.
- **Scheduler** (`scheduler.py`): APScheduler `CronTrigger` for daily runs. Activated via `--scheduled` flag.
- **Output**: `output/briefs/YYYY-MM-DD.md` + `.json` sidecar + optional Notion page.
