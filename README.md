# API Ingestion Framework — User Guide

## Overview

This Streamlit app is a management UI for a **config-driven API ingestion pipeline** in Snowflake. It lets you register external REST APIs, manage credentials and network access, run ingestion (full or incremental), monitor every retry, and turn the landed JSON into flattened SQL views — all without writing SQL.

### Architecture

```
┌──────────────────────┐      ┌───────────────────────────┐      ┌──────────────────────────┐
│  INGESTION_CONFIGS   │─────▶│  USP_UNIVERSAL_INGESTOR   │─────▶│  LANDING_TABLE (config)  │
│  (what to call)      │      │  (calls the API)          │      │  or API_RAW_DATA (default)│
├──────────────────────┤      ├───────────────────────────┤      ├──────────────────────────┤
│  API_ID (surrogate)  │      │  Reads config             │      │  API_ID (FK)             │
│  API_NAME (unique)   │      │  Authenticates            │      │  API_NAME                │
│  ENDPOINT_URL        │      │  Paginates                │      │  STATUS_CODE             │
│  AUTH_TYPE           │      │  Applies watermark        │      │  PAYLOAD (VARIANT)       │
│  SECRET_NAME         │      │  Deduplicates (SHA-256)   │      │  PAYLOAD_HASH            │
│  LANDING_TABLE       │      │  Routes to landing table  │      │  INGEST_TS               │
│  PAGINATION_TYPE     │      │  Logs every retry         │      │                          │
│  INCREMENTAL_FLAG    │      │  Persists new watermark   │      └──────────────────────────┘
│  WATERMARK_*         │      └───────────────────────────┘
└──────────────────────┘                  │
                                          ▼
                           ┌───────────────────────────────┐
                           │  INGESTION_RESPONSE_LOG       │
                           │  One row per ATTEMPT (retry-  │
                           │  level): status, error, time, │
                           │  ATTEMPT_NUMBER, IS_FINAL,    │
                           │  PAGE_NUMBER, API_ID          │
                           └───────────────────────────────┘
```

---

## Setting Up a New API (Step-by-Step)

### Scenario: You want to ingest data from `https://api.example.com/v1/data`

### Step 1: Create Network Access (Tab 2 — "Manage Secrets & EAI")

The API's hostname must be whitelisted for Snowflake to reach it.

1. Go to **Tab 2 → Create Network Rule**
2. Enter:
   - **Network Rule Name**: `NR_EXAMPLE_API`
   - **Allowed Hosts**: `api.example.com` (or `*.example.com` for wildcard)
3. Click **Create Network Rule**
4. The **EAI is automatically rebuilt** — the new network rule is added to `EAI_UNIVERSAL_INGESTOR` along with all existing rules and secrets.

### Step 2: Create a Secret (Tab 2 — "Manage Secrets & EAI")

| API Auth Method | Secret Type | What to Enter |
|---|---|---|
| API key in header | **GENERIC_STRING** | The API key string |
| OAuth2 client credentials | **PASSWORD** | Username = Client ID, Password = Client Secret |
| Snowflake-managed OAuth2 | **OAUTH2** | Pick the security integration when creating the secret |
| No auth needed | *Skip this step* | — |

**Example for an API key:**
1. Select **Secret Type**: `GENERIC_STRING`
2. Enter:
   - **Secret Name**: `SK_EXAMPLE_API`
   - **Secret String**: *(paste your API key)*
3. Click **Create Secret** — the EAI auto-rebuilds.

### Step 3: Register the API Config (Tab 1 — "Manage API Configs")

1. Go to **Tab 1 → Add New API Config**
2. Enter `API_NAME` and `ENDPOINT_URL`
3. **Live Network-Rule Validation** runs as you type the URL:
   - ✅ Green caption: ``Host covered by network rule: `api.example.com` (rule: NR_EXAMPLE_API)``
   - ⚠ Warning + parsed host + first 8 allowed entries if not covered. The **Add Config** button hard-blocks unless you tick **"Acknowledge gap — save anyway"**.
4. Select **AUTH_TYPE** — the form dynamically shows only relevant fields:

| AUTH_TYPE | Fields Shown |
|---|---|
| `NONE` | No auth fields |
| `API_KEY` | SECRET_NAME (dropdown), API_KEY_HEADER |
| `OAUTH2_BASIC` | SECRET_NAME (dropdown), TOKEN_URL |
| `OAUTH2_INTEGRATION` | SECRET_NAME (dropdown), EXTRA_HEADERS_JSON *(integration is bound to the secret automatically)* |

> SECRET_NAME is a dropdown filtered by the correct type. If no matching secrets exist, you'll see **"+ Create Secret →"** with a link back to Tab 2.

5. Fill in remaining fields:

| Field | Value | Notes |
|---|---|---|
| **LANDING_TABLE** | `EXAMPLE_RAW` | Pick from dropdown, type a new name, or leave default `API_RAW_DATA` |
| **PAGINATION_TYPE** | `PAGE` / `OFFSET` / `NONE` | PAGE_PARAM and START_INDEX appear only when not `NONE` |
| **INCREMENTAL SYNC** | *(checkbox)* | See **Incremental Sync** section below |
| **MAX_RETRIES / RETRY_DELAY / TIMEOUT** | `6 / 15 / 30` | Sensible defaults |

6. Click **Add Config** — the ingestor procedure auto-rebuilds with the new secret.

### Step 4: Run It (Tab 3 — "Run Ingestion")

1. Go to **Tab 3**, select the API, click **Run Ingestion**.
2. Watch the progress bar; the success message includes the watermark transition (e.g. `Watermark: 2025-01-01 → 2025-05-25`) when incremental is on.

### Step 5: Verify (Tabs 4, 5, 7)

- **Tab 4 (Ingestion Console)** — every retry attempt is logged individually; see **Retry Drill-Down** below.
- **Tab 5 (View Raw Data)** — browse landed JSON.
- **Tab 7 (Data Studio)** — discover schema and generate flattened views.

### Step 6 (Optional): Schedule It (Tab 6 — "Task Scheduler")

Same as before — interval or CRON, with auto-suspend on N failures.

---

## Incremental Sync (Watermark)

Avoid re-pulling the entire dataset every run. The framework filters by a value the API exposes (e.g., `updated_at`) and persists the new high-water mark after each successful run.

### How to enable

In the **Add Config** form, check **"Enable Incremental Sync"** and provide:

| Field | Example | What it does |
|---|---|---|
| **WATERMARK_PARAM** | `since` | Query-string parameter to send (e.g. `?since=...`). Maps to whatever the API expects: `since`, `modified_after`, `updated_after`. |
| **WATERMARK_FIELD** | `updated_at` | Dotted JSON path inside each record (e.g. `updated_at` or `meta.updated_at`) — the procedure walks every record and tracks the running max. |
| **Initial LAST_SYNC_VALUE** | `2025-01-01T00:00:00Z` *(optional)* | Seed value for the first run. Leave blank to fetch all data on the first run. |

### What happens at runtime

1. **First run** — if seeded, hits `?since=<seed>`; if not, fetches everything.
2. **During run** — every record's `WATERMARK_FIELD` is inspected; the running max is tracked.
3. **After success** — the procedure runs `UPDATE INGESTION_CONFIGS SET LAST_SYNC_VALUE = <new_max>`.
4. **Failure** — watermark is **not** persisted (no data gaps).
5. The success message reports `Watermark: <old> -> <new>`.

### Reset / Backfill (Tab 1 — "Manage Existing API")

In the **INCREMENTAL SYNC CONTROL** section under each API:
- **Override LAST_SYNC_VALUE** — type a value and click **Apply Watermark** to backfill from a chosen point.
- **Clear (Full Backfill)** — sets `LAST_SYNC_VALUE = NULL` so the next run does a complete reload.

> Watermark comparison is numeric-aware (falls back to string compare). ISO-8601 timestamps sort correctly out of the box.

---

## Data Studio (Tab 7)

Turn raw JSON into queryable columns.

1. Pick a **Landing Table** (auto-discovered from `INFORMATION_SCHEMA`).
2. Pick **Filter by API** and **Sample Size**.
3. Set the **Records JSON Path** (default `data` matches the framework's chunked payload — leave blank if `PAYLOAD` itself is one record).
4. Click **Discover Schema** — every record is walked, leaf paths collected, types inferred (`TIMESTAMP_TZ`, `NUMBER`, `BOOLEAN`, `STRING`, `FLOAT`, `OBJECT`, `ARRAY`).
5. Review the schema table:

| Column | Meaning |
|---|---|
| `PATH` | Dotted JSON path |
| `TYPE` | Best-fit Snowflake type (or `STRING` fallback) |
| `COVERAGE_%` | % of sampled records that contain this field |
| `OBSERVED_TYPES` | All types seen for this path |

6. Use the **Quality Check** expander to spot fields with < 100% coverage (catches API drift / removed fields).
7. Choose **Type Strategy**:
   - **Inferred** — casts to detected types (faster downstream, riskier)
   - **All STRING (safe)** — never errors, cast as you query
8. Click **Create / Replace View** — generates `LATERAL FLATTEN(input => PAYLOAD:<records_path>)` view, e.g.:

```sql
CREATE OR REPLACE VIEW API_DATA_PIPELINE.RAW_LANDING.V_EXAMPLE AS
SELECT base.INGEST_TS, base.API_NAME, base.STATUS_CODE,
       rec.value:id::NUMBER       AS ID,
       rec.value:updated_at::TIMESTAMP_TZ AS UPDATED_AT,
       rec.value:name::STRING     AS NAME
FROM API_DATA_PIPELINE.RAW_LANDING.EXAMPLE_RAW base,
     LATERAL FLATTEN(input => base.PAYLOAD:data) rec;
```

9. Or click **Download DDL** to save the SQL file.

---

## Retry Drill-Down (Tab 4 — Ingestion Console)

Every HTTP attempt is logged as its own row in `INGESTION_RESPONSE_LOG`. The Console surfaces this in three layers:

### Top metrics
`PAGES WITH RETRIES` · `RECOVERED` · `EXHAUSTED (FAILED)` · avg attempts per retried page.

### Summary table
Pages where the framework had to retry, showing API, page #, attempt count, final status, and outcome (`Recovered` / `Exhausted`).

### Inspector
Pick any retried page from the dropdown to see the full attempt-by-attempt history:

```
ATTEMPT_NUMBER | IS_FINAL_ATTEMPT | STATUS_CODE | RESPONSE_TIME_SECONDS | ERROR_MESSAGE_TEXT
1              | FALSE            | 503         | 1.2                   | HTTP 503
2              | FALSE            | 503         | 1.4                   | HTTP 503
3              | TRUE             | 200         | 0.9                   | NULL
```

> Transient errors that eventually succeeded are **fully visible** here — perfect for spotting flaky upstream APIs before they exhaust.

---

## Network Rule Compatibility

Two safeguards prevent runtime "host not allowed" failures:

1. **Live validation** in the Add Config form — refuses to save unless the URL host is covered (or you explicitly acknowledge the gap).
2. **Compatibility Linter** at the top of Tab 1 — auto-collapsed expander listing every existing config whose `ENDPOINT_URL` host isn't covered by any current network rule. Surface drift after rules are rotated/dropped.

Matching supports exact host, `host:port`, and `*.suffix` wildcards.

---

## Auth Type Reference

| AUTH_TYPE | Required Fields | How It Works |
|---|---|---|
| `NONE` | — | No authentication. Direct HTTP call. |
| `API_KEY` | SECRET_NAME, API_KEY_HEADER | Reads key from a `GENERIC_STRING` secret, adds it as the named HTTP header. |
| `OAUTH2_BASIC` | SECRET_NAME, TOKEN_URL | Uses client ID/secret from a `PASSWORD` secret, calls TOKEN_URL to get a bearer token. |
| `OAUTH2_INTEGRATION` | SECRET_NAME | Uses Snowflake's managed OAuth flow. The integration is bound to the secret — no separate config field. |

---

## Pagination Reference

| PAGINATION_TYPE | Behavior | Example URL |
|---|---|---|
| `NONE` | Single request | `https://api.example.com/data` |
| `PAGE` | Appends `?{PAGE_PARAM}=1`, `=2`, ... | `?page=1` |
| `OFFSET` | Appends `?{PAGE_PARAM}=0`, `=100`, ... | `?offset=0` |

Pagination stops when the response contains `{"data": []}` (empty data array).

---

## Tab Reference

| Tab | Purpose |
|---|---|
| **Manage API Configs** | Compatibility Linter; CRUD for configs; **Reset Watermark** control; toggle/delete. Auto-rebuilds the ingestor on any change. |
| **Manage Secrets & EAI** | View/create Snowflake secrets, security integrations, and network rules. EAI auto-rebuilds. |
| **Run Ingestion** | Run selected APIs, run-all sequential, or run-all parallel via Snowflake Tasks. |
| **Ingestion Console** | Filter logs by API/status, success rate, avg response time, error drill-down, and the **Retry Drill-Down** panel. |
| **View Raw Data** | Browse landed JSON across all landing tables. |
| **Task Scheduler** | Create/manage Snowflake Tasks; INTERVAL / CRON; resume/suspend/drop/run-now; execution telemetry. |
| **Data Studio** | Schema discovery + one-click flattened view generation + quality checks. |

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| "Configuration not found or inactive" | API_NAME typo or `ACTIVE_FLAG = FALSE` | Check Tab 1, toggle active if needed |
| "Auth failed: SECRET_NAME not configured" | SECRET_NAME blank in config | Edit the config row to add the secret name |
| HTTP 401 / 403 errors | Credentials expired or wrong | Update the secret in Tab 2 |
| "Could not connect" / timeout | Hostname not in any network rule | Add network rule in Tab 2 (EAI auto-rebuilds). Check the **Compatibility Linter** in Tab 1. |
| **Add Config blocked** | URL host not covered by any network rule | Add the rule first, or tick "Acknowledge gap" to override |
| Duplicate data not appearing | Payload hash already exists (dedup working) | Expected — identical responses are skipped |
| Watermark not advancing | `WATERMARK_FIELD` doesn't match the API's response shape | Use Tab 7 → Discover Schema to confirm the path; update the config |
| Want to re-pull all history | Watermark stuck on a recent value | Tab 1 → INCREMENTAL SYNC CONTROL → **Clear (Full Backfill)** |
| Flaky API but final status 200 | Transient errors hidden in old logs | Open Tab 4 → **Retry Drill-Down** to see every attempt |
| Generated view fails to create | Inferred type cast errors on real data | In Tab 7, switch **Type Strategy** to "All STRING (safe)" |
| Task auto-suspended | Exceeded `SUSPEND_TASK_AFTER_NUM_FAILURES` | Fix the API issue, then Resume in Tab 6 |

---

## Key Snowflake Objects

| Object | Location | Purpose |
|---|---|---|
| `INGESTION_CONFIGS` | `API_DATA_PIPELINE.METADATA` | Config table — one row per API. `API_ID` is the rename-safe surrogate key; `API_NAME` is the unique business key. |
| `INGESTION_RESPONSE_LOG` | `API_DATA_PIPELINE.METADATA` | One row per HTTP attempt. Powers the Retry Drill-Down. |
| `API_RAW_DATA` | `API_DATA_PIPELINE.RAW_LANDING` | Default landing table (carries `API_ID` for stable joins after renames). |
| `<LANDING_TABLE>` | `API_DATA_PIPELINE.RAW_LANDING` | Custom per-API landing tables — auto-created and self-healed (`API_ID` column added on next run). |
| `USP_UNIVERSAL_INGESTOR` | `API_DATA_PIPELINE.METADATA` | Main ingestion procedure: auth, paginate, watermark, retry-with-logging, dedupe, write. |
| `USP_REBUILD_INGESTOR` | `API_DATA_PIPELINE.METADATA` | Auto-rebuilds ingestor with current secrets. |
| `EAI_UNIVERSAL_INGESTOR` | Account-level integration | Controls network + secret access. Auto-rebuilt on rule/secret changes. |
| `TASK_INGEST_<API>` | `API_DATA_PIPELINE.METADATA` | Snowflake Tasks for scheduled ingestion. |
| `V_<API>` (generated) | `API_DATA_PIPELINE.RAW_LANDING` | Flattened views created via Data Studio. |
