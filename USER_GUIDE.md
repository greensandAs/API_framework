# API Ingestion Framework — User Guide

## Overview

This Streamlit app is a management UI for a **config-driven API ingestion pipeline** in Snowflake. It lets you register external REST APIs, manage credentials, run ingestion, and monitor results — all without writing SQL.

### Architecture

```
┌──────────────────────┐      ┌───────────────────────────┐      ┌─────────────────────────┐
│  INGESTION_CONFIGS   │─────▶│  USP_UNIVERSAL_INGESTOR   │─────▶│  LANDING_TABLE (config)  │
│  (what to call)      │      │  (calls the API)          │      │  or API_RAW_DATA (default)│
├──────────────────────┤      ├───────────────────────────┤      ├─────────────────────────┤
│  API_NAME            │      │  Reads config             │      │  API_NAME               │
│  ENDPOINT_URL        │      │  Authenticates            │      │  STATUS_CODE            │
│  AUTH_TYPE           │      │  Paginates                │      │  PAYLOAD (VARIANT)      │
│  SECRET_NAME         │      │  Deduplicates (SHA-256)   │      │  PAYLOAD_HASH           │
│  LANDING_TABLE       │      │  Routes to landing table  │      │  INGEST_TS              │
│  PAGINATION_TYPE     │      │  Logs every call          │      │                         │
└──────────────────────┘      └───────────────────────────┘      └─────────────────────────┘
                                        │
                                        ▼
                              ┌───────────────────────────┐
                              │  INGESTION_RESPONSE_LOG   │
                              │  (status, timing, errors) │
                              └───────────────────────────┘
```

---

## Setting Up a New API (Step-by-Step)

### Scenario: You want to ingest data from `https://api.example.com/v1/data`

### Step 1: Create Network Access (Tab 2 — "Manage Secrets & EAI")

The API's hostname must be whitelisted for Snowflake to reach it.

1. Go to **Tab 2 → Create Network Rule**
2. Enter:
   - **Network Rule Name**: `NR_EXAMPLE_API`
   - **Allowed Hosts**: `api.example.com`
3. Click **Create Network Rule**
4. The **EAI is automatically rebuilt** — the new network rule is added to `EAI_UNIVERSAL_INGESTOR` along with all existing rules and secrets. No manual SQL needed.

### Step 2: Create a Secret (Tab 2 — "Manage Secrets & EAI")

Choose the secret type based on how the API authenticates:

| API Auth Method | Secret Type | What to Enter |
|---|---|---|
| API key in header | **GENERIC_STRING** | The API key string |
| OAuth2 client credentials | **PASSWORD** | Username = Client ID, Password = Client Secret |
| Snowflake-managed OAuth2 | **OAUTH2** | Security Integration name + optional refresh token |
| No auth needed | *Skip this step* | — |

**Example for an API key:**
1. Select **Secret Type**: `GENERIC_STRING`
2. Enter:
   - **Secret Name**: `SK_EXAMPLE_API`
   - **Secret String**: *(paste your API key)*
   - **Comment**: `API key for Example API`
3. Click **Create Secret**
4. The **EAI is automatically rebuilt** — the new secret is added to `EAI_UNIVERSAL_INGESTOR` along with all existing rules and secrets. No manual SQL needed.

### Step 3: Register the API Config (Tab 1 — "Manage API Configs")

1. Go to **Tab 1 → Add New API Config**
2. Select **AUTH_TYPE** first — the form dynamically shows only relevant fields:

| AUTH_TYPE | Fields Shown |
|---|---|
| `NONE` | No auth fields |
| `API_KEY` | SECRET_NAME (dropdown), API_KEY_HEADER |
| `OAUTH2_BASIC` | SECRET_NAME (dropdown), TOKEN_URL |
| `OAUTH2_INTEGRATION` | SECRET_NAME (dropdown), INTEGRATION_NAME (dropdown), EXTRA_HEADERS_JSON |

> **Note**: SECRET_NAME and INTEGRATION_NAME are populated as dropdowns filtered by the correct type. If no matching secrets exist, the dropdown shows **"+ Create Secret →"** with a message to go to Tab 2.

3. Fill in the remaining fields:

| Field | Value | Notes |
|---|---|---|
| **API_NAME** | `EXAMPLE_API_DATA` | Unique identifier, used everywhere |
| **ENDPOINT_URL** | `https://api.example.com/v1/data` | Full URL |
| **HTTP_METHOD** | `GET` | Usually GET for data pulls |
| **LANDING_TABLE** | `EXAMPLE_RAW` | Target table in RAW_LANDING (auto-created if it doesn't exist). Leave blank to use default `API_RAW_DATA`. |
| **PAGINATION_TYPE** | `PAGE` or `NONE` | See pagination guide below. PAGE_PARAM and START_INDEX only appear when not `NONE`. |
| **MAX_RETRIES** | `6` | Retry count on failure |
| **RETRY_DELAY_SEC** | `15` | Wait between retries |
| **TIMEOUT_SEC** | `30` | HTTP request timeout |

4. Click **Add Config**
5. The ingestor procedure is **automatically rebuilt** with the new secret — no extra steps needed.

### Step 4: Run It (Tab 3 — "Run Ingestion")

1. Go to **Tab 3**
2. Select `EXAMPLE_API_DATA` from the multi-select
3. Click **Run Ingestion**
4. Watch the progress bar and success/error messages

### Step 5: Verify (Tab 4 & Tab 5)

- **Tab 4 (Monitor & Logs)**: Check status code, response time, any errors
- **Tab 5 (View Raw Data)**: Select the landing table, filter by API, and inspect the landed JSON

### Step 6 (Optional): Schedule It (Tab 6 — "Task Scheduler")

Automate recurring ingestion using Snowflake Tasks:

1. Go to **Tab 6 → New Schedule** (click the expander to open)
2. Select the **Target API** from the dropdown
3. Task name auto-generates as `TASK_INGEST_<API_NAME>` — customize if needed
4. Choose a **Schedule Type**:
   - **INTERVAL**: Run every N minutes (e.g., `60` = hourly)
   - **CRON**: Full cron expression with timezone (e.g., `0 2 * * *` = daily at 2 AM UTC). [Cron guide](https://crontab.guru/)
5. Optionally set **Auto-suspend after N failures** to stop the task if the API goes offline
6. Check **"Create as SUSPENDED"** (recommended) to test before going live
7. Click **Create Scheduled Task**
8. Use the **Task Controls** section below to Resume, Suspend, Run Now, or Drop tasks
9. Monitor runs in the **Execution Telemetry** section — filter by task/state, view duration, and drill into failures

---

## Using an Existing API

If the API is already configured:

1. Go to **Tab 3 — Run Ingestion**
2. Select the API(s) from the dropdown
3. Click **Run Ingestion** (selected) or **Run All** (all active) or **Run All Parallel** (concurrent)
4. Check results in **Tab 4** and **Tab 5**

To temporarily disable an API without deleting it:
1. Go to **Tab 1 → Toggle Active / Delete**
2. Select the API and click **Toggle Active Flag**

---

## Auth Type Reference

| AUTH_TYPE | Required Fields | How It Works |
|---|---|---|
| `NONE` | — | No authentication. Direct HTTP call. |
| `API_KEY` | SECRET_NAME, API_KEY_HEADER | Reads key from Snowflake secret, adds it as an HTTP header. |
| `OAUTH2_BASIC` | SECRET_NAME, TOKEN_URL | Uses client ID/secret from a PASSWORD secret, calls TOKEN_URL to get a bearer token. |
| `OAUTH2_INTEGRATION` | SECRET_NAME, INTEGRATION_NAME | Uses Snowflake's managed OAuth flow via a Security Integration. Snowflake handles token refresh. |

---

## Pagination Reference

| PAGINATION_TYPE | Behavior | Example URL |
|---|---|---|
| `NONE` | Single request, no pagination | `https://api.example.com/data` |
| `PAGE` | Appends `?{PAGE_PARAM}=1`, `=2`, ... | `https://api.example.com/data?page=1` |
| `OFFSET` | Appends `?{PAGE_PARAM}=0`, `=100`, `=200`, ... | `https://api.example.com/data?offset=0` |

Pagination stops when the response contains `{"data": []}` (empty data array).

---

## Tab Reference

| Tab | Purpose |
|---|---|
| **Manage API Configs** | View all configs, add new APIs, toggle active/delete. Auto-rebuilds the ingestor on any change. |
| **Manage Secrets & EAI** | View/create Snowflake secrets, security integrations, and network rules. EAI is **auto-rebuilt** when secrets or rules are created. |
| **Run Ingestion** | Select and run specific APIs, run all sequentially, or run all in parallel via Snowflake Tasks. |
| **Monitor & Logs** | Filter logs by API/status, view metrics (call count, success rate, avg response time), bar charts, error drill-down. |
| **View Raw Data** | Browse landed JSON across all landing tables. Select table from dropdown (populated from config), filter by API, preview or expand full payloads. |
| **Task Scheduler** | Create and manage Snowflake Tasks for automated ingestion. Schedule per-API with interval or CRON, manage task state (resume/suspend/drop/run now), and monitor execution history with telemetry metrics. |

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| "Configuration not found or inactive" | API_NAME typo or ACTIVE_FLAG = FALSE | Check Tab 1, toggle active if needed |
| "Auth failed: SECRET_NAME not configured" | SECRET_NAME column is blank in config | Edit the config row to add the secret name |
| HTTP 401 / 403 errors | Credentials expired or wrong | Update the secret in Tab 2, or check API provider |
| "Could not connect" / timeout | Hostname not in network rule or EAI | Add network rule in Tab 2 (EAI is auto-rebuilt) |
| Duplicate data not appearing | Payload hash already exists (dedup working) | This is expected — identical responses are skipped |
| Task not running | Task is in SUSPENDED state | Go to Tab 6 → Task Controls → click Resume |
| Task history empty | No runs yet or insufficient privileges | Ensure the role has `MONITOR EXECUTION` privilege on the account |
| Task auto-suspended | Exceeded `SUSPEND_TASK_AFTER_NUM_FAILURES` limit | Fix the underlying API issue, then Resume the task in Tab 6 |

---

## Key Snowflake Objects

| Object | Location | Purpose |
|---|---|---|
| `INGESTION_CONFIGS` | `API_DATA_PIPELINE.METADATA` | Config table — one row per API |
| `INGESTION_RESPONSE_LOG` | `API_DATA_PIPELINE.METADATA` | Every HTTP call logged with status/timing |
| `API_RAW_DATA` | `API_DATA_PIPELINE.RAW_LANDING` | Default landing table for JSON payloads |
| `<LANDING_TABLE>` | `API_DATA_PIPELINE.RAW_LANDING` | Custom per-API landing tables (auto-created) |
| `USP_UNIVERSAL_INGESTOR` | `API_DATA_PIPELINE.METADATA` | Main ingestion procedure |
| `USP_REBUILD_INGESTOR` | `API_DATA_PIPELINE.METADATA` | Auto-rebuilds ingestor with current secrets |
| `EAI_UNIVERSAL_INGESTOR` | Account-level integration | Controls network + secret access |
| `TASK_INGEST_<API>` | `API_DATA_PIPELINE.METADATA` | Snowflake Tasks for scheduled ingestion (one per API) |
