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

session = get_session()

from tiger.sidebar import get_session_context, render_sidebar, render_topbar

_user, _role, _wh = get_session_context()
nav_choice = render_sidebar(_logo_uri, _user, _role, _wh)
render_topbar(nav_choice, _wh)


# ─────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────
def _render_page(page_name, module_path, **kwargs):
    try:
        import importlib
        mod = importlib.import_module(module_path)
        mod.render(**kwargs)
    except ImportError as e:
        st.error(f"Failed to load {page_name}: {str(e)}")
    except Exception as e:
        st.error(f"Error rendering {page_name}")
        st.exception(e)


_PAGES = {
    "Manage API Configs":   ("tiger.pages.config",    {}),
    "Manage Secrets & EAI": ("tiger.pages.secrets",   {}),
    "Run Ingestion":        ("tiger.pages.run",       {"default_warehouse": _wh}),
    "Ingestion Console":    ("tiger.pages.console",   {}),
    "Data Explorer":        ("tiger.pages.explorer",  {}),
    "Task Scheduler":       ("tiger.pages.scheduler", {"default_warehouse": _wh}),
    "Pipeline Overview":    ("tiger.pages.help",      {}),
}

if nav_choice in _PAGES:
    module_path, kwargs = _PAGES[nav_choice]
    _render_page(nav_choice, module_path, **kwargs)
else:
    st.warning(f"Unknown page: {nav_choice}")
    st.info("Select a page from the sidebar.")
