"""Tiger SnowSync — Manage Secrets & EAI page."""
import streamlit as st
import pandas as pd

from tiger.db import (
    META, run_query, exec_sql,
    is_safe_name, escape_sql_literal,
    get_secrets_df, get_integrations_df,
    rebuild_eai,
)
from tiger.helpers import (
    section_label, styled_dataframe,
)


def render() -> None:
    """Render the Manage Secrets & EAI page."""
    section_label("SECURITY INFRASTRUCTURE")
    st.header("Secrets & External Access")
    st.caption("Onboarding pipeline: Network Rules → Security Integrations → Secrets → EAI auto-rebuilds.")

    eai_ok = False
    eai_rule_count = 0
    eai_secret_count = 0
    try:
        run_query("DESCRIBE INTEGRATION EAI_UNIVERSAL_INGESTOR")
        eai_ok = True
        try:
            nr_count_df = run_query(f"SHOW NETWORK RULES IN SCHEMA {META}")
            eai_rule_count = len(nr_count_df) if not nr_count_df.empty else 0
        except Exception:
            pass
        try:
            s_count_df = get_secrets_df()
            eai_secret_count = len(s_count_df) if not s_count_df.empty else 0
        except Exception:
            pass
    except Exception:
        pass

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

    # ─── Step 1: Network Rules ───
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

    # ─── Step 2: Security Integrations ───
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

    # ─── Step 3: Secrets ───
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
