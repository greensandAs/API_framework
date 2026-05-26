import streamlit as st
import pandas as pd
import re
import time
import json
import base64
from datetime import datetime
try:
    import plotly.graph_objects as go
    _PLOTLY_OK = True
except Exception:
    _PLOTLY_OK = False
try:
    from streamlit_searchbox import st_searchbox
    _SEARCHBOX_OK = True
except Exception:
    _SEARCHBOX_OK = False

# ─── Tiger SnowSync theme + UI helpers + knowledge base ───
from tiger.styles import inject_styles
from tiger.helpers import (
    section_label, empty_state, make_sparkline_svg,
    dd_tile, cfg_card, styled_dataframe, stitch_row, active_pill,
)
from tiger.knowledge import (
    ERROR_KNOWLEDGE,
    _humanize_schedule, _humanize_cron, _parse_next_runs,
    _ds_infer_type, _ds_walk, _ds_collect_records, _ds_parse_payload,
)
from tiger.db import (
    DB, META, RAW,
    is_safe_name, is_safe_literal, escape_sql_literal,
    run_query, exec_sql,
    rebuild_ingestor, rebuild_eai,
    get_secrets_df, get_integrations_df, get_allowed_hosts,
    extract_url_host, check_host_allowed,
    get_session,
)

st.set_page_config(page_title="Tiger SnowSync", layout="wide", page_icon="🗃️", initial_sidebar_state="expanded")
inject_styles()

# ─── Brand logo (rendered manually in the sidebar with full size control) ───
@st.cache_data(show_spinner=False)
def _load_logo_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""

_LOGO_PATH = "Tiger_Snow_sync_logo_new.png"   # ships alongside streamlit_app.py
_logo_b64 = _load_logo_b64(_LOGO_PATH)
_logo_uri = f"data:image/png;base64,{_logo_b64}" if _logo_b64 else ""

# Snowpark session (managed by tiger.db; keep `session` alias for any direct uses)
session = get_session()

# ─── Sidebar navigation imports + topbar ───
from tiger.sidebar import get_session_context, render_sidebar, render_topbar

_user, _role, _wh = get_session_context()
nav_choice = render_sidebar(_logo_uri, _user, _role, _wh)
render_topbar(nav_choice, _wh)

# ─────────────────────────────────────────────
# TAB 1: Manage API Configs
# ─────────────────────────────────────────────
if nav_choice == "Manage API Configs":
    section_label("CONFIGURATION REGISTRY")
    st.header("API Configurations")
    st.caption("Registry-only view. Use **Run Ingestion** in the sidebar to execute.")

    if "cfg_search" not in st.session_state:
        st.session_state["cfg_search"] = ""
    if "cfg_show_all" not in st.session_state:
        st.session_state["cfg_show_all"] = False

    configs = run_query(f"SELECT * FROM {META}.INGESTION_CONFIGS ORDER BY API_NAME")
    all_api_names = configs["API_NAME"].tolist() if not configs.empty else []

    list_tab, new_tab, manage_tab = st.tabs(["📋  List", "➕  New Endpoint", "⚙  Manage Existing"])

    # ─── Compute health (network-rule gap detection) ───
    network_gap_apis = set()
    if not configs.empty and "ENDPOINT_URL" in configs.columns:
        try:
            allowed_entries = get_allowed_hosts()
            for _, crow in configs.iterrows():
                url = crow.get("ENDPOINT_URL")
                if not url or pd.isna(url):
                    continue
                ok, _matched, _reason = check_host_allowed(str(url), allowed_entries)
                if not ok:
                    network_gap_apis.add(crow.get("API_NAME"))
        except Exception:
            pass

    if not configs.empty:
        active_count = int((configs["ACTIVE_FLAG"] == True).sum())
        inactive_count = len(configs) - active_count
        gap_count = len(network_gap_apis)
        incremental_count = int((configs.get("INCREMENTAL_FLAG", pd.Series(dtype=bool)) == True).sum()) if "INCREMENTAL_FLAG" in configs.columns else 0
    else:
        active_count = inactive_count = gap_count = incremental_count = 0

    with list_tab:
        # Status-aware glow keyed off overall health
        overall_glow = "err" if gap_count > 0 else ("warn" if inactive_count > 0 else "ok")

        # Hero tile (full width)
        dd_tile("REGISTERED APIs", len(configs), f"{active_count} active · {gap_count} gap",
                "up" if gap_count == 0 else "down", live=True, size="hero", glow=overall_glow)

        st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)

        # 3-card row below the hero (no overlap)
        m1, m2, m3 = st.columns(3)
        with m1:
            dd_tile("ACTIVE", active_count, f"{inactive_count} inactive", "flat",
                    glow="ok" if active_count else None)
        with m2:
            dd_tile("INCREMENTAL", incremental_count, f"of {len(configs)}", "flat")
        with m3:
            delta_dir = "down" if gap_count > 0 else "up"
            dd_tile("NETWORK GAPS", gap_count,
                    "needs network rule" if gap_count else "all hosts covered",
                    delta_dir, glow="err" if gap_count else "ok")

        st.markdown("<div style='height: 1.4rem;'></div>", unsafe_allow_html=True)

        # ─── Status legend ───
        st.markdown(
            "<div class='legend-bar'>"
            "<span class='legend-item'><span class='legend-dot healthy'></span>Healthy</span>"
            "<span class='legend-item'><span class='legend-dot warning'></span>Network Gap</span>"
            "<span class='legend-item'><span class='legend-dot error'></span>Error</span>"
            "<span class='legend-item'><span class='legend-dot inactive'></span>Inactive</span>"
            "</div>",
            unsafe_allow_html=True
        )

        # ─── Per-API rollup stats (last 7 days, surfaced on card hover) ───
        api_stats = {}
        try:
            stats_df = run_query(
                f"SELECT API_NAME, "
                f"  MAX(INSERT_DATETIME_UTC) AS LAST_RUN, "
                f"  COUNT(*) AS TOTAL_CALLS, "
                f"  SUM(CASE WHEN STATUS_CODE = 200 THEN 1 ELSE 0 END) AS OK_CALLS "
                f"FROM {META}.INGESTION_RESPONSE_LOG "
                f"WHERE INSERT_DATETIME_UTC >= DATEADD('DAY', -7, CURRENT_TIMESTAMP()) "
                f"GROUP BY API_NAME"
            )
            for _, sr in stats_df.iterrows():
                api_stats[sr["API_NAME"]] = {
                    "last_run": sr.get("LAST_RUN"),
                    "total":    int(sr.get("TOTAL_CALLS") or 0),
                    "ok":       int(sr.get("OK_CALLS") or 0),
                }
        except Exception as _stats_e:
            st.caption(f"Stats rollup unavailable: {str(_stats_e)}")

        # ─── Filter chips + search ───
        filt_col, search_col = st.columns([3, 2])
        with filt_col:
            filter_choice = st.radio(
                "Filter",
                ["All", "Active", "Inactive", "Network Gap"],
                horizontal=True,
                label_visibility="collapsed",
                key="cfg_filter",
            )
        with search_col:
            if _SEARCHBOX_OK:
                def _search_apis(searchterm: str):
                    s = (searchterm or "").strip().lower()
                    if not s:
                        return all_api_names
                    return [n for n in all_api_names if s in str(n).lower()]
                picked = st_searchbox(
                    _search_apis,
                    placeholder="🔍  Search APIs…",
                    key="cfg_searchbox",
                    clear_on_submit=False,
                )
                st.session_state["cfg_search"] = picked or ""
            else:
                st.text_input(
                    "🔍  Search APIs",
                    key="cfg_search",
                    placeholder="Filter by name…",
                    label_visibility="collapsed",
                )

        st.markdown(
            f"<div class='chip-bar'>"
            f"<span class='chip {'active' if filter_choice=='All' else 'muted'}'>● ALL {len(configs)}</span>"
            f"<span class='chip {'active' if filter_choice=='Active' else 'muted'}'>✓ ACTIVE {active_count}</span>"
            f"<span class='chip {'muted' if filter_choice!='Inactive' else 'active'}'>○ INACTIVE {inactive_count}</span>"
            f"<span class='chip {'warn' if filter_choice=='Network Gap' or gap_count>0 else 'muted'}'>⚠ NETWORK GAP {gap_count}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        # ─── Card grid ───
        view_df = configs.copy()
        if filter_choice == "Active":
            view_df = view_df[view_df["ACTIVE_FLAG"] == True]
        elif filter_choice == "Inactive":
            view_df = view_df[view_df["ACTIVE_FLAG"] == False]
        elif filter_choice == "Network Gap":
            view_df = view_df[view_df["API_NAME"].isin(network_gap_apis)]

        # Apply search filter — exact API_NAME match if searchbox returned a selection,
        # else case-insensitive substring (text_input fallback)
        search_q = (st.session_state.get("cfg_search") or "").strip()
        if search_q:
            if search_q in all_api_names:
                view_df = view_df[view_df["API_NAME"] == search_q]
            else:
                view_df = view_df[view_df["API_NAME"].astype(str).str.lower().str.contains(search_q.lower(), na=False)]

        # Pagination — first 10 by default, expandable
        total_visible = len(view_df)
        cards_per_page = 10
        show_all = bool(st.session_state.get("cfg_show_all", False))
        if not show_all and total_visible > cards_per_page:
            paged_df = view_df.head(cards_per_page)
        else:
            paged_df = view_df

        st.caption(f"Showing **{len(paged_df)}** of **{total_visible}** matching config(s)")

        if paged_df.empty:
            if search_q:
                st.info(f"No configs match search '{search_q}'.")
            else:
                st.info("No configs match this filter.")
        else:
            for _, r in paged_df.iterrows():
                name = r.get("API_NAME") or "—"
                endpoint = r.get("ENDPOINT_URL") or "(no endpoint)"
                is_active = bool(r.get("ACTIVE_FLAG"))
                has_gap = name in network_gap_apis

                if not is_active:
                    status = "inactive"
                elif has_gap:
                    status = "warning"
                else:
                    status = "healthy"

                badges = []
                auth = (r.get("AUTH_TYPE") or "NONE")
                if auth and auth != "NONE":
                    badges.append({"text": auth, "cls": "accent"})
                pag = (r.get("PAGINATION_TYPE") or "NONE")
                if pag and pag != "NONE":
                    badges.append({"text": pag, "cls": ""})
                is_incremental = bool(r.get("INCREMENTAL_FLAG", False))
                if is_incremental:
                    badges.append({"text": "INCREMENTAL", "cls": "accent"})
                if has_gap:
                    badges.append({"text": "NETWORK GAP", "cls": "warn"})
                if not is_active:
                    badges.append({"text": "INACTIVE", "cls": ""})

                meta_parts = []
                lt = r.get("LANDING_TABLE")
                lt_str = "" if (lt is None or pd.isna(lt)) else str(lt).strip()
                if not lt_str or lt_str.lower() in ("none", "null"):
                    lt_str = "API_RAW_DATA"
                meta_parts.append(f"→ {lt_str}")

                # Created timestamp (always)
                created_ts = r.get("CREATED_TS")
                if created_ts is not None and not pd.isna(created_ts):
                    try:
                        meta_parts.append(f"created: {pd.to_datetime(created_ts).strftime('%Y-%m-%d %H:%M')}")
                    except Exception:
                        meta_parts.append(f"created: {created_ts}")

                # Watermark only when incremental is enabled
                if is_incremental:
                    lsv = r.get("LAST_SYNC_VALUE")
                    if lsv and not pd.isna(lsv):
                        meta_parts.append(f"watermark: {lsv}")

                meta = " · ".join(meta_parts)

                # Hover stats (visible only on hover; 7-day rollup)
                stats = api_stats.get(name)
                hov = []
                if stats and stats["total"] > 0:
                    err_rate = ((stats["total"] - stats["ok"]) / stats["total"]) * 100
                    err_cls = "ok" if err_rate < 1 else ("err" if err_rate >= 5 else "")
                    last_run = stats["last_run"]
                    last_run_str = pd.to_datetime(last_run).strftime("%Y-%m-%d %H:%M") if last_run is not None and not pd.isna(last_run) else "—"
                    hov = [
                        {"label": "last run", "value": last_run_str},
                        {"label": "7d calls", "value": f"{stats['total']:,}"},
                        {"label": "7d err", "value": f"{err_rate:.1f}%", "cls": err_cls},
                    ]

                cfg_card(name, endpoint, badges=badges, meta=meta, status=status, hover_stats=hov)

            # Show-all toggle for long lists
            if not show_all and total_visible > cards_per_page:
                if st.button(f"Show all ({total_visible})", use_container_width=True, key="cfg_show_all_btn"):
                    st.session_state["cfg_show_all"] = True
                    st.rerun()
            elif show_all and total_visible > cards_per_page:
                if st.button("Collapse to 10", use_container_width=True, key="cfg_collapse_btn"):
                    st.session_state["cfg_show_all"] = False
                    st.rerun()

        st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

        # ─── Compatibility Linter (kept for detail) ───
        if not configs.empty and network_gap_apis:
            with st.expander(
                f"⚠ Network Rule Compatibility — {len(network_gap_apis)} config(s) have endpoints not covered by any network rule",
                expanded=False
            ):
                st.caption(
                    "These APIs will fail at runtime with a network access error until a matching network rule is added "
                    "in the **Manage Secrets & EAI** tab."
                )
                try:
                    allowed_entries = get_allowed_hosts()
                    mismatches = []
                    for _, crow in configs.iterrows():
                        if crow.get("API_NAME") not in network_gap_apis:
                            continue
                        url = crow.get("ENDPOINT_URL") or ""
                        ok, matched, reason = check_host_allowed(str(url), allowed_entries)
                        host_p, _ = extract_url_host(str(url))
                        mismatches.append({
                            "API_NAME": crow.get("API_NAME"),
                            "HOST": host_p or "(unparseable)",
                            "ENDPOINT_URL": str(url),
                            "REASON": reason,
                        })
                    if mismatches:
                        styled_dataframe(pd.DataFrame(mismatches))
                except Exception as _e:
                    st.caption(f"Compatibility linter unavailable: {str(_e)}")

    with new_tab:
        section_label("NEW ENDPOINT")
        st.subheader("Add New API Config")

        if "form_version" not in st.session_state:
            st.session_state.form_version = 0
        fv = st.session_state.form_version

        # ─── STEP 1 · CONNECTIVITY ─────────────────────────────────────────
        st.markdown("#### 🌐  Step 1: Connectivity")
        with st.container(border=True):
            api_name = st.text_input("API_NAME (unique key)", key=f"new_api_name_{fv}")

            existing_apis = set(configs["API_NAME"].tolist()) if not configs.empty else set()
            if api_name and api_name in existing_apis:
                st.warning(f"'{api_name}' already exists. Choose a different name.")

            endpoint_url = st.text_input("ENDPOINT_URL", key=f"new_url_{fv}")

            url_allowed = True
            url_match_reason = ""
            if endpoint_url:
                allowed_entries = get_allowed_hosts()
                url_allowed, matched, reason = check_host_allowed(endpoint_url, allowed_entries)
                if url_allowed:
                    st.caption(f"Host covered by network rule: `{matched}`")
                else:
                    host_p, _ = extract_url_host(endpoint_url)
                    allowed_preview = ", ".join(sorted({a["entry"] for a in allowed_entries})[:8]) or "(none defined)"
                    st.warning(
                        f"**Host not covered by any network rule.** {reason}.\n\n"
                        f"Parsed host: `{host_p or '(unparseable)'}`\n\n"
                        f"Allowed entries: `{allowed_preview}`\n\n"
                        f"Add a rule in the **Manage Secrets & EAI** tab before saving, "
                        f"or check 'Acknowledge gap' below to save anyway."
                    )
                    url_match_reason = reason

            url_override = False
            if endpoint_url and not url_allowed:
                url_override = st.checkbox(
                    "Acknowledge gap — save without a matching network rule (config will fail at runtime until added)",
                    key=f"new_url_override_{fv}"
                )

            http_method = st.selectbox("HTTP_METHOD", ["GET", "POST", "PUT", "DELETE"], key=f"new_method_{fv}")

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # ─── STEP 2 · SECURITY ─────────────────────────────────────────────
        st.markdown("#### 🔐  Step 2: Security & Authentication")
        with st.container(border=True):
            auth_type = st.selectbox("AUTH_TYPE", ["NONE", "API_KEY", "OAUTH2_BASIC", "OAUTH2_INTEGRATION"], key=f"new_auth_{fv}")

            secret_opts = []
            try:
                sdf = get_secrets_df()
                if not sdf.empty:
                    type_map = {"API_KEY": "GENERIC_STRING", "OAUTH2_BASIC": "PASSWORD", "OAUTH2_INTEGRATION": "OAUTH2"}
                    if auth_type in type_map and "SECRET_TYPE" in sdf.columns:
                        secret_opts = sdf[sdf["SECRET_TYPE"] == type_map[auth_type]]["NAME"].tolist()
            except Exception as e:
                st.caption(f"Debug: secrets error: {e}")

            secret_name = ""
            api_key_header = ""
            token_url = ""
            extra_headers = ""

            if auth_type == "API_KEY":
                sk_options = secret_opts if secret_opts else ["+ Create Secret →"]
                secret_name = st.selectbox("SECRET_NAME", [""] + sk_options, key=f"new_sk_apikey_{fv}")
                if secret_name == "+ Create Secret →":
                    st.info("No GENERIC_STRING secrets found. Go to **Manage Secrets & EAI** tab to create one.")
                    secret_name = ""
                api_key_header = st.text_input("API_KEY_HEADER", value="X-Api-Key", key=f"new_api_header_{fv}")

            elif auth_type == "OAUTH2_BASIC":
                sk_options = secret_opts if secret_opts else ["+ Create Secret →"]
                secret_name = st.selectbox("SECRET_NAME", [""] + sk_options, key=f"new_sk_oauth_basic_{fv}")
                if secret_name == "+ Create Secret →":
                    st.info("No PASSWORD secrets found. Go to **Manage Secrets & EAI** tab to create one.")
                    secret_name = ""
                token_url = st.text_input("TOKEN_URL", key=f"new_token_url_{fv}")

            elif auth_type == "OAUTH2_INTEGRATION":
                sk_options = secret_opts if secret_opts else ["+ Create Secret →"]
                secret_name = st.selectbox("SECRET_NAME", [""] + sk_options, key=f"new_sk_oauth_int_{fv}")
                if secret_name == "+ Create Secret →":
                    st.info("No OAUTH2 secrets found. Go to **Manage Secrets & EAI** tab to create one.")
                    secret_name = ""
                st.caption("The OAuth2 integration is bound to the secret automatically — no separate selection needed.")
                extra_headers = st.text_input("EXTRA_HEADERS_JSON", placeholder='{"Client-Id": "abc123"}', key=f"new_headers_{fv}")

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # ─── STEP 3 · DATA STRATEGY ────────────────────────────────────────
        st.markdown("#### 📊  Step 3: Data Strategy")
        with st.container(border=True):
            landing_tables_list = []
            try:
                lt_df = run_query(
                    f"SELECT TABLE_NAME FROM {DB}.INFORMATION_SCHEMA.TABLES "
                    f"WHERE TABLE_SCHEMA = 'RAW_LANDING' ORDER BY TABLE_NAME"
                )
                if not lt_df.empty:
                    landing_tables_list = lt_df["TABLE_NAME"].tolist()
            except Exception:
                pass

            landing_options = ["(Default) API_RAW_DATA", "(New) Enter custom name..."] + [
                f"{RAW}.{t}" for t in landing_tables_list
            ]
            landing_choice = st.selectbox("LANDING_TABLE", landing_options, key=f"new_table_select_{fv}")

            if landing_choice.startswith("(New)"):
                landing_table = st.text_input(
                    "Custom Landing Table Name",
                    placeholder="e.g. MY_NEW_TABLE",
                    key=f"new_table_custom_{fv}"
                )
            elif landing_choice.startswith("(Default)"):
                landing_table = "API_RAW_DATA"
            else:
                landing_table = landing_choice

            pagination_type = st.selectbox("PAGINATION_TYPE", ["NONE", "PAGE", "OFFSET"], key=f"new_pag_type_{fv}")
            page_param = None
            start_index = 1

            if pagination_type != "NONE":
                page_param = st.text_input("PAGE_PARAM", key=f"new_page_param_{fv}")
                start_index = st.number_input("START_INDEX", value=1, min_value=0, key=f"new_start_idx_{fv}")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            section_label("INCREMENTAL SYNC")
            incremental_flag = st.checkbox(
                "Enable Incremental Sync (watermark-based)",
                key=f"new_incr_flag_{fv}",
                help="When enabled, the ingestor appends a watermark filter to the URL on each run and persists the highest value seen in the response."
            )
            watermark_param = ""
            watermark_field = ""
            last_sync_value = ""
            if incremental_flag:
                wm_c1, wm_c2 = st.columns(2)
                with wm_c1:
                    watermark_param = st.text_input(
                        "WATERMARK_PARAM",
                        placeholder="since",
                        key=f"new_wm_param_{fv}",
                        help="Query-string parameter the API expects (e.g. 'since', 'modified_after', 'updated_after')."
                    )
                with wm_c2:
                    watermark_field = st.text_input(
                        "WATERMARK_FIELD",
                        placeholder="updated_at",
                        key=f"new_wm_field_{fv}",
                        help="Dotted JSON path inside each record to read the new high-water mark from (e.g. 'updated_at' or 'meta.updated_at')."
                    )
                last_sync_value = st.text_input(
                    "Initial LAST_SYNC_VALUE (optional)",
                    placeholder="2025-01-01T00:00:00Z",
                    key=f"new_wm_last_{fv}",
                    help="Seed value for the first run. Leave blank to fetch all data on the first run."
                )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # ─── STEP 4 · RESILIENCE ───────────────────────────────────────────
        st.markdown("#### 🛡  Step 4: Resilience Settings")
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                max_retries = st.number_input("MAX_RETRIES", value=6, min_value=1, key=f"new_retries_{fv}")
            with c2:
                retry_delay = st.number_input("RETRY_DELAY", value=15, min_value=1, key=f"new_delay_{fv}")
            with c3:
                timeout_sec = st.number_input("TIMEOUT", value=30, min_value=5, key=f"new_timeout_{fv}")

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        # ─── FORM ACTIONS ──────────────────────────────────────────────────
        btn_col1, btn_col2, _ = st.columns([1.2, 1, 4])

        with btn_col2:
            if st.button("Cancel", type="secondary", use_container_width=True, key=f"cancel_new_{fv}"):
                st.session_state["expand_new_endpoint"] = False
                st.rerun()

        with btn_col1:
            submit_clicked = st.button("Add Config", type="primary", use_container_width=True, key=f"submit_new_{fv}")

        if submit_clicked:
            if not api_name:
                st.error("API_NAME is required.")
            elif api_name in existing_apis:
                st.error(f"'{api_name}' already exists. Choose a different name.")
            elif not is_safe_name(api_name):
                st.error("Invalid name. Use only letters, digits, and underscores.")
            elif landing_table and not re.match(r'^[A-Za-z_][A-Za-z0-9_.]*$', landing_table):
                st.error("Invalid LANDING_TABLE name. Use only letters, digits, underscores, and dots for qualified names.")
            elif endpoint_url and not url_allowed and not url_override:
                st.error(
                    f"ENDPOINT_URL host is not covered by any network rule ({url_match_reason}). "
                    f"Add a rule in **Manage Secrets & EAI**, or tick the 'Acknowledge gap' checkbox to override."
                )
            else:
                try:
                    exec_sql(
                        f"INSERT INTO {META}.INGESTION_CONFIGS "
                        "(API_NAME, ENDPOINT_URL, HTTP_METHOD, AUTH_TYPE, API_KEY_HEADER, "
                        "SECRET_NAME, TOKEN_URL, LANDING_TABLE, PAGINATION_TYPE, PAGE_PARAM, "
                        "START_INDEX, MAX_RETRIES, RETRY_DELAY_SEC, TIMEOUT_SEC, EXTRA_HEADERS_JSON, "
                        "INCREMENTAL_FLAG, WATERMARK_PARAM, WATERMARK_FIELD, LAST_SYNC_VALUE) "
                        "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?",
                        params=[
                            api_name, endpoint_url, http_method, auth_type,
                            api_key_header or None, secret_name or None,
                            token_url or None,
                            landing_table or "API_RAW_DATA",
                            pagination_type, page_param or None,
                            start_index, max_retries, retry_delay, timeout_sec,
                            extra_headers or None,
                            bool(incremental_flag),
                            (watermark_param or None) if incremental_flag else None,
                            (watermark_field or None) if incremental_flag else None,
                            (last_sync_value or None) if incremental_flag else None,
                        ]
                    )
                    rebuild_msg = rebuild_ingestor()
                    st.toast(f"Added '{api_name}' — {rebuild_msg}", icon="✅")

                    st.session_state.form_version += 1
                    st.session_state["expand_new_endpoint"] = False
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

    manage_open = bool(st.session_state.get("manage_api"))
    with manage_tab:
        section_label("ENDPOINT CONTROL")
        st.subheader("Manage Existing API")

        if not configs.empty:
            _saved_pick = st.session_state.get("manage_api")
            _initial_idx = configs["API_NAME"].tolist().index(_saved_pick) if _saved_pick in configs["API_NAME"].tolist() else 0
            selected_api = st.selectbox(
                "Select API to Manage",
                configs["API_NAME"].tolist(),
                index=_initial_idx,
                key="manage_api_picker",
            )
            st.session_state["manage_api"] = selected_api

            row = configs[configs["API_NAME"] == selected_api].iloc[0]

            c_stat, c_meth, c_auth = st.columns(3)
            with c_stat:
                st.markdown(active_pill(row["ACTIVE_FLAG"]), unsafe_allow_html=True)
            with c_meth:
                st.caption(f"**Method:** {row.get('HTTP_METHOD', 'GET')}")
            with c_auth:
                st.caption(f"**Auth:** {row.get('AUTH_TYPE', 'NONE')}")

            st.code(row.get("ENDPOINT_URL", ""), language="http")

            with st.expander("View Full Configuration JSON"):
                st.json(row.to_dict())

            st.divider()

            section_label("TUNE RESILIENCE PARAMETERS")
            col_ret, col_del, col_time = st.columns(3)
            with col_ret:
                new_retries = st.number_input("Max Retries", value=int(row.get("MAX_RETRIES", 6)), min_value=1, key="upd_ret")
            with col_del:
                new_delay = st.number_input("Retry Delay (s)", value=int(row.get("RETRY_DELAY_SEC", 15)), min_value=1, key="upd_del")
            with col_time:
                new_timeout = st.number_input("Timeout (s)", value=int(row.get("TIMEOUT_SEC", 30)), min_value=5, key="upd_time")

            if st.button("Update Parameters", type="secondary"):
                try:
                    exec_sql(
                        f"UPDATE {META}.INGESTION_CONFIGS SET MAX_RETRIES = ?, RETRY_DELAY_SEC = ?, TIMEOUT_SEC = ? WHERE API_NAME = ?",
                        params=[new_retries, new_delay, new_timeout, selected_api]
                    )
                    st.success(f"Successfully updated resilience parameters for {selected_api}")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {str(e)}")

            st.divider()

            section_label("INCREMENTAL SYNC CONTROL")
            current_inc = bool(row.get("INCREMENTAL_FLAG", False)) if "INCREMENTAL_FLAG" in row.index else False
            current_param = row.get("WATERMARK_PARAM") if "WATERMARK_PARAM" in row.index else None
            current_field = row.get("WATERMARK_FIELD") if "WATERMARK_FIELD" in row.index else None
            current_lsv = row.get("LAST_SYNC_VALUE") if "LAST_SYNC_VALUE" in row.index else None
            current_param = "" if pd.isna(current_param) else str(current_param or "")
            current_field = "" if pd.isna(current_field) else str(current_field or "")
            current_lsv = "" if pd.isna(current_lsv) else str(current_lsv or "")

            if not current_inc:
                st.caption(
                    "Incremental sync is **disabled** for this API. Enable by recreating the config "
                    "with the Incremental Sync option, or run: "
                    f"`UPDATE {META}.INGESTION_CONFIGS SET INCREMENTAL_FLAG = TRUE, "
                    "WATERMARK_PARAM = '<param>', WATERMARK_FIELD = '<field>' "
                    f"WHERE API_NAME = '{selected_api}'`"
                )
            else:
                wm_info_c1, wm_info_c2 = st.columns(2)
                with wm_info_c1:
                    st.caption(
                        f"**Watermark Param:** `{current_param or '(unset)'}` &nbsp; "
                        f"**Watermark Field:** `{current_field or '(unset)'}`",
                        unsafe_allow_html=True
                    )
                with wm_info_c2:
                    st.caption(f"**Current LAST_SYNC_VALUE:** `{current_lsv or '(none — next run is full load)'}`")

                new_lsv = st.text_input(
                    "Override LAST_SYNC_VALUE",
                    value=current_lsv,
                    placeholder="2025-01-01T00:00:00Z",
                    key=f"upd_lsv_{selected_api}",
                    help="Set a specific value to backfill from a chosen point in time. "
                         "Leave blank and click 'Clear' to force a full reload on the next run."
                )

                bf_c1, bf_c2 = st.columns(2)
                with bf_c1:
                    if st.button("Apply Watermark", use_container_width=True, key="btn_apply_wm"):
                        try:
                            new_val = (new_lsv or "").strip()
                            exec_sql(
                                f"UPDATE {META}.INGESTION_CONFIGS SET LAST_SYNC_VALUE = ? WHERE API_NAME = ?",
                                params=[new_val if new_val else None, selected_api]
                            )
                            display_val = new_val if new_val else "(NULL — full reload on next run)"
                            st.toast(f"Watermark updated for '{selected_api}': {display_val}", icon="🎯")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update failed: {str(e)}")
                with bf_c2:
                    if st.button("Clear (Full Backfill)", use_container_width=True, key="btn_clear_wm"):
                        try:
                            exec_sql(
                                f"UPDATE {META}.INGESTION_CONFIGS SET LAST_SYNC_VALUE = NULL WHERE API_NAME = ?",
                                params=[selected_api]
                            )
                            st.toast(f"Cleared watermark for '{selected_api}'. Next run will fetch all data.", icon="🔄")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Clear failed: {str(e)}")

            st.divider()

            section_label("DANGER ZONE")
            st.markdown("""
            <style>
                [data-testid="stButton"] > button[kind="secondary"]:has(+ div) {{}}

                div.danger-amber [data-testid="stButton"] button {{
                    border-color: #f0b429 !important;
                    color: #f0b429 !important;
                    background: transparent !important;
                }}
                div.danger-amber [data-testid="stButton"] button:hover {{
                    background: rgba(240,180,41,0.15) !important;
                    border-color: #f0b429 !important;
                    box-shadow: 0 0 14px rgba(240,180,41,0.25) !important;
                    color: #f0b429 !important;
                }}

                div.danger-red [data-testid="stButton"] button {{
                    border-color: #d32f2f !important;
                    color: #d32f2f !important;
                    background: transparent !important;
                }}
                div.danger-red [data-testid="stButton"] button:hover {{
                    background: rgba(211,47,47,0.15) !important;
                    border-color: #d32f2f !important;
                    box-shadow: 0 0 14px rgba(211,47,47,0.25) !important;
                    color: #d32f2f !important;
                }}

                div.danger-red-confirm [data-testid="stButton"] button {{
                    border-color: #d32f2f !important;
                    color: #ffffff !important;
                    background: #d32f2f !important;
                }}
                div.danger-red-confirm [data-testid="stButton"] button:hover {{
                    background: #b71c1c !important;
                    border-color: #b71c1c !important;
                    box-shadow: 0 0 14px rgba(211,47,47,0.35) !important;
                    color: #ffffff !important;
                }}
            </style>
            """, unsafe_allow_html=True)
            col_toggle, col_delete = st.columns(2)

            with col_toggle:
                action_text = "Deactivate API" if row["ACTIVE_FLAG"] else "Activate API"
                st.markdown('<div class="danger-amber">', unsafe_allow_html=True)
                if st.button(action_text, use_container_width=True, key="btn_danger_toggle"):
                    exec_sql(
                        f"UPDATE {META}.INGESTION_CONFIGS SET ACTIVE_FLAG = NOT ACTIVE_FLAG WHERE API_NAME = ?",
                        params=[selected_api]
                    )
                    rebuild_msg = rebuild_ingestor()
                    st.success(f"{action_text} successful — {rebuild_msg}")
                    time.sleep(1.5)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            with col_delete:
                st.markdown('<div class="danger-red">', unsafe_allow_html=True)
                with st.popover("Delete Config", use_container_width=True):
                    st.warning(f"Permanent delete for **{selected_api}**. This cannot be undone.")
                    confirm_text = st.text_input(
                        f'Type "{selected_api}" to confirm',
                        key=f"delete_confirm_{selected_api}",
                        placeholder=selected_api,
                    )
                    delete_armed = (confirm_text == selected_api)
                    st.markdown('<div class="danger-red-confirm">', unsafe_allow_html=True)
                    if st.button(
                        "Yes, Delete Completely",
                        use_container_width=True,
                        key="btn_danger_delete_confirm",
                        disabled=not delete_armed,
                    ):
                        exec_sql(
                            f"DELETE FROM {META}.INGESTION_CONFIGS WHERE API_NAME = ?",
                            params=[selected_api]
                        )
                        rebuild_msg = rebuild_ingestor()
                        st.toast(f"Deleted '{selected_api}' — {rebuild_msg}", icon="🗑")
                        time.sleep(1.0)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No API configurations available to manage.")

# ─────────────────────────────────────────────
# TAB 2: Manage Secrets & EAI
# ─────────────────────────────────────────────
elif nav_choice == "Manage Secrets & EAI":
    from tiger.pages import secrets as page_secrets
    page_secrets.render()

# ─────────────────────────────────────────────
# TAB 3: Run Ingestion (3-phase redesign)
# ─────────────────────────────────────────────
elif nav_choice == "Run Ingestion":
    from tiger.pages import run as page_run
    page_run.render(default_warehouse=_wh)

    if eai_ok:
        st.markdown(f"""
        <div style="background:rgba(63,185,80,0.06);border:1px solid rgba(63,185,80,0.2);border-radius:8px;padding:14px 20px;margin-bottom:1rem;display:flex;align-items:center;gap:14px;">
            <span style="font-size:1.2rem;color:#3fb950;">●</span>
            <div style="flex:1;">
                <span style="font-weight:700;color:#e6edf3;font-size:0.9rem;">EAI_UNIVERSAL_INGESTOR</span>
                <span style="color:#8b949e;font-size:0.78rem;margin-left:12px;">{eai_rule_count} network rule(s) · {eai_secret_count} secret(s)</span>
            </div>
            <span style="background:rgba(63,185,80,0.1);color:#3fb950;padding:3px 10px;border-radius:4px;font-size:0.62rem;font-weight:700;letter-spacing:1px;font-family:'JetBrains Mono',monospace;border:1px solid rgba(63,185,80,0.2);">ACTIVE</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:rgba(248,81,73,0.06);border:1px solid rgba(248,81,73,0.2);border-radius:8px;padding:14px 20px;margin-bottom:1rem;display:flex;align-items:center;gap:14px;">
            <span style="font-size:1.2rem;color:#f85149;">○</span>
            <div style="flex:1;">
                <span style="font-weight:700;color:#e6edf3;font-size:0.9rem;">EAI_UNIVERSAL_INGESTOR</span>
                <span style="color:#8b949e;font-size:0.78rem;margin-left:12px;">Not found — create network rules and secrets first</span>
            </div>
            <span style="background:rgba(248,81,73,0.1);color:#f85149;padding:3px 10px;border-radius:4px;font-size:0.62rem;font-weight:700;letter-spacing:1px;font-family:'JetBrains Mono',monospace;border:1px solid rgba(248,81,73,0.2);">MISSING</span>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Step 1: Network Rules", expanded=True):
        st.caption("Whitelist API hostnames so Snowflake can reach them. EAI is auto-rebuilt when you add a rule.")

        try:
            nr_df = run_query(f"SHOW NETWORK RULES IN SCHEMA {META}")
            if not nr_df.empty:
                nr_df.columns = [c.upper() for c in nr_df.columns]
                host_list = []
                for rule_name in nr_df["NAME"].tolist():
                    try:
                        desc = run_query(f"DESCRIBE NETWORK RULE {META}.{rule_name}")
                        desc.columns = [c.upper() for c in desc.columns]
                        if "VALUE_LIST" in desc.columns:
                            hosts = desc["VALUE_LIST"].iloc[0] if not desc.empty else ""
                        else:
                            hosts = ""
                        host_list.append(hosts)
                    except Exception:
                        host_list.append("")
                nr_df["ALLOWED_HOSTS"] = host_list
                display_cols = [c for c in ["NAME", "ALLOWED_HOSTS", "CREATED_ON"] if c in nr_df.columns]
                styled_dataframe(nr_df[display_cols] if display_cols else nr_df)
            else:
                st.info("No network rules found. Add one below.")
        except Exception:
            st.info("No network rules found. Add one below.")

        st.divider()
        section_label("ADD NETWORK RULE")
        with st.form("create_nr", clear_on_submit=True):
            nr_c1, nr_c2 = st.columns([1, 2])
            with nr_c1:
                nr_name = st.text_input("Rule Name")
            with nr_c2:
                nr_hosts = st.text_input("Allowed Hosts (comma-separated)", placeholder="api.example.com, api2.example.com")
            if st.form_submit_button("Create Network Rule", type="primary"):
                if not nr_name or not nr_hosts:
                    st.warning("Name and hosts are required.")
                elif not is_safe_name(nr_name):
                    st.error("Invalid name. Use only letters, digits, and underscores.")
                else:
                    try:
                        hosts = ", ".join([f"'{escape_sql_literal(h.strip())}'" for h in nr_hosts.split(",")])
                        exec_sql(
                            f"CREATE OR REPLACE NETWORK RULE {META}.{nr_name} "
                            f"MODE = EGRESS TYPE = HOST_PORT VALUE_LIST = ({hosts})"
                        )
                        eai_msg = rebuild_eai()
                        st.toast(f"Network rule '{nr_name}' created — {eai_msg}", icon="🌐")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with st.expander("Step 2: Security Integrations", expanded=False):
        st.caption(
            "Required before creating OAUTH2-type secrets. Only Client Credentials flow is supported. "
            "**Names must start with `SEC_INT_API_`** so the framework can distinguish its own integrations from "
            "unrelated account-level integrations (Snowsight OAuth, SCIM, SSO, etc.)."
        )

        try:
            integrations_df = get_integrations_df()
            if "NAME" in integrations_df.columns and "TYPE" in integrations_df.columns:
                api_auth_df = integrations_df[
                    (integrations_df["TYPE"] == "API_AUTHENTICATION") &
                    (integrations_df["NAME"].str.startswith("SEC_INT_API_", na=False))
                ]
            else:
                api_auth_df = pd.DataFrame()
            if not api_auth_df.empty:
                display_cols = [c for c in ["NAME", "TYPE", "ENABLED", "CREATED_ON", "COMMENT"] if c in api_auth_df.columns]
                styled_dataframe(api_auth_df[display_cols] if display_cols else api_auth_df)
            else:
                st.info("No framework-owned integrations found (none matching `SEC_INT_API_*`). Add one below if using OAuth2.")
        except Exception:
            st.info("Unable to list security integrations.")

        st.divider()
        section_label("ADD SECURITY INTEGRATION")
        with st.form("create_oauth_integration", clear_on_submit=True):
            oi_c1, oi_c2 = st.columns(2)
            with oi_c1:
                oi_name = st.text_input("Integration Name *", placeholder="SEC_INT_API_<your_api>")
                oi_client_id = st.text_input("OAuth Client ID *")
                oi_client_secret = st.text_input("OAuth Client Secret *", type="password")
                oi_token_endpoint = st.text_input("Token Endpoint URL *", placeholder="https://auth.example.com/oauth/token")
            with oi_c2:
                oi_auth_method = st.selectbox("Client Auth Method", ["CLIENT_SECRET_POST", "CLIENT_SECRET_BASIC"])
                oi_scopes = st.text_input("Allowed Scopes (comma-separated)", placeholder="read, write")
                oi_token_validity = st.number_input("Token Validity (seconds)", value=0, min_value=0, help="0 = provider default")
                oi_comment = st.text_input("Comment")
            oi_enabled = st.toggle("Enabled", value=True)

            if st.form_submit_button("Create Integration", type="primary"):
                if not oi_name or not oi_client_id or not oi_client_secret or not oi_token_endpoint:
                    st.error("All fields marked with * are required.")
                elif not is_safe_name(oi_name):
                    st.error("Invalid name. Use only letters, digits, and underscores.")
                elif not oi_name.startswith("SEC_INT_API_"):
                    st.error("Integration name must start with `SEC_INT_API_` (framework convention).")
                else:
                    try:
                        escaped_client_id = escape_sql_literal(oi_client_id)
                        escaped_client_secret = escape_sql_literal(oi_client_secret)
                        escaped_token_endpoint = escape_sql_literal(oi_token_endpoint)
                        escaped_comment = escape_sql_literal(oi_comment)
                        scopes_clause = ""
                        if oi_scopes.strip():
                            scopes_list = ", ".join([f"'{escape_sql_literal(s.strip())}'" for s in oi_scopes.split(",")])
                            scopes_clause = f"OAUTH_ALLOWED_SCOPES = ({scopes_list})"
                        validity_clause = f"OAUTH_ACCESS_TOKEN_VALIDITY = {int(oi_token_validity)}" if oi_token_validity > 0 else ""
                        comment_clause = f"COMMENT = '{escaped_comment}'" if oi_comment else ""
                        sql = (
                            f"CREATE SECURITY INTEGRATION {oi_name} "
                            f"TYPE = API_AUTHENTICATION "
                            f"AUTH_TYPE = OAUTH2 "
                            f"OAUTH_CLIENT_AUTH_METHOD = {oi_auth_method} "
                            f"OAUTH_CLIENT_ID = '{escaped_client_id}' "
                            f"OAUTH_CLIENT_SECRET = '{escaped_client_secret}' "
                            f"OAUTH_GRANT = 'CLIENT_CREDENTIALS' "
                            f"OAUTH_TOKEN_ENDPOINT = '{escaped_token_endpoint}' "
                            f"{scopes_clause} {validity_clause} "
                            f"ENABLED = {str(oi_enabled).upper()} "
                            f"{comment_clause}"
                        )
                        exec_sql(sql)
                        get_integrations_df.clear()
                        st.toast(f"Security integration '{oi_name}' created.", icon="🔐")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with st.expander("Step 3: Secrets", expanded=False):
        st.caption("Store API keys and OAuth credentials. EAI is auto-rebuilt when you add a secret.")

        secrets_df = get_secrets_df()
        if not secrets_df.empty:
            for stype in ["GENERIC_STRING", "PASSWORD", "OAUTH2"]:
                type_df = secrets_df[secrets_df["SECRET_TYPE"] == stype] if "SECRET_TYPE" in secrets_df.columns else pd.DataFrame()
                if not type_df.empty:
                    section_label(stype)
                    display_cols = [c for c in ["NAME", "COMMENT", "CREATED_ON"] if c in type_df.columns]
                    styled_dataframe(type_df[display_cols] if display_cols else type_df, height=200)
        else:
            st.info("No secrets found. Create one below.")

        st.divider()
        section_label("ADD SECRET")
        secret_type = st.selectbox("Secret Type", ["GENERIC_STRING", "PASSWORD", "OAUTH2"])

        if secret_type == "GENERIC_STRING":
            with st.form("create_generic_secret", clear_on_submit=True):
                sg_c1, sg_c2 = st.columns(2)
                with sg_c1:
                    s_name = st.text_input("Secret Name")
                    s_value = st.text_input("Secret String", type="password")
                with sg_c2:
                    s_comment = st.text_input("Comment")
                if st.form_submit_button("Create Secret", type="primary"):
                    if not s_name or not s_value:
                        st.warning("Name and value are required.")
                    elif not is_safe_name(s_name):
                        st.error("Invalid name. Use only letters, digits, and underscores.")
                    else:
                        try:
                            exec_sql(
                                f"CREATE SECRET {META}.{s_name} "
                                f"TYPE = GENERIC_STRING SECRET_STRING = '{escape_sql_literal(s_value)}' "
                                f"COMMENT = '{escape_sql_literal(s_comment)}'"
                            )
                            get_secrets_df.clear()
                            try:
                                eai_msg = rebuild_eai()
                                st.toast(f"Secret '{s_name}' created — {eai_msg}", icon="🔑")
                            except Exception:
                                st.toast(f"Secret '{s_name}' created (EAI rebuild skipped)", icon="🔑")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        elif secret_type == "PASSWORD":
            with st.form("create_password_secret", clear_on_submit=True):
                sp_c1, sp_c2 = st.columns(2)
                with sp_c1:
                    s_name = st.text_input("Secret Name")
                    s_user = st.text_input("Username (Client ID)")
                with sp_c2:
                    s_pass = st.text_input("Password (Client Secret)", type="password")
                    s_comment = st.text_input("Comment")
                if st.form_submit_button("Create Secret", type="primary"):
                    if not s_name or not s_user or not s_pass:
                        st.warning("All fields are required.")
                    elif not is_safe_name(s_name):
                        st.error("Invalid name. Use only letters, digits, and underscores.")
                    else:
                        try:
                            exec_sql(
                                f"CREATE SECRET {META}.{s_name} "
                                f"TYPE = PASSWORD USERNAME = '{escape_sql_literal(s_user)}' PASSWORD = '{escape_sql_literal(s_pass)}' "
                                f"COMMENT = '{escape_sql_literal(s_comment)}'"
                            )
                            get_secrets_df.clear()
                            try:
                                eai_msg = rebuild_eai()
                                st.toast(f"Secret '{s_name}' created — {eai_msg}", icon="🔑")
                            except Exception:
                                st.toast(f"Secret '{s_name}' created (EAI rebuild skipped)", icon="🔑")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        elif secret_type == "OAUTH2":
            int_opts = []
            try:
                idf = get_integrations_df()
                if not idf.empty and "TYPE" in idf.columns and "NAME" in idf.columns:
                    int_opts = idf[
                        (idf["TYPE"].str.contains("API_AUTHENTICATION", case=False, na=False)) &
                        (idf["NAME"].str.startswith("SEC_INT_API_", na=False))
                    ]["NAME"].tolist()
            except Exception:
                pass

            with st.form("create_oauth_secret", clear_on_submit=True):
                so_c1, so_c2 = st.columns(2)
                with so_c1:
                    s_name = st.text_input("Secret Name")
                    if int_opts:
                        s_int = st.selectbox("Security Integration", int_opts, key="oauth_sec_int")
                    else:
                        s_int = st.text_input("Security Integration Name (none found — create one in Step 2)")
                with so_c2:
                    s_refresh = st.text_input("OAuth Refresh Token", type="password")
                    s_comment = st.text_input("Comment")
                if st.form_submit_button("Create Secret", type="primary"):
                    if not s_name or not s_int:
                        st.warning("Name and integration are required.")
                    elif not is_safe_name(s_name) or not is_safe_name(s_int):
                        st.error("Invalid name. Use only letters, digits, and underscores.")
                    else:
                        try:
                            escaped_refresh = escape_sql_literal(s_refresh) if s_refresh else ""
                            refresh_clause = f"OAUTH_REFRESH_TOKEN = '{escaped_refresh}'" if s_refresh else ""
                            exec_sql(
                                f"CREATE SECRET {META}.{s_name} "
                                f"TYPE = OAUTH2 API_AUTHENTICATION = {s_int} "
                                f"{refresh_clause} COMMENT = '{escape_sql_literal(s_comment)}'"
                            )
                            get_secrets_df.clear()
                            try:
                                eai_msg = rebuild_eai()
                                st.toast(f"Secret '{s_name}' created — {eai_msg}", icon="🔑")
                            except Exception:
                                st.toast(f"Secret '{s_name}' created (EAI rebuild skipped)", icon="🔑")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

# ─────────────────────────────────────────────
# TAB 3: Run Ingestion (3-phase redesign)
# ─────────────────────────────────────────────
elif nav_choice == "Run Ingestion":
    from tiger.pages import run as page_run
    page_run.render(default_warehouse=_wh)

# ─────────────────────────────────────────────
# TAB 4: Ingestion Console (4-zone redesign)
# ─────────────────────────────────────────────
elif nav_choice == "Ingestion Console":
    section_label("SYSTEM TELEMETRY")
    st.header("Ingestion Console")
    st.caption("KPIs · time-series trend · per-API health · retry analysis · incidents.")

    # ─── ZONE 1 · COMMAND BAR ───
    bar_c1, bar_c2, bar_c3, bar_c4 = st.columns([2, 2, 1, 1])
    with bar_c1:
        time_range = st.select_slider(
            "Time Window",
            options=["1h", "6h", "24h", "7d", "30d"],
            value="24h",
            label_visibility="collapsed",
            key="console_time_range",
        )
    TIME_MAP = {
        "1h": ("HOUR", 1), "6h": ("HOUR", 6),
        "24h": ("HOUR", 24), "7d": ("DAY", 7), "30d": ("DAY", 30),
    }
    _unit, _amt = TIME_MAP[time_range]
    time_pred = f"INSERT_DATETIME_UTC >= DATEADD('{_unit}', -{_amt}, CURRENT_TIMESTAMP())"
    bucket_unit = "DAY" if time_range == "30d" else "HOUR"

    try:
        all_log_apis_df = run_query(f"SELECT DISTINCT API_NAME FROM {META}.INGESTION_RESPONSE_LOG ORDER BY API_NAME")
        all_log_apis = all_log_apis_df["API_NAME"].tolist() if not all_log_apis_df.empty else []
    except Exception:
        all_log_apis = []

    with bar_c2:
        api_filter = st.multiselect(
            "APIs",
            all_log_apis,
            placeholder="All APIs",
            label_visibility="collapsed",
            key="console_api_filter",
        )
    with bar_c3:
        status_filter = st.selectbox(
            "Status",
            ["All", "OK only", "Errors only"],
            label_visibility="collapsed",
            key="console_status_filter",
        )
    with bar_c4:
        if st.button("🔄", use_container_width=True, key="console_refresh", help="Refresh"):
            st.cache_data.clear()
            st.rerun()

    # Build WHERE
    where_parts = [time_pred]
    params = []
    if api_filter:
        ph = ", ".join(["?" for _ in api_filter])
        where_parts.append(f"API_NAME IN ({ph})")
        params.extend(api_filter)
    if status_filter == "OK only":
        where_parts.append("STATUS_CODE = 200")
    elif status_filter == "Errors only":
        where_parts.append("(STATUS_CODE IS NULL OR STATUS_CODE != 200)")
    where_sql = " AND ".join(where_parts)

    # Active-filters chip bar
    api_chips = "".join(f"<span class='chip'>{a}</span>" for a in api_filter) if api_filter else "<span class='chip muted'>ALL APIs</span>"
    status_chip = ""
    if status_filter != "All":
        status_chip = f"<span class='chip warn'>{status_filter.upper()}</span>"
    st.markdown(
        f"<div class='chip-bar'>"
        f"<span class='chip active'>⏱ LAST {time_range.upper()}</span>"
        f"{api_chips}{status_chip}"
        f"</div>",
        unsafe_allow_html=True
    )

    # ─── KPI query (full window, no row limit) ───
    try:
        kpi = run_query(
            f"""
            SELECT
                COUNT(*)                                                       AS TOTAL_CALLS,
                COUNT(DISTINCT API_NAME)                                       AS ACTIVE_APIS,
                SUM(CASE WHEN STATUS_CODE = 200 THEN 1 ELSE 0 END)             AS OK_CALLS,
                AVG(RESPONSE_TIME_SECONDS)                                     AS AVG_RT,
                MAX(RESPONSE_TIME_SECONDS)                                     AS MAX_RT,
                COUNT(DISTINCT CASE WHEN STATUS_CODE != 200 OR STATUS_CODE IS NULL
                                    THEN API_NAME END)                         AS APIS_WITH_ERRORS,
                SUM(CASE WHEN STATUS_CODE != 200 OR STATUS_CODE IS NULL THEN 1 ELSE 0 END) AS FAIL_CALLS,
                COUNT(DISTINCT DATE_TRUNC('{bucket_unit}', INSERT_DATETIME_UTC)) AS ACTIVE_BUCKETS
            FROM {META}.INGESTION_RESPONSE_LOG
            WHERE {where_sql}
            """,
            params=params if params else None
        ).iloc[0]
        total = int(kpi["TOTAL_CALLS"] or 0)
        ok = int(kpi["OK_CALLS"] or 0)
        fails = int(kpi["FAIL_CALLS"] or 0)
        avg_rt = float(kpi["AVG_RT"] or 0)
        max_rt = float(kpi["MAX_RT"] or 0)
        active_apis = int(kpi["ACTIVE_APIS"] or 0)
        apis_err = int(kpi["APIS_WITH_ERRORS"] or 0)
        active_buckets = int(kpi["ACTIVE_BUCKETS"] or 1)
        sr = (ok / max(total, 1)) * 100
    except Exception as _e:
        st.error(f"Failed to load KPIs: {_e}")
        total = ok = fails = active_apis = apis_err = active_buckets = 0
        avg_rt = max_rt = 0.0
        sr = 0.0

    if total == 0:
        empty_state("📭", "No log entries", f"Nothing recorded in the last {time_range} window.")
    else:
        # ─── ZONE 2 · KPI TILES ───
        # Sparklines for hero/total
        try:
            ts_simple = run_query(
                f"""
                SELECT DATE_TRUNC('{bucket_unit}', INSERT_DATETIME_UTC) AS BUCKET,
                       COUNT(*)                                          AS CALLS,
                       SUM(CASE WHEN STATUS_CODE = 200 THEN 1 ELSE 0 END) AS OK
                FROM {META}.INGESTION_RESPONSE_LOG
                WHERE {where_sql}
                GROUP BY 1
                ORDER BY 1
                """,
                params=params if params else None
            )
            calls_series = ts_simple["CALLS"].tolist()[-24:] if not ts_simple.empty else None
            sr_series = (
                (ts_simple["OK"].astype(float) / ts_simple["CALLS"].clip(lower=1) * 100).tolist()[-24:]
                if not ts_simple.empty else None
            )
        except Exception:
            calls_series, sr_series = None, None

        hero_col, r1c1, r1c2 = st.columns([2, 1, 1])
        with hero_col:
            sr_glow = "ok" if sr >= 99 else ("warn" if sr >= 90 else "err")
            dd_tile(
                "SUCCESS RATE", f"{sr:.2f}%",
                f"{ok:,} ok · {fails:,} failed",
                "up" if sr >= 99 else "down",
                live=True, size="hero", glow=sr_glow,
                spark_data=sr_series,
            )
        with r1c1:
            dd_tile("TOTAL CALLS", f"{total:,}",
                    f"last {time_range}", "flat",
                    spark_data=calls_series)
        with r1c2:
            rt_disp = f"{avg_rt*1000:.0f}ms" if avg_rt < 1 else f"{avg_rt:.2f}s"
            rt_glow = "ok" if avg_rt < 2 else ("warn" if avg_rt < 10 else "err")
            dd_tile("AVG LATENCY", rt_disp, f"max: {max_rt:.1f}s", "flat", glow=rt_glow)

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            dd_tile("FAILED CALLS", fails,
                    "needs attention" if fails else "clean",
                    "down" if fails else "flat",
                    glow="err" if fails > 0 else None)
        with r2c2:
            dd_tile("APIs WITH ERRORS", apis_err,
                    f"of {active_apis} active",
                    "down" if apis_err else "flat")
        with r2c3:
            tph = total / max(active_buckets, 1)
            unit_lbl = "per day" if bucket_unit == "DAY" else "per hour"
            dd_tile("THROUGHPUT", f"{tph:.0f}",
                    f"{unit_lbl} · {active_buckets} bkt(s)", "flat")

        st.markdown("<div style='height:1.0rem'></div>", unsafe_allow_html=True)

        # ─── ZONE 3 · TIME-SERIES CHART ───
        section_label("TIMELINE")
        try:
            ts_df = run_query(
                f"""
                SELECT DATE_TRUNC('{bucket_unit}', INSERT_DATETIME_UTC) AS BUCKET,
                       API_NAME,
                       COUNT(*)                                         AS CALLS,
                       SUM(CASE WHEN STATUS_CODE = 200 THEN 1 ELSE 0 END) AS OK,
                       AVG(RESPONSE_TIME_SECONDS)                       AS AVG_RT
                FROM {META}.INGESTION_RESPONSE_LOG
                WHERE {where_sql}
                GROUP BY 1, 2
                ORDER BY 1
                """,
                params=params if params else None
            )
        except Exception as _e:
            ts_df = pd.DataFrame()
            st.caption(f"Time-series unavailable: {_e}")

        if _PLOTLY_OK and not ts_df.empty:
            ts_pivot = ts_df.pivot_table(
                index="BUCKET", columns="API_NAME",
                values="CALLS", aggfunc="sum", fill_value=0,
            ).sort_index()
            ts_agg = ts_df.groupby("BUCKET", as_index=False).agg(CALLS=("CALLS", "sum"), OK=("OK", "sum"))
            ts_agg["ERR_RATE"] = ((ts_agg["CALLS"] - ts_agg["OK"]) / ts_agg["CALLS"].clip(lower=1)) * 100

            fig_ts = go.Figure()
            for api_n in ts_pivot.columns:
                fig_ts.add_trace(go.Bar(
                    x=ts_pivot.index, y=ts_pivot[api_n],
                    name=str(api_n), marker_line_width=0,
                    hovertemplate=f"<b>{api_n}</b><br>%{{x}}<br>%{{y}} calls<extra></extra>",
                ))
            fig_ts.add_trace(go.Scatter(
                x=ts_agg["BUCKET"], y=ts_agg["ERR_RATE"],
                name="Error Rate %",
                line=dict(color="#ef4444", width=2, dash="dot"),
                yaxis="y2",
                hovertemplate="%{x}<br>Error rate: %{y:.1f}%<extra></extra>",
            ))
            fig_ts.update_layout(
                barmode="stack",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d0d0d",
                font=dict(color="#a1a1aa", family="JetBrains Mono", size=11),
                legend=dict(bgcolor="rgba(17,17,17,0.8)", bordercolor="#1f1f1f", borderwidth=1, font=dict(size=10)),
                margin=dict(l=10, r=10, t=10, b=10), height=240,
                xaxis=dict(showgrid=False, tickfont=dict(size=9)),
                yaxis=dict(title="Calls", gridcolor="#1f1f1f", zerolinecolor="#1f1f1f", title_font=dict(size=10)),
                yaxis2=dict(title="Error %", overlaying="y", side="right", range=[0, 100],
                            gridcolor="rgba(239,68,68,0.05)",
                            tickfont=dict(color="#ef4444", size=9),
                            title_font=dict(color="#ef4444", size=10)),
            )
            st.plotly_chart(fig_ts, use_container_width=True)
        elif not ts_df.empty:
            st.bar_chart(ts_df.pivot_table(index="BUCKET", columns="API_NAME", values="CALLS", aggfunc="sum", fill_value=0))

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # ─── ZONE 4 · TABBED DETAIL PANELS ───
        tab_feed, tab_health, tab_retries, tab_errors, tab_intel = st.tabs([
            "📡  Activity Feed", "🏥  Per-API Health", "🔁  Retry Analysis", "🚨  Incidents", "🧠  Error Intelligence",
        ])

        # — Activity Feed —
        with tab_feed:
            log_limit = st.slider("Show last N rows", 25, 500, 100, step=25, key="feed_limit")
            try:
                feed_logs = run_query(
                    f"""
                    SELECT API_NAME, API_URL, STATUS_CODE, RESPONSE_TIME_SECONDS,
                           INSERT_DATETIME_UTC, ERROR_MESSAGE_TEXT
                    FROM {META}.INGESTION_RESPONSE_LOG
                    WHERE {where_sql}
                    ORDER BY INSERT_DATETIME_UTC DESC
                    LIMIT {int(log_limit)}
                    """,
                    params=params if params else None
                )
            except Exception as _e:
                feed_logs = pd.DataFrame()
                st.caption(f"Feed unavailable: {_e}")

            if feed_logs.empty:
                empty_state("📭", "No activity", "Nothing in this window.")
            else:
                feed_logs["INSERT_DATETIME_UTC"] = pd.to_datetime(feed_logs["INSERT_DATETIME_UTC"])
                bucket_fmt = "%Y-%m-%d" if bucket_unit == "DAY" else "%Y-%m-%d %H:00"
                feed_logs["BUCKET_STR"] = feed_logs["INSERT_DATETIME_UTC"].dt.strftime(bucket_fmt)

                for bucket_str, group in feed_logs.groupby("BUCKET_STR", sort=False):
                    ok_in = int((group["STATUS_CODE"] == 200).sum())
                    fail_in = len(group) - ok_in
                    label = (
                        f"🕐 {bucket_str}  ·  {len(group)} calls"
                        + (f"  ·  ✓ {ok_in} ok" if ok_in else "")
                        + (f"  ·  ✗ {fail_in} failed" if fail_in else "")
                    )
                    with st.expander(label, expanded=(fail_in > 0)):
                        for _, row in group.iterrows():
                            stitch_row(row.get("API_NAME") or "—",
                                       row.get("API_URL") or "—",
                                       row.get("STATUS_CODE"))

        # — Per-API Health —
        with tab_health:
            try:
                health_df = run_query(
                    f"""
                    SELECT API_NAME,
                           COUNT(*)                                            AS CALLS,
                           SUM(CASE WHEN STATUS_CODE = 200 THEN 1 ELSE 0 END) AS OK,
                           ROUND(AVG(RESPONSE_TIME_SECONDS), 2)               AS AVG_RT,
                           ROUND(MAX(RESPONSE_TIME_SECONDS), 2)               AS MAX_RT,
                           MAX(INSERT_DATETIME_UTC)                           AS LAST_RUN
                    FROM {META}.INGESTION_RESPONSE_LOG
                    WHERE {where_sql}
                    GROUP BY API_NAME
                    ORDER BY (OK / NULLIF(CALLS, 0)) ASC NULLS FIRST
                    """,
                    params=params if params else None
                )
            except Exception as _e:
                health_df = pd.DataFrame()
                st.caption(f"Health unavailable: {_e}")

            if health_df.empty:
                empty_state("🏥", "No data", "No log activity in this window.")
            else:
                health_df["SUCCESS_RATE"] = (health_df["OK"].astype(float) / health_df["CALLS"].clip(lower=1) * 100).round(1)
                health_df["FAILS"] = health_df["CALLS"] - health_df["OK"]
                for _, h in health_df.iterrows():
                    sr_v = float(h["SUCCESS_RATE"])
                    h_status = "healthy" if sr_v >= 99 else ("warning" if sr_v >= 90 else "error")
                    bar_color = "#29B5E8" if sr_v >= 99 else ("#f59e0b" if sr_v >= 90 else "#ef4444")
                    last_run_v = h["LAST_RUN"]
                    last_run_s = pd.to_datetime(last_run_v).strftime("%Y-%m-%d %H:%M") if pd.notna(last_run_v) else "—"
                    cfg_card(
                        h["API_NAME"],
                        f"{sr_v}% success · {int(h['CALLS']):,} calls · avg {h['AVG_RT']}s · max {h['MAX_RT']}s",
                        badges=[
                            {"text": f"✓ {int(h['OK']):,}", "cls": "accent"},
                            {"text": f"✗ {int(h['FAILS']):,}", "cls": "danger" if h["FAILS"] > 0 else ""},
                        ],
                        meta=f"last run: {last_run_s}",
                        status=h_status,
                    )
                    st.markdown(
                        f"<div style='width:100%;height:3px;background:#1f1f1f;border-radius:2px;margin:-4px 0 8px;'>"
                        f"<div style='width:{sr_v}%;height:3px;background:{bar_color};border-radius:2px;'></div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        # — Retry Analysis —
        with tab_retries:
            st.caption("Pages where the framework had to retry — including transient errors that eventually succeeded.")
            try:
                retry_summary = run_query(
                    f"""
                    WITH base AS (
                        SELECT API_NAME, PAGE_NUMBER, ATTEMPT_NUMBER, STATUS_CODE,
                               ERROR_MESSAGE_TEXT, RESPONSE_TIME_SECONDS, IS_FINAL_ATTEMPT,
                               INSERT_DATETIME_UTC, API_URL
                        FROM {META}.INGESTION_RESPONSE_LOG
                        WHERE {where_sql}
                          AND PAGE_NUMBER IS NOT NULL
                          AND ATTEMPT_NUMBER IS NOT NULL
                    ),
                    grouped AS (
                        SELECT API_NAME, PAGE_NUMBER,
                               MIN(INSERT_DATETIME_UTC) AS RUN_STARTED_UTC,
                               MAX(INSERT_DATETIME_UTC) AS RUN_ENDED_UTC,
                               COUNT(*) AS ATTEMPTS,
                               MAX(CASE WHEN IS_FINAL_ATTEMPT THEN STATUS_CODE END) AS FINAL_STATUS,
                               MAX(CASE WHEN IS_FINAL_ATTEMPT AND STATUS_CODE = 200 THEN 'Recovered'
                                        WHEN IS_FINAL_ATTEMPT THEN 'Exhausted'
                                        ELSE NULL END) AS OUTCOME
                        FROM base
                        GROUP BY API_NAME, PAGE_NUMBER
                        HAVING COUNT(*) > 1
                    )
                    SELECT API_NAME, PAGE_NUMBER, ATTEMPTS, FINAL_STATUS, OUTCOME,
                           RUN_STARTED_UTC, RUN_ENDED_UTC
                    FROM grouped
                    ORDER BY RUN_STARTED_UTC DESC
                    LIMIT 200
                    """,
                    params=params if params else None
                )
            except Exception as _e:
                retry_summary = pd.DataFrame()
                st.caption(f"Drill-down unavailable: {_e}")

            if retry_summary.empty:
                empty_state("✅", "No retries", "Either no retries happened in this window, or the migration hasn't been applied.")
            else:
                rec_count = int((retry_summary["OUTCOME"] == "Recovered").sum())
                exh_count = int((retry_summary["OUTCOME"] == "Exhausted").sum())
                avg_attempts = float(retry_summary["ATTEMPTS"].mean())

                rm1, rm2, rm3 = st.columns(3)
                with rm1:
                    dd_tile("PAGES WITH RETRIES", len(retry_summary))
                with rm2:
                    dd_tile("RECOVERED", rec_count, "transient → 200", "up" if rec_count else "flat",
                            glow="ok" if rec_count else None)
                with rm3:
                    dd_tile("EXHAUSTED", exh_count, "all attempts failed" if exh_count else "none",
                            "down" if exh_count else "flat", glow="err" if exh_count else None)

                st.caption(f"Average attempts per retried page: **{avg_attempts:.2f}**")

                # Recovery funnel
                if _PLOTLY_OK:
                    funnel_total = len(retry_summary)
                    funnel_recovered = rec_count
                    funnel_exhausted = exh_count
                    fig_funnel = go.Figure(go.Funnel(
                        y=["Pages w/ retries", "Recovered", "Exhausted"],
                        x=[funnel_total, funnel_recovered, funnel_exhausted],
                        marker=dict(color=["#29B5E8", "#29B5E8", "#ef4444"]),
                        textinfo="value+percent initial",
                        connector=dict(line=dict(color="#1f1f1f", width=1)),
                    ))
                    fig_funnel.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d0d0d",
                        font=dict(color="#a1a1aa", family="JetBrains Mono", size=11),
                        margin=dict(l=0, r=0, t=0, b=0), height=180,
                    )
                    st.plotly_chart(fig_funnel, use_container_width=True)

                styled_dataframe(retry_summary)

                retry_summary["LABEL"] = (
                    retry_summary["API_NAME"].astype(str) + " — page " +
                    retry_summary["PAGE_NUMBER"].astype(str) + " (" +
                    retry_summary["ATTEMPTS"].astype(str) + " attempts, " +
                    retry_summary["OUTCOME"].fillna("—").astype(str) + ")"
                )
                pick = st.selectbox(
                    "Inspect attempt history",
                    [""] + retry_summary["LABEL"].tolist(),
                    key="retry_pick",
                )
                if pick:
                    sel_row = retry_summary[retry_summary["LABEL"] == pick].iloc[0]
                    sel_api = sel_row["API_NAME"]
                    sel_page = int(sel_row["PAGE_NUMBER"])
                    try:
                        attempts_df = run_query(
                            f"SELECT ATTEMPT_NUMBER, IS_FINAL_ATTEMPT, STATUS_CODE, "
                            f"RESPONSE_TIME_SECONDS, ERROR_MESSAGE_TEXT, INSERT_DATETIME_UTC, API_URL "
                            f"FROM {META}.INGESTION_RESPONSE_LOG "
                            f"WHERE API_NAME = ? AND PAGE_NUMBER = ? "
                            f"ORDER BY ATTEMPT_NUMBER",
                            params=[sel_api, sel_page]
                        )
                        if attempts_df.empty:
                            st.info("No attempt rows found.")
                        else:
                            st.caption(
                                f"**{len(attempts_df)} attempt(s)** for `{sel_api}` page `{sel_page}` — "
                                f"final status: `{attempts_df.iloc[-1]['STATUS_CODE']}`"
                            )
                            styled_dataframe(attempts_df)
                    except Exception as _e:
                        st.error(f"Could not load attempt history: {_e}")

        # — Incidents —
        with tab_errors:
            try:
                errors_df = run_query(
                    f"""
                    SELECT API_NAME, STATUS_CODE, ERROR_MESSAGE_TEXT,
                           API_URL, INSERT_DATETIME_UTC, RETRY_COUNT
                    FROM {META}.INGESTION_RESPONSE_LOG
                    WHERE {where_sql}
                      AND (STATUS_CODE != 200 OR STATUS_CODE IS NULL)
                    ORDER BY INSERT_DATETIME_UTC DESC
                    LIMIT 200
                    """,
                    params=params if params else None
                )
            except Exception as _e:
                errors_df = pd.DataFrame()
                st.caption(f"Incidents unavailable: {_e}")

            if errors_df.empty:
                empty_state("✅", "No incidents", f"All calls returned 200 in the last {time_range}.")
            else:
                if "ERROR_MESSAGE_TEXT" in errors_df.columns:
                    msg_series = errors_df["ERROR_MESSAGE_TEXT"].fillna(
                        "HTTP " + errors_df["STATUS_CODE"].astype("Int64").astype(str)
                    )
                    error_counts = msg_series.value_counts().head(5)
                    section_label("TOP ERROR PATTERNS")
                    for msg, count in error_counts.items():
                        st.markdown(
                            f"<div class='cfg-card error'>"
                            f"<div class='name' style='font-size:0.8rem;'>{str(msg)[:160]}</div>"
                            f"<div class='meta'>{count} occurrence(s)</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                st.divider()
                section_label("FULL INCIDENT LOG")
                styled_dataframe(errors_df)

        # — Error Intelligence —
        with tab_intel:
            st.caption("Each error code grouped, ranked, and explained. Click any code for likely causes, actions, and a deep-link to the affected API config.")

            try:
                error_freq_df = run_query(
                    f"""
                    SELECT
                        COALESCE(STATUS_CODE::STRING, 'NULL') AS CODE,
                        COUNT(*)                              AS OCCURRENCES,
                        COUNT(DISTINCT API_NAME)              AS APIS_AFFECTED,
                        MAX(INSERT_DATETIME_UTC)              AS LAST_SEEN,
                        MIN(INSERT_DATETIME_UTC)              AS FIRST_SEEN
                    FROM {META}.INGESTION_RESPONSE_LOG
                    WHERE {where_sql}
                      AND (STATUS_CODE != 200 OR STATUS_CODE IS NULL)
                    GROUP BY 1
                    ORDER BY OCCURRENCES DESC
                    """,
                    params=params if params else None
                )
            except Exception as _e:
                error_freq_df = pd.DataFrame()
                st.caption(f"Error intelligence unavailable: {_e}")

            try:
                error_api_df = run_query(
                    f"""
                    SELECT
                        COALESCE(STATUS_CODE::STRING, 'NULL') AS CODE,
                        API_NAME,
                        COUNT(*)                              AS OCCURRENCES,
                        MAX(INSERT_DATETIME_UTC)              AS LAST_SEEN,
                        ANY_VALUE(ERROR_MESSAGE_TEXT)         AS SAMPLE_MESSAGE
                    FROM {META}.INGESTION_RESPONSE_LOG
                    WHERE {where_sql}
                      AND (STATUS_CODE != 200 OR STATUS_CODE IS NULL)
                    GROUP BY 1, 2
                    ORDER BY 1, OCCURRENCES DESC
                    """,
                    params=params if params else None
                )
            except Exception:
                error_api_df = pd.DataFrame()

            if error_freq_df.empty:
                empty_state("✅", "No errors in this window",
                            f"All calls returned 200 in the last {time_range}.")
            else:
                total_errors = int(error_freq_df["OCCURRENCES"].sum())
                unique_codes = len(error_freq_df)
                most_common = str(error_freq_df.iloc[0]["CODE"])
                most_common_hits = int(error_freq_df.iloc[0]["OCCURRENCES"])

                s1, s2, s3 = st.columns(3)
                with s1:
                    dd_tile("TOTAL ERROR CALLS", f"{total_errors:,}", "non-200", "down", glow="err")
                with s2:
                    dd_tile("DISTINCT ERROR CODES", unique_codes, "types seen", "flat")
                with s3:
                    dd_tile("MOST FREQUENT", most_common, f"{most_common_hits:,} hits", "down", glow="err")

                st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                section_label("ERROR CODE BREAKDOWN")

                for _, erow in error_freq_df.iterrows():
                    code = str(erow["CODE"])
                    count = int(erow["OCCURRENCES"])
                    apis_hit = int(erow["APIS_AFFECTED"])
                    last_s = pd.to_datetime(erow["LAST_SEEN"]).strftime("%Y-%m-%d %H:%M") if pd.notna(erow["LAST_SEEN"]) else "—"
                    kb = ERROR_KNOWLEDGE.get(code, {})

                    sev = kb.get("severity", "warning")
                    icon = kb.get("icon", "❓")
                    label = kb.get("label", f"HTTP {code}")
                    cat = kb.get("category", "Unknown")
                    urgency = kb.get("urgency", "Investigate")

                    bar_pct = min(100, round(count / max(total_errors, 1) * 100, 1))
                    bar_color = "#ef4444" if sev == "error" else ("#f59e0b" if sev == "warning" else "#29B5E8")
                    card_status = "error" if sev == "error" else ("warning" if sev == "warning" else "healthy")
                    badge_cls_cat = "danger" if sev == "error" else "warn"

                    st.markdown(f"""
                    <div class='cfg-card {card_status}'>
                      <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;'>
                        <div>
                          <span style='font-family:var(--font-mono);font-size:1.4rem;font-weight:800;color:{bar_color};'>{icon} {code}</span>
                          <span style='font-family:var(--font-display);font-weight:700;font-size:0.95rem;color:var(--text-primary);margin-left:10px;'>{label}</span>
                        </div>
                        <div style='display:flex;gap:6px;align-items:center;flex-wrap:wrap;'>
                          <span class='badge {badge_cls_cat}'>{cat}</span>
                          <span class='badge accent'>{count:,} hits</span>
                          <span class='badge'>{apis_hit} API(s)</span>
                        </div>
                      </div>
                      <div style='margin:10px 0 4px;'>
                        <div style='width:100%;height:4px;background:#1f1f1f;border-radius:2px;'>
                          <div style='width:{bar_pct}%;height:4px;background:{bar_color};border-radius:2px;transition:width 0.4s ease;'></div>
                        </div>
                        <div style='font-family:var(--font-mono);font-size:0.6rem;color:var(--text-muted);margin-top:4px;'>
                          {bar_pct}% of all errors · last seen {last_s}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if kb:
                        with st.expander(f"📖  What is {code}? — {urgency}",
                                         expanded=(sev == "error" and code == most_common)):
                            k1, k2 = st.columns(2)
                            with k1:
                                st.markdown("**What happened**")
                                st.caption(kb["what_happened"])
                                st.markdown("**Likely causes**")
                                for cause in kb["likely_causes"]:
                                    st.caption(f"• {cause}")
                            with k2:
                                st.markdown("**Actions to take**")
                                for action in kb["actions"]:
                                    st.caption(f"→ {action}")
                                st.markdown("**Retry behaviour**")
                                st.caption(kb["retry_behaviour"])

                            if kb.get("snowflake_tip"):
                                st.markdown(
                                    f"""<div style='background:rgba(41,181,232,0.06);border:1px solid rgba(41,181,232,0.2);border-left:3px solid #29B5E8;border-radius:6px;padding:10px 14px;margin-top:8px;'>
                                      <div style='font-family:var(--font-mono);font-size:0.65rem;color:#29B5E8;font-weight:700;letter-spacing:1px;margin-bottom:4px;'>❄️ SNOWFLAKE TIP</div>
                                      <div style='font-size:0.78rem;color:var(--text-secondary);'>{kb["snowflake_tip"]}</div>
                                    </div>""",
                                    unsafe_allow_html=True
                                )

                            if not error_api_df.empty:
                                api_rows = error_api_df[error_api_df["CODE"] == code]
                                if not api_rows.empty:
                                    st.markdown("**Affected APIs**")
                                    styled_dataframe(
                                        api_rows[["API_NAME", "OCCURRENCES", "LAST_SEEN", "SAMPLE_MESSAGE"]],
                                        height=180,
                                    )
                                    # Quick-link buttons (one per affected API, max 4 to avoid clutter)
                                    visible_rows = api_rows.head(4)
                                    qa_cols = st.columns(max(len(visible_rows), 1))
                                    for idx, (_, api_row) in enumerate(visible_rows.iterrows()):
                                        with qa_cols[idx]:
                                            if st.button(
                                                f"⚙ {api_row['API_NAME']}",
                                                key=f"goto_manage_{code}_{api_row['API_NAME']}",
                                                use_container_width=True,
                                                help="Open this API in the Manage Existing tab",
                                            ):
                                                st.session_state["active_nav"] = "Manage API Configs"
                                                st.session_state["manage_api"] = api_row["API_NAME"]
                                                st.rerun()
                    else:
                        with st.expander(f"❓ Unknown code {code}"):
                            st.caption(
                                f"HTTP {code} is not in the built-in knowledge base. "
                                f"Check the [MDN HTTP status reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) "
                                "or the API's documentation."
                            )
                            if not error_api_df.empty:
                                api_rows = error_api_df[error_api_df["CODE"] == code]
                                if not api_rows.empty:
                                    styled_dataframe(api_rows, height=150)

# ─────────────────────────────────────────────
# TAB 5: View Raw Data
# ─────────────────────────────────────────────
elif nav_choice == "Data Explorer":
    section_label("DATA EXPLORER")
    st.header("Browse, Discover, Model")
    st.caption("Persistent context · dual-pane payload inspector · field-level SQL builder.")

    # ─── Initialise session state once ───
    if "de_api" not in st.session_state:
        st.session_state["de_api"] = "All"
    if "browse_page" not in st.session_state:
        st.session_state["browse_page"] = 0
    if "selected_hash" not in st.session_state:
        st.session_state["selected_hash"] = None

    # ─── Layout: left context panel + right working area ───
    left_ctx, right_work = st.columns([1, 3], gap="large")

    # ╔═══════════════════ LEFT CONTEXT PANEL ═══════════════════╗
    with left_ctx:
        section_label("DATA SOURCE")
        try:
            ls_tables = run_query(
                f"SELECT TABLE_NAME FROM {DB}.INFORMATION_SCHEMA.TABLES "
                f"WHERE TABLE_SCHEMA = 'RAW_LANDING' ORDER BY TABLE_NAME"
            )
            landing_tables = ls_tables["TABLE_NAME"].tolist() if not ls_tables.empty else ["API_RAW_DATA"]
        except Exception:
            landing_tables = ["API_RAW_DATA"]
        if "API_RAW_DATA" not in landing_tables:
            landing_tables.insert(0, "API_RAW_DATA")

        de_table = st.selectbox(
            "Landing Table",
            landing_tables,
            key="de_table_picker",
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        section_label("FILTER BY API")

        try:
            api_counts_df = run_query(
                f"SELECT API_NAME, COUNT(*) AS RECORDS, MAX(INGEST_TS) AS LAST_INGEST, "
                f"COUNT(DISTINCT PAYLOAD_HASH) AS UNIQUE_PAYLOADS "
                f"FROM {RAW}.{de_table} GROUP BY API_NAME ORDER BY RECORDS DESC"
            )
            api_options_rich = api_counts_df.to_dict("records") if not api_counts_df.empty else []
        except Exception:
            api_options_rich = []

        total_records = sum(int(r.get("RECORDS") or 0) for r in api_options_rich)
        api_picker_options = [f"All APIs ({total_records:,})"] + [
            f"{r['API_NAME']} ({int(r.get('RECORDS') or 0):,})"
            for r in api_options_rich
        ]

        # Map display label → actual API_NAME (or "All")
        if "de_api" not in st.session_state:
            st.session_state["de_api"] = "All"

        # Find current display label
        current_label = api_picker_options[0]
        for opt in api_picker_options[1:]:
            if opt.split(" (")[0] == st.session_state["de_api"]:
                current_label = opt
                break

        picked_label = st.selectbox(
            "API",
            api_picker_options,
            index=api_picker_options.index(current_label) if current_label in api_picker_options else 0,
            key="de_api_picker",
            label_visibility="collapsed",
        )
        # Decode back to API_NAME
        new_api = "All" if picked_label.startswith("All APIs") else picked_label.rsplit(" (", 1)[0]
        if new_api != st.session_state["de_api"]:
            st.session_state["de_api"] = new_api
            st.session_state["browse_page"] = 0
            st.session_state["selected_hash"] = None
            st.rerun()
        de_api = st.session_state["de_api"]

        # Quick context card
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if de_api != "All" and api_options_rich:
            api_meta = next((r for r in api_options_rich if r["API_NAME"] == de_api), {})
            section_label("CONTEXT")
            st.markdown(f"""
            <div class='cfg-card healthy' style='padding:12px 14px;'>
              <div class='name' style='font-size:0.85rem;'>{de_api}</div>
              <div class='endpoint'>{int(api_meta.get('RECORDS', 0)):,} records</div>
              <div class='badges'>
                <span class='badge accent'>{int(api_meta.get('UNIQUE_PAYLOADS', 0)):,} unique</span>
              </div>
              <div class='meta'>last ingest: {str(api_meta.get('LAST_INGEST', ''))[:16]}</div>
            </div>
            """, unsafe_allow_html=True)

    # ╔══════════════════ RIGHT WORKING AREA ════════════════════╗
    with right_work:
        tab_browse, tab_schema, tab_builder = st.tabs([
            "🗂  Browse Payloads", "🔬  Schema Discovery", "🔧  SQL Builder",
        ])

        # ───── BROWSE PAYLOADS ─────
        with tab_browse:
            bc1, bc2, bc3 = st.columns([2, 1, 1])
            with bc1:
                st.text_input(
                    "Search PAYLOAD_HASH",
                    placeholder="Paste a hash to jump to a record…",
                    label_visibility="collapsed",
                    key="browse_hash_search",
                )
            with bc2:
                sort_by = st.selectbox(
                    "Sort",
                    ["Newest first", "Oldest first", "Errors first"],
                    label_visibility="collapsed",
                    key="browse_sort",
                )
            with bc3:
                page_size = st.select_slider(
                    "Page size",
                    options=[10, 25, 50, 100],
                    value=10,
                    label_visibility="collapsed",
                    key="browse_page_size",
                )

            sort_sql = {
                "Newest first": "ORDER BY INGEST_TS DESC",
                "Oldest first": "ORDER BY INGEST_TS ASC",
                "Errors first": "ORDER BY STATUS_CODE ASC NULLS FIRST, INGEST_TS DESC",
            }[sort_by]

            api_where = "WHERE API_NAME = ?" if de_api != "All" else ""
            api_params = [de_api] if de_api != "All" else None
            offset = st.session_state["browse_page"] * page_size

            try:
                records_df = run_query(
                    f"SELECT PAYLOAD_HASH, API_NAME, STATUS_CODE, INGEST_TS, URL_ATTEMPTED, "
                    f"LENGTH(PAYLOAD::STRING) AS PAYLOAD_BYTES "
                    f"FROM {RAW}.{de_table} {api_where} {sort_sql} "
                    f"LIMIT {int(page_size)} OFFSET {int(offset)}",
                    params=api_params,
                )
            except Exception as _e:
                records_df = pd.DataFrame()
                st.caption(f"Records query failed: {_e}")

            if records_df.empty:
                empty_state("📭", "No records",
                            "Run an ingestion first, then browse payloads here.")
            else:
                # Summary tiles
                try:
                    total_q = run_query(
                        f"SELECT COUNT(*) AS C FROM {RAW}.{de_table} {api_where}",
                        params=api_params,
                    )
                    total_recs = int(total_q["C"].iloc[0])
                except Exception:
                    total_recs = len(records_df)

                try:
                    where_ok = (api_where + (" AND" if api_where else "WHERE")) + " STATUS_CODE = 200"
                    ok_q = run_query(
                        f"SELECT COUNT(*) AS C FROM {RAW}.{de_table} {where_ok}",
                        params=api_params,
                    )
                    ok_recs = int(ok_q["C"].iloc[0])
                except Exception:
                    ok_recs = 0

                try:
                    size_q = run_query(
                        f"SELECT ROUND(AVG(LENGTH(PAYLOAD::STRING))/1024, 1) AS AVG_KB, "
                        f"ROUND(MAX(LENGTH(PAYLOAD::STRING))/1024, 1) AS MAX_KB "
                        f"FROM {RAW}.{de_table} {api_where}",
                        params=api_params,
                    )
                    avg_kb_raw = size_q["AVG_KB"].iloc[0]
                    max_kb_raw = size_q["MAX_KB"].iloc[0]
                    avg_kb = 0.0 if avg_kb_raw is None or pd.isna(avg_kb_raw) else float(avg_kb_raw)
                    max_kb = 0.0 if max_kb_raw is None or pd.isna(max_kb_raw) else float(max_kb_raw)
                except Exception:
                    avg_kb = max_kb = 0.0

                ok_pct = round(ok_recs / max(total_recs, 1) * 100, 1)
                sm1, sm2, sm3 = st.columns(3)
                with sm1:
                    dd_tile("TOTAL RECORDS", f"{total_recs:,}", live=True)
                with sm2:
                    dd_tile("CLEAN RECORDS", f"{ok_pct}%",
                            f"{ok_recs:,} status 200",
                            "up" if ok_pct >= 99 else "down")
                with sm3:
                    dd_tile("AVG SIZE", f"{avg_kb:.1f} KB",
                            f"max: {max_kb:.1f} KB", "flat")

                st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

                # Dual-pane: list (left) + inspector (right)
                list_col, inspect_col = st.columns([2, 3])

                with list_col:
                    section_label("RECORDS")
                    for _, rec in records_df.iterrows():
                        h = rec["PAYLOAD_HASH"]
                        sc = rec.get("STATUS_CODE")
                        ts = str(rec.get("INGEST_TS", ""))[:16]
                        api_n = rec.get("API_NAME", "")
                        size_b = int(rec.get("PAYLOAD_BYTES") or 0)
                        is_sel = st.session_state["selected_hash"] == h
                        sc_color = "#29B5E8" if sc == 200 else ("#ef4444" if sc is not None and not pd.isna(sc) else "#f59e0b")
                        sc_label = str(int(sc)) if sc is not None and not pd.isna(sc) else "ERR"
                        h_short = (str(h) or "")[:16] + "…"

                        st.markdown(f"""
                        <div style='background:{"var(--bg-elevated)" if is_sel else "var(--bg-card)"};
                                    border:1px solid {"rgba(41,181,232,0.4)" if is_sel else "var(--border-subtle)"};
                                    border-left:3px solid {sc_color};
                                    border-radius:6px;padding:8px 12px;margin-bottom:4px;'>
                          <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <span style='font-family:var(--font-mono);font-size:0.65rem;color:var(--text-muted);'>{h_short}</span>
                            <span style='font-family:var(--font-mono);font-size:0.7rem;font-weight:700;color:{sc_color};'>{sc_label}</span>
                          </div>
                          <div style='font-size:0.7rem;color:var(--text-secondary);margin-top:3px;'>{api_n} · {ts}</div>
                          <div style='font-size:0.65rem;color:var(--text-muted);margin-top:2px;'>{size_b:,} bytes</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("Inspect →", key=f"sel_rec_{h}", use_container_width=True):
                            st.session_state["selected_hash"] = h
                            st.rerun()

                with inspect_col:
                    section_label("PAYLOAD INSPECTOR")
                    sel_h = st.session_state.get("selected_hash")
                    if not sel_h:
                        st.markdown("""
                        <div style='background:var(--bg-card);border:1px dashed var(--border-strong);
                                    border-radius:8px;padding:40px;text-align:center;margin-top:24px;'>
                          <div style='font-size:1.5rem;'>👈</div>
                          <div style='color:var(--text-secondary);font-size:0.85rem;margin-top:8px;'>
                            Select a record to inspect its payload
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        try:
                            full = run_query(
                                f"SELECT * FROM {RAW}.{de_table} WHERE PAYLOAD_HASH = ?",
                                params=[sel_h],
                            )
                        except Exception as _e:
                            full = pd.DataFrame()
                            st.caption(f"Lookup failed: {_e}")

                        if full.empty:
                            st.info("Record not found.")
                        else:
                            r = full.iloc[0]
                            sc_val = r.get("STATUS_CODE")
                            sc_col = "#29B5E8" if sc_val == 200 else "#ef4444"
                            sc_disp = str(int(sc_val)) if sc_val is not None and not pd.isna(sc_val) else "ERR"
                            ingest_ts = str(r.get("INGEST_TS", ""))[:16]
                            payload_str = str(r.get("PAYLOAD") or "")
                            pay_size = len(payload_str)

                            mc1, mc2, mc3 = st.columns(3)
                            with mc1:
                                dd_tile("STATUS", sc_disp, status_pill=False)
                            with mc2:
                                dd_tile("INGESTED", ingest_ts, status_pill=False)
                            with mc3:
                                dd_tile("SIZE", f"{pay_size/1024:.1f}KB", status_pill=False)

                            st.markdown(
                                f"<div style='font-family:var(--font-mono);font-size:0.65rem;"
                                f"color:var(--text-muted);margin:8px 0 4px;word-break:break-all;'>"
                                f"🔗 {r.get('URL_ATTEMPTED', '—')}</div>",
                                unsafe_allow_html=True
                            )
                            try:
                                payload_obj = json.loads(payload_str) if payload_str else {}
                                st.json(payload_obj, expanded=True)
                            except Exception:
                                st.code(payload_str, language="json")

                            st.download_button(
                                "⬇ Download Payload JSON",
                                data=payload_str,
                                file_name=f"{str(sel_h)[:12]}.json",
                                mime="application/json",
                                use_container_width=True,
                                key=f"dl_payload_{sel_h}",
                            )

                # Pagination bar
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                total_pages = max(1, -(-total_recs // page_size))
                pg1, pg2, pg3 = st.columns([1, 3, 1])
                with pg1:
                    if st.button("← Prev", use_container_width=True,
                                 disabled=(st.session_state["browse_page"] == 0),
                                 key="browse_prev"):
                        st.session_state["browse_page"] -= 1
                        st.rerun()
                with pg2:
                    st.markdown(
                        f"<div style='text-align:center;font-family:var(--font-mono);"
                        f"font-size:0.72rem;color:var(--text-muted);padding-top:8px;'>"
                        f"Page {st.session_state['browse_page'] + 1} of {total_pages}"
                        f" · {total_recs:,} total records</div>",
                        unsafe_allow_html=True
                    )
                with pg3:
                    if st.button("Next →", use_container_width=True,
                                 disabled=(st.session_state["browse_page"] >= total_pages - 1),
                                 key="browse_next"):
                        st.session_state["browse_page"] += 1
                        st.rerun()

        # ───── SCHEMA DISCOVERY ─────
        with tab_schema:
            st.markdown("#### Step 1 · Configure Sample")
            cfg_c1, cfg_c2, cfg_c3 = st.columns([2, 1, 1])
            with cfg_c1:
                ds_records_path = st.text_input(
                    "Records JSON Path",
                    value="data",
                    key="ds_records_path",
                    help="Dotted path to the array inside PAYLOAD. "
                         "Leave blank if PAYLOAD is the record itself."
                )
            with cfg_c2:
                ds_sample = st.number_input(
                    "Sample Size",
                    min_value=10, max_value=2000,
                    value=int(st.session_state.get("pref_sample_size", 100)),
                    step=10, key="ds_sample",
                )
            with cfg_c3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                discover_clicked = st.button(
                    "🔬 Discover Schema",
                    type="primary",
                    use_container_width=True,
                    key="btn_ds_discover",
                )

            if ds_records_path:
                st.caption(f"Will extract records from: `PAYLOAD:{ds_records_path}` (expects an array).")
            else:
                st.caption("No path set — treats PAYLOAD itself as a single record.")

            if discover_clicked:
                try:
                    where_clause = ""
                    params = []
                    if de_api != "All":
                        where_clause = "WHERE API_NAME = ?"
                        params = [de_api]
                    sample_df = run_query(
                        f"SELECT PAYLOAD FROM {RAW}.{de_table} {where_clause} LIMIT {int(ds_sample)}",
                        params=params if params else None,
                    )
                    if sample_df.empty:
                        st.warning("No rows returned for the selected filter.")
                    else:
                        path_types = {}
                        path_counts = {}
                        total_records = 0
                        for _, srow in sample_df.iterrows():
                            payload = _ds_parse_payload(srow["PAYLOAD"])
                            if payload is None:
                                continue
                            records = _ds_collect_records(payload, (ds_records_path or "").strip())
                            for rec in records:
                                total_records += 1
                                for path, val in _ds_walk(rec):
                                    t = _ds_infer_type(val)
                                    path_types.setdefault(path, set()).add(t)
                                    path_counts[path] = path_counts.get(path, 0) + 1
                        if total_records == 0:
                            st.warning("No records found at the given path.")
                        else:
                            schema_rows = []
                            for path, types in sorted(path_types.items()):
                                preferred = ["TIMESTAMP_TZ", "BOOLEAN", "NUMBER", "FLOAT", "OBJECT", "ARRAY", "STRING"]
                                chosen = next((t for t in preferred if t in types), "VARIANT")
                                coverage_pct = round(100.0 * path_counts[path] / total_records, 1)
                                schema_rows.append({
                                    "PATH": path, "TYPE": chosen,
                                    "COVERAGE_%": coverage_pct,
                                    "OBSERVED_TYPES": ", ".join(sorted(types)),
                                })
                            schema_df = pd.DataFrame(schema_rows)
                            st.session_state["ds_schema_df"] = schema_df
                            st.session_state["ds_schema_table"] = de_table
                            st.session_state["ds_schema_api"] = de_api
                            st.session_state["ds_schema_records_path"] = (ds_records_path or "").strip()
                            st.session_state["ds_schema_total"] = total_records
                            quality = {}
                            for path, types in path_types.items():
                                vals_seen = path_counts.get(path, 0)
                                null_rate = 1 - (vals_seen / max(total_records, 1))
                                quality[path] = {
                                    "null_rate": round(null_rate * 100, 1),
                                    "type_conflict": len(types) > 1,
                                    "types": sorted(types),
                                }
                            st.session_state["ds_quality"] = quality
                            st.success(
                                f"Discovered **{len(schema_rows)} fields** across "
                                f"**{total_records:,} records** from {ds_sample} payloads."
                            )
                except Exception as _e:
                    st.error(f"Schema discovery failed: {_e}")

            if ("ds_schema_df" in st.session_state
                and st.session_state.get("ds_schema_api") == de_api
                and not st.session_state["ds_schema_df"].empty):

                sch_df = st.session_state["ds_schema_df"]
                quality = st.session_state.get("ds_quality", {})

                full_cov = int((sch_df["COVERAGE_%"] >= 99.9).sum())
                partial_cov = int(((sch_df["COVERAGE_%"] < 99.9) & (sch_df["COVERAGE_%"] > 0)).sum())
                conflicts = sum(1 for v in quality.values() if v.get("type_conflict"))

                kq1, kq2, kq3, kq4 = st.columns(4)
                with kq1:
                    dd_tile("FIELDS", len(sch_df), "total", "flat")
                with kq2:
                    pct = round(full_cov / max(len(sch_df), 1) * 100)
                    dd_tile("FULL COVERAGE", full_cov, f"{pct}%",
                            "up" if full_cov == len(sch_df) else "flat",
                            glow="ok" if full_cov == len(sch_df) else None)
                with kq3:
                    dd_tile("PARTIAL FIELDS", partial_cov,
                            "sparse in some records",
                            "down" if partial_cov else "flat")
                with kq4:
                    dd_tile("TYPE CONFLICTS", conflicts,
                            "multi-type fields",
                            "down" if conflicts else "flat",
                            glow="warn" if conflicts else None)

                st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                section_label("FIELD CATALOGUE")

                display_df = sch_df.copy()
                display_df["NULL_RATE_%"] = display_df["PATH"].map(lambda p: quality.get(p, {}).get("null_rate", 0))
                display_df["TYPE_CONFLICT"] = display_df["PATH"].map(
                    lambda p: "⚠ Yes" if quality.get(p, {}).get("type_conflict") else "✓ No"
                )

                qf1, qf2, qf3 = st.columns(3)
                with qf1:
                    show_partial = st.checkbox("Partial only", key="sch_show_partial")
                with qf2:
                    show_conflicts = st.checkbox("Conflicts only", key="sch_show_conflicts")
                with qf3:
                    field_search = st.text_input(
                        "Search fields",
                        placeholder="Filter by path…",
                        label_visibility="collapsed",
                        key="sch_field_search",
                    )

                view_sch = display_df.copy()
                if show_partial:
                    view_sch = view_sch[view_sch["COVERAGE_%"] < 99.9]
                if show_conflicts:
                    view_sch = view_sch[view_sch["TYPE_CONFLICT"] == "⚠ Yes"]
                if field_search:
                    view_sch = view_sch[view_sch["PATH"].str.lower().str.contains(field_search.lower(), na=False)]

                styled_dataframe(
                    view_sch[["PATH", "TYPE", "COVERAGE_%", "NULL_RATE_%", "TYPE_CONFLICT", "OBSERVED_TYPES"]]
                )

                if conflicts > 0:
                    with st.expander(
                        f"⚠ {conflicts} field(s) have type conflicts",
                        expanded=False
                    ):
                        for fpath, q in quality.items():
                            if q.get("type_conflict"):
                                ts = "".join(f"<span class='badge warn'>{t}</span>" for t in q["types"])
                                st.markdown(f"""
                                <div class='cfg-card warning'>
                                  <div class='name' style='font-size:0.82rem;'>{fpath}</div>
                                  <div class='badges'>{ts}</div>
                                  <div class='meta'>Recommended: VARIANT (safe) or STRING (lossy but universal)</div>
                                </div>
                                """, unsafe_allow_html=True)

                st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                st.caption("Switch to the **🔧 SQL Builder** tab to generate a flattened view from this schema.")

        # ───── SQL BUILDER ─────
        with tab_builder:
            section_label("FLATTENED VIEW GENERATOR")

            has_schema = (
                "ds_schema_df" in st.session_state
                and not st.session_state["ds_schema_df"].empty
                and st.session_state.get("ds_schema_api") == de_api
            )
            if not has_schema:
                empty_state(
                    "🔬", "No schema for this API yet",
                    "Run <strong>🔬 Schema Discovery</strong> first, then come back to generate the SQL view."
                )
            else:
                sch_df = st.session_state["ds_schema_df"]

                vb1, vb2, vb3 = st.columns([2, 1, 1])
                with vb1:
                    safe_default = (
                        f"V_{re.sub(r'[^A-Za-z0-9_]', '_', de_api)}" if de_api != "All"
                        else f"V_{de_table}_FLAT"
                    )
                    ds_view_name = st.text_input("View Name", value=safe_default, key="ds_view_name")
                with vb2:
                    type_strategy = st.selectbox(
                        "Type Strategy",
                        ["Inferred", "All STRING (safe)", "All VARIANT (safe++)"],
                        key="ds_type_strategy",
                    )
                with vb3:
                    include_meta = st.checkbox(
                        "Include framework cols",
                        value=True,
                        key="ds_include_meta",
                    )

                section_label("FIELD SELECTION")
                st.caption("Tick / untick fields, then click **Apply Selection** to regenerate the SQL. Includes quick-pick presets to save clicks.")

                # Initialise per-API selection state once
                sel_state_key = f"ds_field_sel__{de_api}__{de_table}"
                if sel_state_key not in st.session_state:
                    # Default: all fields selected
                    st.session_state[sel_state_key] = {str(p): True for p in sch_df["PATH"].tolist()}
                # Make sure any new paths discovered are added
                for p in sch_df["PATH"].tolist():
                    st.session_state[sel_state_key].setdefault(str(p), True)

                # ── Quick-pick presets (rerun-cheap, mutate session_state then rerun) ──
                pp1, pp2, pp3, pp4 = st.columns(4)
                with pp1:
                    if st.button("✓ Select all", use_container_width=True, key="ds_pp_all"):
                        for p in sch_df["PATH"]:
                            st.session_state[sel_state_key][str(p)] = True
                        st.rerun()
                with pp2:
                    if st.button("Only ≥ 99% coverage", use_container_width=True, key="ds_pp_full"):
                        for _, fr in sch_df.iterrows():
                            st.session_state[sel_state_key][str(fr["PATH"])] = bool(fr["COVERAGE_%"] >= 99.0)
                        st.rerun()
                with pp3:
                    if st.button("Drop type conflicts", use_container_width=True, key="ds_pp_no_conflicts"):
                        quality_local = st.session_state.get("ds_quality", {})
                        for p in sch_df["PATH"]:
                            if quality_local.get(str(p), {}).get("type_conflict"):
                                st.session_state[sel_state_key][str(p)] = False
                        st.rerun()
                with pp4:
                    if st.button("✗ Clear all", use_container_width=True, key="ds_pp_none"):
                        for p in sch_df["PATH"]:
                            st.session_state[sel_state_key][str(p)] = False
                        st.rerun()

                # ── Form: checkboxes + Apply (no rerun until submit) ──
                from collections import defaultdict
                field_groups = defaultdict(list)
                for _, fr in sch_df.iterrows():
                    top = str(fr["PATH"]).split(".")[0]
                    field_groups[top].append(fr.to_dict())

                with st.form("ds_field_selection_form", clear_on_submit=False):
                    pending_selection = {}
                    for group_name, fields in field_groups.items():
                        with st.expander(f"📁 {group_name}  ({len(fields)} fields)",
                                         expanded=len(field_groups) <= 3):
                            for fd in fields:
                                path = str(fd["PATH"])
                                cov = float(fd["COVERAGE_%"])
                                ftype = fd["TYPE"]
                                pending_selection[path] = st.checkbox(
                                    f"`{path}`  ·  {ftype}  ·  {cov}%",
                                    value=bool(st.session_state[sel_state_key].get(path, True)),
                                    key=f"field_form_{de_api}_{path}",
                                )

                    apply_clicked = st.form_submit_button(
                        "Apply Selection",
                        type="primary",
                        use_container_width=True,
                    )

                if apply_clicked:
                    # Persist the new selection
                    for k, v in pending_selection.items():
                        st.session_state[sel_state_key][k] = v
                    st.toast("Field selection applied — SQL regenerated below.", icon="✅")

                # Build the actually-selected list from persisted state
                selected_fields = []
                for _, fr in sch_df.iterrows():
                    if st.session_state[sel_state_key].get(str(fr["PATH"]), True):
                        selected_fields.append(fr.to_dict())

                st.caption(f"**{len(selected_fields)}** of {len(sch_df)} fields will be in the view.")

                section_label("GENERATED SQL")
                type_map = {
                    "STRING": "STRING", "NUMBER": "NUMBER", "FLOAT": "FLOAT",
                    "BOOLEAN": "BOOLEAN", "TIMESTAMP_TZ": "TIMESTAMP_TZ",
                    "OBJECT": "VARIANT", "ARRAY": "ARRAY", "VARIANT": "VARIANT",
                }
                cols_sql = []
                if include_meta:
                    cols_sql += [
                        "    base.INGEST_TS",
                        "    base.API_NAME",
                        "    base.STATUS_CODE",
                        "    base.URL_ATTEMPTED",
                    ]
                for fd in selected_fields:
                    path = fd["PATH"]
                    ftype = fd["TYPE"]
                    if type_strategy == "Inferred":
                        t = type_map.get(ftype, "STRING")
                    elif type_strategy == "All VARIANT (safe++)":
                        t = "VARIANT"
                    else:
                        t = "STRING"
                    access = "rec.value"
                    for part in path.split("."):
                        access += f":{part}"
                    alias = re.sub(r"[^A-Za-z0-9_]", "_", path).upper()
                    cols_sql.append(f"    {access}::{t} AS {alias}")

                rp = st.session_state.get("ds_schema_records_path", "")
                from_clause = (
                    f"FROM {RAW}.{st.session_state['ds_schema_table']} base,\n"
                    f"     LATERAL FLATTEN(input => base.PAYLOAD"
                    + (f":{rp}" if rp else "") + ") rec"
                )
                api_filter_sql = ""
                if de_api != "All":
                    api_filter_sql = f"\nWHERE base.API_NAME = '{escape_sql_literal(de_api)}'"
                safe_view = re.sub(r"[^A-Za-z0-9_]", "_", ds_view_name) if ds_view_name else "V_FLAT"
                view_ddl = (
                    f"-- Generated by Tiger SnowSync · Data Explorer\n"
                    f"-- API: {de_api} · {len(selected_fields)} fields\n\n"
                    f"CREATE OR REPLACE VIEW {RAW}.{safe_view} AS\nSELECT\n"
                    + ",\n".join(cols_sql) + "\n"
                    + from_clause + api_filter_sql + ";"
                )
                st.code(view_ddl, language="sql")

                act1, act2, act3 = st.columns(3)
                with act1:
                    if st.button("▶ Create View",
                                 type="primary",
                                 use_container_width=True,
                                 key="btn_create_view"):
                        if not is_safe_name(safe_view):
                            st.error("Invalid view name.")
                        elif not selected_fields:
                            st.warning("Select at least one field.")
                        else:
                            try:
                                exec_sql(view_ddl)
                                st.toast(f"View {RAW}.{safe_view} created ({len(selected_fields)} fields)", icon="✅")
                            except Exception as e:
                                st.error(f"Create view failed: {str(e)}")
                with act2:
                    st.download_button(
                        "⬇ Download DDL",
                        data=view_ddl,
                        file_name=f"{safe_view}.sql",
                        mime="text/sql",
                        use_container_width=True,
                        key="btn_dl_ddl",
                    )
                with act3:
                    if st.button("👁 Preview View", use_container_width=True, key="btn_preview_view"):
                        try:
                            preview = run_query(f"SELECT * FROM {RAW}.{safe_view} LIMIT 10")
                            st.session_state["view_preview"] = preview
                        except Exception:
                            st.warning("View doesn't exist yet. Create it first, then preview.")

                if "view_preview" in st.session_state and st.session_state["view_preview"] is not None:
                    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                    section_label("PREVIEW · FIRST 10 ROWS")
                    styled_dataframe(st.session_state["view_preview"])

# ─────────────────────────────────────────────
# TAB 6: Task Scheduler (6-zone redesign)
# ─────────────────────────────────────────────
elif nav_choice == "Task Scheduler":
    from tiger.pages import scheduler as page_scheduler
    page_scheduler.render(default_warehouse=_wh)

# ─────────────────────────────────────────────
# HELP: Pipeline Overview
# ─────────────────────────────────────────────
elif nav_choice == "Pipeline Overview":
    from tiger.pages import help as page_help
    page_help.render()
