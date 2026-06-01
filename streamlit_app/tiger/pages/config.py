"""Tiger SnowSync — Manage API Configs page."""
import re
import json

import streamlit as st
import pandas as pd

try:
    from streamlit_searchbox import st_searchbox
    _SEARCHBOX_OK = True
except Exception:
    _SEARCHBOX_OK = False

from tiger.helpers import (
    section_label, cfg_card, styled_dataframe, active_pill,
)
from tiger.db import (
    DB, META, RAW,
    is_safe_name, escape_sql_literal,
    run_query, exec_sql,
    rebuild_ingestor,
    get_secrets_df, get_allowed_hosts,
    extract_url_host, check_host_allowed,
)


def _is_valid_json(s):
    try:
        json.loads(s)
        return True
    except Exception:
        return False


def render() -> None:
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

    from tiger.helpers import dd_tile

    with list_tab:
        overall_glow = "err" if gap_count > 0 else ("warn" if inactive_count > 0 else "ok")

        dd_tile("REGISTERED APIs", len(configs), f"{active_count} active · {gap_count} gap",
                "up" if gap_count == 0 else "down", live=True, size="hero", glow=overall_glow)

        st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)

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

        st.markdown(
            "<div class='legend-bar'>"
            "<span class='legend-item'><span class='legend-dot healthy'></span>Healthy</span>"
            "<span class='legend-item'><span class='legend-dot warning'></span>Network Gap</span>"
            "<span class='legend-item'><span class='legend-dot error'></span>Error</span>"
            "<span class='legend-item'><span class='legend-dot inactive'></span>Inactive</span>"
            "</div>",
            unsafe_allow_html=True
        )

        api_stats = {}
        try:
            stats_df = run_query(
                f"SELECT API_NAME, LAST_RUN_TIME AS LAST_RUN, "
                f"LAST_RUN_RECORDS AS TOTAL_CALLS, "
                f"LAST_RUN_STATUS "
                f"FROM {META}.V_ACTIVE_API_STATUS"
            )
            for _, sr in stats_df.iterrows():
                total = int(sr.get("TOTAL_CALLS") or 0) if not pd.isna(sr.get("TOTAL_CALLS")) else 0
                api_stats[sr["API_NAME"]] = {
                    "last_run": sr.get("LAST_RUN"),
                    "total":    total,
                    "ok":       total if sr.get("LAST_RUN_STATUS") == "SUCCESS" else 0,
                }
        except Exception:
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
                    default_options=all_api_names[:20],
                )
                st.session_state["cfg_search"] = picked or ""
            else:
                search_options = [""] + all_api_names
                picked = st.selectbox(
                    "🔍  Search APIs",
                    search_options,
                    index=0,
                    key="cfg_search_select",
                    placeholder="Search or select an API…",
                    label_visibility="collapsed",
                )
                st.session_state["cfg_search"] = picked or ""

        st.markdown(
            f"<div class='chip-bar'>"
            f"<span class='chip {'active' if filter_choice=='All' else 'muted'}'>● ALL {len(configs)}</span>"
            f"<span class='chip {'active' if filter_choice=='Active' else 'muted'}'>✓ ACTIVE {active_count}</span>"
            f"<span class='chip {'muted' if filter_choice!='Inactive' else 'active'}'>○ INACTIVE {inactive_count}</span>"
            f"<span class='chip {'warn' if filter_choice=='Network Gap' or gap_count>0 else 'muted'}'>⚠ NETWORK GAP {gap_count}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        view_df = configs.copy()
        if filter_choice == "Active":
            view_df = view_df[view_df["ACTIVE_FLAG"] == True]
        elif filter_choice == "Inactive":
            view_df = view_df[view_df["ACTIVE_FLAG"] == False]
        elif filter_choice == "Network Gap":
            view_df = view_df[view_df["API_NAME"].isin(network_gap_apis)]

        search_q = (st.session_state.get("cfg_search") or "").strip()
        if search_q:
            if search_q in all_api_names:
                view_df = view_df[view_df["API_NAME"] == search_q]
            else:
                view_df = view_df[view_df["API_NAME"].astype(str).str.lower().str.contains(search_q.lower(), na=False)]

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

                created_ts = r.get("CREATED_TS")
                if created_ts is not None and not pd.isna(created_ts):
                    try:
                        meta_parts.append(f"created: {pd.to_datetime(created_ts).strftime('%Y-%m-%d %H:%M')}")
                    except Exception:
                        meta_parts.append(f"created: {created_ts}")

                if is_incremental:
                    lsv = r.get("LAST_SYNC_VALUE")
                    if lsv and not pd.isna(lsv):
                        meta_parts.append(f"watermark: {lsv}")

                meta = " · ".join(meta_parts)

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

            if not show_all and total_visible > cards_per_page:
                if st.button(f"Show all ({total_visible})", use_container_width=True, key="cfg_show_all_btn"):
                    st.session_state["cfg_show_all"] = True
                    st.rerun()
            elif show_all and total_visible > cards_per_page:
                if st.button("Collapse to 10", use_container_width=True, key="cfg_collapse_btn"):
                    st.session_state["cfg_show_all"] = False
                    st.rerun()

        st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

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

        st.markdown("#### 🌐  Step 1: Connectivity")
        with st.container(border=True):
            api_name = st.text_input("API_NAME (unique key)", key=f"new_api_name_{fv}")

            existing_apis = set(configs["API_NAME"].tolist()) if not configs.empty else set()
            if api_name and api_name in existing_apis:
                st.warning(f"'{api_name}' already exists. Choose a different name.")

            endpoint_url = st.text_input("ENDPOINT_URL", key=f"new_url_{fv}")

            if endpoint_url and not endpoint_url.startswith(("http://", "https://")):
                st.warning("URL should start with `http://` or `https://`")

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

            http_method = st.selectbox("HTTP_METHOD", ["GET", "POST"], key=f"new_method_{fv}",
                                         help="GET = standard REST fetch. POST = query-style APIs (GraphQL, HubSpot Search, Salesforce Bulk).")

            if http_method == "POST":
                st.info("**POST is for query-style APIs only.** Use when the API requires a JSON body to describe what data to fetch.")

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

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

        request_body_raw = None
        if http_method == "POST":
            st.markdown("#### 📝  Step 2b: Query Body")
            with st.container(border=True):
                section_label("REQUEST BODY (POST)")
                request_body_raw = st.text_area(
                    "REQUEST_BODY_JSON",
                    placeholder='{\n  "query": "{ users { id name email } }"\n}',
                    height=120,
                    key=f"new_req_body_{fv}",
                    help="JSON body sent with every POST request to query the API."
                )
                if request_body_raw:
                    try:
                        json.loads(request_body_raw)
                        st.caption("✓ Valid JSON body")
                    except Exception as e:
                        st.error(f"Invalid JSON: {str(e)}")
            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

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

            pagination_type = st.selectbox(
                "PAGINATION_TYPE",
                ["NONE", "PAGE", "OFFSET", "CURSOR", "LINK"],
                key=f"new_pag_type_{fv}",
                help="NONE: single fetch · PAGE: ?page=1,2,3 · OFFSET: ?offset=0,100 · CURSOR: next_token · LINK: follows Link header (GitHub/GitLab)"
            )
            page_param = None
            page_size = 100
            limit_param = "limit"
            start_index = 1
            cursor_param = ""
            cursor_path = ""
            has_more_path = ""
            total_pages_path = ""
            max_pages = 10000
            records_path = "data"

            if pagination_type == "NONE":
                st.caption("Single fetch — no pagination applied.")

            elif pagination_type in ("PAGE", "OFFSET"):
                pg_c1, pg_c2, pg_c3 = st.columns(3)
                with pg_c1:
                    page_param = st.text_input(
                        "PAGE_PARAM",
                        value="page" if pagination_type == "PAGE" else "offset",
                        key=f"new_page_param_{fv}",
                        help="Query param name the API expects"
                    )
                with pg_c2:
                    page_size = st.number_input("PAGE_SIZE", value=100, min_value=1, max_value=10000, key=f"new_page_size_{fv}")
                with pg_c3:
                    limit_param = st.text_input("LIMIT_PARAM", value="limit", key=f"new_limit_param_{fv}",
                                                help="Query param for page size (e.g. 'limit', 'per_page')")
                start_index = st.number_input("START_INDEX", value=1, min_value=0, key=f"new_start_idx_{fv}")

            elif pagination_type == "CURSOR":
                cu_c1, cu_c2 = st.columns(2)
                with cu_c1:
                    cursor_param = st.text_input("CURSOR_PARAM", placeholder="next_token", key=f"new_cursor_param_{fv}",
                                                 help="Query param name for the cursor value")
                with cu_c2:
                    cursor_path = st.text_input("CURSOR_PATH", placeholder="pagination.next_cursor", key=f"new_cursor_path_{fv}",
                                                help="Dotted JSON path to the next cursor in the response")
                page_size = st.number_input("PAGE_SIZE", value=100, min_value=1, max_value=10000, key=f"new_page_size_{fv}")
                limit_param = st.text_input("LIMIT_PARAM", value="limit", key=f"new_limit_param_{fv}")
                st.caption("Example: Stripe uses `data[-1].id`, Salesforce uses `nextRecordsUrl`.")

            elif pagination_type == "LINK":
                st.info("LINK header pagination is automatic — follows `rel=\"next\"` URL from the HTTP Link header. No extra config needed.")
                page_size = st.number_input("PAGE_SIZE (hint only)", value=100, min_value=1, key=f"new_page_size_{fv}")

            with st.expander("Advanced: Pagination Termination Hints", expanded=False):
                pm_c1, pm_c2 = st.columns(2)
                with pm_c1:
                    has_more_path = st.text_input("HAS_MORE_PATH", placeholder="pagination.has_more", key=f"new_has_more_{fv}",
                                                  help="Dotted path to a boolean signaling more pages exist")
                with pm_c2:
                    total_pages_path = st.text_input("TOTAL_PAGES_PATH", placeholder="pagination.total_pages", key=f"new_total_pg_{fv}",
                                                     help="Dotted path to total page count")
                max_pages = st.number_input("MAX_PAGES (safety ceiling)", value=10000, min_value=1, key=f"new_max_pages_{fv}",
                                            help="Hard stop to prevent infinite loops.")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            section_label("RECORDS PATH")
            records_path = st.text_input("RECORDS_PATH", value="data", key=f"new_records_path_{fv}",
                                         help="Dotted path inside the response JSON where the array of records lives (e.g. 'data', 'results', 'items', 'value').")
            common_paths = {"data": "Standard (Stripe, Tiger)", "results": "Django/FastAPI", "items": "Azure",
                           "value": "Microsoft Graph", "records": "Salesforce", "content": "Spring Boot"}
            if records_path in common_paths:
                st.caption(f"✓ Known pattern: {common_paths[records_path]}")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            section_label("STATIC FILTERS")
            filter_mode = st.radio("Filter mode", ["None", "Simple key-value", "JSON (advanced)"],
                                   horizontal=True, key=f"new_filter_mode_{fv}")
            filter_params_json = None
            if filter_mode == "Simple key-value":
                num_filters = st.number_input("Number of filters", min_value=1, max_value=10, value=1, key=f"new_filter_count_{fv}")
                filter_dict = {}
                for fi in range(int(num_filters)):
                    fk_col, fv_col = st.columns(2)
                    with fk_col:
                        fk = st.text_input(f"Key {fi+1}", key=f"new_fk_{fi}_{fv}", placeholder="status")
                    with fv_col:
                        fval = st.text_input(f"Value {fi+1}", key=f"new_fv_{fi}_{fv}", placeholder="active")
                    if fk and fval:
                        filter_dict[fk] = fval
                if filter_dict:
                    filter_params_json = json.dumps(filter_dict)
                    st.caption(f"Will append: `{'&'.join(f'{k}={v}' for k, v in filter_dict.items())}`")
            elif filter_mode == "JSON (advanced)":
                filter_json_raw = st.text_area("FILTER_PARAMS JSON",
                    placeholder='{\n  "status": "active",\n  "category": ["electronics", "books"]\n}',
                    height=100, key=f"new_filter_json_{fv}")
                if filter_json_raw:
                    try:
                        parsed = json.loads(filter_json_raw)
                        filter_params_json = json.dumps(parsed)
                        st.caption(f"✓ Valid JSON — {len(parsed)} filter(s)")
                    except Exception as e:
                        st.error(f"Invalid JSON: {str(e)}")
                        filter_params_json = None

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
            elif pagination_type == "CURSOR" and not cursor_param:
                st.error("CURSOR pagination requires CURSOR_PARAM to be configured.")
            elif pagination_type == "CURSOR" and not cursor_path:
                st.error("CURSOR pagination requires CURSOR_PATH to be configured.")
            elif http_method == "POST" and request_body_raw and not _is_valid_json(request_body_raw):
                st.error("REQUEST_BODY_JSON is not valid JSON. Fix or clear it.")
            else:
                try:
                    exec_sql(
                        f"INSERT INTO {META}.INGESTION_CONFIGS "
                        "(API_NAME, ENDPOINT_URL, HTTP_METHOD, AUTH_TYPE, API_KEY_HEADER, "
                        "SECRET_NAME, TOKEN_URL, LANDING_TABLE, PAGINATION_TYPE, PAGE_PARAM, "
                        "START_INDEX, MAX_RETRIES, RETRY_DELAY_SEC, TIMEOUT_SEC, EXTRA_HEADERS_JSON, "
                        "INCREMENTAL_FLAG, WATERMARK_PARAM, WATERMARK_FIELD, LAST_SYNC_VALUE, "
                        "PAGE_SIZE, LIMIT_PARAM, CURSOR_PARAM, CURSOR_PATH, "
                        "HAS_MORE_PATH, TOTAL_PAGES_PATH, MAX_PAGES, RECORDS_PATH, "
                        "REQUEST_BODY_JSON, FILTER_PARAMS) "
                        "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                        "       ?, ?, ?, ?, ?, ?, ?, ?, ?, TRY_PARSE_JSON(?)",
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
                            page_size,
                            limit_param or "limit",
                            cursor_param or None,
                            cursor_path or None,
                            has_more_path or None,
                            total_pages_path or None,
                            max_pages,
                            records_path or "data",
                            request_body_raw or None,
                            filter_params_json or None,
                        ]
                    )
                    rebuild_msg = rebuild_ingestor()
                    st.toast(f"Added '{api_name}' — {rebuild_msg}", icon="✅")

                    st.session_state.form_version += 1
                    st.session_state["expand_new_endpoint"] = False
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

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
                    st.toast(f"Updated resilience parameters for '{selected_api}'", icon="✅")
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
                    st.toast(f"{action_text} — {rebuild_msg}", icon="✅")
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
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No API configurations available to manage.")
