"""Tiger SnowSync — Snowflake DB helpers (session, queries, EAI/secret rebuild,
network-rule compatibility, cached SHOW results)."""
import re
from urllib.parse import urlparse as _nr_urlparse

import streamlit as st
import pandas as pd


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
DB = "API_DATA_PIPELINE"
META = f"{DB}.METADATA"
RAW = f"{DB}.RAW_LANDING"

SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,254}$")
SAFE_VALUE_RE = re.compile(r"^[^'\\;]*$")


# ─────────────────────────────────────────────
# Session bootstrap (singleton)
# ─────────────────────────────────────────────
_conn = st.connection("snowflake")
_session = _conn.session()


def get_session():
    """Return the active Snowpark session for this Streamlit app."""
    return _session


# ─────────────────────────────────────────────
# Validators / sanitizers
# ─────────────────────────────────────────────
def is_safe_name(name: str) -> bool:
    return bool(SAFE_NAME_RE.match(name or ""))


def is_safe_literal(value: str) -> bool:
    return bool(SAFE_VALUE_RE.match(value or ""))


def escape_sql_literal(value: str) -> str:
    return (value or "").replace("'", "''")


# ─────────────────────────────────────────────
# Core SQL helpers
# ─────────────────────────────────────────────
def run_query(sql, params=None):
    if params:
        df = _session.sql(sql, params=params).to_pandas()
    else:
        df = _session.sql(sql).to_pandas()
    df.columns = [c.strip('"') for c in df.columns]
    return df


def exec_sql(sql, params=None):
    if params:
        _session.sql(sql, params=params).collect()
    else:
        _session.sql(sql).collect()


# ─────────────────────────────────────────────
# Cached metadata helpers
# ─────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def get_secrets_df():
    df = run_query(f"SHOW SECRETS IN SCHEMA {META}")
    df.columns = [c.upper() for c in df.columns]
    return df


@st.cache_data(ttl=60, show_spinner=False)
def get_integrations_df():
    df = run_query("SHOW SECURITY INTEGRATIONS")
    df.columns = [c.upper() for c in df.columns]
    return df


@st.cache_data(ttl=60, show_spinner=False)
def get_allowed_hosts():
    """Return a list of dicts: [{rule, entry, host, port}] aggregated from every
    network rule in the METADATA schema. Used to validate ENDPOINT_URL against the EAI."""
    out = []
    try:
        nr_df = run_query(f"SHOW NETWORK RULES IN SCHEMA {META}")
        nr_df.columns = [c.upper() for c in nr_df.columns]
    except Exception:
        return out
    if nr_df.empty:
        return out
    for _, r in nr_df.iterrows():
        name = r.get("NAME")
        if not name:
            continue
        try:
            d = run_query(f"DESC NETWORK RULE {META}.{name}")
            d.columns = [c.upper() for c in d.columns]
            if "VALUE_LIST" in d.columns and not d.empty:
                v = d["VALUE_LIST"].iloc[0]
                if v:
                    for x in str(v).split(","):
                        x = x.strip()
                        if not x:
                            continue
                        host, _, port = x.partition(":")
                        out.append({
                            "rule": str(name),
                            "entry": x,
                            "host": host.lower().strip(),
                            "port": port.strip() if port else ""
                        })
        except Exception:
            continue
    return out


# ─────────────────────────────────────────────
# Network-rule URL validation
# ─────────────────────────────────────────────
def extract_url_host(url: str):
    """Return (host_lower, port_str) parsed from a URL. Empty strings on failure."""
    if not url:
        return "", ""
    try:
        u = _nr_urlparse(url if "://" in url else f"https://{url}")
        host = (u.hostname or "").lower()
        port = str(u.port) if u.port else ""
        return host, port
    except Exception:
        return "", ""


def check_host_allowed(url: str, allowed_entries=None):
    """Return (is_allowed: bool, matched_entry: str|None, reason: str).
    Matches exact host, host:port, and *.suffix wildcards."""
    if allowed_entries is None:
        allowed_entries = get_allowed_hosts()
    host, port = extract_url_host(url)
    if not host:
        return False, None, "Could not parse host from URL"
    if not allowed_entries:
        return False, None, "No network rules defined in METADATA schema"
    for a in allowed_entries:
        a_host = a["host"]
        a_port = a["port"]
        if a_host == host:
            if not a_port or a_port == port or (not port and a_port in ("443", "80")):
                return True, f"{a['entry']} (rule: {a['rule']})", "exact host match"
        if a_host.startswith("*."):
            suffix = a_host[1:]
            if host.endswith(suffix):
                return True, f"{a['entry']} (rule: {a['rule']})", "wildcard match"
    return False, None, f"Host '{host}' not covered by any network rule"


# ─────────────────────────────────────────────
# Higher-level orchestration
# ─────────────────────────────────────────────
def rebuild_ingestor():
    result = run_query(f"CALL {META}.USP_REBUILD_INGESTOR()")
    return result.iloc[0, 0]


def rebuild_eai():
    nr_df = run_query(f"SHOW NETWORK RULES IN SCHEMA {META}")
    nr_df.columns = [c.upper() for c in nr_df.columns]
    rules = [f"{META}.{r}" for r in nr_df["NAME"].tolist()] if not nr_df.empty else []

    sdf = get_secrets_df()
    secrets = [f"{META}.{s}" for s in sdf["NAME"].tolist()] if not sdf.empty else []

    rules_clause = ", ".join(rules) if rules else ""
    secrets_clause = ", ".join(secrets) if secrets else ""

    sql = (
        f"CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION EAI_UNIVERSAL_INGESTOR "
        f"ALLOWED_NETWORK_RULES = ({rules_clause}) "
        f"ALLOWED_AUTHENTICATION_SECRETS = ({secrets_clause}) "
        f"ENABLED = TRUE"
    )
    exec_sql(sql)
    return f"EAI rebuilt with {len(rules)} rule(s) and {len(secrets)} secret(s)"
