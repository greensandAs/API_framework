"""Tiger SnowSync — sidebar nav + topbar render."""
import streamlit as st

from tiger.db import run_query


# ─────────────────────────────────────────────
# Sidebar groups
# ─────────────────────────────────────────────
NAV_GROUPS = [
    ("SETUP", [
        ("⚙   Configs",        "Manage API Configs"),
        ("🔐  Secrets & EAI",   "Manage Secrets & EAI"),
    ]),
    ("EXECUTE", [
        ("▶   Run Ingestion",   "Run Ingestion"),
        ("📊  Console",         "Ingestion Console"),
    ]),
    ("EXPLORE", [
        ("🗂   Data Explorer",   "Data Explorer"),
        ("⏱   Scheduler",       "Task Scheduler"),
    ]),
    ("HELP", [
        ("🗺   Pipeline Overview", "Pipeline Overview"),
    ]),
]


def get_session_context():
    """Pull the active user / role / warehouse from the Snowflake session."""
    try:
        ctx = run_query("SELECT CURRENT_USER() AS U, CURRENT_ROLE() AS R, CURRENT_WAREHOUSE() AS W")
        if not ctx.empty:
            return (
                str(ctx["U"].iloc[0]),
                str(ctx["R"].iloc[0]),
                str(ctx["W"].iloc[0]),
            )
    except Exception:
        pass
    return "—", "—", "—"


def render_sidebar(logo_uri: str, user: str, role: str, current_wh: str) -> str:
    """
    Render the sidebar nav, branding, and Settings expander.
    Returns the currently-active page key.
    """
    if "active_nav" not in st.session_state:
        st.session_state["active_nav"] = "Manage API Configs"

    with st.sidebar:
        if logo_uri:
            st.markdown(
                f"<div class='sb-logo'><img src='{logo_uri}' alt='Tiger SnowSync'></div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            "<div class='sb-tagline'>Accelerating the Data Den</div>",
            unsafe_allow_html=True,
        )

        for group_label, items in NAV_GROUPS:
            st.markdown(f"<div class='sb-group'>{group_label}</div>", unsafe_allow_html=True)
            for label, key in items:
                if st.button(label, key=f"nav_btn_{key}", use_container_width=True):
                    st.session_state["active_nav"] = key
                    st.rerun()

        nav_choice = st.session_state["active_nav"]

        # ─── Settings (cross-tab defaults) ───
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        with st.expander("⚙  Settings", expanded=False):
            try:
                wh_df = run_query("SHOW WAREHOUSES")
                wh_df.columns = [c.upper() for c in wh_df.columns]
                wh_options = wh_df["NAME"].tolist() if not wh_df.empty else [current_wh]
            except Exception:
                wh_options = [current_wh]

            if "pref_warehouse" not in st.session_state:
                st.session_state["pref_warehouse"] = (
                    current_wh if current_wh in wh_options
                    else (wh_options[0] if wh_options else "COMPUTE_WH")
                )

            st.selectbox("Default Warehouse (for new tasks)", wh_options, key="pref_warehouse")
            st.number_input(
                "Default Schema Sample Size",
                min_value=10, max_value=2000, step=10, value=100,
                key="pref_sample_size",
            )
            st.text_input("Default Landing Table", value="API_RAW_DATA", key="pref_landing_table")

        st.markdown(f"""
        <div class='sb-footer'>
          <div>👤 {user}</div>
          <div>🛡 {role}</div>
        </div>
        """, unsafe_allow_html=True)

    return nav_choice


def render_topbar(nav_choice: str, warehouse: str) -> None:
    """Render the sticky page-header topbar."""
    st.markdown(f"""
    <div class='topbar'>
      <div class='topbar-brand'>
        <span class='topbar-icon'>🐅</span>
        <div>
          <span class='topbar-title'>{nav_choice}</span>
          <span class='topbar-sub'>TIGER SNOWSYNC · NATIVE API ACCELERATOR</span>
        </div>
      </div>
      <div class='topbar-meta'>
        <span class='pill accent'>🏢 {warehouse}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
