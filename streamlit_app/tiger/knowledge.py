"""Tiger SnowSync — error knowledge base + humanize helpers + schema-discovery utils."""
import re
import json
from datetime import datetime
import pandas as pd


# ─────────────────────────────────────────────
# Error-code knowledge base (used by Console → Error Intelligence tab)
# ─────────────────────────────────────────────
ERROR_KNOWLEDGE = {
    "400": {
        "label": "Bad Request", "severity": "error", "category": "Client", "icon": "🔴",
        "what_happened": "The API rejected the request because the payload or query parameters were malformed or invalid.",
        "likely_causes": [
            "WATERMARK_PARAM name doesn't match what the API expects",
            "EXTRA_HEADERS_JSON is malformed JSON",
            "Date format in LAST_SYNC_VALUE is wrong for this API",
            "PAGE_PARAM or START_INDEX value out of accepted range",
        ],
        "actions": [
            "Check EXTRA_HEADERS_JSON is valid JSON in the config",
            "Verify the WATERMARK_PARAM name against the API docs",
            "Try the endpoint in Postman/curl with the same params",
            "Inspect ERROR_MESSAGE_TEXT for the API's own error body",
        ],
        "snowflake_tip": "Run `SELECT ERROR_MESSAGE_TEXT FROM INGESTION_RESPONSE_LOG WHERE STATUS_CODE = 400 LIMIT 10` — the API usually returns a body explaining what's wrong.",
        "retry_behaviour": "Framework will retry — but retries won't help if the request itself is invalid.",
        "urgency": "Fix config before next run",
    },
    "401": {
        "label": "Unauthorized", "severity": "error", "category": "Auth", "icon": "🔐",
        "what_happened": "The API rejected the request because credentials are missing or invalid.",
        "likely_causes": [
            "SECRET_NAME points to a deleted or rotated secret",
            "API key has expired or been revoked by the provider",
            "OAuth token endpoint is returning a bad token",
            "API_KEY_HEADER name doesn't match what the API expects",
            "EAI_UNIVERSAL_INGESTOR was not rebuilt after secret changes",
        ],
        "actions": [
            "Rotate the secret in Manage Secrets & EAI",
            "Rebuild the EAI (auto-triggered on secret create)",
            "Verify the API key is still valid in the provider dashboard",
            "For OAuth: check the security integration token endpoint URL",
        ],
        "snowflake_tip": "Run `DESCRIBE SECRET API_DATA_PIPELINE.METADATA.<secret_name>` to confirm the secret still exists. Then rebuild EAI.",
        "retry_behaviour": "Retries will all fail — auth won't self-heal.",
        "urgency": "Immediate action required",
    },
    "403": {
        "label": "Forbidden", "severity": "error", "category": "Auth", "icon": "🚫",
        "what_happened": "Credentials are valid but this account lacks permission for this endpoint.",
        "likely_causes": [
            "API plan/tier doesn't include this endpoint",
            "IP allowlist on the API side is blocking Snowflake's egress IPs",
            "Scope missing from the OAuth token (check security integration)",
            "The endpoint requires a different auth type than configured",
        ],
        "actions": [
            "Check if Snowflake's NAT IPs need to be allowlisted with the API provider",
            "Verify the OAuth scopes in the security integration include required permissions",
            "Confirm the API account has the subscription level for this endpoint",
        ],
        "snowflake_tip": "Snowflake's outbound IPs vary by region. Run `SELECT SYSTEM$ALLOWLIST()` for the IP ranges to whitelist with the API provider.",
        "retry_behaviour": "Retries will all fail — this is an access-control issue.",
        "urgency": "Requires provider-side change",
    },
    "404": {
        "label": "Not Found", "severity": "warning", "category": "Client", "icon": "🔍",
        "what_happened": "The endpoint URL returned nothing — either the path is wrong or the resource no longer exists.",
        "likely_causes": [
            "ENDPOINT_URL has a typo or outdated version prefix (e.g. /v1/ vs /v2/)",
            "The API has been sunset or the resource moved",
            "Pagination overshot — page number beyond the last page (often harmless)",
        ],
        "actions": [
            "Check if the API provider has released a new API version",
            "If pagination-related and only on high page numbers, it's likely the paginator running past the last page (safe to ignore)",
            "Verify the ENDPOINT_URL against current API documentation",
        ],
        "snowflake_tip": "Check `API_URL` alongside `PAGE_NUMBER` — if 404s only appear on high pages it's likely safe.",
        "retry_behaviour": "Framework retries — but a genuine 404 won't self-heal.",
        "urgency": "Investigate if not pagination-related",
    },
    "408": {
        "label": "Request Timeout", "severity": "warning", "category": "Network", "icon": "⏱",
        "what_happened": "The API accepted the connection but didn't respond within the configured timeout.",
        "likely_causes": [
            "TIMEOUT_SEC is too low for this API's response time",
            "API is under load and slow to respond",
            "Large payload page — consider reducing page size",
        ],
        "actions": [
            "Increase TIMEOUT_SEC in the config (default: 30s)",
            "If the API supports page size, add a page_size param to the URL",
            "Check AVG_RESPONSE_TIME_SECONDS for trend",
        ],
        "snowflake_tip": "",
        "retry_behaviour": "Framework retries with backoff — often self-heals.",
        "urgency": "Monitor — tune timeout if persistent",
    },
    "429": {
        "label": "Too Many Requests", "severity": "warning", "category": "Rate Limit", "icon": "🚦",
        "what_happened": "The API is rate-limiting this integration. Too many requests in a given window.",
        "likely_causes": [
            "RETRY_DELAY_SEC is too low — retries are hitting the rate limit again",
            "Running multiple APIs against the same provider in parallel",
            "Low API tier with a tight rate limit",
        ],
        "actions": [
            "Increase RETRY_DELAY_SEC to at least 60s",
            "Switch from Parallel to Sequential execution for this provider",
            "Read the API response headers for Retry-After value — match RETRY_DELAY_SEC to it",
            "Consider scheduling at off-peak hours",
        ],
        "snowflake_tip": "Most APIs include a `Retry-After` header value in the error body. Set RETRY_DELAY_SEC to that value.",
        "retry_behaviour": "Framework retries with backoff — usually self-heals if RETRY_DELAY_SEC is high enough.",
        "urgency": "Tune retry delay",
    },
    "500": {
        "label": "Internal Server Error", "severity": "warning", "category": "Server", "icon": "💥",
        "what_happened": "The API's server crashed or hit an unexpected error processing the request.",
        "likely_causes": [
            "API provider outage or degraded service",
            "Specific query parameters trigger a server-side bug",
            "Large watermark range causing server-side timeout",
        ],
        "actions": [
            "Check the API provider's status page",
            "The framework will retry — monitor if it self-heals",
            "If incremental, try narrowing the watermark range manually",
        ],
        "snowflake_tip": "",
        "retry_behaviour": "Framework retries with backoff — usually self-heals during provider recovery.",
        "urgency": "Monitor provider status page",
    },
    "502": {
        "label": "Bad Gateway", "severity": "warning", "category": "Network", "icon": "🌐",
        "what_happened": "An intermediate proxy or load balancer in front of the API failed.",
        "likely_causes": [
            "API provider is deploying or restarting",
            "CDN/gateway issue on the provider side",
        ],
        "actions": [
            "Usually transient — let the framework retry",
            "Check provider status page if persistent",
        ],
        "snowflake_tip": "",
        "retry_behaviour": "Almost always self-heals on retry.",
        "urgency": "Usually self-resolving",
    },
    "503": {
        "label": "Service Unavailable", "severity": "error", "category": "Server", "icon": "🔴",
        "what_happened": "The API is temporarily down — either for maintenance or overloaded.",
        "likely_causes": [
            "Scheduled maintenance window",
            "Provider outage",
        ],
        "actions": [
            "Check the provider's status page and maintenance schedule",
            "Schedule ingestion outside known maintenance windows",
        ],
        "snowflake_tip": "",
        "retry_behaviour": "Framework retries — recovers once the provider is back.",
        "urgency": "Check provider status",
    },
    "504": {
        "label": "Gateway Timeout", "severity": "warning", "category": "Network", "icon": "⌛",
        "what_happened": "The API gateway timed out waiting for the backend to respond.",
        "likely_causes": [
            "Very large data page — backend slow to build the response",
            "Provider infrastructure is slow",
        ],
        "actions": [
            "Reduce page size if the API supports it",
            "Increase TIMEOUT_SEC in the config",
            "Schedule during off-peak hours",
        ],
        "snowflake_tip": "",
        "retry_behaviour": "Framework retries — may self-heal off-peak.",
        "urgency": "Tune page size and timeout",
    },
    "NULL": {
        "label": "No Status Code (Framework Error)", "severity": "error", "category": "Framework", "icon": "⚠️",
        "what_happened": "The request never completed — the error occurred before a response was received. Usually a network or EAI issue.",
        "likely_causes": [
            "ENDPOINT_URL host is not in any network rule — EAI blocks the call",
            "EAI_UNIVERSAL_INGESTOR was not rebuilt after adding the API config",
            "DNS resolution failure — the host doesn't exist",
            "SSL certificate error on the API endpoint",
            "Snowflake warehouse suspended mid-run",
        ],
        "actions": [
            "Go to Manage Secrets & EAI and verify the host is in a network rule",
            "Rebuild the EAI",
            "Check ERROR_MESSAGE_TEXT — it contains the Python exception message",
            "Try the URL in a browser — if it fails there, it's a bad URL",
        ],
        "snowflake_tip": "Run `SHOW EXTERNAL ACCESS INTEGRATIONS LIKE 'EAI_UNIVERSAL_INGESTOR'` and check ALLOWED_NETWORK_RULES. Then `DESC NETWORK RULE <rule>` for VALUE_LIST.",
        "retry_behaviour": "Retries will all fail until EAI/network rule is fixed.",
        "urgency": "Immediate — nothing will work until this is resolved",
    },
}


# ─────────────────────────────────────────────
# Schedule humanizers
# ─────────────────────────────────────────────
def _humanize_schedule(sched: str) -> str:
    """Convert raw SCHEDULE string to human-readable text."""
    if not sched or sched == "—":
        return "No schedule set"
    m = re.match(r"(\d+)\s*(MINUTE|HOUR|DAY)", sched, re.IGNORECASE)
    if m:
        qty, unit = int(m.group(1)), m.group(2).upper()
        if unit == "MINUTE":
            if qty < 60:
                return f"Every {qty} minute{'s' if qty > 1 else ''}"
            hrs = qty // 60
            return f"Every {hrs} hour{'s' if hrs > 1 else ''}"
        if unit == "HOUR":
            return f"Every {qty} hour{'s' if qty > 1 else ''}"
        return f"Every {qty} day{'s' if qty > 1 else ''}"
    c = re.match(r"USING CRON\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", sched, re.IGNORECASE)
    if c:
        mn, hr, dom, mo, dow = c.group(1), c.group(2), c.group(3), c.group(4), c.group(5)
        if mn == "0" and dom == "*" and mo == "*":
            day_map = {"0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat"}
            return f"Daily at {hr}:00 UTC" if dow == "*" else f"Every {day_map.get(dow, dow)} at {hr}:00 UTC"
    return f"CRON: {sched}"


def _humanize_cron(expr: str) -> str:
    parts = (expr or "").strip().split()
    if len(parts) != 5:
        return "⚠ Invalid CRON — expected 5 fields (min hr dom mon dow)"
    mn, hr, dom, mo, dow = parts
    desc = []
    try:
        if mn == "0" and hr != "*":
            desc.append(f"At {hr}:00")
        elif mn != "*" and hr != "*":
            desc.append(f"At {hr}:{mn.zfill(2)}")
        else:
            desc.append(f"Minute: {mn}, Hour: {hr}")
        if dow == "*" and dom == "*":
            desc.append("every day")
        elif dow != "*":
            day_map = {"0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat"}
            desc.append(f"on {day_map.get(dow, dow)}")
        return "🕐 " + " ".join(desc) + " UTC"
    except Exception:
        return f"CRON: {expr}"


def _expand_cron_field(expr: str, lo: int, hi: int):
    """Expand a single CRON field into a sorted list of valid integer values.
    Supports: '*', '*/N', 'a-b', 'a,b,c', 'N', and combinations like '1-5,7'.
    """
    if expr is None or expr == "":
        return list(range(lo, hi + 1))
    expr = expr.strip()
    if expr == "*":
        return list(range(lo, hi + 1))
    out = set()
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        # Step: */N or a-b/N
        if "/" in part:
            range_part, step_part = part.split("/", 1)
            try:
                step = int(step_part)
            except Exception:
                continue
            if range_part == "*":
                start, end = lo, hi
            elif "-" in range_part:
                a, b = range_part.split("-", 1)
                try:
                    start, end = int(a), int(b)
                except Exception:
                    continue
            else:
                try:
                    start = int(range_part)
                    end = hi
                except Exception:
                    continue
            for v in range(start, end + 1, max(step, 1)):
                if lo <= v <= hi:
                    out.add(v)
        elif "-" in part:
            a, b = part.split("-", 1)
            try:
                a, b = int(a), int(b)
                for v in range(a, b + 1):
                    if lo <= v <= hi:
                        out.add(v)
            except Exception:
                continue
        else:
            try:
                v = int(part)
                if lo <= v <= hi:
                    out.add(v)
            except Exception:
                continue
    return sorted(out)


def _parse_next_runs(tasks_df, horizon_hours: int = 24):
    """Return list of {task, warehouse, time, hour_offset} for the next N hours.
    Handles interval schedules (N MINUTE/HOUR/DAY) and full CRON expressions
    (5-field) with *, */N, ranges, and lists.
    """
    if tasks_df is None or tasks_df.empty:
        return []
    now = datetime.utcnow()
    events = []
    for _, t in tasks_df.iterrows():
        name = str(t.get("NAME") or "")
        sched = str(t.get("SCHEDULE") or "")
        state = str(t.get("STATE") or "").lower()
        wh = str(t.get("WAREHOUSE") or "")
        if state != "started" or not sched:
            continue

        # ── Interval ────────────────────────────────────────
        m = re.match(r"(\d+)\s*(MINUTE|HOUR|DAY)", sched, re.IGNORECASE)
        if m:
            qty = int(m.group(1))
            unit = m.group(2).upper()
            mins = qty if unit == "MINUTE" else (qty * 60 if unit == "HOUR" else qty * 1440)
            t_next = now
            limit = now + pd.Timedelta(hours=horizon_hours)
            while t_next < limit:
                t_next = t_next + pd.Timedelta(minutes=mins)
                if t_next < limit:
                    events.append({
                        "task": name, "warehouse": wh, "time": t_next,
                        "hour_offset": (t_next - now).total_seconds() / 3600,
                    })
            continue

        # ── CRON ────────────────────────────────────────────
        c = re.match(r"USING CRON\s+(.+?)\s+(\S+)\s*$", sched, re.IGNORECASE)
        if c:
            cron_str = c.group(1).strip()
            parts = cron_str.split()
            if len(parts) != 5:
                continue
            try:
                minutes = _expand_cron_field(parts[0], 0, 59)
                hours = _expand_cron_field(parts[1], 0, 23)
                doms = _expand_cron_field(parts[2], 1, 31)
                months = _expand_cron_field(parts[3], 1, 12)
                # CRON DOW: 0 or 7 = Sunday. Python weekday(): Mon=0..Sun=6.
                dows_raw = _expand_cron_field(parts[4], 0, 7)
                dows = set()
                for d in dows_raw:
                    py_dow = (d - 1) % 7  # convert: 0/7=Sun→6, 1=Mon→0, ..., 6=Sat→5
                    dows.add(py_dow)
            except Exception:
                continue

            limit = now + pd.Timedelta(hours=horizon_hours)
            cur = now.replace(second=0, microsecond=0)
            # iterate minute-by-minute? Too expensive. Iterate over (hour, minute) candidates per day.
            for d_off in range(0, max(2, (horizon_hours // 24) + 2)):
                day = (cur + pd.Timedelta(days=d_off)).to_pydatetime() if hasattr((cur + pd.Timedelta(days=d_off)), "to_pydatetime") else (cur + pd.Timedelta(days=d_off))
                if day.month not in months:
                    continue
                if day.day not in doms:
                    continue
                # CRON: if both DOM and DOW are restricted (not '*'), match if EITHER. Here we just AND DOW.
                if day.weekday() not in dows:
                    continue
                for h in hours:
                    for mn in minutes:
                        cand = day.replace(hour=h, minute=mn, second=0, microsecond=0)
                        if now < cand <= limit:
                            events.append({
                                "task": name, "warehouse": wh, "time": cand,
                                "hour_offset": (cand - now).total_seconds() / 3600,
                            })
    return sorted(events, key=lambda x: x["time"])


# ─────────────────────────────────────────────
# Data Explorer schema-discovery helpers
# ─────────────────────────────────────────────
def _ds_infer_type(value):
    if value is None:
        return "STRING"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "NUMBER"
    if isinstance(value, float):
        return "FLOAT"
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return "TIMESTAMP_TZ"
        except Exception:
            pass
        return "STRING"
    if isinstance(value, list):
        return "ARRAY"
    if isinstance(value, dict):
        return "OBJECT"
    return "VARIANT"


def _ds_walk(obj, prefix=""):
    """Yield (path, value) pairs for leaf scalars only; dicts recurse, arrays stop at top."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                yield from _ds_walk(v, new_prefix)
            else:
                yield (new_prefix, v)
    else:
        yield (prefix, obj)


def _ds_collect_records(payload, records_path: str):
    """Extract list of records from a chunked payload by walking records_path."""
    cur = payload
    if records_path:
        for part in records_path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return []
    if isinstance(cur, list):
        return cur
    if isinstance(cur, dict):
        return [cur]
    return []


def _ds_parse_payload(p):
    if p is None:
        return None
    if isinstance(p, (dict, list)):
        return p
    try:
        return json.loads(p)
    except Exception:
        return None
