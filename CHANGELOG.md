# CHANGELOG

## [1.1.0] — 2026-06-22

### 🔒 Security
- **fix: ENVIRONMENT variable now correctly detected in production** (`main.py`, `webhooks.py`)
  - Previously `NODE_ENV`/`ENV` were checked; `ENVIRONMENT` (the Railway variable) was ignored
  - `/docs` is now hidden in production; webhook fail-closed protection now activates correctly
- **security: Added security headers to Next.js** (`next.config.js`)
  - `X-Frame-Options: DENY` (clickjacking protection)
  - `X-Content-Type-Options: nosniff`
  - `Strict-Transport-Security` with preload
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy` (Clerk + Stripe compatible)
  - `Permissions-Policy`

### ⚡ Performance / Scalability
- **fix: Firestore SDK sync calls no longer block the event loop** (`firestore_client.py`)
  - All `doc_ref.set()`, `.get()`, `.stream()`, `.count().get()` calls wrapped in `asyncio.get_event_loop().run_in_executor(ThreadPoolExecutor)`
  - Dedicated `ThreadPoolExecutor(max_workers=20)` for Firestore operations
- **fix: Anthropic SDK sync calls no longer block the event loop** (`summary_agent.py`)
  - All `client.messages.create()` calls wrapped in `run_in_executor` with dedicated AI thread pool
- **perf: 4 Claude API calls → 1 unified call** (`summary_agent.py`, `prompts.py`)
  - TranscriptCleaner + SummaryGenerator + KeyPoints + ChapterDetector merged into single structured JSON call
  - Estimated latency reduction: ~60% (30s → 12s)
  - Estimated token cost reduction: ~30%
- **perf: Anthropic Prompt Caching enabled** (`prompts.py`)
  - System prompt marked with `cache_control: {type: ephemeral}`
  - Estimated savings: ~38% on repeated calls (system prompt tokens cached)
- **fix: YouTube transcript extraction is now async** (`youtube.py`)
  - `get_transcript()`, `_get_transcript_via_api()`, `_get_transcript_via_whisper()` run in thread pool
  - Previously blocked uvicorn event loop for entire Whisper transcription duration

### 🏗 Architecture
- **refactor: Chunking strategy for long transcripts** (`summary_agent.py`)
  - Transcripts > 14,000 chars split into overlapping chunks (12,000 chars, 400 overlap)
  - Map-reduce: chunks summarized in parallel with `claude-haiku` (cheaper), then synthesized with Sonnet
  - Fixes truncation bug: vídeos of 2h+ no longer lose 70% of their content
- **refactor: Firestore client renamed `init_pocketbase` → `init_firestore`** (`firestore_client.py`)
  - `init_pocketbase` kept as alias for backward compatibility
- **refactor: `pb_list` now uses single Firestore query** with `offset()` instead of double round-trip

### 🛡 Rate Limiting
- **security: Rate limiting added to `/api/summaries`** — 10 req/min per IP (`summaries.py`)
- **security: Rate limiting added to `/api/billing/checkout`** — 5 req/min per IP (`billing.py`)
- **security: Rate limiting added to `/api/billing/portal`** — 5 req/min per IP (`billing.py`)
- **deps: `slowapi==0.1.9` added to `requirements.txt`**

### 🎯 UX
- **fix: Polling interval reduced from 3s → 5s** (`dashboard/page.tsx`) — saves ~40% of polling requests
- **feat: Polling auto-stops after 10 minutes** with user-visible error message
- **fix: Copyright year updated to dynamic current year** (`page.tsx`)
- **feat: Accessibility improvements** (`page.tsx`) — semantic HTML (`<main>`, `<nav role>`, `<article>`, `<section aria-label>`), `aria-label` on interactive elements
- **fix: Demo card updated from "2024" to "2025"** in example card

### 📈 SEO
- **feat: Sitemap generated via `app/sitemap.ts`** — Next.js native, auto-served at `/sitemap.xml`
- **feat: Robots policy via `app/robots.ts`** — blocks /dashboard, /sign-in, /sign-up, /api/ from indexing
- **feat: Improved OpenGraph metadata** — `og:image`, `twitter:card`, `twitter:image`, `metadataBase`
- **feat: Extended keyword list** in layout metadata
- **feat: Per-page metadata** (`page.tsx` exports its own `Metadata`)

### 🧪 Testing
- **feat: Real pytest test suite** replacing manual scripts (`tests/`)
  - `test_schemas.py` — 10 tests for URL validation, SSRF, language validation
  - `test_youtube_service.py` — 17 tests for video ID extraction, duration parsing, timestamp formatting
  - `test_firestore_client.py` — 10 tests for filter parsing, JSON escaping, timestamp serialization
  - `test_prompts.py` — 12 tests for prompt completeness, caching config, chunking logic
  - **49 tests, 0 failures**
- **feat: `pytest.ini` configuration file** added
- **feat: GitHub Actions CI** (`.github/workflows/ci.yml`) — lint + test backend, type-check + build frontend

### 📚 Documentation
- **docs: README.md fully rewritten** — installation, env vars, architecture, deployment, troubleshooting
- **docs: CHANGELOG.md created**
- **docs: SECURITY_FIXES.md updated** with new fixes from this release

## [1.0.0] — 2026-05 (pre-release)

Initial MVP. Firebase/Firestore migration from PocketBase. Clerk auth, Stripe billing, 
YouTube transcript pipeline, Claude AI summarization.
