"""Tiger SnowSync — Manage Secrets & EAI page (production redesign)."""
import time

import streamlit as st
import pandas as pd

from tiger.db import (
    META, run_query, exec_sql,
    is_safe_name, escape_sql_literal,
    get_secrets_df, get_integrations_df, get_allowed_hosts,
    extract_url_host, check_host_allowed,
    rebuild_eai,
)
from tiger.helpers import (
    section_label, styled_dataframe, cfg_card, empty_state,
    paginated_items, paginated_controls,
)


def _dep_node(col, title, count, status, items, icon):
    color = "#29B5E8" if status == "ok" else ("#f59e0b" if status == "warn" else "#ef4444")
    items_html = "".join([
        f"<div style='font-family:var(--font-mono);font-size:0.65rem;color:var(--text-secondary);"
        f"padding:2px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{item}</div>"
        for item in (items[:3] or ["(none)"])
    ])
    more = (f"<div style='color:var(--text-muted);font-size:0.6rem;"
            f"font-family:var(--font-mono);'>+{len(items)-3} more</div>"
            if len(items) > 3 else "")
    col.markdown(f"""
    <div style='background:var(--bg-card);border:1px solid rgba(255,255,255,0.06);
                border-top:3px solid {color};border-radius:8px;padding:14px 16px;min-height:120px;'>
      <div style='font-family:var(--font-mono);font-size:0.6rem;font-weight:700;color:{color};
                  letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;'>
        {icon}&nbsp; {title}
      </div>
      <div style='font-family:var(--font-display);font-weight:800;font-size:1.6rem;color:var(--text-primary);'>
        {count}
      </div>
      <div style='margin-top:8px;border-top:1px solid var(--border-subtle);padding-top:8px;'>
        {items_html}{more}
      </div>
    </div>
    """, unsafe_allow_html=True)


def _dep_arrow(col, active):
    color = "#29B5E8" if active else "#52525b"
    col.markdown(f"""
    <div style='display:flex;align-items:center;justify-content:center;height:120px;font-size:1.4rem;color:{color};'>
      &rarr;
    </div>
    """, unsafe_allow_html=True)


def render() -> None:
    """Render the Manage Secrets & EAI page."""
    section_label("SECURITY INFRASTRUCTURE")
    st.header("Secrets & External Access")
    st.caption("Infrastructure-as-dashboard: EAI health · dependency chain · full lifecycle management.")

    # ─────────────────────────────────────────────────────────
    # DATA FETCH (once at top)
    # ─────────────────────────────────────────────────────────
    eai_detail = {}
    eai_ok = False
    try:
        eai_rows = run_query("DESCRIBE INTEGRATION EAI_UNIVERSAL_INGESTOR")
        eai_rows.columns = [c.upper() for c in eai_rows.columns]
        eai_ok = True
        if "PROPERTY" in eai_rows.columns and "PROPERTY_VALUE" in eai_rows.columns:
            eai_detail = dict(zip(eai_rows["PROPERTY"], eai_rows["PROPERTY_VALUE"]))
    except Exception:
        pass

    try:
        nr_df = run_query(f"SHOW NETWORK RULES IN SCHEMA {META}")
        nr_df.columns = [c.upper() for c in nr_df.columns]
    except Exception:
        nr_df = pd.DataFrame()

    nr_names = nr_df["NAME"].tolist() if not nr_df.empty else []

    sec_df = get_secrets_df()
    sec_names = sec_df["NAME"].tolist() if not sec_df.empty else []

    try:
        int_df = get_integrations_df()
        if "NAME" in int_df.columns and "TYPE" in int_df.columns:
            int_df = int_df[
                (int_df["TYPE"].str.contains("API_AUTHENTICATION", case=False, na=False)) &
                (int_df["NAME"].str.startswith("SEC_INT_API_", na=False))
            ].copy()
        else:
            int_df = pd.DataFrame()
    except Exception:
        int_df = pd.DataFrame()
    int_names = int_df["NAME"].tolist() if not int_df.empty else []

    try:
        configs_df = run_query(
            f"SELECT API_NAME, ENDPOINT_URL, SECRET_NAME FROM {META}.INGESTION_CONFIGS"
        )
    except Exception:
        configs_df = pd.DataFrame(columns=["API_NAME", "ENDPOINT_URL", "SECRET_NAME"])

    nr_count = len(nr_names)
    sec_count = len(sec_names)
    eai_enabled = str(eai_detail.get("ENABLED", "false")).lower() == "true"

    # ─────────────────────────────────────────────────────────
    # ZONE 1: EAI HEALTH COMMAND CENTER
    # ─────────────────────────────────────────────────────────
    eai_color = "#29B5E8" if eai_ok and eai_enabled else "#ef4444"
    eai_icon = "●" if eai_ok and eai_enabled else "○"
    eai_label = "ACTIVE" if eai_ok and eai_enabled else ("DISABLED" if eai_ok else "MISSING")

    st.markdown(f"""
    <div style="background:{'rgba(41,181,232,0.06)' if eai_ok else 'rgba(239,68,68,0.06)'};
                border:1px solid {'rgba(41,181,232,0.25)' if eai_ok else 'rgba(239,68,68,0.25)'};
                border-left:4px solid {eai_color};border-radius:10px;padding:16px 20px;margin-bottom:1rem;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:1rem;color:{eai_color};">{eai_icon}</span>
            <span style="font-family:var(--font-display);font-weight:800;font-size:1rem;color:var(--text-primary);">
              EAI_UNIVERSAL_INGESTOR
            </span>
            <span style="background:{'rgba(41,181,232,0.1)' if eai_ok else 'rgba(239,68,68,0.1)'};
                         color:{eai_color};padding:2px 10px;border-radius:4px;font-size:0.6rem;font-weight:700;
                         font-family:var(--font-mono);letter-spacing:1px;
                         border:1px solid {'rgba(41,181,232,0.2)' if eai_ok else 'rgba(239,68,68,0.2)'};">
              {eai_label}
            </span>
          </div>
          <div style="display:flex;gap:20px;margin-top:10px;flex-wrap:wrap;">
            <span style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-secondary);">
              <span style="color:var(--text-muted);">Network Rules</span>&nbsp;{nr_count}
            </span>
            <span style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-secondary);">
              <span style="color:var(--text-muted);">Secrets Bound</span>&nbsp;{sec_count}
            </span>
            <span style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-secondary);">
              <span style="color:var(--text-muted);">Comment</span>&nbsp;{str(eai_detail.get('COMMENT', '—'))[:40] or '—'}
            </span>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    eai_c1, eai_c2, eai_c3, eai_c4 = st.columns(4)

    with eai_c1:
        if st.button("🔄 Rebuild EAI", use_container_width=True, type="primary", key="btn_rebuild_eai",
                     help="Recreates EAI with all current network rules and secrets"):
            with st.spinner("Rebuilding EAI..."):
                try:
                    msg = rebuild_eai()
                    st.toast(msg, icon="✅")
                    get_allowed_hosts.clear()
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Rebuild failed: {str(e)}")

    with eai_c2:
        if st.button("🔍 Inspect EAI", use_container_width=True, key="btn_inspect_eai",
                     help="Show full DESCRIBE INTEGRATION output"):
            st.session_state["show_eai_inspect"] = not st.session_state.get("show_eai_inspect", False)

    with eai_c3:
        st.text_input("Test URL", placeholder="https://api.example.com/ping",
                      label_visibility="collapsed", key="eai_test_url")

    with eai_c4:
        if st.button("🧪 Test Connectivity", use_container_width=True, key="btn_test_conn",
                     disabled=not st.session_state.get("eai_test_url", ""),
                     help="Check if this host is covered by a network rule"):
            url_to_test = st.session_state.get("eai_test_url", "")
            if url_to_test:
                allowed_entries = get_allowed_hosts()
                ok, matched, reason = check_host_allowed(url_to_test, allowed_entries)
                if ok:
                    st.success(f"✓ Host covered — matched rule: `{matched}`")
                else:
                    host_p, _ = extract_url_host(url_to_test)
                    st.error(f"✗ {reason}\n\nHost `{host_p}` is not in any network rule. Add it in the Network Rules tab below.")

    if st.session_state.get("show_eai_inspect"):
        with st.container(border=True):
            section_label("EAI FULL DESCRIPTOR")
            if eai_detail:
                styled_dataframe(pd.DataFrame(eai_detail.items(), columns=["Property", "Value"]), height=250)
            else:
                st.info("EAI not found — create network rules and secrets first.")

    # ─────────────────────────────────────────────────────────
    # ZONE 2: DEPENDENCY GRAPH
    # ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    section_label("INFRASTRUCTURE DEPENDENCY CHAIN")

    dep_c1, dep_c2, dep_c3, dep_c4, dep_c5 = st.columns([2, 0.3, 2, 0.3, 2])
    _dep_node(dep_c1, "Network Rules", nr_count, "ok" if nr_names else "err", nr_names, "🌐")
    _dep_arrow(dep_c2, bool(nr_names))
    _dep_node(dep_c3, "Security Integrations", len(int_names), "ok" if int_names else "warn", int_names, "🔐")
    _dep_arrow(dep_c4, bool(sec_names))
    _dep_node(dep_c5, "Secrets", sec_count, "ok" if sec_names else "err", sec_names, "🔑")

    st.markdown(f"""
    <div style='background:var(--bg-card);border:1px solid rgba(255,255,255,0.06);border-radius:8px;
                padding:10px 16px;margin-top:8px;display:flex;align-items:center;gap:12px;'>
      <span style='color:var(--text-muted);font-family:var(--font-mono);font-size:0.65rem;'>EAI BINDS ALL ↑</span>
      <div style='flex:1;height:1px;background:var(--border-subtle);'></div>
      <span style='font-family:var(--font-mono);font-size:0.7rem;color:{"#29B5E8" if eai_ok else "#ef4444"};font-weight:700;'>
        {"✓ EAI_UNIVERSAL_INGESTOR ACTIVE" if eai_ok and eai_enabled else "✗ EAI MISSING — REBUILD REQUIRED"}
      </span>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # ZONE 3: TABBED RESOURCE PANELS
    # ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    tab_nr, tab_int, tab_sec = st.tabs([
        f"🌐  Network Rules  ({nr_count})",
        f"🔐  Security Integrations  ({len(int_names)})",
        f"🔑  Secrets  ({sec_count})",
    ])

    # ═══════════════════════════════════════════════════════════
    # TAB 1: NETWORK RULES
    # ═══════════════════════════════════════════════════════════
    with tab_nr:
        @st.dialog("＋ Create Network Rule", width="large")
        def _create_nr_dialog():
            add_nr_c1, add_nr_c2 = st.columns([1, 2])
            with add_nr_c1:
                nr_name_new = st.text_input("Rule Name", placeholder="NR_SALESFORCE", key="dlg_nr_name",
                                            help="Convention: NR_<PROVIDER> e.g. NR_SALESFORCE")
                if nr_name_new:
                    if not is_safe_name(nr_name_new):
                        st.error("Use only letters, digits, and underscores.")
                    elif nr_name_new in nr_names:
                        st.warning(f"`{nr_name_new}` already exists — saving will replace it.")

            with add_nr_c2:
                nr_hosts_new = st.text_area("Allowed Hosts (one per line or comma-separated)",
                                            placeholder="api.salesforce.com\nlogin.salesforce.com\n*.my.salesforce.com",
                                            height=100, key="dlg_nr_hosts",
                                            help="Use *.domain.com for wildcard subdomains. Add :443 to restrict to a specific port.")
                if nr_hosts_new:
                    parsed_preview = [h.strip() for line in nr_hosts_new.splitlines() for h in line.split(",") if h.strip()]
                    st.markdown(
                        "<div class='chip-bar'>"
                        + "".join([f"<span class='chip active'>{'✓' if '.' in h else '⚠'} {h}</span>" for h in parsed_preview[:6]])
                        + (f"<span class='chip muted'>+{len(parsed_preview)-6} more</span>" if len(parsed_preview) > 6 else "")
                        + "</div>",
                        unsafe_allow_html=True
                    )

            if nr_hosts_new and not configs_df.empty and "ENDPOINT_URL" in configs_df.columns:
                potential_parsed = [h.strip() for line in nr_hosts_new.splitlines() for h in line.split(",") if h.strip()]
                newly_covered = []
                for _, cr in configs_df.iterrows():
                    url = cr.get("ENDPOINT_URL") or ""
                    if url:
                        host_p, _ = extract_url_host(str(url))
                        for h in potential_parsed:
                            h_clean = h.strip().lstrip("*.")
                            if host_p and (host_p.endswith(h_clean) or host_p == h_clean):
                                newly_covered.append(cr["API_NAME"])
                                break
                if newly_covered:
                    st.success(f"✓ This rule will cover **{len(newly_covered)} existing config(s):** {', '.join(newly_covered[:5])}")

            st.divider()
            dnr_a, dnr_c = st.columns(2)
            with dnr_a:
                if st.button("Create Network Rule", type="primary", key="dlg_btn_create_nr",
                             use_container_width=True,
                             disabled=not (nr_name_new and nr_hosts_new)):
                    if not is_safe_name(nr_name_new):
                        st.error("Invalid rule name.")
                    else:
                        parsed = [h.strip() for line in nr_hosts_new.splitlines() for h in line.split(",") if h.strip()]
                        if not parsed:
                            st.error("At least one host is required.")
                        else:
                            try:
                                hosts_sql = ", ".join([f"'{escape_sql_literal(h)}'" for h in parsed])
                                exec_sql(f"CREATE OR REPLACE NETWORK RULE {META}.{nr_name_new} MODE = EGRESS TYPE = HOST_PORT VALUE_LIST = ({hosts_sql})")
                                eai_msg = rebuild_eai()
                                get_allowed_hosts.clear()
                                st.session_state["secrets_dialog"] = None
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
            with dnr_c:
                if st.button("Cancel", use_container_width=True, key="dlg_btn_cancel_nr"):
                    st.session_state["secrets_dialog"] = None
                    st.rerun()

        nr_top_l, nr_top_r = st.columns([4, 1])
        with nr_top_l:
            st.caption(f"{nr_count} network rule(s) registered")
        with nr_top_r:
            if st.button("＋ New Network Rule", type="primary", use_container_width=True, key="btn_open_nr_dialog"):
                st.session_state["secrets_dialog"] = "nr"
                st.rerun()

        if st.session_state.get("secrets_dialog") == "nr":
            _create_nr_dialog()

        if nr_names:
            section_label("REGISTERED NETWORK RULES")

            _nr_page_items = paginated_items(nr_names, "pg_nr_rules", page_size=10)
            for rule_name in _nr_page_items:
                try:
                    desc = run_query(f"DESCRIBE NETWORK RULE {META}.{rule_name}")
                    desc.columns = [c.upper() for c in desc.columns]
                    hosts_raw = desc["VALUE_LIST"].iloc[0] if "VALUE_LIST" in desc.columns and not desc.empty else ""
                    hosts = [h.strip() for h in str(hosts_raw).split(",") if h.strip()]
                except Exception:
                    hosts = []

                covered_apis = []
                if not configs_df.empty and "ENDPOINT_URL" in configs_df.columns:
                    for _, cr in configs_df.iterrows():
                        url = cr.get("ENDPOINT_URL") or ""
                        if url:
                            host_p, _ = extract_url_host(str(url))
                            for h in hosts:
                                h_clean = h.strip().lstrip("*.")
                                if host_p and (host_p.endswith(h_clean) or host_p == h_clean):
                                    covered_apis.append(cr["API_NAME"])
                                    break

                badges = [
                    {"text": f"{len(hosts)} host(s)", "cls": "accent"},
                    {"text": "EGRESS", "cls": ""},
                ]
                if covered_apis:
                    badges.append({"text": f"covers {len(covered_apis)} API(s)", "cls": "accent"})
                else:
                    badges.append({"text": "no API mapped", "cls": "warn"})

                hosts_display = " · ".join(hosts[:4])
                if len(hosts) > 4:
                    hosts_display += f" +{len(hosts)-4} more"

                cfg_card(
                    name=rule_name,
                    endpoint=hosts_display or "(no hosts)",
                    badges=badges,
                    meta=f"covers: {', '.join(covered_apis[:3]) or 'none'}",
                    status="healthy" if covered_apis else "warning"
                )

                nr_a1, nr_a2, nr_a3 = st.columns([1, 1, 4])
                with nr_a1:
                    if st.button("✏ Edit Hosts", key=f"nr_edit_{rule_name}", use_container_width=True):
                        st.session_state[f"nr_edit_open_{rule_name}"] = not st.session_state.get(f"nr_edit_open_{rule_name}", False)

                with nr_a2:
                    with st.popover("🗑 Delete", use_container_width=True):
                        st.warning(f"Delete **{rule_name}**?\n\nThis will remove {len(hosts)} host(s) from the allowlist and require an EAI rebuild.")
                        if covered_apis:
                            st.error(f"⚠ **{len(covered_apis)} API(s) will lose network access:** {', '.join(covered_apis)}")
                        confirm_nr = st.text_input(f'Type "{rule_name}" to confirm', key=f"nr_del_confirm_{rule_name}", placeholder=rule_name)
                        if st.button("Confirm Delete", key=f"nr_del_btn_{rule_name}", disabled=(confirm_nr != rule_name), type="primary"):
                            try:
                                exec_sql(f"DROP NETWORK RULE {META}.{rule_name}")
                                eai_msg = rebuild_eai()
                                get_allowed_hosts.clear()
                                st.toast(f"Deleted '{rule_name}' — {eai_msg}", icon="🗑")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                if st.session_state.get(f"nr_edit_open_{rule_name}"):
                    with st.container(border=True):
                        section_label(f"EDIT HOSTS · {rule_name}")
                        st.caption("Replaces the host list for this rule. EAI is rebuilt automatically.")
                        new_hosts = st.text_area("Hosts (one per line or comma-separated)", value="\n".join(hosts), height=120, key=f"nr_edit_hosts_{rule_name}")
                        ed_c1, ed_c2 = st.columns(2)
                        with ed_c1:
                            if st.button("Save Changes", type="primary", use_container_width=True, key=f"nr_edit_save_{rule_name}"):
                                parsed = [h.strip() for line in new_hosts.splitlines() for h in line.split(",") if h.strip()]
                                if not parsed:
                                    st.error("At least one host required.")
                                else:
                                    try:
                                        hosts_sql = ", ".join([f"'{escape_sql_literal(h)}'" for h in parsed])
                                        exec_sql(f"CREATE OR REPLACE NETWORK RULE {META}.{rule_name} MODE = EGRESS TYPE = HOST_PORT VALUE_LIST = ({hosts_sql})")
                                        eai_msg = rebuild_eai()
                                        get_allowed_hosts.clear()
                                        st.toast(f"Rule '{rule_name}' updated — {eai_msg}", icon="✅")
                                        st.session_state[f"nr_edit_open_{rule_name}"] = False
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(str(e))
                        with ed_c2:
                            if st.button("Cancel", use_container_width=True, key=f"nr_edit_cancel_{rule_name}"):
                                st.session_state[f"nr_edit_open_{rule_name}"] = False
                                st.rerun()

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            paginated_controls(nr_names, "pg_nr_rules", page_size=10)
        else:
            empty_state("🌐", "No network rules yet", "Add a rule below to allow Snowflake to reach external APIs.")

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # TAB 2: SECURITY INTEGRATIONS
    # ═══════════════════════════════════════════════════════════
    with tab_int:
        @st.dialog("＋ Create Security Integration", width="large")
        def _create_int_dialog():
            st.caption("Required before creating OAUTH2-type secrets. Only Client Credentials flow is supported. "
                       "**Names must start with `SEC_INT_API_`**.")

            with st.form("dlg_create_oauth_integration", clear_on_submit=False):
                oi_c1, oi_c2 = st.columns(2)
                with oi_c1:
                    oi_name = st.text_input("Integration Name *", placeholder="SEC_INT_API_<your_api>", key="dlg_oi_name")
                    oi_client_id = st.text_input("OAuth Client ID *", key="dlg_oi_client_id")
                    oi_client_secret = st.text_input("OAuth Client Secret *", type="password", key="dlg_oi_client_secret")
                    oi_token_endpoint = st.text_input("Token Endpoint URL *", placeholder="https://auth.example.com/oauth/token", key="dlg_oi_token_ep")
                with oi_c2:
                    oi_auth_method = st.selectbox("Client Auth Method", ["CLIENT_SECRET_POST", "CLIENT_SECRET_BASIC"], key="dlg_oi_auth_method")
                    oi_scopes = st.text_input("Allowed Scopes (comma-separated)", placeholder="read, write", key="dlg_oi_scopes")
                    oi_token_validity = st.number_input("Token Validity (seconds)", value=0, min_value=0, help="0 = provider default", key="dlg_oi_token_validity")
                    oi_comment = st.text_input("Comment", key="dlg_oi_comment")
                oi_enabled = st.toggle("Enabled", value=True, key="dlg_oi_enabled")

                st.divider()
                d_a, d_c = st.columns(2)
                with d_a:
                    submitted = st.form_submit_button("Create Integration", type="primary", use_container_width=True)
                with d_c:
                    cancelled = st.form_submit_button("Cancel", use_container_width=True)

                if cancelled:
                    st.session_state["secrets_dialog"] = None
                    st.rerun()

                if submitted:
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
                            st.session_state["secrets_dialog"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        int_top_l, int_top_r = st.columns([4, 1])
        with int_top_l:
            st.caption(f"{len(int_names)} security integration(s) registered")
        with int_top_r:
            if st.button("＋ New Integration", type="primary", use_container_width=True, key="btn_open_int_dialog"):
                st.session_state["secrets_dialog"] = "int"
                st.rerun()

        if st.session_state.get("secrets_dialog") == "int":
            _create_int_dialog()

        if int_names:
            section_label("API AUTHENTICATION INTEGRATIONS")

            _int_page_items = paginated_items(int_names, "pg_int_list", page_size=10)
            for int_name in _int_page_items:
                int_row = int_df[int_df["NAME"] == int_name].iloc[0] if not int_df.empty else {}
                enabled = str(int_row.get("ENABLED", "false")).lower() == "true" if len(int_row) else False
                created = str(int_row.get("CREATED_ON", ""))[:10]

                linked_secrets = []
                if not sec_df.empty and "INTEGRATION_NAME" in sec_df.columns:
                    linked_secrets = sec_df[sec_df["INTEGRATION_NAME"] == int_name]["NAME"].tolist()

                cfg_card(
                    name=int_name,
                    endpoint="TYPE = API_AUTHENTICATION · OAUTH2 · CLIENT_CREDENTIALS",
                    badges=[
                        {"text": "ENABLED" if enabled else "DISABLED", "cls": "accent" if enabled else ""},
                        {"text": f"{len(linked_secrets)} secret(s)", "cls": "accent" if linked_secrets else "warn"},
                        {"text": f"created: {created}", "cls": ""},
                    ],
                    meta=f"linked secrets: {', '.join(linked_secrets) or 'none'}",
                    status="healthy" if enabled else "inactive"
                )

                int_a1, int_a2, int_a3 = st.columns([1, 1, 4])
                with int_a1:
                    toggle_label = "Disable" if enabled else "Enable"
                    with st.popover(f"{'⏸' if enabled else '▶'} {toggle_label}", use_container_width=True):
                        st.warning(f"{'Disable' if enabled else 'Enable'} **{int_name}**?")
                        if not enabled and linked_secrets:
                            st.info(f"ℹ {len(linked_secrets)} secret(s) depend on this integration.")
                        confirm_toggle = st.text_input(f'Type "{int_name}" to confirm', key=f"int_toggle_confirm_{int_name}", placeholder=int_name)
                        if st.button(f"Confirm {toggle_label}", key=f"int_toggle_btn_{int_name}",
                                     disabled=(confirm_toggle != int_name), type="primary"):
                            try:
                                state = "FALSE" if enabled else "TRUE"
                                exec_sql(f"ALTER SECURITY INTEGRATION {int_name} SET ENABLED = {state}")
                                get_integrations_df.clear()
                                st.toast(f"{toggle_label}d {int_name}", icon="✅")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                with int_a2:
                    with st.popover("🗑 Drop", use_container_width=True):
                        if linked_secrets:
                            st.error(f"⚠ **{len(linked_secrets)} secret(s) depend on this integration:**\n{', '.join(linked_secrets)}\n\nDrop those secrets first.")
                        else:
                            st.warning(f"Drop **{int_name}**? Cannot be undone.")
                            confirm_int = st.text_input(f'Type "{int_name}" to confirm', key=f"int_del_{int_name}", placeholder=int_name)
                            if st.button("Confirm Drop", key=f"int_del_btn_{int_name}",
                                         disabled=(confirm_int != int_name or bool(linked_secrets)), type="primary"):
                                try:
                                    exec_sql(f"DROP SECURITY INTEGRATION IF EXISTS {int_name}")
                                    get_integrations_df.clear()
                                    st.toast(f"Dropped {int_name}", icon="🗑")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            paginated_controls(int_names, "pg_int_list", page_size=10)
        else:
            empty_state("🔐", "No API security integrations", "Only needed for OAuth2 flows. Skip if using API keys.")

    # ═══════════════════════════════════════════════════════════
    # TAB 3: SECRETS
    # ═══════════════════════════════════════════════════════════
    with tab_sec:
        @st.dialog("＋ Create Secret", width="large")
        def _create_sec_dialog():
            secret_type = st.selectbox("Secret Type", ["GENERIC_STRING", "PASSWORD", "OAUTH2"], key="dlg_new_sec_type",
                                       help="GENERIC_STRING → API Key · PASSWORD → OAuth2 Basic · OAUTH2 → OAuth2 Token")

            if secret_type == "GENERIC_STRING":
                with st.form("dlg_create_generic_secret", clear_on_submit=False):
                    sg_c1, sg_c2 = st.columns(2)
                    with sg_c1:
                        s_name = st.text_input("Secret Name", key="dlg_gs_name")
                        s_value = st.text_input("Secret String", type="password", key="dlg_gs_value")
                    with sg_c2:
                        s_comment = st.text_input("Comment", key="dlg_gs_comment")
                    st.divider()
                    sa, sc = st.columns(2)
                    with sa:
                        submitted = st.form_submit_button("Create Secret", type="primary", use_container_width=True)
                    with sc:
                        cancelled = st.form_submit_button("Cancel", use_container_width=True)
                    if cancelled:
                        st.session_state["secrets_dialog"] = None
                        st.rerun()
                    if submitted:
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
                                    rebuild_eai()
                                except Exception:
                                    pass
                                st.session_state["secrets_dialog"] = None
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

            elif secret_type == "PASSWORD":
                with st.form("dlg_create_password_secret", clear_on_submit=False):
                    sp_c1, sp_c2 = st.columns(2)
                    with sp_c1:
                        s_name = st.text_input("Secret Name", key="dlg_pw_name")
                        s_user = st.text_input("Username (Client ID)", key="dlg_pw_user")
                    with sp_c2:
                        s_pass = st.text_input("Password (Client Secret)", type="password", key="dlg_pw_pass")
                        s_comment = st.text_input("Comment", key="dlg_pw_comment")
                    st.divider()
                    sa, sc = st.columns(2)
                    with sa:
                        submitted = st.form_submit_button("Create Secret", type="primary", use_container_width=True)
                    with sc:
                        cancelled = st.form_submit_button("Cancel", use_container_width=True)
                    if cancelled:
                        st.session_state["secrets_dialog"] = None
                        st.rerun()
                    if submitted:
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
                                    rebuild_eai()
                                except Exception:
                                    pass
                                st.session_state["secrets_dialog"] = None
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

                with st.form("dlg_create_oauth_secret", clear_on_submit=False):
                    so_c1, so_c2 = st.columns(2)
                    with so_c1:
                        s_name = st.text_input("Secret Name", key="dlg_o2_name")
                        if int_opts:
                            s_int = st.selectbox("Security Integration", int_opts, key="dlg_o2_sec_int")
                        else:
                            s_int = st.text_input("Security Integration Name (none found — create one first)", key="dlg_o2_sec_int")
                    with so_c2:
                        s_refresh = st.text_input("OAuth Refresh Token", type="password", key="dlg_o2_refresh")
                        s_comment = st.text_input("Comment", key="dlg_o2_comment")
                    st.divider()
                    sa, sc = st.columns(2)
                    with sa:
                        submitted = st.form_submit_button("Create Secret", type="primary", use_container_width=True)
                    with sc:
                        cancelled = st.form_submit_button("Cancel", use_container_width=True)
                    if cancelled:
                        st.session_state["secrets_dialog"] = None
                        st.rerun()
                    if submitted:
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
                                    rebuild_eai()
                                except Exception:
                                    pass
                                st.session_state["secrets_dialog"] = None
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

        sec_top_l, sec_top_r = st.columns([4, 1])
        with sec_top_l:
            st.caption(f"{sec_count} secret(s) registered")
        with sec_top_r:
            if st.button("＋ New Secret", type="primary", use_container_width=True, key="btn_open_sec_dialog"):
                st.session_state["secrets_dialog"] = "sec"
                st.rerun()

        if st.session_state.get("secrets_dialog") == "sec":
            _create_sec_dialog()

        if not sec_df.empty:
            section_label("CREDENTIAL STORE")

            type_labels = {
                "GENERIC_STRING": "🔑  API Keys",
                "PASSWORD": "🔐  OAuth2 Basic (Username/Password)",
                "OAUTH2": "🎟  OAuth2 Token Secrets",
            }

            _all_sec_rows = []
            for stype in ["GENERIC_STRING", "PASSWORD", "OAUTH2"]:
                type_df = sec_df[sec_df["SECRET_TYPE"] == stype] if "SECRET_TYPE" in sec_df.columns else pd.DataFrame()
                if not type_df.empty:
                    for _, sec_row in type_df.iterrows():
                        _all_sec_rows.append((stype, sec_row))

            _sec_page_items = paginated_items(_all_sec_rows, "pg_sec_list", page_size=10)
            _last_type = None
            for stype, sec_row in _sec_page_items:
                if stype != _last_type:
                    section_label(type_labels.get(stype, stype))
                    _last_type = stype

                s_name = sec_row.get("NAME", "—")
                s_comment = sec_row.get("COMMENT") or ""
                s_created = str(sec_row.get("CREATED_ON", ""))[:10]

                using_apis = []
                if not configs_df.empty and "SECRET_NAME" in configs_df.columns:
                    using_apis = configs_df[configs_df["SECRET_NAME"] == s_name]["API_NAME"].tolist()

                badges = [{"text": stype, "cls": "accent"}]
                if using_apis:
                    badges.append({"text": f"used by {len(using_apis)} API(s)", "cls": "accent"})
                else:
                    badges.append({"text": "unused", "cls": "warn"})

                cfg_card(
                    name=s_name,
                    endpoint=s_comment or "(no description)",
                    badges=badges,
                    meta=f"created: {s_created} · used by: {', '.join(using_apis[:3]) or 'no APIs'}",
                    status="healthy" if using_apis else "warning"
                )

                sec_a1, sec_a2, sec_a3 = st.columns([1, 1, 4])

                with sec_a1:
                    if st.button("🔄 Rotate", key=f"sec_rotate_{s_name}", use_container_width=True,
                                 help="Update the secret value without changing its name"):
                        st.session_state[f"rotate_open_{s_name}"] = not st.session_state.get(f"rotate_open_{s_name}", False)

                with sec_a2:
                    with st.popover("🗑 Delete", use_container_width=True):
                        if using_apis:
                            st.error(f"⚠ **{len(using_apis)} API(s) use this secret:**\n{', '.join(using_apis)}\n\nUpdate those configs first or ingestion will fail with 401.")
                        st.warning(f"Delete **{s_name}**? EAI will be rebuilt.")
                        confirm_sec = st.text_input(f'Type "{s_name}" to confirm', key=f"sec_del_confirm_{s_name}", placeholder=s_name)
                        if st.button("Confirm Delete", key=f"sec_del_btn_{s_name}", disabled=(confirm_sec != s_name), type="primary"):
                            try:
                                exec_sql(f"DROP SECRET IF EXISTS {META}.{s_name}")
                                get_secrets_df.clear()
                                try:
                                    eai_msg = rebuild_eai()
                                    st.toast(f"Deleted '{s_name}' — {eai_msg}", icon="🗑")
                                except Exception:
                                    st.toast(f"Deleted '{s_name}'", icon="🗑")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

                if st.session_state.get(f"rotate_open_{s_name}"):
                    with st.container(border=True):
                        section_label(f"ROTATE SECRET · {s_name}")
                        if using_apis:
                            st.info(f"ℹ **{len(using_apis)} API(s)** will automatically use the new credential on next run: {', '.join(using_apis)}")

                        if stype == "GENERIC_STRING":
                            new_val = st.text_input("New Secret String", type="password", key=f"rot_val_{s_name}",
                                                    help="The old value is overwritten. No downtime for existing configs.")
                            if st.button("Apply Rotation", type="primary", key=f"rot_apply_{s_name}", disabled=not new_val):
                                try:
                                    exec_sql(f"ALTER SECRET {META}.{s_name} SET SECRET_STRING = '{escape_sql_literal(new_val)}'")
                                    get_secrets_df.clear()
                                    st.toast(f"Rotated '{s_name}' — new credential active immediately", icon="🔄")
                                    st.session_state[f"rotate_open_{s_name}"] = False
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                        elif stype == "PASSWORD":
                            rot_c1, rot_c2 = st.columns(2)
                            with rot_c1:
                                new_user = st.text_input("New Username / Client ID", key=f"rot_user_{s_name}")
                            with rot_c2:
                                new_pass = st.text_input("New Password / Client Secret", type="password", key=f"rot_pass_{s_name}")
                            if st.button("Apply Rotation", type="primary", key=f"rot_apply_{s_name}", disabled=not (new_user and new_pass)):
                                try:
                                    exec_sql(f"ALTER SECRET {META}.{s_name} SET USERNAME = '{escape_sql_literal(new_user)}' PASSWORD = '{escape_sql_literal(new_pass)}'")
                                    get_secrets_df.clear()
                                    st.toast(f"Rotated '{s_name}'", icon="🔄")
                                    st.session_state[f"rotate_open_{s_name}"] = False
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                        elif stype == "OAUTH2":
                            new_token = st.text_input("New OAuth Refresh Token", type="password", key=f"rot_token_{s_name}")
                            if st.button("Apply Rotation", type="primary", key=f"rot_apply_{s_name}", disabled=not new_token):
                                try:
                                    exec_sql(f"ALTER SECRET {META}.{s_name} SET OAUTH_REFRESH_TOKEN = '{escape_sql_literal(new_token)}'")
                                    get_secrets_df.clear()
                                    st.toast(f"Rotated '{s_name}'", icon="🔄")
                                    st.session_state[f"rotate_open_{s_name}"] = False
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                        if st.button("Cancel", key=f"rot_cancel_{s_name}", use_container_width=True):
                            st.session_state[f"rotate_open_{s_name}"] = False
                            st.rerun()

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            paginated_controls(_all_sec_rows, "pg_sec_list", page_size=10)
        else:
            empty_state("🔑", "No secrets yet", "Create a secret below to store API credentials.")
