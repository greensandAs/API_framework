# 🐅 Tiger SnowSync — User Guide
### Accelerating API Ingestion for the Data Den

**Tiger SnowSync** is a **Tiger Analytics** enterprise accelerator: a metadata-driven, native Snowflake pipeline for ingesting external REST APIs without leaving the Snowflake ecosystem.

## Overview

This Streamlit app is the management UI for the Tiger SnowSync ingestion pipeline. It lets you register external REST APIs, manage credentials and network access, run ingestion (full or incremental), monitor every retry, and turn the landed JSON into flattened SQL views — all without writing SQL.

### Architecture

```
┌──────────────────────────┐     ┌─────────────────────────────────┐     ┌──────────────────────────┐
│  INGESTION_CONFIGS       │────▶│  USP_UNIVERSAL_INGESTOR         │────▶│  LANDING_TABLE (config)  │
│  (what to call)          │     │  (calls the API)                │     │  or API_RAW_DATA         │
├──────────────────────────┤     ├─────────────────────────────────┤     ├──────────────────────────┤
│  API_NAME (unique)       │     │  Reads config                   │     │  API_NAME                │
│  ENDPOINT_URL            │     │  Authenticates (key/OAuth)      │     │  STATUS_CODE             │
│  HTTP_METHOD (GET/POST)  │     │  Paginates (PAGE/OFFSET/        │     │  PAYLOAD (VARIANT)       │
│  AUTH_TYPE               │     │    CURSOR/LINK)                 │     │  PAYLOAD_HASH (dedup)    │
│  PAGINATION_TYPE         │     │  Applies watermark              │     │  INGEST_TS               │
│  CURSOR_PARAM/PATH       │     │  Deduplicates (MERGE + SHA-256) │     └──────────────────────────┘
│  RECORDS_PATH            │     │  Stages → MERGE (batch dedup)   │
│  FILTER_PARAMS           │     │  Logs every attempt (RUN_ID)    │
│  REQUEST_BODY_JSON       │     │  Persists watermark on success  │
│  INCREMENTAL_FLAG        │     │  Writes run summary             │
│  WATERMARK_*             │     └─────────────────────────────────┘
│  PAGE_SIZE / LIMIT_PARAM │                   │
│  MAX_PAGES               │                   ▼
└──────────────────────────┘     ┌─────────────────────────────────┐
                                 │  INGESTION_RESPONSE_LOG         │
          ┌──────────────────┐   │  One row per ATTEMPT (RUN_ID,   │
          │ TASK_INGEST_<API>│   │  PAGE_NUMBER, ATTEMPT_NUMBER)   │
          │ (Snowflake Task) │   └─────────────────────────────────┘
          │ CRON / interval  │                   │
          └───────┬──────────┘                   ▼
                  │              ┌─────────────────────────────────┐
                  └─────────────│  INGESTION_RUN_SUMMARY           │
                   CALL proc    │  One row per RUN (RUN_ID,        │
                                │  pages, records, status, wm)     │
                                └─────────────────────────────────┘
                                                 │
                                                 ▼
                                ┌─────────────────────────────────┐
                                │  Views:                          │
                                │  V_LATEST_RUNS                   │
                                │  V_ACTIVE_API_STATUS             │
                                │  V_ERROR_SUMMARY_7D              │
                                └─────────────────────────────────┘
```

---

## Setting Up a New API (Step-by-Step)

### Scenario: You want to ingest data from `https://api.example.com/v1/data`

### Step 1: Create Network Access (Secrets & EAI page → Network Rules tab)

1. Click **＋ New Network Rule** (opens dialog)
2. Enter:
   - **Rule Name**: `NR_EXAMPLE_API`
   - **Allowed Hosts**: `api.example.com`
3. Click **Create** — EAI auto-rebuilds

### Step 2: Create a Secret (Secrets & EAI page → Secrets tab)

| API Auth Method | Secret Type | What to Enter |
|---|---|---|
| API key in header | **GENERIC_STRING** | The API key string |
| OAuth2 client credentials | **PASSWORD** | Username = Client ID, Password = Client Secret |
| Snowflake-managed OAuth2 | **OAUTH2** | Pick the security integration |
| No auth needed | *Skip this step* | — |

### Step 3: Register the API Config (Manage API Configs → New Endpoint tab)

1. Enter `API_NAME` and `ENDPOINT_URL`
2. **Live Network-Rule Validation** runs as you type the URL
3. Select **HTTP_METHOD**: `GET` (default) or `POST` (for GraphQL/query APIs)
4. Select **AUTH_TYPE** and associated fields
5. Configure **Pagination** (see Pagination Reference below)
6. Set **RECORDS_PATH** (where the array lives in the response JSON)
7. Optionally configure **Static Filters** and **Incremental Sync**
8. Click **Add Config**

### Step 4: Run It (Run Ingestion page)

Select the API, choose mode (Sequential/Parallel/Dry Run), click **Run**.

### Step 5: Verify (Ingestion Console + Data Explorer)

- **Console** — KPIs, timeline, per-API health, run summary, retry analysis, error intelligence
- **Data Explorer** — browse payloads, discover schema, generate flattened views

### Step 6 (Optional): Schedule It (Task Scheduler page)

Click **＋ New Schedule** → choose interval or CRON → the dialog handles creation.

---

## Pagination Reference

| Type | How it works | Config fields |
|---|---|---|
| `NONE` | Single request | — |
| `PAGE` | `?{PAGE_PARAM}=1, 2, 3...` | `PAGE_PARAM`, `PAGE_SIZE`, `LIMIT_PARAM` (optional), `START_INDEX` |
| `OFFSET` | `?{PAGE_PARAM}=0, 100, 200...` | `PAGE_PARAM`, `PAGE_SIZE`, `LIMIT_PARAM` (optional), `START_INDEX` |
| `CURSOR` | Next-token from response body | `CURSOR_PARAM`, `CURSOR_PATH`, `PAGE_SIZE`, `LIMIT_PARAM` (optional) |
| `LINK` | Follows `Link: <url>; rel="next"` header | No extra config — automatic. Set `RECORDS_PATH` to blank for flat-array APIs |

### Termination signals (all types):
- Empty `data` array → stop
- `HAS_MORE_PATH` returns `false` → stop
- `TOTAL_PAGES_PATH` reached → stop
- `MAX_PAGES` ceiling hit → stop with WARNING

### CURSOR-specific behavior:
- Watermark only appended on **first page** (cursor encodes position)
- `cursor_token = None` or empty string → pagination complete
- Already-encoded cursors preserved (no double-encoding)

### LINK-specific behavior:
- Filters/watermark only appended on **first page** (subsequent URLs from Link header are complete)
- URL validated (`http`/`https` + valid hostname) before following

---

## Incremental Sync (Watermark)

| Field | Example | What it does |
|---|---|---|
| **WATERMARK_PARAM** | `since` | Query-string parameter to send |
| **WATERMARK_FIELD** | `updated_at` | Dotted path to the high-water mark in each record |
| **Initial LAST_SYNC_VALUE** | `2025-01-01T00:00:00Z` | Seed value (optional) |

**Watermark comparison** handles:
- Numeric values (`float` comparison)
- ISO 8601 timestamps (`datetime.fromisoformat` with `Z`/`+00:00` normalization)
- String fallback (lexicographic)

**Reset/Backfill**: Manage Existing API → Incremental Sync Control → Apply/Clear.

---

## Data Strategy

| Feature | Config field | Purpose |
|---|---|---|
| Records extraction | `RECORDS_PATH` | Dotted path to the array (e.g. `data`, `results`, `items`). Blank = top-level. |
| Static filters | `FILTER_PARAMS` | JSON dict of query params appended to every request |
| POST body | `REQUEST_BODY_JSON` | JSON body for POST-based query APIs (GraphQL, HubSpot Search) |
| Page size | `PAGE_SIZE` | Records per page (used with LIMIT_PARAM if configured) |
| Limit param | `LIMIT_PARAM` | Query param name for page size (e.g. `limit`, `per_page`). Only appended when explicitly set. |
| Safety ceiling | `MAX_PAGES` | Hard stop to prevent infinite pagination loops (default 10000) |

---

## Deduplication

The framework uses **content-hash deduplication** via MERGE:

1. Each chunk of records is hashed (`SHA-256` of `{"data": [records]}`)
2. Chunks are staged in a temporary table during the run
3. After all pages are fetched, a single `MERGE INTO target USING staging ON PAYLOAD_HASH` writes only new data
4. Duplicate chunks are counted as `records_skipped`

This approach is **set-based** (one MERGE per run, not per-chunk lookups) for optimal performance.

---

## Run Isolation (RUN_ID)

Every procedure execution generates a UUID `run_id` that is stored in both:
- `INGESTION_RESPONSE_LOG.RUN_ID` (per-attempt)
- `INGESTION_RUN_SUMMARY.RUN_ID` (per-run)

This allows the Console to scope all views to a specific run — no cross-run pollution in retry analysis or metrics.

---

## Auth Type Reference

| AUTH_TYPE | Required Fields | How It Works |
|---|---|---|
| `NONE` | — | No authentication |
| `API_KEY` | SECRET_NAME, API_KEY_HEADER | Header-based API key from GENERIC_STRING secret |
| `OAUTH2_BASIC` | SECRET_NAME, TOKEN_URL | Client credentials flow (PASSWORD secret → bearer token) |
| `OAUTH2_INTEGRATION` | SECRET_NAME | Snowflake-managed OAuth via security integration |

---

## Resilience

| Feature | Behavior |
|---|---|
| Configurable retries | `MAX_RETRIES` attempts per page (default 6) |
| Retry delay | `RETRY_DELAY_SEC` between attempts (default 15s) |
| `Retry-After` header | Honored for 429 responses (overrides delay) |
| Fast-fail | Non-retryable codes (4xx except 429) exit immediately |
| `SUSPEND_TASK_AFTER_NUM_FAILURES` | Tasks auto-suspend after N consecutive failures |

**Retryable codes**: 429, 500, 502, 503, 504

---

## Page Reference

| Page | Purpose |
|---|---|
| **Manage API Configs** | CRUD for configs; network gap detection; watermark control; toggle/delete |
| **Manage Secrets & EAI** | EAI command center; dependency graph; network rules, integrations, secrets lifecycle (create/edit/rotate/delete) |
| **Run Ingestion** | Execute selected APIs (sequential/parallel/dry-run) with live progress |
| **Ingestion Console** | KPIs, timeline, per-API health, run summary, retry analysis, error intelligence |
| **Data Explorer** | Browse payloads, schema discovery, SQL view builder |
| **Task Scheduler** | Create/manage Snowflake Tasks; CRON/interval; timeline; execution history |
| **Pipeline Overview** | Architecture diagram + capabilities reference |

---

## Key Snowflake Objects

| Object | Location | Purpose |
|---|---|---|
| `INGESTION_CONFIGS` | `METADATA` | Config table — all API settings including pagination, auth, filters, watermark |
| `INGESTION_RESPONSE_LOG` | `METADATA` | One row per HTTP attempt (RUN_ID, PAGE_NUMBER, ATTEMPT_NUMBER) |
| `INGESTION_RUN_SUMMARY` | `METADATA` | One row per run (RUN_ID, pages, records, status, watermarks) |
| `API_RAW_DATA` | `RAW_LANDING` | Default landing table |
| `V_LATEST_RUNS` | `METADATA` | Latest run per API (pre-aggregated) |
| `V_ACTIVE_API_STATUS` | `METADATA` | Active APIs with last run metrics |
| `V_ERROR_SUMMARY_7D` | `METADATA` | 7-day error frequency by API + code |
| `USP_UNIVERSAL_INGESTOR` | `METADATA` | Main ingestion procedure |
| `USP_REBUILD_INGESTOR` | `METADATA` | Rebuilds ingestor with current secrets |
| `EAI_UNIVERSAL_INGESTOR` | Account-level | External access integration |
| `TASK_INGEST_<API>` | `METADATA` | Scheduled ingestion tasks |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| "Configuration not found or inactive" | API_NAME typo or `ACTIVE_FLAG = FALSE` | Check config, toggle active |
| "Auth failed: SECRET_NAME not configured" | SECRET_NAME blank | Edit config to add secret |
| HTTP 401 / 403 | Credentials expired | Rotate secret (Secrets tab → 🔄 Rotate) |
| "Could not connect" / timeout | Host not in network rule | Add rule (Secrets & EAI → Network Rules) |
| "CURSOR_PATH not configured" | Missing config for CURSOR pagination | Set CURSOR_PATH in config |
| "CURSOR_PARAM not configured" | Missing query param name | Set CURSOR_PARAM in config |
| Duplicate data not appearing | Hash dedup working | Expected behavior |
| Watermark not advancing (LINK) | `RECORDS_PATH` set to "data" but API returns flat array | Set RECORDS_PATH to blank |
| Schema Discovery shows "ARRAY" | Double-nested payload from old runs | Re-run ingestion after procedure fix |
| Progress shows "0 records" | Old procedure version | Rebuild: `CALL USP_REBUILD_INGESTOR()` |
| 368 "retries" on one page | Cross-run pollution (pre-RUN_ID) | Deploy RUN_ID fix + rebuild |
| `limit=100` rejected by API | Default LIMIT_PARAM was being appended | Clear LIMIT_PARAM in config (new default = empty) |
| Total pages off-by-one (0-based API) | Fixed in latest version | Rebuild procedure |
| Task auto-suspended | N consecutive failures | Fix API issue, then Resume |

---

## Deployment

1. Run `DDL/setup.sql` (schema migrations, tables, indexes, views)
2. Run `Procedures/USP_REBUILD_INGESTOR.sql` (create rebuild proc)
3. `CALL API_DATA_PIPELINE.METADATA.USP_REBUILD_INGESTOR()` (binds secrets)
4. Deploy Streamlit app (redeploy from workspace)

---

## File Structure

```
API_framework/
├── DDL/
│   └── setup.sql                    # Schema, tables, indexes, views
├── Procedures/
│   ├── USP_UNIVERSAL_INGESTOR.sql   # Main ingestion procedure
│   └── USP_REBUILD_INGESTOR.sql     # Dynamic rebuild with secrets
├── streamlit_app/
│   ├── streamlit_app.py             # Thin router (70 lines)
│   ├── pyproject.toml               # Dependencies
│   ├── snowflake.yml                # App config
│   └── tiger/
│       ├── db.py                    # Session, SQL helpers, validators
│       ├── helpers.py               # UI components, pagination
│       ├── knowledge.py             # Error KB, CRON parser, schema helpers
│       ├── styles.py                # Dark theme CSS
│       ├── sidebar.py               # Navigation + settings
│       └── pages/
│           ├── config.py            # Manage API Configs
│           ├── secrets.py           # Secrets & EAI
│           ├── run.py               # Run Ingestion
│           ├── console.py           # Ingestion Console
│           ├── explorer.py          # Data Explorer
│           ├── scheduler.py         # Task Scheduler
│           └── help.py              # Pipeline Overview
└── README.md
```
