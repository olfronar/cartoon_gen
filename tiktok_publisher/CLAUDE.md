# TikTok Publisher Internals

Pipeline: OAuth authentication (one-time) -> find per-script videos (prefer captioned) -> read script JSON for title -> chunked file upload via TikTok inbox API (drafts to creator inbox, user publishes manually) -> poll until sent to inbox. No LLM calls. Uses stdlib `urllib.request` + `http.server` (no extra dependencies).

## Pipeline stages

- **Auth** (`auth.py`): TikTok OAuth 2.0 authorization code flow with PKCE. Starts a cloudflared tunnel to expose a local HTTP server with an HTTPS URL (TikTok requires non-localhost redirect URIs). User registers the tunnel URL in TikTok Developer portal, then authorizes in browser. Callback is handled automatically. Tokens saved to `output/tiktok_tokens.json`. Auto-refreshes expired access tokens (24h lifetime). Refresh tokens rotate on each use (365-day lifetime).
- **Video finder** (`pipeline/video_finder.py`): Thin wrapper around `find_script_videos()` from `shared/utils.py` with `prefer_captioned=True`. Prefers `script_video_captioned.mp4`, falls back to `script_video.mp4`. Auto-detects latest date.
- **Uploader** (`pipeline/uploader.py`): TikTok inbox upload with chunked FILE_UPLOAD. Init -> sequential chunk PUT (5-64MB chunks) -> poll status until `SEND_TO_USER_INBOX`. Videos arrive as drafts in the creator's TikTok inbox for manual publishing.
- **Runner** (`pipeline/runner.py`): Async orchestrator. Sequential uploads (TikTok rate limit: 6 req/min on init). Reads `CartoonScript` from JSON sidecar for title + logline. Continues on individual upload failures.

## Auth flow

1. `python -m tiktok_publisher auth` -- starts a cloudflared tunnel, shows the HTTPS redirect URI to register in the TikTok Developer portal
2. After registering the URI, press Enter -- opens browser for TikTok authorization, callback is handled automatically via the tunnel
3. Tokens auto-refresh on expiry during upload; force refresh via `auth --refresh`

## Output

- `output/tiktok_tokens.json` -- OAuth tokens (gitignored via `output/`)
- Videos are uploaded individually (one TikTok post per script), not as a compiled video
