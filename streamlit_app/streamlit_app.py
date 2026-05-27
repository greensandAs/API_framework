"""Tiger SnowSync — main router."""
import base64

import streamlit as st

from tiger.styles import inject_styles
from tiger.db import get_session

st.set_page_config(page_title="Tiger SnowSync", layout="wide", page_icon="🗃️", initial_sidebar_state="expanded")
inject_styles()


@st.cache_data(show_spinner=False)
def _load_logo_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""


_LOGO_PATH = "Tiger_Snow_sync_logo_new.png"
_logo_b64 = _load_logo_b64(_LOGO_PATH)
_logo_uri = f"data:image/png;base64,{_logo_b64}" if _logo_b64 else ""

# Snowpark session
session = get_session()

# ─── Sidebar nav + topbar ───
from tiger.sidebar import get_session_context, render_sidebar, render_topbar

_user, _role, _wh = get_session_context()
nav_choice = render_sidebar(_logo_uri, _user, _role, _wh)
render_topbar(nav_choice, _wh)


# ─────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────
if nav_choice == "Manage API Configs":
    from tiger.pages import config as page_config
    page_config.render()

elif nav_choice == "Manage Secrets & EAI":
    from tiger.pages import secrets as page_secrets
    page_secrets.render()

elif nav_choice == "Run Ingestion":
    from tiger.pages import run as page_run
    page_run.render(default_warehouse=_wh)

elif nav_choice == "Ingestion Console":
    from tiger.pages import console as page_console
    page_console.render()

elif nav_choice == "Data Explorer":
    from tiger.pages import explorer as page_explorer
    page_explorer.render()

elif nav_choice == "Task Scheduler":
    from tiger.pages import scheduler as page_scheduler
    page_scheduler.render(default_warehouse=_wh)

elif nav_choice == "Pipeline Overview":
    from tiger.pages import help as page_help
    page_help.render()
