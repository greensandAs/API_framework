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

st.set_page_config(page_title="Tiger SnowSync", layout="wide", page_icon="🗃️", initial_sidebar_state="expanded")

# ─── Brand logo (rendered manually in the sidebar with full size control) ───
@st.cache_data(show_spinner=False)
def _load_logo_b64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""

_LOGO_PATH = "Tiger_Snow_sync_logo.png"   # ships alongside streamlit_app.py
_logo_b64 = _load_logo_b64(_LOGO_PATH)
_logo_uri = f"data:image/png;base64,{_logo_b64}" if _logo_b64 else ""

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

    :root {
        --bg-deep: #0a0a0a;
        --bg-card: #111111;
        --bg-elevated: #1a1a1a;
        --bg-hover: #161616;
        --border-subtle: #1f1f1f;
        --border-strong: #2e2e2e;
        --text-primary: #fafafa;
        --text-secondary: #a1a1aa;
        --text-muted: #52525b;
        --accent-green: #29B5E8;
        --accent-green-glow: rgba(41,181,232,0.08);
        --accent-red: #ef4444;
        --accent-blue: #29B5E8;
        --accent-amber: #f59e0b;
        --border-active: rgba(41,181,232,0.3);
        --space-1: 4px; --space-2: 8px; --space-3: 12px;
        --space-4: 16px; --space-6: 24px; --space-8: 32px;
        --font-display: 'Manrope', sans-serif;
        --font-body: 'Inter', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
        color-scheme: dark;
    }

    .block-container { padding-top: 0.6rem; padding-bottom: 1rem; max-width: 100%; font-family: var(--font-body); }
    html, body, [class*="css"] { font-family: var(--font-body); }
    .main .block-container { background: var(--bg-deep); }

    h1, h2, h3, h4, h5, h6 { font-family: var(--font-display) !important; font-weight: 800 !important; letter-spacing: -0.03em !important; color: var(--text-primary) !important; }
    [data-testid="stHeading"] { color: var(--text-primary) !important; }
    .main .block-container .stMarkdown p,
    .main .block-container .stMarkdown li,
    .main .block-container .stMarkdown span,
    .main .block-container .stMarkdown td,
    .main .block-container .stMarkdown th { color: var(--text-primary) !important; }
    .main .block-container label,
    .main .block-container .stSelectbox label,
    .main .block-container .stNumberInput label,
    .main .block-container .stTextInput label,
    .main .block-container .stCheckbox label { color: var(--text-secondary) !important; }
    .main .block-container .stCaption p { color: var(--text-muted) !important; font-family: var(--font-mono) !important; font-size: 0.72rem !important; }
    .main .block-container .stMarkdown strong { color: var(--text-primary) !important; }
    .main .block-container .stMarkdown a { color: var(--accent-blue) !important; }
    .main .block-container [data-testid="stText"] { color: var(--text-primary) !important; }

    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a0e14 0%, #0d1117 50%, #111820 100%); border-right: 1px solid var(--border-subtle); }
    section[data-testid="stSidebar"]::after { content: ''; position: absolute; top: 0; right: 0; bottom: 0; width: 1px; background: linear-gradient(180deg, transparent, var(--accent-green), transparent); opacity: 0.15; }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] label { color: var(--text-secondary) !important; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2 { color: var(--text-primary) !important; }

    .stTabs { margin-top: 0.2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; flex-wrap: nowrap; overflow-x: auto; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0; scrollbar-width: thin; }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { height: 2px; }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 1px; }
    .stTabs [data-baseweb="tab"] { border-radius: 0; padding: 8px 16px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; min-width: fit-content; transition: all 0.2s; border-bottom: 2px solid transparent; font-family: var(--font-mono); letter-spacing: 0.3px; text-transform: uppercase; color: var(--text-secondary) !important; }
    .stTabs [data-baseweb="tab"]:hover { border-bottom-color: var(--text-muted); }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid var(--accent-green) !important; color: var(--accent-green) !important; }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 1rem; }

    [data-testid="stMetric"] {
        background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 16px 18px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        transition: all 0.25s cubic-bezier(.22,1,.36,1); position: relative; overflow: hidden;
    }
    [data-testid="stMetric"]::after { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--accent-green); opacity: 0; transition: opacity 0.25s; }
    [data-testid="stMetric"]:hover { border-color: var(--border-active); transform: translateY(-2px); box-shadow: 0 4px 20px rgba(63,185,80,0.06); }
    [data-testid="stMetric"]:hover::after { opacity: 1; }
    [data-testid="stMetricLabel"] { font-size: 0.66rem !important; color: var(--text-secondary) !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.8px; font-family: var(--font-mono) !important; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 800 !important; color: var(--text-primary) !important; font-family: var(--font-display) !important; letter-spacing: -0.5px; }

    .stButton>button { border-radius: 6px; font-weight: 600; font-size: 0.8rem; transition: all 0.15s; border: 1px solid var(--border-subtle); padding: 8px 20px; font-family: var(--font-display); letter-spacing: 0.2px; }
    .stButton>button:hover { border-color: var(--accent-green); color: var(--accent-green); box-shadow: 0 0 12px var(--accent-green-glow); }
    .stButton>button[kind="primary"] { background: var(--accent-green); border: none; color: var(--bg-deep); font-weight: 700; }
    .stButton>button[kind="primary"]:hover { box-shadow: 0 0 20px rgba(63,185,80,0.25); transform: translateY(-1px); }

    .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea { background-color: var(--bg-card) !important; color: var(--text-primary) !important; border-color: var(--border-subtle) !important; font-family: var(--font-body) !important; border-radius: 6px !important; }
    .main .block-container [data-baseweb="select"] span,
    .main .block-container [data-baseweb="select"] div { color: var(--text-primary) !important; }
    .main .block-container [data-baseweb="input"] input { color: var(--text-primary) !important; background: var(--bg-card) !important; }

    div[data-testid="stExpander"] { border-radius: 8px; border: 1px solid var(--border-subtle); overflow: hidden; background: var(--bg-card); }
    div[data-testid="stExpander"] summary { font-weight: 600; font-size: 0.84rem; padding: 12px 16px; font-family: var(--font-body); }
    div[data-testid="stExpander"] summary span { color: var(--text-primary) !important; }
    div[data-testid="stExpander"] .stMarkdown p,
    div[data-testid="stExpander"] .stMarkdown span { color: var(--text-primary) !important; }

    .stDataFrame { border-radius: 8px; overflow: hidden; border: 1px solid var(--border-subtle); }
    [data-testid="stDataFrame"] { background: var(--bg-deep) !important; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12) !important; overflow: hidden; }
    .dvn-scroller { background: var(--bg-deep) !important; }
    [data-testid="stDataFrame"] [data-testid="glideDataEditor"],
    [data-testid="stDataFrame"] canvas { background: var(--bg-deep) !important; }
    [data-testid="stDataFrame"] header,
    [data-testid="stDataFrame"] th { background: var(--bg-elevated) !important; color: var(--text-primary) !important; }
    [data-testid="stDataFrame"] td { color: var(--text-primary) !important; }
    [data-testid="stDataFrame"] .gdg-header { background: var(--bg-elevated) !important; color: var(--text-primary) !important; }
    [data-testid="stDataFrame"] .gdg-cell { color: var(--text-primary) !important; background: var(--bg-deep) !important; }

    div[data-testid="stForm"] { background-color: var(--bg-card); padding: 1.5rem; border-radius: 8px; border-left: 3px solid var(--accent-green); box-shadow: 0 1px 3px rgba(0,0,0,0.3); }

    hr { border-color: var(--border-subtle) !important; }

    [data-testid="stAlert"], [data-testid="stNotification"], div[role="alert"] { background: var(--bg-card) !important; border: 1px solid var(--border-subtle) !important; border-radius: 8px !important; color: var(--text-primary) !important; }
    [data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] strong,
    [data-testid="stNotification"] p, [data-testid="stNotification"] span,
    div[role="alert"] p, div[role="alert"] span { color: var(--text-primary) !important; }

    [data-testid="stToast"] { background: var(--bg-elevated) !important; color: var(--text-primary) !important; border: 1px solid var(--border-subtle) !important; }
    [data-testid="stToast"] p, [data-testid="stToast"] span { color: var(--text-primary) !important; }

    .main .block-container .stCheckbox span { color: var(--text-primary) !important; }
    .stMarkdown code { background: rgba(255,255,255,0.06) !important; color: var(--text-primary) !important; font-family: var(--font-mono) !important; border-radius: 3px; padding: 1px 5px; }
    .stMarkdown pre { background: var(--bg-card) !important; border: 1px solid var(--border-subtle) !important; border-radius: 6px !important; }
    .stMarkdown pre code { background: transparent !important; }

    .stDownloadButton>button { border-radius: 6px; font-weight: 500; font-size: 0.76rem; border: 1px solid var(--border-subtle); font-family: var(--font-mono); }
    .stDownloadButton>button:hover { border-color: var(--accent-green); color: var(--accent-green); }

    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-secondary); }

    .stSpinner>div { border-color: var(--accent-green) transparent transparent transparent !important; }

    div[data-testid="stPopover"] > div > div > div .stButton > button,
    div[data-testid="stPopover"] > div > div > div [data-testid="stButton"] > button,
    div[data-testid="stPopover"] button[data-testid="stBaseButton-secondary"] {
        background: #f85149 !important;
        color: #ffffff !important;
        border: none !important;
        border-color: #f85149 !important;
    }
    div[data-testid="stPopover"] > div > div > div .stButton > button:hover,
    div[data-testid="stPopover"] > div > div > div [data-testid="stButton"] > button:hover,
    div[data-testid="stPopover"] button[data-testid="stBaseButton-secondary"]:hover {
        background: #da3633 !important;
        color: #ffffff !important;
        border-color: #da3633 !important;
        box-shadow: 0 0 18px rgba(248,81,73,0.3) !important;
        transform: none !important;
    }
    div[data-testid="stPopover"] > button {
        border-color: #f85149 !important;
        color: #f85149 !important;
        background: transparent !important;
    }
    div[data-testid="stPopover"] > button:hover {
        background: rgba(248,81,73,0.12) !important;
        border-color: #f85149 !important;
        box-shadow: 0 0 14px rgba(248,81,73,0.2) !important;
        color: #f85149 !important;
    }

    .section-label {
        color: var(--accent-green) !important;
        font-weight: 600;
        font-size: 0.68rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        font-family: var(--font-mono);
        margin-bottom: 0.25rem;
    }

    .stitch-row {
        display: flex; align-items: center;
        background: var(--bg-card); padding: 1rem; border-radius: 8px; margin-bottom: 8px;
        border: 1px solid var(--border-subtle);
        transition: all 0.2s;
    }
    .stitch-row:hover { border-color: var(--border-active); }
    .stitch-row-content { flex-grow: 1; }
    .stitch-row-title { font-weight: 700; font-family: var(--font-display); color: var(--text-primary); }
    .stitch-row-sub { font-size: 0.72rem; color: var(--text-secondary); font-family: var(--font-body); font-weight: 500; }
    .stitch-row-status { font-family: var(--font-display); font-weight: 800; font-size: 1.1rem; }

    .stitch-pill {
        display: inline-block; padding: 0.2rem 0.75rem; border-radius: 999px;
        font-family: var(--font-mono); font-weight: 600; font-size: 0.68rem; letter-spacing: 0.5px;
    }
    .pill-active { background: rgba(63,185,80,0.1); color: var(--accent-green); border: 1px solid rgba(63,185,80,0.2); }
    .pill-inactive { background: rgba(248,81,73,0.1); color: var(--accent-red); border: 1px solid rgba(248,81,73,0.2); }
    .pill-success { background: rgba(63,185,80,0.1); color: var(--accent-green); border: 1px solid rgba(63,185,80,0.2); }
    .pill-error { background: rgba(248,81,73,0.1); color: var(--accent-red); border: 1px solid rgba(248,81,73,0.2); }

    div[data-testid="stPopover"] { background: var(--bg-elevated) !important; border: 1px solid var(--border-subtle) !important; }
    .main .block-container [data-baseweb="popover"] li { color: var(--text-primary) !important; }

    /* ──────────────────────────────────────────────────────────
       Datadog/Vercel-style metric tiles, config cards, chips
       ────────────────────────────────────────────────────────── */
    .dd-tile {
        background: rgba(17,17,17,0.55);
        backdrop-filter: blur(14px) saturate(150%);
        -webkit-backdrop-filter: blur(14px) saturate(150%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.18s cubic-bezier(.22,1,.36,1);
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .dd-tile::after {
        content: '';
        position: absolute; inset: 0;
        border-radius: inherit;
        background: linear-gradient(135deg, rgba(255,255,255,0.04), transparent 60%);
        pointer-events: none;
    }
    .dd-tile:hover {
        border-color: rgba(255,255,255,0.10);
        transform: translateY(-1px);
        box-shadow: 0 12px 32px rgba(0,220,130,0.06);
    }
    /* Status glow variants */
    .dd-tile.glow-ok {
        box-shadow: 0 0 0 1px rgba(41,181,232,0.18), 0 8px 24px rgba(41,181,232,0.06);
    }
    .dd-tile.glow-warn {
        box-shadow: 0 0 0 1px rgba(245,158,11,0.22), 0 8px 24px rgba(245,158,11,0.07);
        animation: dd-glow-warn 3.4s ease-in-out infinite;
    }
    .dd-tile.glow-err {
        box-shadow: 0 0 0 1px rgba(239,68,68,0.25), 0 8px 24px rgba(239,68,68,0.08);
        animation: dd-glow-err 2.8s ease-in-out infinite;
    }
    @keyframes dd-glow-warn {
        0%,100% { box-shadow: 0 0 0 1px rgba(245,158,11,0.18), 0 8px 24px rgba(245,158,11,0.06); }
        50%     { box-shadow: 0 0 0 1px rgba(245,158,11,0.38), 0 10px 32px rgba(245,158,11,0.14); }
    }
    @keyframes dd-glow-err {
        0%,100% { box-shadow: 0 0 0 1px rgba(239,68,68,0.20), 0 8px 24px rgba(239,68,68,0.06); }
        50%     { box-shadow: 0 0 0 1px rgba(239,68,68,0.45), 0 12px 36px rgba(239,68,68,0.18); }
    }
    /* Bento sizes */
    .dd-tile.hero { min-height: 150px; padding: 22px 26px; }
    .dd-tile.hero .value { font-size: 2.4rem; }
    .dd-tile.hero .label { font-size: 0.7rem; }

    /* Tile head row (label + status pill) */
    .dd-tile .tile-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
    .dd-tile .tile-pill {
        font-family: var(--font-mono); font-size: 0.58rem; font-weight: 700;
        padding: 2px 7px; border-radius: 4px;
        letter-spacing: 0.6px; text-transform: uppercase;
        background: rgba(255,255,255,0.04); color: var(--text-secondary);
        border: 1px solid var(--border-subtle);
        white-space: nowrap;
    }
    .dd-tile .tile-pill.ok   { background: var(--accent-green-glow); color: var(--accent-green); border-color: rgba(0,220,130,0.25); }
    .dd-tile .tile-pill.warn { background: rgba(245,158,11,0.08); color: var(--accent-amber); border-color: rgba(245,158,11,0.25); }
    .dd-tile .tile-pill.err  { background: rgba(239,68,68,0.08); color: var(--accent-red); border-color: rgba(239,68,68,0.30); }
    .dd-tile::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, var(--accent-green), transparent);
        opacity: 0; transition: opacity 0.25s;
    }
    .dd-tile:hover::before { opacity: 0.5; }
    .dd-tile.live::before { opacity: 1; }
    .dd-tile .pulse {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--accent-green); display: inline-block;
        box-shadow: 0 0 0 0 rgba(0,220,130,0.7);
        animation: dd-pulse 2s infinite;
    }
    @keyframes dd-pulse {
        0%   { box-shadow: 0 0 0 0 rgba(41,181,232,0.7); }
        70%  { box-shadow: 0 0 0 8px rgba(41,181,232,0); }
        100% { box-shadow: 0 0 0 0 rgba(41,181,232,0); }
    }
    .dd-tile .label {
        font-family: var(--font-mono); font-size: 0.62rem; font-weight: 600;
        color: var(--text-muted); letter-spacing: 1.2px; text-transform: uppercase;
        display: flex; align-items: center; gap: 6px;
    }
    .dd-tile .value {
        font-family: var(--font-display); font-size: 1.85rem; font-weight: 800;
        color: var(--text-primary); letter-spacing: -0.8px; line-height: 1;
        margin: 6px 0 4px;
    }
    .dd-tile .delta {
        font-family: var(--font-mono); font-size: 0.7rem; font-weight: 600;
        display: inline-flex; align-items: center; gap: 4px;
    }
    .dd-tile .delta.up   { color: var(--accent-green); }
    .dd-tile .delta.down { color: var(--accent-red); }
    .dd-tile .delta.flat { color: var(--text-muted); }

    /* Configuration card */
    .cfg-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--border-strong);
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        transition: all 0.15s ease;
        position: relative;
    }
    .cfg-card:hover { background: var(--bg-hover); border-color: var(--border-strong); }
    .cfg-card.healthy  { border-left-color: var(--accent-green); }
    .cfg-card.warning  { border-left-color: var(--accent-amber); }
    .cfg-card.error    { border-left-color: var(--accent-red); }
    .cfg-card.inactive { border-left-color: var(--text-muted); opacity: 0.65; }
    .cfg-card .name {
        font-family: var(--font-display); font-weight: 800; font-size: 0.95rem;
        color: var(--text-primary); letter-spacing: -0.3px;
    }
    .cfg-card .endpoint {
        font-family: var(--font-mono); font-size: 0.74rem;
        color: var(--text-secondary); margin-top: 4px;
        word-break: break-all;
    }
    .cfg-card .badges { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
    .cfg-card .badge {
        font-family: var(--font-mono); font-size: 0.6rem; font-weight: 600;
        padding: 2px 8px; border-radius: 4px;
        text-transform: uppercase; letter-spacing: 0.5px;
        background: rgba(255,255,255,0.04); color: var(--text-secondary);
        border: 1px solid var(--border-subtle);
    }
    .cfg-card .badge.accent  { background: rgba(0,220,130,0.08); color: var(--accent-green); border-color: rgba(0,220,130,0.2); }
    .cfg-card .badge.warn    { background: rgba(245,158,11,0.08); color: var(--accent-amber); border-color: rgba(245,158,11,0.2); }
    .cfg-card .badge.danger  { background: rgba(239,68,68,0.08); color: var(--accent-red); border-color: rgba(239,68,68,0.2); }
    .cfg-card .meta {
        font-size: 0.72rem; color: var(--text-muted); margin-top: 8px;
        font-family: var(--font-body);
    }

    /* Filter chip bar */
    .chip-bar { display: flex; gap: 8px; margin: 6px 0 14px; flex-wrap: wrap; }
    .chip {
        background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle);
        border-radius: 999px; padding: 5px 12px;
        font-size: 0.74rem; font-family: var(--font-mono); font-weight: 600;
        color: var(--text-secondary);
    }
    .chip.active { background: var(--accent-green-glow); border-color: rgba(0,220,130,0.3); color: var(--accent-green); }
    .chip.warn   { background: rgba(245,158,11,0.06); border-color: rgba(245,158,11,0.3); color: var(--accent-amber); }
    .chip.muted  { color: var(--text-muted); }

    /* Sticky topbar */
    .topbar {
        position: sticky; top: 0; z-index: 100;
        background: linear-gradient(180deg, rgba(10,10,10,0.95) 0%, rgba(10,10,10,0.85) 100%);
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--border-subtle);
        padding: 12px 6px; margin: -8px 0 18px;
        display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
    }
    .topbar-brand { display: flex; align-items: center; gap: 12px; }
    .topbar-icon {
        font-size: 1.3rem; line-height: 1;
        background: var(--accent-green-glow); border: 1px solid rgba(0,220,130,0.2);
        width: 32px; height: 32px; border-radius: 8px;
        display: inline-flex; align-items: center; justify-content: center;
    }
    .topbar-title {
        font-family: var(--font-display); font-weight: 800; font-size: 1.05rem;
        color: var(--text-primary); letter-spacing: -0.5px;
    }
    .topbar-sub {
        font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-muted);
        padding-left: 12px; border-left: 1px solid var(--border-subtle);
        margin-left: 4px; letter-spacing: 0.4px; text-transform: uppercase;
    }
    .topbar-meta { display: flex; gap: 6px; flex-wrap: wrap; }
    .pill {
        background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle);
        border-radius: 6px; padding: 5px 10px;
        font-family: var(--font-mono); font-size: 0.66rem; font-weight: 600;
        color: var(--text-secondary); letter-spacing: 0.4px;
        display: inline-flex; align-items: center; gap: 5px;
    }
    .pill.accent { background: var(--accent-green-glow); border-color: rgba(0,220,130,0.2); color: var(--accent-green); }

    /* Sparkline inside dd-tile */
    .dd-tile .spark { margin-top: 10px; opacity: 0.85; line-height: 0; }
    .dd-tile .spark svg { display: block; width: 100%; height: 28px; }

    /* Status legend bar */
    .legend-bar {
        display: flex; gap: 18px; flex-wrap: wrap;
        padding: 10px 14px; margin: -2px 0 14px;
        background: rgba(255,255,255,0.02);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        font-family: var(--font-mono);
        font-size: 0.7rem;
        color: var(--text-secondary);
    }
    .legend-item { display: inline-flex; align-items: center; gap: 6px; }
    .legend-dot {
        width: 8px; height: 8px; border-radius: 50%;
        display: inline-block;
    }
    .legend-dot.healthy  { background: var(--accent-green); }
    .legend-dot.warning  { background: var(--accent-amber); }
    .legend-dot.error    { background: var(--accent-red); }
    .legend-dot.inactive { background: var(--text-muted); }

    /* cfg-card hover overlay */
    .cfg-card { cursor: default; }
    .cfg-card .hover-stats {
        position: absolute; right: 18px; top: 14px;
        display: flex; gap: 14px;
        opacity: 0; transition: opacity 0.18s;
        font-family: var(--font-mono); font-size: 0.66rem;
        color: var(--text-muted);
    }
    .cfg-card:hover .hover-stats { opacity: 1; }
    .cfg-card .hover-stats .stat-label { color: var(--text-muted); }
    .cfg-card .hover-stats .stat-value { color: var(--text-primary); font-weight: 600; margin-left: 4px; }
    .cfg-card .hover-stats .stat-value.ok    { color: var(--accent-green); }
    .cfg-card .hover-stats .stat-value.err   { color: var(--accent-red); }

    /* Skeleton loader */
    .skeleton {
        background: linear-gradient(90deg, var(--bg-card) 25%, var(--bg-elevated) 50%, var(--bg-card) 75%);
        background-size: 200% 100%;
        animation: shimmer 1.4s infinite;
        border-radius: 8px;
    }
    @keyframes shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    .skeleton.tile { height: 110px; }
    .skeleton.row  { height: 18px; margin: 6px 0; }

    /* Inline code block polish (used by st.code) */
    .stCodeBlock pre, code[class*="language-"] {
        background: #0d0d0d !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        font-family: var(--font-mono) !important;
        font-size: 0.78rem !important;
    }

    /* Sidebar nav (Vercel/Linear style) */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a0a 0%, #0d0d0d 100%) !important;
        border-right: 1px solid var(--border-subtle) !important;
        padding-top: 14px;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 18px 16px; }
    section[data-testid="stSidebar"] .sb-brand {
        display: flex; align-items: center; gap: 10px;
        padding: 6px 8px 14px;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 14px;
    }
    section[data-testid="stSidebar"] .sb-brand-icon {
        width: 30px; height: 30px; border-radius: 7px;
        background: var(--accent-green-glow); border: 1px solid rgba(0,220,130,0.2);
        display: inline-flex; align-items: center; justify-content: center; font-size: 1.05rem;
    }
    section[data-testid="stSidebar"] .sb-brand-name {
        font-family: var(--font-display); font-weight: 800;
        color: var(--text-primary); letter-spacing: -0.4px;
        font-size: 0.98rem;
    }
    section[data-testid="stSidebar"] .sb-brand-sub {
        font-family: var(--font-mono); font-size: 0.62rem;
        color: var(--text-muted); letter-spacing: 0.5px; text-transform: uppercase;
    }
    /* Radio styled as nav list */
    section[data-testid="stSidebar"] [role="radiogroup"] {
        display: flex; flex-direction: column; gap: 2px;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 8px 12px; border-radius: 6px;
        cursor: pointer; transition: all 0.12s;
        font-family: var(--font-body); font-weight: 500;
        font-size: 0.86rem;
        color: var(--text-secondary) !important;
        position: relative;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.03);
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"],
    section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: var(--accent-green-glow);
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before {
        content: ''; position: absolute; left: 0; top: 8px; bottom: 8px; width: 2px;
        background: var(--accent-green); border-radius: 2px;
    }
    /* Hide the radio circle */
    section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none !important; }
    section[data-testid="stSidebar"] .sb-footer {
        margin-top: 24px; padding: 12px 8px;
        border-top: 1px solid var(--border-subtle);
        font-family: var(--font-mono); font-size: 0.66rem; color: var(--text-muted);
    }
    section[data-testid="stSidebar"] .sb-group {
        font-family: var(--font-mono); font-size: 0.6rem; font-weight: 700;
        color: var(--text-muted); letter-spacing: 1.4px; text-transform: uppercase;
        padding: 14px 8px 6px; margin-top: 4px;
    }
    section[data-testid="stSidebar"] .sb-tagline {
        font-family: var(--font-mono); font-size: 0.66rem; font-weight: 600;
        color: var(--text-muted); letter-spacing: 0.8px;
        padding: 4px 10px 12px; margin-top: -4px;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 4px;
    }
    section[data-testid="stSidebar"] .sb-logo {
        padding: 8px 10px 4px;
        text-align: center;
        background: linear-gradient(180deg, #0a0a0a 0%, #0d0d0d 100%);
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] .sb-logo img {
        width: 100%;
        max-width: 220px;
        height: auto;
        display: block;
        margin: 0 auto;
        filter: drop-shadow(0 2px 8px rgba(0,0,0,0.4));
        mix-blend-mode: screen;
        background: transparent;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important; border: 1px solid transparent !important;
        color: var(--text-secondary) !important;
        text-align: left !important; justify-content: flex-start !important;
        padding: 7px 12px !important; font-weight: 500 !important;
        font-size: 0.86rem !important; font-family: var(--font-body) !important;
        border-radius: 6px !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.03) !important;
        color: var(--text-primary) !important;
        border-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

conn = st.connection("snowflake")
session = conn.session()

DB = "API_DATA_PIPELINE"
META = f"{DB}.METADATA"
RAW = f"{DB}.RAW_LANDING"

SAFE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,254}$")
SAFE_VALUE_RE = re.compile(r"^[^'\\;]*$")

def is_safe_name(name: str) -> bool:
    return bool(SAFE_NAME_RE.match(name))

def is_safe_literal(value: str) -> bool:
    return bool(SAFE_VALUE_RE.match(value))

def escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")

def run_query(sql, params=None):
    if params:
        df = session.sql(sql, params=params).to_pandas()
    else:
        df = session.sql(sql).to_pandas()
    df.columns = [c.strip('"') for c in df.columns]
    return df

def exec_sql(sql, params=None):
    if params:
        session.sql(sql, params=params).collect()
    else:
        session.sql(sql).collect()

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

# ─────────────────────────────────────────────
# Network Rule / URL Compatibility helpers
# ─────────────────────────────────────────────
from urllib.parse import urlparse as _nr_urlparse

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
        # exact host match
        if a_host == host:
            if not a_port or a_port == port or (not port and a_port in ("443", "80")):
                return True, f"{a['entry']} (rule: {a['rule']})", "exact host match"
        # wildcard prefix: *.domain.com matches anything ending with .domain.com
        if a_host.startswith("*."):
            suffix = a_host[1:]  # ".domain.com"
            if host.endswith(suffix):
                return True, f"{a['entry']} (rule: {a['rule']})", "wildcard match"
    return False, None, f"Host '{host}' not covered by any network rule"

# ─────────────────────────────────────────────
# Data Explorer (Schema Discovery) helpers
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

def _ds_collect_records(payload, records_path):
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

# ─────────────────────────────────────────────
# Error Code Knowledge Base
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
            "Try the endpoint in a REST client (Postman/curl) with same params",
            "Inspect ERROR_MESSAGE_TEXT — APIs usually echo the validation error",
        ],
        "snowflake_tip": "Run `SELECT ERROR_MESSAGE_TEXT FROM INGESTION_RESPONSE_LOG WHERE STATUS_CODE = 400 LIMIT 10` — the API usually returns a body explaining exactly what's wrong.",
        "retry_behaviour": "Framework retries — but retries won't help if the request itself is invalid.",
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
            "Rebuild the EAI (use the Rebuild button in Secrets tab)",
            "Verify the API key is still valid in the provider dashboard",
            "For OAuth: check the security integration token endpoint URL",
        ],
        "snowflake_tip": "Run `DESCRIBE SECRET <META>.<secret_name>` to confirm the secret still exists. Then rebuild EAI.",
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
        "snowflake_tip": "Snowflake's outbound IPs vary by region. Check `SELECT SYSTEM$ALLOWLIST()` for the IP ranges to whitelist with the API provider.",
        "retry_behaviour": "Retries will all fail — this is an access control issue.",
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
            "If only on high page numbers, this may be the paginator passing the last page (safe)",
            "Verify the ENDPOINT_URL against current API documentation",
        ],
        "snowflake_tip": "Check API_URL alongside PAGE_NUMBER — if 404s only appear on high page numbers it's likely the paginator running past the last page.",
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
            "Increase TIMEOUT_SEC in the config (current default: 30s)",
            "If the API supports page size, add a page_size param to the URL",
            "Check AVG_RESPONSE_TIME_SECONDS in the log for trend",
        ],
        "snowflake_tip": "Look at AVG_RT_WHEN_ERROR vs the configured TIMEOUT_SEC — if they're close, raise the timeout.",
        "retry_behaviour": "Framework retries with backoff — often self-heals.",
        "urgency": "Monitor — tune timeout if persistent",
    },
    "429": {
        "label": "Too Many Requests", "severity": "warning", "category": "Rate Limit", "icon": "🚦",
        "what_happened": "The API is rate-limiting this integration. Too many requests in a given window.",
        "likely_causes": [
            "RETRY_DELAY_SEC is too low — retries are hitting the rate limit again",
            "Running multiple APIs against the same provider simultaneously (parallel mode)",
            "Low API tier with a tight rate limit",
        ],
        "actions": [
            "Increase RETRY_DELAY_SEC to at least 60s for rate-limited APIs",
            "Switch from Parallel to Sequential execution for this provider",
            "Match RETRY_DELAY_SEC to the Retry-After header value",
            "Schedule this API at off-peak hours",
        ],
        "snowflake_tip": "Check ERROR_MESSAGE_TEXT — most APIs include a Retry-After header value in the error body. Set RETRY_DELAY_SEC to that value.",
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
            "Let the framework retry — monitor if it self-heals",
            "If incremental, try narrowing the watermark range manually",
        ],
        "snowflake_tip": "If 500s spike on a single API, set a Snowflake task alert via SUSPEND_TASK_AFTER_NUM_FAILURES so it doesn't burn credits during an outage.",
        "retry_behaviour": "Framework retries with backoff — usually self-heals during provider recovery.",
        "urgency": "Monitor provider status page",
    },
    "502": {
        "label": "Bad Gateway", "severity": "warning", "category": "Network", "icon": "🌐",
        "what_happened": "An intermediate proxy or load balancer in front of the API failed.",
        "likely_causes": ["API provider is deploying or restarting", "CDN/gateway issue on the provider side"],
        "actions": ["Usually transient — let the framework retry", "Check provider status page if persistent"],
        "snowflake_tip": "If 502s correlate with deployments, schedule ingestion outside the provider's known release windows.",
        "retry_behaviour": "Almost always self-heals on retry.",
        "urgency": "Usually self-resolving",
    },
    "503": {
        "label": "Service Unavailable", "severity": "error", "category": "Server", "icon": "🔴",
        "what_happened": "The API is temporarily down — either for maintenance or overloaded.",
        "likely_causes": ["Scheduled maintenance window", "Provider outage"],
        "actions": [
            "Check the provider's status page and maintenance schedule",
            "Schedule ingestion outside of known maintenance windows",
        ],
        "snowflake_tip": "If 503s cluster on weekends, the provider likely runs maintenance then. Use a CRON schedule that avoids those windows.",
        "retry_behaviour": "Framework retries — recovers once the provider is back.",
        "urgency": "Check provider status",
    },
    "504": {
        "label": "Gateway Timeout", "severity": "warning", "category": "Network", "icon": "⌛",
        "what_happened": "The API gateway timed out waiting for the backend to respond.",
        "likely_causes": [
            "Very large data page — the backend is slow to build the response",
            "Provider infrastructure is slow",
        ],
        "actions": [
            "Reduce page size if the API supports it",
            "Increase TIMEOUT_SEC in the config",
            "Schedule during off-peak hours",
        ],
        "snowflake_tip": "If using OFFSET pagination, large offsets are exponentially slow. Switch to PAGE-based or cursor-based if the API supports it.",
        "retry_behaviour": "Framework retries — may self-heal on off-peak retries.",
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
            "Rebuild the EAI (Rebuild button in the Secrets tab)",
            "Check ERROR_MESSAGE_TEXT — it will contain the Python exception message",
            "Try the URL in a browser — if it fails there, it's a bad URL",
        ],
        "snowflake_tip": "Run `SHOW EXTERNAL ACCESS INTEGRATIONS LIKE 'EAI_UNIVERSAL_INGESTOR'` and check ALLOWED_NETWORK_RULES. Then `DESC NETWORK RULE <rule>` to see the VALUE_LIST.",
        "retry_behaviour": "Retries will all fail until EAI/network rule is fixed.",
        "urgency": "Immediate — nothing will work until this is resolved",
    },
}


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

def section_label(text):
    st.markdown(f"<p class='section-label'>{text}</p>", unsafe_allow_html=True)

def empty_state(icon, title, subtitle):
    """Reusable illustrated empty-state card."""
    st.markdown(f"""
    <div style="background: var(--bg-card); border: 1px dashed var(--border-strong); border-radius: 10px; padding: 32px; text-align: center; margin: 18px 0;">
        <div style="font-size: 2rem; margin-bottom: 8px;">{icon}</div>
        <div style="font-family: var(--font-display); font-weight: 800; color: var(--text-primary); font-size: 1.05rem;">{title}</div>
        <div style="color: var(--text-secondary); font-size: 0.82rem; margin-top: 6px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

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
            day_map = {"0":"Sun","1":"Mon","2":"Tue","3":"Wed","4":"Thu","5":"Fri","6":"Sat"}
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
            day_map = {"0":"Sun","1":"Mon","2":"Tue","3":"Wed","4":"Thu","5":"Fri","6":"Sat"}
            desc.append(f"on {day_map.get(dow, dow)}")
        return "🕐 " + " ".join(desc) + " UTC"
    except Exception:
        return f"CRON: {expr}"

def _parse_next_runs(tasks_df, horizon_hours=24):
    """Return list of {task, warehouse, time, hour_offset} for the next N hours."""
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
        c = re.match(r"USING CRON\s+(\S+)\s+(\S+)", sched, re.IGNORECASE)
        if c and c.group(2).isdigit():
            h = int(c.group(2))
            for d_off in (0, 1):
                t_cand = now.replace(hour=h, minute=0, second=0, microsecond=0) + pd.Timedelta(days=d_off)
                if now < t_cand < now + pd.Timedelta(hours=horizon_hours):
                    events.append({
                        "task": name, "warehouse": wh, "time": t_cand,
                        "hour_offset": (t_cand - now).total_seconds() / 3600,
                    })
    return sorted(events, key=lambda x: x["time"])



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

def make_sparkline_svg(values, color="#29B5E8", width=200, height=28):
    """Render a tiny SVG sparkline for inline embedding in dd-tile HTML."""
    if values is None or len(values) < 2:
        return ""
    try:
        vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    except Exception:
        return ""
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    rng = max(mx - mn, 1e-9)
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = i * (width / max(n - 1, 1))
        y = height - ((v - mn) / rng) * (height - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    path = "M " + " L ".join(pts)
    last_x, last_y = pts[-1].split(",")
    return (
        f"<svg viewBox='0 0 {width} {height}' xmlns='http://www.w3.org/2000/svg' preserveAspectRatio='none'>"
        f"<path d='{path}' fill='none' stroke='{color}' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round' opacity='0.85'/>"
        f"<circle cx='{last_x}' cy='{last_y}' r='2' fill='{color}'/>"
        f"</svg>"
    )

def dd_tile(label, value, delta=None, delta_dir="flat", live=False, spark_data=None, spark_color=None, size="default", glow=None, status_pill=None):
    """Datadog/Vercel-style metric tile. status_pill: optional auto-derived from glow if None.
    Pass status_pill='custom text' or status_pill=False to suppress."""
    # Sanitize NaN/None values to a clean "—"
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)) or (isinstance(value, str) and value.lower() in ("nan", "none")):
            value = "—"
    except Exception:
        pass
    if delta is not None:
        try:
            if (isinstance(delta, float) and pd.isna(delta)) or (isinstance(delta, str) and delta.lower() in ("nan", "none")):
                delta = None
        except Exception:
            pass
    classes = ["dd-tile"]
    if live: classes.append("live")
    if size == "hero": classes.append("hero")
    if glow in ("ok", "warn", "err"): classes.append(f"glow-{glow}")
    cls = " ".join(classes)
    pulse = "<span class='pulse'></span>" if live else ""
    delta_html = ""
    if delta:
        arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(delta_dir, "→")
        delta_html = f"<div class='delta {delta_dir}'>{arrow} {delta}</div>"
    spark_html = ""
    if spark_data is not None:
        color_default = {"up": "#29B5E8", "down": "#ef4444", "flat": "#a1a1aa"}.get(delta_dir, "#29B5E8")
        color = spark_color or color_default
        svg = make_sparkline_svg(list(spark_data), color=color)
        if svg:
            spark_html = f"<div class='spark'>{svg}</div>"

    # Auto-derive status pill from glow if not explicitly set
    pill_html = ""
    if status_pill is False:
        pill_html = ""
    elif status_pill:
        pill_html = f"<span class='tile-pill'>{status_pill}</span>"
    elif glow == "ok":
        pill_html = "<span class='tile-pill ok'>ONLINE</span>"
    elif glow == "warn":
        pill_html = "<span class='tile-pill warn'>WARNING</span>"
    elif glow == "err":
        pill_html = "<span class='tile-pill err'>CRITICAL</span>"

    st.markdown(f"""
    <div class='{cls}'>
      <div class='tile-head'>
        <div class='label'>{pulse}{label}</div>
        {pill_html}
      </div>
      <div class='value'>{value}</div>
      {delta_html}
      {spark_html}
    </div>
    """, unsafe_allow_html=True)

def cfg_card(name, endpoint, badges=None, meta=None, status="healthy", hover_stats=None):
    """Configuration Registry card. status ∈ {healthy, warning, error, inactive}.
    hover_stats: list of {label, value, cls} dicts shown on hover."""
    badges = badges or []
    badge_html = "".join(
        f"<span class='badge {b.get('cls','')}'>{b['text']}</span>" for b in badges
    )
    meta_html = f"<div class='meta'>{meta}</div>" if meta else ""
    hover_html = ""
    if hover_stats:
        items = "".join(
            f"<span><span class='stat-label'>{h['label']}:</span>"
            f"<span class='stat-value {h.get('cls','')}'>{h['value']}</span></span>"
            for h in hover_stats
        )
        hover_html = f"<div class='hover-stats'>{items}</div>"
    st.markdown(f"""
    <div class='cfg-card {status}'>
      {hover_html}
      <div class='name'>{name}</div>
      <div class='endpoint'>{endpoint or ''}</div>
      <div class='badges'>{badge_html}</div>
      {meta_html}
    </div>
    """, unsafe_allow_html=True)

def styled_dataframe(df, height=400):
    h_css = f"max-height:{height}px;overflow-y:auto;"
    html = df.to_html(index=False, escape=True, classes="ct-table")
    st.markdown(f'''<div style="{h_css}overflow-x:auto;border:1px solid rgba(255,255,255,0.1);border-radius:8px;">
    <style>
    .ct-table {{width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:0.76rem;}}
    .ct-table th {{background:#161b22;color:#e6edf3;padding:8px 12px;text-align:left;border-bottom:2px solid rgba(255,255,255,0.12);font-weight:600;font-size:0.72rem;position:sticky;top:0;z-index:1;}}
    .ct-table td {{background:#0d1117;color:#e6edf3;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.06);}}
    .ct-table tr:hover td {{background:#1c2333;}}
    </style>{html}</div>''', unsafe_allow_html=True)

def stitch_row(title, subtitle, status_code):
    color = "#3fb950" if status_code == 200 else "#f85149"
    status_display = str(int(status_code)) if pd.notna(status_code) else "ERR"
    st.markdown(f"""
        <div class="stitch-row" style="border-left: 3px solid {color};">
            <div class="stitch-row-content">
                <div class="stitch-row-title">{title}</div>
                <div class="stitch-row-sub">{subtitle}</div>
            </div>
            <div class="stitch-row-status" style="color: {color};">{status_display}</div>
        </div>
    """, unsafe_allow_html=True)

def active_pill(is_active):
    if is_active:
        return "<span class='stitch-pill pill-active'>ACTIVE</span>"
    return "<span class='stitch-pill pill-inactive'>INACTIVE</span>"

# ─── Sticky Topbar ───
try:
    _ctx = run_query("SELECT CURRENT_USER() AS U, CURRENT_ROLE() AS R, CURRENT_WAREHOUSE() AS W")
    _user = str(_ctx["U"].iloc[0]) if not _ctx.empty else "—"
    _role = str(_ctx["R"].iloc[0]) if not _ctx.empty else "—"
    _wh = str(_ctx["W"].iloc[0]) if not _ctx.empty else "—"
except Exception:
    _user, _role, _wh = "—", "—", "—"

# ─── Sidebar Navigation ───
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

if "active_nav" not in st.session_state:
    st.session_state["active_nav"] = "Manage API Configs"

with st.sidebar:
    if _logo_uri:
        st.markdown(
            f"<div class='sb-logo'><img src='{_logo_uri}' alt='Tiger SnowSync'></div>",
            unsafe_allow_html=True
        )
    st.markdown(
        "<div class='sb-tagline'>Accelerating the Data Den</div>",
        unsafe_allow_html=True
    )

    for group_label, items in NAV_GROUPS:
        st.markdown(f"<div class='sb-group'>{group_label}</div>", unsafe_allow_html=True)
        for label, key in items:
            is_active = st.session_state["active_nav"] == key
            cls = " active" if is_active else ""
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
            wh_options = wh_df["NAME"].tolist() if not wh_df.empty else [_wh]
        except Exception:
            wh_options = [_wh]

        if "pref_warehouse" not in st.session_state:
            st.session_state["pref_warehouse"] = _wh if _wh in wh_options else (wh_options[0] if wh_options else "COMPUTE_WH")

        st.selectbox("Default Warehouse (for new tasks)", wh_options, key="pref_warehouse")
        st.number_input("Default Schema Sample Size", min_value=10, max_value=2000, step=10, value=100, key="pref_sample_size")
        st.text_input("Default Landing Table", value="API_RAW_DATA", key="pref_landing_table")

    st.markdown(f"""
    <div class='sb-footer'>
      <div>👤 {_user}</div>
      <div>🛡 {_role}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── Sticky Topbar (page header) ───
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
    <span class='pill accent'>🏢 {_wh}</span>
  </div>
</div>
""", unsafe_allow_html=True)

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
    section_label("SECURITY INFRASTRUCTURE")
    st.header("Secrets & External Access")
    st.caption("Onboarding pipeline: Network Rules → Security Integrations → Secrets → EAI auto-rebuilds.")

    eai_ok = False
    eai_rule_count = 0
    eai_secret_count = 0
    try:
        eai_df = run_query("DESCRIBE INTEGRATION EAI_UNIVERSAL_INGESTOR")
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
    section_label("DATA HARVESTING")
    st.header("Run Ingestion")
    st.caption("Three-phase flow: select APIs → choose how to run → live monitor.")

    # ─── Pull enriched config + last-run rollup ───
    try:
        pre_run_df = run_query(f"""
            SELECT
                c.API_NAME,
                c.ACTIVE_FLAG,
                c.INCREMENTAL_FLAG,
                c.LAST_SYNC_VALUE,
                MAX(l.INSERT_DATETIME_UTC) AS LAST_RUN_TS,
                COUNT(l.INSERT_DATETIME_UTC) AS RUNS_24H,
                SUM(CASE WHEN l.STATUS_CODE != 200 OR l.STATUS_CODE IS NULL THEN 1 ELSE 0 END) AS FAILS_24H
            FROM {META}.INGESTION_CONFIGS c
            LEFT JOIN {META}.INGESTION_RESPONSE_LOG l
                ON c.API_NAME = l.API_NAME
               AND l.INSERT_DATETIME_UTC >= DATEADD('HOUR', -24, CURRENT_TIMESTAMP())
            WHERE c.ACTIVE_FLAG = TRUE
            GROUP BY c.API_NAME, c.ACTIVE_FLAG, c.INCREMENTAL_FLAG, c.LAST_SYNC_VALUE
            ORDER BY c.API_NAME
        """)
    except Exception as _ex:
        st.warning(f"Could not load pre-run context: {_ex}")
        pre_run_df = pd.DataFrame()

    if pre_run_df.empty:
        empty_state("📭", "No active APIs",
                    "Activate at least one API in <strong>Manage API Configs</strong> first.")
    else:
        api_list = pre_run_df["API_NAME"].tolist()

        # ─────────────────────────────────────
        # PHASE 1 — SELECT
        # ─────────────────────────────────────
        section_label("PHASE 1 · SELECT")

        if "ri_selection" not in st.session_state:
            st.session_state["ri_selection"] = []

        # Smart selection shortcuts
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        with sc1:
            if st.button("Select All", use_container_width=True, key="ri_sel_all"):
                st.session_state["ri_selection"] = api_list
                st.rerun()
        with sc2:
            if st.button("Failed (24h)", use_container_width=True, key="ri_sel_failed"):
                failed = pre_run_df[pre_run_df["FAILS_24H"].fillna(0) > 0]["API_NAME"].tolist()
                st.session_state["ri_selection"] = failed
                st.rerun()
        with sc3:
            if st.button("Stale (>12h)", use_container_width=True, key="ri_sel_stale"):
                now = pd.Timestamp.utcnow().tz_localize(None)
                lr = pd.to_datetime(pre_run_df["LAST_RUN_TS"]).dt.tz_localize(None)
                stale_mask = lr.isna() | ((now - lr).dt.total_seconds() > 12 * 3600)
                st.session_state["ri_selection"] = pre_run_df[stale_mask]["API_NAME"].tolist()
                st.rerun()
        with sc4:
            if st.button("Never Run", use_container_width=True, key="ri_sel_never"):
                never = pre_run_df[pre_run_df["LAST_RUN_TS"].isna()]["API_NAME"].tolist()
                st.session_state["ri_selection"] = never
                st.rerun()
        with sc5:
            if st.button("Clear", use_container_width=True, key="ri_sel_clear"):
                st.session_state["ri_selection"] = []
                st.rerun()

        # Multiselect drives `ri_selection` directly via key — survives reruns from radio etc.
        selected_apis = st.multiselect(
            "Selected APIs",
            api_list,
            key="ri_selection",
        )

        # ─── Selection preview — make it crystal clear what will run ───
        if selected_apis:
            sel_chips = "".join(
                f"<span class='chip active'>{a}</span>" for a in selected_apis
            )
            st.markdown(
                f"<div class='chip-bar'>"
                f"<span class='chip warn'>✓ {len(selected_apis)} SELECTED</span>"
                f"{sel_chips}"
                f"</div>",
                unsafe_allow_html=True
            )

            with st.expander(f"Preview: {len(selected_apis)} selected API(s) — confirm before running", expanded=True):
                preview_df = pre_run_df[pre_run_df["API_NAME"].isin(selected_apis)]
                for _, prow in preview_df.iterrows():
                    _name = prow["API_NAME"]
                    _last = prow["LAST_RUN_TS"]
                    _fails = int(prow["FAILS_24H"] or 0)
                    _runs = int(prow["RUNS_24H"] or 0)
                    _inc = bool(prow["INCREMENTAL_FLAG"])
                    _wm = prow["LAST_SYNC_VALUE"]

                    if _last is None or pd.isna(_last):
                        status, badge_cls, badge_txt = "warning", "warn", "NEVER RUN"
                        ago_str = "—"
                    elif _fails > 0:
                        status, badge_cls, badge_txt = "warning", "warn", f"{_fails} FAIL/24H"
                        ago_str = pd.to_datetime(_last).strftime("%Y-%m-%d %H:%M")
                    else:
                        status, badge_cls, badge_txt = "healthy", "accent", "HEALTHY"
                        ago_str = pd.to_datetime(_last).strftime("%Y-%m-%d %H:%M")

                    badges = [{"text": badge_txt, "cls": badge_cls}]
                    if _inc:
                        wm_str = "" if (_wm is None or pd.isna(_wm)) else f" {_wm}"
                        badges.append({"text": f"INCR{wm_str}", "cls": "accent"})
                    else:
                        badges.append({"text": "FULL", "cls": ""})
                    meta_parts = [f"last run: {ago_str}", f"24h: {_runs} calls / {_fails} fail"]
                    cfg_card(_name, "", badges=badges, meta=" · ".join(meta_parts), status=status)
        else:
            st.caption("No APIs selected. Use the shortcuts above or pick from the multiselect.")

        st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)

        # ─────────────────────────────────────
        # PHASE 2 — CONFIGURE
        # ─────────────────────────────────────
        section_label("PHASE 2 · CONFIGURE")

        run_mode = st.radio(
            "Execution mode",
            ["Sequential", "Parallel", "Dry Run"],
            horizontal=True,
            key="ri_mode",
            label_visibility="collapsed",
        )

        # Mode descriptions
        modes_info = {
            "Sequential": ("⏯  One at a time, with live log. Best for **1-5 APIs** or debugging. "
                          "Keep the browser open."),
            "Parallel":   ("⚡ Fire all selected via persistent Snowflake tasks. Best for **production / 10+ APIs**. "
                          "Safe to close the browser."),
            "Dry Run":    ("🧪 Validate configs and network rules — no data movement. Best for **new APIs**."),
        }
        st.caption(modes_info[run_mode])

        # Per-mode controls
        run_warehouse = None
        if run_mode == "Parallel":
            try:
                wh_df = run_query("SHOW WAREHOUSES")
                wh_df.columns = [c.upper() for c in wh_df.columns]
                wh_options = wh_df["NAME"].tolist() if not wh_df.empty else [_wh]
            except Exception:
                wh_options = [_wh]
            run_warehouse = st.selectbox(
                "Warehouse for parallel tasks",
                wh_options,
                index=wh_options.index(st.session_state.get("pref_warehouse", _wh)) if st.session_state.get("pref_warehouse", _wh) in wh_options else 0,
                key="ri_wh",
            )
            st.caption("Tip: Tasks are persistent. They appear in the **Scheduler** tab so you can re-fire them.")

        st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)

        # ─────────────────────────────────────
        # PHASE 3 — EXECUTE / MONITOR
        # ─────────────────────────────────────
        section_label("PHASE 3 · EXECUTE")

        # Pre-flight summary so the user knows exactly what's about to run
        if selected_apis:
            preview_list = ", ".join(selected_apis[:8])
            if len(selected_apis) > 8:
                preview_list += f" + {len(selected_apis) - 8} more"
            st.markdown(
                f"<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); "
                f"border-left: 3px solid var(--accent-green); border-radius: 6px; "
                f"padding: 10px 14px; margin-bottom: 8px;'>"
                f"<div style='font-family: var(--font-mono); font-size: 0.66rem; "
                f"color: var(--text-muted); letter-spacing: 1px; text-transform: uppercase;'>"
                f"PRE-FLIGHT · {run_mode.upper()}</div>"
                f"<div style='color: var(--text-primary); font-size: 0.86rem; margin-top: 4px;'>"
                f"About to call <strong>{len(selected_apis)}</strong> API(s): "
                f"<span style='font-family: var(--font-mono); color: var(--accent-green);'>{preview_list}</span>"
                f"</div></div>",
                unsafe_allow_html=True
            )
        else:
            st.caption("⚠ No APIs selected. Pick at least one in Phase 1 above.")

        run_clicked = st.button(
            f"▶ Run {run_mode} ({len(selected_apis)} API)",
            type="primary",
            disabled=(not selected_apis),
            use_container_width=True,
            key="ri_run_btn",
        )

        if run_clicked:
            if not selected_apis:
                st.warning("Select at least one API.")
            elif run_mode == "Dry Run":
                # Validate-only — no data movement
                allowed_entries = get_allowed_hosts()
                results = []
                for api in selected_apis:
                    cfg_row = pre_run_df[pre_run_df["API_NAME"] == api].iloc[0]
                    try:
                        endpoint = run_query(
                            f"SELECT ENDPOINT_URL FROM {META}.INGESTION_CONFIGS WHERE API_NAME = ?",
                            params=[api]
                        )
                        url = endpoint["ENDPOINT_URL"].iloc[0] if not endpoint.empty else ""
                        ok, matched, reason = check_host_allowed(str(url), allowed_entries)
                        results.append({
                            "API_NAME": api,
                            "URL": url,
                            "NETWORK_OK": "✓" if ok else "✗",
                            "DETAIL": matched if ok else reason,
                        })
                    except Exception as e:
                        results.append({"API_NAME": api, "URL": "—", "NETWORK_OK": "✗", "DETAIL": str(e)})
                styled_dataframe(pd.DataFrame(results))
                ok_count = sum(1 for r in results if r["NETWORK_OK"] == "✓")
                st.toast(f"Dry run complete · {ok_count}/{len(results)} OK", icon="🧪")

            elif run_mode == "Sequential":
                # Reset stop flag
                st.session_state["ri_stop_requested"] = False
                stop_col, _ = st.columns([1, 5])
                with stop_col:
                    if st.button("⛔ Stop", key="ri_stop_btn", use_container_width=True):
                        st.session_state["ri_stop_requested"] = True

                progress = st.progress(0)
                log_window = st.empty()
                log_history = []

                def _log(msg):
                    log_history.append(msg)
                    log_window.code("\n".join(log_history[-200:]), language="bash")

                _log(f"$ ingest --apis {','.join(selected_apis)}")
                _log(f"# {len(selected_apis)} target(s) queued · sequential")
                _log("")

                for i, api in enumerate(selected_apis):
                    if st.session_state.get("ri_stop_requested"):
                        _log(f"⛔ Stop requested. Halted after {i} API(s).")
                        break
                    _log(f"> [{i+1}/{len(selected_apis)}] initializing {api} ...")
                    try:
                        result = run_query(f"CALL {META}.USP_UNIVERSAL_INGESTOR(?)", params=[api])
                        msg = result.iloc[0, 0]
                        if "Success" in str(msg):
                            _log(f"  ✓ {api}  →  {msg}")
                        else:
                            _log(f"  ✗ {api}  →  {msg}")
                    except Exception as e:
                        _log(f"  ✗ {api}  →  ERROR: {str(e)}")
                    progress.progress((i + 1) / len(selected_apis))

                _log("")
                _log("$ done.")

            elif run_mode == "Parallel":
                # Fire-and-forget via persistent tasks
                if not run_warehouse or not is_safe_name(run_warehouse):
                    st.error("Invalid warehouse.")
                else:
                    fired = []
                    skipped = []
                    with st.spinner(f"Firing {len(selected_apis)} parallel task(s)..."):
                        for api in selected_apis:
                            if not is_safe_name(api):
                                skipped.append((api, "unsafe name"))
                                continue
                            task_name = f"TASK_INGEST_{api}"
                            try:
                                # Check if a persistent task exists (avoid DDL when possible)
                                existing = run_query(
                                    f"SHOW TASKS LIKE '{task_name}' IN SCHEMA {META}"
                                )
                                if existing.empty:
                                    # Create as persistent (no SCHEDULE → manual execution only)
                                    escaped_api = escape_sql_literal(api)
                                    exec_sql(
                                        f"CREATE TASK IF NOT EXISTS {META}.{task_name} "
                                        f"WAREHOUSE = {run_warehouse} "
                                        f"AS CALL {META}.USP_UNIVERSAL_INGESTOR('{escaped_api}')"
                                    )
                                exec_sql(f"EXECUTE TASK {META}.{task_name}")
                                fired.append(task_name)
                            except Exception as e:
                                skipped.append((api, str(e)[:80]))

                    if fired:
                        st.session_state["ri_last_fired_tasks"] = fired
                        st.session_state["ri_last_fired_at"] = pd.Timestamp.utcnow().isoformat()
                        st.toast(f"🚀 Fired {len(fired)} parallel task(s) — safe to close browser.", icon="🚀")
                    if skipped:
                        for api, reason in skipped:
                            st.error(f"Skipped {api}: {reason}")

        # ─────────────────────────────────────
        # LIVE MONITORING (always visible if any tasks fired this session)
        # ─────────────────────────────────────
        if st.session_state.get("ri_last_fired_tasks"):
            st.markdown("<div style='height: 1.0rem;'></div>", unsafe_allow_html=True)
            section_label("LIVE MONITOR")
            mon_col1, mon_col2 = st.columns([1, 5])
            with mon_col1:
                refresh_clicked = st.button("🔄 Refresh", use_container_width=True, key="ri_mon_refresh")

            fired_tasks = st.session_state["ri_last_fired_tasks"]
            placeholders = ", ".join([f"'{t}'" for t in fired_tasks if is_safe_name(t)])
            try:
                mon_df = run_query(f"""
                    SELECT NAME, STATE, SCHEDULED_TIME, COMPLETED_TIME,
                           TIMESTAMPDIFF(SECOND, SCHEDULED_TIME, COMPLETED_TIME) AS DURATION_SEC,
                           ERROR_MESSAGE
                    FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
                        SCHEDULED_TIME_RANGE_START => DATEADD('MINUTE', -30, CURRENT_TIMESTAMP()),
                        RESULT_LIMIT => 200
                    ))
                    WHERE NAME IN ({placeholders})
                    ORDER BY SCHEDULED_TIME DESC
                """)
            except Exception as _e:
                mon_df = pd.DataFrame()
                st.caption(f"Task history unavailable: {_e}")

            if mon_df.empty:
                st.info("Tasks just fired — give Snowflake a few seconds, then click Refresh.")
            else:
                # Latest row per task
                latest = mon_df.groupby("NAME", as_index=False).first()
                succeeded = int((latest["STATE"] == "SUCCEEDED").sum())
                failed = int((latest["STATE"] == "FAILED").sum())
                running = int(latest["STATE"].isin(["RUNNING", "EXECUTING"]).sum())
                pending = len(fired_tasks) - len(latest)

                tm1, tm2, tm3, tm4 = st.columns(4)
                with tm1: dd_tile("PENDING", pending, "queued", "flat")
                with tm2: dd_tile("RUNNING", running, "live" if running else "—", "up" if running else "flat", live=running > 0)
                with tm3: dd_tile("SUCCEEDED", succeeded, "—", "up" if succeeded else "flat", glow="ok" if succeeded else None)
                with tm4: dd_tile("FAILED", failed, "—", "down" if failed else "flat", glow="err" if failed else None)

                st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)
                for _, mrow in latest.iterrows():
                    st_state = mrow["STATE"]
                    if st_state == "SUCCEEDED":
                        status_cls = "healthy"
                    elif st_state == "FAILED":
                        status_cls = "error"
                    elif st_state in ("RUNNING", "EXECUTING"):
                        status_cls = "warning"
                    else:
                        status_cls = "inactive"

                    dur = mrow.get("DURATION_SEC")
                    dur_str = f"{int(dur)}s" if dur is not None and not pd.isna(dur) else "—"
                    err_msg = mrow.get("ERROR_MESSAGE")
                    err_str = f" · {str(err_msg)[:80]}" if err_msg and not pd.isna(err_msg) else ""
                    sched_t = pd.to_datetime(mrow["SCHEDULED_TIME"]).strftime("%H:%M:%S") if mrow.get("SCHEDULED_TIME") is not None else "—"

                    cfg_card(
                        mrow["NAME"],
                        f"{st_state} · {dur_str} · scheduled {sched_t}{err_str}",
                        badges=[{"text": st_state, "cls": "accent" if st_state == "SUCCEEDED" else ("warn" if st_state in ("RUNNING", "EXECUTING") else "danger")}],
                        meta="",
                        status=status_cls,
                    )

                cl1, _ = st.columns([1, 5])
                with cl1:
                    if st.button("Clear monitor", key="ri_mon_clear", use_container_width=True):
                        st.session_state["ri_last_fired_tasks"] = []
                        st.rerun()

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
    section_label("AUTOMATION CONTROLS")
    st.header("Task Scheduler")
    st.caption("Monitor → manage → create. Bulk actions, schedule timeline, conflict detection.")

    # ─── Load tasks ───
    try:
        tasks_df = run_query(f"SHOW TASKS IN SCHEMA {META}")
        if not tasks_df.empty:
            tasks_df.columns = [c.upper() for c in tasks_df.columns]
            # Show only framework-owned tasks (created by this app)
            if "NAME" in tasks_df.columns:
                tasks_df = tasks_df[tasks_df["NAME"].astype(str).str.startswith("TASK_INGEST_")].reset_index(drop=True)
        task_names = tasks_df["NAME"].tolist() if not tasks_df.empty else []
    except Exception as _e:
        st.warning(f"Could not load tasks: {_e}")
        tasks_df = pd.DataFrame()
        task_names = []

    # Pre-load active API list and warehouse list (for create form)
    try:
        active_apis_df = run_query(
            f"SELECT API_NAME FROM {META}.INGESTION_CONFIGS WHERE ACTIVE_FLAG = TRUE ORDER BY API_NAME"
        )
        api_options = active_apis_df["API_NAME"].tolist() if not active_apis_df.empty else []
    except Exception:
        api_options = []
    try:
        wh_q = run_query("SHOW WAREHOUSES")
        wh_q.columns = [c.upper() for c in wh_q.columns]
        wh_options = wh_q["NAME"].tolist() if not wh_q.empty else [_wh]
    except Exception:
        wh_options = [_wh]

    # ╔══════════════════ ZONE 1 · COMMAND BAR ══════════════════╗
    cmd_left, cmd_right = st.columns([4, 1])
    with cmd_left:
        if task_names:
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if st.button("▶ Resume All", use_container_width=True, key="bulk_resume"):
                    cnt = 0
                    for tn in task_names:
                        try:
                            exec_sql(f"ALTER TASK {META}.{tn} RESUME")
                            cnt += 1
                        except Exception:
                            pass
                    st.toast(f"Resumed {cnt}/{len(task_names)} tasks", icon="▶")
                    time.sleep(0.4); st.rerun()
            with bc2:
                if st.button("⏸ Suspend All", use_container_width=True, key="bulk_suspend"):
                    cnt = 0
                    for tn in task_names:
                        try:
                            exec_sql(f"ALTER TASK {META}.{tn} SUSPEND")
                            cnt += 1
                        except Exception:
                            pass
                    st.toast(f"Suspended {cnt}/{len(task_names)} tasks", icon="⏸")
                    time.sleep(0.4); st.rerun()
            with bc3:
                if st.button("🚀 Execute All Now", use_container_width=True, key="bulk_execute"):
                    cnt = 0
                    for tn in task_names:
                        try:
                            exec_sql(f"EXECUTE TASK {META}.{tn}")
                            cnt += 1
                        except Exception:
                            pass
                    st.toast(f"Fired {cnt}/{len(task_names)} tasks", icon="🚀")
        else:
            st.caption("No tasks yet — click **＋ New Schedule** to create your first one.")
    with cmd_right:
        st.write("")
        if st.button("＋ New Schedule", type="primary", use_container_width=True, key="open_create_dialog"):
            st.session_state["create_task_open"] = not st.session_state.get("create_task_open", False)

    # ╔════════════════════ ZONE 2 · KPI TILES ════════════════════╗
    if not tasks_df.empty:
        total_tasks = len(tasks_df)
        running = int((tasks_df["STATE"] == "started").sum()) if "STATE" in tasks_df.columns else 0
        suspended = int((tasks_df["STATE"] == "suspended").sum()) if "STATE" in tasks_df.columns else 0
        wh_used = tasks_df["WAREHOUSE"].nunique() if "WAREHOUSE" in tasks_df.columns else 0

        # 7-day history rollup
        try:
            placeholders = ",".join([f"'{escape_sql_literal(t)}'" for t in task_names]) if task_names else "'__NONE__'"
            hist_kpi = run_query(f"""
                SELECT COUNT(*) AS TOTAL_RUNS,
                       SUM(CASE WHEN STATE='SUCCEEDED' THEN 1 ELSE 0 END) AS SUCCEEDED,
                       SUM(CASE WHEN STATE='FAILED' THEN 1 ELSE 0 END) AS FAILED,
                       ROUND(AVG(TIMESTAMPDIFF(SECOND, SCHEDULED_TIME, COMPLETED_TIME)), 1) AS AVG_DUR
                FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
                    SCHEDULED_TIME_RANGE_START => DATEADD('DAY', -7, CURRENT_TIMESTAMP()),
                    RESULT_LIMIT => 1000
                ))
                WHERE NAME IN ({placeholders})
            """)
            total_runs = int(hist_kpi["TOTAL_RUNS"].iloc[0] or 0)
            succeeded = int(hist_kpi["SUCCEEDED"].iloc[0] or 0)
            failed = int(hist_kpi["FAILED"].iloc[0] or 0)
            _avg_dur_raw = hist_kpi["AVG_DUR"].iloc[0]
            avg_dur = 0.0 if _avg_dur_raw is None or pd.isna(_avg_dur_raw) else float(_avg_dur_raw)
            hist_sr = round(succeeded / max(total_runs, 1) * 100, 1)
        except Exception:
            total_runs = succeeded = failed = 0
            avg_dur = 0.0
            hist_sr = 0.0

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        hero_col, k1, k2 = st.columns([2, 1, 1])
        with hero_col:
            sr_glow = "ok" if hist_sr >= 99 else ("warn" if hist_sr >= 90 else "err")
            dd_tile(
                "7-DAY SUCCESS RATE", f"{hist_sr:.1f}%",
                f"{succeeded:,} ok · {failed:,} failed · {total_runs:,} runs",
                "up" if hist_sr >= 99 else "down",
                live=running > 0, size="hero", glow=sr_glow,
            )
        with k1:
            dd_tile("RUNNING NOW", running, "executing" if running else "idle",
                    "up" if running else "flat", live=running > 0,
                    glow="ok" if running else None)
        with k2:
            dd_tile("SUSPENDED", suspended, "paused" if suspended else "none",
                    "down" if suspended else "flat",
                    glow="warn" if suspended else None)

        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        k3, k4, k5 = st.columns(3)
        with k3:
            dd_tile("TOTAL TASKS", total_tasks, f"across {wh_used} warehouse(s)", "flat")
        with k4:
            dur_disp = f"{avg_dur:.0f}s" if avg_dur < 60 else f"{avg_dur/60:.1f}m"
            dd_tile("AVG DURATION", dur_disp, "last 7 days", "flat")
        with k5:
            dd_tile("FAILED RUNS (7D)", failed,
                    "needs attention" if failed else "clean",
                    "down" if failed else "flat",
                    glow="err" if failed > 0 else None)

        # ╔══════════════════ ZONE 3 · TIMELINE ══════════════════╗
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_label("SCHEDULE TIMELINE · NEXT 24 HOURS")
        timeline_events = _parse_next_runs(tasks_df, horizon_hours=24)

        if timeline_events and _PLOTLY_OK:
            wh_colors = {}
            palette = ["#29B5E8", "#f59e0b", "#c084fc", "#3fb950", "#ef4444", "#a78bfa"]
            for i, wh in enumerate(tasks_df["WAREHOUSE"].dropna().unique() if "WAREHOUSE" in tasks_df.columns else []):
                wh_colors[wh] = palette[i % len(palette)]

            fig_tl = go.Figure()
            seen_wh = set()
            for ev in timeline_events:
                color = wh_colors.get(ev["warehouse"], "#29B5E8")
                fig_tl.add_trace(go.Scatter(
                    x=[ev["time"]], y=[ev["task"]],
                    mode="markers",
                    marker=dict(symbol="line-ns", size=18, color=color, line=dict(color=color, width=3)),
                    name=ev["warehouse"],
                    legendgroup=ev["warehouse"],
                    showlegend=(ev["warehouse"] not in seen_wh),
                    hovertemplate=(
                        f"<b>{ev['task']}</b><br>"
                        f"🏢 {ev['warehouse']}<br>"
                        f"⏱ {ev['time'].strftime('%Y-%m-%d %H:%M UTC')}<br>"
                        f"In {ev['hour_offset']:.1f}h<extra></extra>"
                    ),
                ))
                seen_wh.add(ev["warehouse"])

            # Conflict detection
            conflicts = []
            for i, e1 in enumerate(timeline_events):
                for e2 in timeline_events[i+1:]:
                    if e1["warehouse"] == e2["warehouse"]:
                        delta = abs((e1["time"] - e2["time"]).total_seconds())
                        if delta < 120:
                            conflicts.append((e1, e2))
            for c1, c2 in conflicts:
                mid_t = c1["time"] + (c2["time"] - c1["time"]) / 2
                fig_tl.add_vline(
                    x=mid_t, line=dict(color="#ef4444", width=1, dash="dot"),
                    annotation_text="⚠ contention",
                    annotation_font=dict(color="#ef4444", size=9),
                )

            fig_tl.add_vline(
                x=datetime.utcnow(), line=dict(color="#29B5E8", width=1.5, dash="dash"),
                annotation_text="NOW",
                annotation_font=dict(color="#29B5E8", size=9, family="JetBrains Mono"),
            )

            fig_tl.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d0d0d",
                font=dict(color="#a1a1aa", family="JetBrains Mono", size=10),
                legend=dict(title="Warehouse", bgcolor="rgba(17,17,17,0.9)",
                            bordercolor="#1f1f1f", borderwidth=1, font=dict(size=9)),
                xaxis=dict(showgrid=True, gridcolor="#1f1f1f",
                           tickformat="%H:%M", title="UTC time (next 24h)",
                           title_font=dict(size=10)),
                yaxis=dict(showgrid=False, tickfont=dict(size=9)),
                margin=dict(l=10, r=10, t=10, b=30),
                height=max(160, len(set(e["task"] for e in timeline_events)) * 40 + 60),
            )
            st.plotly_chart(fig_tl, use_container_width=True)

            if conflicts:
                st.warning(
                    f"⚠ **{len(conflicts)} schedule conflict(s) detected** — "
                    "tasks on the same warehouse scheduled within 2 minutes will queue and "
                    "delay each other. Consider staggering."
                )
        elif not timeline_events:
            st.caption("No running tasks with parseable schedules — resume tasks or create one to see the timeline.")
        else:
            st.caption("Plotly not available — timeline skipped.")

        # ╔══════════════════ ZONE 4 · TASK CARDS ══════════════════╗
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_label("SCHEDULED TASKS")

        # Filter row
        f1, f2, f3 = st.columns([2, 2, 2])
        with f1:
            state_filter = st.multiselect(
                "State", ["started", "suspended"],
                label_visibility="collapsed", placeholder="All states",
                key="task_state_filter",
            )
        with f2:
            wh_choices = tasks_df["WAREHOUSE"].dropna().unique().tolist() if "WAREHOUSE" in tasks_df.columns else []
            wh_filter_task = st.multiselect(
                "Warehouse", wh_choices,
                label_visibility="collapsed", placeholder="All warehouses",
                key="task_wh_filter",
            )
        with f3:
            task_search = st.text_input(
                "Search", placeholder="Filter by task name…",
                label_visibility="collapsed", key="task_search",
            )

        filtered_tasks = tasks_df.copy()
        if state_filter:
            filtered_tasks = filtered_tasks[filtered_tasks["STATE"].isin(state_filter)]
        if wh_filter_task:
            filtered_tasks = filtered_tasks[filtered_tasks["WAREHOUSE"].isin(wh_filter_task)]
        if task_search:
            filtered_tasks = filtered_tasks[
                filtered_tasks["NAME"].str.lower().str.contains(task_search.lower(), na=False)
            ]
        st.caption(f"Showing **{len(filtered_tasks)}** of **{total_tasks}** task(s)")

        # Last-run lookup
        last_runs = {}
        failed_set = set()
        if task_names:
            try:
                placeholders = ",".join([f"'{escape_sql_literal(n)}'" for n in task_names])
                recent_hist = run_query(f"""
                    SELECT NAME, STATE, SCHEDULED_TIME, ERROR_MESSAGE,
                           TIMESTAMPDIFF(SECOND, SCHEDULED_TIME, COMPLETED_TIME) AS DURATION_SEC
                    FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
                        SCHEDULED_TIME_RANGE_START => DATEADD('DAY', -1, CURRENT_TIMESTAMP()),
                        RESULT_LIMIT => 500
                    ))
                    WHERE NAME IN ({placeholders})
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY NAME ORDER BY SCHEDULED_TIME DESC) = 1
                """)
                for _, hr in recent_hist.iterrows():
                    last_runs[hr["NAME"]] = hr.to_dict()
                    if hr["STATE"] == "FAILED":
                        failed_set.add(hr["NAME"])
            except Exception:
                pass

        # Render cards
        for _, t in filtered_tasks.iterrows():
            t_name = t.get("NAME", "—")
            t_state = (t.get("STATE") or "").lower()
            t_sched = str(t.get("SCHEDULE") or "—")
            t_wh = str(t.get("WAREHOUSE") or "—")
            last_r = last_runs.get(t_name, {})

            is_running = t_state == "started"
            is_failed = t_name in failed_set
            if is_failed:
                card_status = "error"
            elif is_running:
                card_status = "healthy"
            else:
                card_status = "inactive"

            sched_human = _humanize_schedule(t_sched)
            last_run_ts = str(last_r.get("SCHEDULED_TIME") or "")[:16]
            last_run_st = str(last_r.get("STATE") or "")
            last_run_dur = last_r.get("DURATION_SEC")
            dur_str = (
                f"{int(last_run_dur)}s" if last_run_dur and last_run_dur < 60
                else f"{last_run_dur/60:.1f}m" if last_run_dur else "—"
            )

            badges = [
                {"text": "RUNNING" if is_running else "SUSPENDED", "cls": "accent" if is_running else ""},
                {"text": f"🏢 {t_wh}", "cls": ""},
            ]
            if is_failed:
                badges.append({"text": "LAST RUN FAILED", "cls": "danger"})

            cfg_card(
                name=t_name, endpoint=sched_human, badges=badges,
                meta=f"last run: {last_run_ts or 'never'} · {last_run_st or '—'} · duration: {dur_str}",
                status=card_status,
            )

            if is_failed and last_r.get("ERROR_MESSAGE"):
                st.markdown(f"""
                <div style='background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);
                            border-radius:6px;padding:8px 12px;margin:-6px 0 8px;
                            font-family:var(--font-mono);font-size:0.7rem;color:#ef4444;'>
                  ✗ {str(last_r["ERROR_MESSAGE"])[:200]}
                </div>
                """, unsafe_allow_html=True)

            # Inline actions
            ac1, ac2, ac3, ac4, ac5 = st.columns([1, 1, 1, 1, 2])
            with ac1:
                if is_running:
                    if st.button("⏸ Suspend", key=f"card_suspend_{t_name}", use_container_width=True):
                        try:
                            exec_sql(f"ALTER TASK {META}.{t_name} SUSPEND")
                            st.toast(f"Suspended {t_name}", icon="⏸")
                            time.sleep(0.4); st.rerun()
                        except Exception as e:
                            st.error(str(e))
                else:
                    if st.button("▶ Resume", key=f"card_resume_{t_name}", use_container_width=True, type="primary"):
                        try:
                            exec_sql(f"ALTER TASK {META}.{t_name} RESUME")
                            st.toast(f"Resumed {t_name}", icon="▶")
                            time.sleep(0.4); st.rerun()
                        except Exception as e:
                            st.error(str(e))
            with ac2:
                if st.button("🚀 Run Now", key=f"card_run_{t_name}", use_container_width=True):
                    try:
                        exec_sql(f"EXECUTE TASK {META}.{t_name}")
                        st.toast(f"Task {t_name} fired", icon="🚀")
                    except Exception as e:
                        st.error(str(e))
            with ac3:
                with st.popover("🗑 Drop", use_container_width=True):
                    st.warning(f"Drop **{t_name}**? This removes the schedule permanently.")
                    confirm_drop = st.text_input(
                        f'Type "{t_name}" to confirm',
                        key=f"drop_confirm_{t_name}",
                        placeholder=t_name,
                    )
                    if st.button(
                        "Confirm Drop",
                        key=f"drop_confirm_btn_{t_name}",
                        disabled=(confirm_drop != t_name),
                        type="primary",
                    ):
                        try:
                            exec_sql(f"DROP TASK IF EXISTS {META}.{t_name}")
                            st.toast(f"Dropped {t_name}", icon="🗑")
                            time.sleep(0.4); st.rerun()
                        except Exception as e:
                            st.error(str(e))
            with ac4:
                if st.button("⏱ Reschedule", key=f"card_reschedule_{t_name}", use_container_width=True):
                    st.session_state[f"reschedule_open_{t_name}"] = not st.session_state.get(f"reschedule_open_{t_name}", False)
            with ac5:
                st.caption("")  # spacer

            if st.session_state.get(f"reschedule_open_{t_name}"):
                with st.container(border=True):
                    section_label(f"RESCHEDULE · {t_name}")
                    rs_c1, rs_c2 = st.columns(2)
                    with rs_c1:
                        rs_type = st.selectbox(
                            "Schedule Type",
                            ["INTERVAL (Minutes)", "CRON"],
                            key=f"rs_type_{t_name}",
                        )
                    with rs_c2:
                        if rs_type == "INTERVAL (Minutes)":
                            rs_mins = st.number_input(
                                "Every N minutes", min_value=1, value=60,
                                key=f"rs_mins_{t_name}",
                            )
                            new_sched = f"{rs_mins} MINUTE"
                        else:
                            rs_cron = st.text_input("CRON", value="0 2 * * *", key=f"rs_cron_{t_name}")
                            rs_tz = st.text_input("Timezone", value="UTC", key=f"rs_tz_{t_name}")
                            new_sched = f"USING CRON {rs_cron} {rs_tz}"
                            if rs_cron:
                                st.caption(_humanize_cron(rs_cron))

                    rs_apply, rs_cancel = st.columns(2)
                    with rs_apply:
                        if st.button("Apply New Schedule", type="primary",
                                     use_container_width=True, key=f"rs_apply_{t_name}"):
                            try:
                                exec_sql(f"ALTER TASK {META}.{t_name} SUSPEND")
                                exec_sql(f"ALTER TASK {META}.{t_name} SET SCHEDULE = '{new_sched}'")
                                exec_sql(f"ALTER TASK {META}.{t_name} RESUME")
                                st.toast(f"Rescheduled {t_name}", icon="⏱")
                                st.session_state[f"reschedule_open_{t_name}"] = False
                                time.sleep(0.4); st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    with rs_cancel:
                        if st.button("Cancel", use_container_width=True, key=f"rs_cancel_{t_name}"):
                            st.session_state[f"reschedule_open_{t_name}"] = False
                            st.rerun()

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # ╔══════════════════ ZONE 5 · EXECUTION HISTORY ══════════════════╗
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_label("EXECUTION HISTORY")

        hc1, hc2, hc3 = st.columns([2, 2, 1])
        with hc1:
            hist_window = st.select_slider(
                "History window",
                options=["6h", "24h", "3d", "7d"],
                value="24h", label_visibility="collapsed",
                key="hist_window",
            )
        with hc2:
            hist_task_f = st.multiselect(
                "Tasks", task_names,
                label_visibility="collapsed", placeholder="All tasks",
                key="hist_task_f",
            )
        with hc3:
            hist_limit = st.select_slider(
                "Limit",
                options=[50, 100, 250, 500],
                value=100, label_visibility="collapsed",
                key="hist_limit_v2",
            )

        HIST_WIN = {"6h": ("HOUR", 6), "24h": ("HOUR", 24), "3d": ("DAY", 3), "7d": ("DAY", 7)}[hist_window]
        # Always restrict history to framework-owned tasks (TASK_INGEST_*)
        where_clauses = ["NAME LIKE 'TASK_INGEST_%'"]
        if hist_task_f:
            task_quoted = ",".join("'" + escape_sql_literal(t) + "'" for t in hist_task_f)
            where_clauses.append(f"NAME IN ({task_quoted})")
        task_filter_sql = "WHERE " + " AND ".join(where_clauses)

        try:
            full_hist = run_query(f"""
                SELECT NAME, STATE, SCHEDULED_TIME, COMPLETED_TIME,
                       TIMESTAMPDIFF(SECOND, SCHEDULED_TIME, COMPLETED_TIME) AS DURATION_SEC,
                       ERROR_CODE, ERROR_MESSAGE, QUERY_ID
                FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
                    SCHEDULED_TIME_RANGE_START => DATEADD('{HIST_WIN[0]}', -{HIST_WIN[1]}, CURRENT_TIMESTAMP()),
                    RESULT_LIMIT => {hist_limit}
                ))
                {task_filter_sql}
                ORDER BY SCHEDULED_TIME DESC
            """)
        except Exception as _e:
            full_hist = pd.DataFrame()
            st.caption(f"History unavailable: {_e}")

        ht_timeline, ht_table, ht_failures = st.tabs(["📈 Run Timeline", "📋 Run Log", "🚨 Failures"])

        with ht_timeline:
            if not full_hist.empty and _PLOTLY_OK:
                full_hist["SCHEDULED_TIME"] = pd.to_datetime(full_hist["SCHEDULED_TIME"])
                color_map = {"SUCCEEDED": "#29B5E8", "FAILED": "#ef4444",
                             "RUNNING": "#f59e0b", "SCHEDULED": "#52525b"}
                symbol_map = {"SUCCEEDED": "circle", "FAILED": "x",
                              "RUNNING": "circle-open", "SCHEDULED": "circle-dot"}
                full_hist["DUR_LABEL"] = full_hist["DURATION_SEC"].apply(
                    lambda x: f"{int(x)}s" if x is not None and not pd.isna(x) and x < 60
                    else (f"{x/60:.1f}m" if x is not None and not pd.isna(x) else "—")
                )
                fig_h = go.Figure()
                for state, grp in full_hist.groupby("STATE"):
                    fig_h.add_trace(go.Scatter(
                        x=grp["SCHEDULED_TIME"], y=grp["NAME"], mode="markers",
                        name=str(state),
                        marker=dict(size=12,
                                    color=color_map.get(state, "#52525b"),
                                    symbol=symbol_map.get(state, "circle"),
                                    line=dict(color=color_map.get(state, "#52525b"), width=2)),
                        hovertemplate=("<b>%{y}</b><br>%{x}<br>"
                                       f"State: {state}<br>"
                                       "Duration: %{customdata}<extra></extra>"),
                        customdata=grp["DUR_LABEL"],
                    ))
                fig_h.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0d0d0d",
                    font=dict(color="#a1a1aa", family="JetBrains Mono", size=10),
                    legend=dict(bgcolor="rgba(17,17,17,0.9)", bordercolor="#1f1f1f", borderwidth=1),
                    xaxis=dict(showgrid=True, gridcolor="#1f1f1f", tickformat="%m/%d %H:%M"),
                    yaxis=dict(showgrid=False),
                    margin=dict(l=10, r=10, t=10, b=30),
                    height=max(180, max(1, full_hist["NAME"].nunique()) * 38 + 80),
                )
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("No history in this window.")

        with ht_table:
            if not full_hist.empty:
                styled_dataframe(full_hist.drop(columns=["DUR_LABEL"], errors="ignore"))
            else:
                st.info("No run history.")

        with ht_failures:
            failures = full_hist[full_hist["STATE"] == "FAILED"] if not full_hist.empty else pd.DataFrame()
            if failures.empty:
                empty_state("✅", "No failures", f"All tasks succeeded in the last {hist_window}.")
            else:
                for _, f in failures.iterrows():
                    err_msg = str(f.get("ERROR_MESSAGE") or "Unknown error")
                    ts = str(f.get("SCHEDULED_TIME") or "")[:16]
                    dur = f.get("DURATION_SEC")
                    dur_s = f"{int(dur)}s" if dur is not None and not pd.isna(dur) else "—"
                    st.markdown(f"""
                    <div class='cfg-card error'>
                      <div class='name' style='font-size:0.88rem;'>{f['NAME']}</div>
                      <div class='endpoint'>{ts} · ran for {dur_s}</div>
                      <div style='margin-top:8px;padding:8px 10px;background:rgba(239,68,68,0.06);
                                  border-radius:4px;font-family:var(--font-mono);font-size:0.7rem;color:#ef4444;'>
                        {err_msg[:300]}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    fix_col, qid_col = st.columns([1, 2])
                    with fix_col:
                        api_from_task = str(f["NAME"]).replace("TASK_INGEST_", "")
                        if st.button(f"⚙ Fix {api_from_task}",
                                     key=f"fix_{f['NAME']}_{ts}", use_container_width=True):
                            st.session_state["active_nav"] = "Manage API Configs"
                            st.session_state["manage_api"] = api_from_task
                            st.rerun()
                    with qid_col:
                        qid = f.get("QUERY_ID")
                        if qid:
                            st.caption(f"Query ID: `{qid}`")
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ╔══════════════════ ZONE 6 · NEW SCHEDULE ══════════════════╗
    if st.session_state.get("create_task_open"):
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            section_label("＋ CREATE NEW SCHEDULE")
            nc1, nc2 = st.columns(2)
            with nc1:
                st.markdown("#### 🎯 Target")
                target_api_v2 = st.selectbox("API to schedule", api_options, key="sch_api_v2")

                # Auto-sync task name to API selection
                suggested = f"TASK_INGEST_{target_api_v2}" if target_api_v2 else "TASK_INGEST_"
                if "last_target_api_v2" not in st.session_state:
                    st.session_state["last_target_api_v2"] = target_api_v2
                    st.session_state["sch_name_v2"] = suggested
                if target_api_v2 != st.session_state["last_target_api_v2"]:
                    st.session_state["last_target_api_v2"] = target_api_v2
                    st.session_state["sch_name_v2"] = suggested
                    st.rerun()

                task_name_new = st.text_input("Task name", key="sch_name_v2")
                if task_name_new in task_names:
                    st.warning(f"A task `{task_name_new}` already exists. Creating will replace it.")
                pref_wh_v2 = st.session_state.get("pref_warehouse", _wh)
                task_wh_new = st.selectbox(
                    "Warehouse",
                    wh_options,
                    index=wh_options.index(pref_wh_v2) if pref_wh_v2 in wh_options else 0,
                    key="sch_wh_v2",
                )
                if not tasks_df.empty and "WAREHOUSE" in tasks_df.columns:
                    tasks_on_wh = tasks_df[tasks_df["WAREHOUSE"] == task_wh_new]["NAME"].tolist()
                    if tasks_on_wh:
                        st.caption(f"ℹ {len(tasks_on_wh)} existing task(s) use this warehouse — stagger schedules to avoid contention.")
            with nc2:
                st.markdown("#### ⏱ Schedule")
                sched_type_v2 = st.radio("Type", ["Interval", "CRON"], horizontal=True, key="sch_type_v2")
                schedule_clause_v2 = ""
                if sched_type_v2 == "Interval":
                    cqty, cunit = st.columns(2)
                    with cqty:
                        sched_qty = st.number_input("Every", min_value=1, value=60, key="sch_qty")
                    with cunit:
                        sched_unit = st.selectbox("Unit", ["MINUTE", "HOUR"], key="sch_unit")
                    schedule_clause_v2 = f"{sched_qty} {sched_unit}"
                    st.caption(_humanize_schedule(schedule_clause_v2))
                else:
                    cron_presets = {
                        "Custom": "",
                        "Every hour": "0 * * * *",
                        "Every 6 hours": "0 */6 * * *",
                        "Daily at 2am": "0 2 * * *",
                        "Daily at midnight": "0 0 * * *",
                        "Weekdays at 6am": "0 6 * * 1-5",
                    }
                    preset = st.selectbox("Preset", list(cron_presets.keys()), key="cron_preset")

                    # Sync the text input when preset changes
                    if "last_cron_preset" not in st.session_state:
                        st.session_state["last_cron_preset"] = "Custom"
                    if preset != st.session_state["last_cron_preset"]:
                        st.session_state["last_cron_preset"] = preset
                        if cron_presets[preset]:
                            st.session_state["sch_cron_v2"] = cron_presets[preset]
                            st.rerun()

                    cron_val = st.text_input(
                        "CRON expression",
                        key="sch_cron_v2",
                        placeholder="min hr dom mon dow",
                    )
                    tz_val = st.text_input("Timezone", value="UTC", key="sch_tz_v2")
                    if cron_val:
                        st.caption(_humanize_cron(cron_val))
                        if len(cron_val.split()) != 5:
                            st.error("CRON must have exactly 5 fields: min hr dom mon dow")
                    schedule_clause_v2 = f"USING CRON {cron_val} {tz_val}" if cron_val else ""

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                create_suspended_v2 = st.checkbox(
                    "Create as SUSPENDED (resume manually)", value=True, key="sch_susp_v2"
                )
                auto_suspend_v2 = st.number_input(
                    "Auto-suspend after N consecutive failures (0 = never)",
                    min_value=0, value=3, key="sch_auto_susp",
                )

            ac_create, ac_cancel, _ = st.columns([1, 1, 2])
            with ac_create:
                if st.button(
                    "Create Schedule", type="primary",
                    use_container_width=True, key="btn_create_task_v2",
                    disabled=not (target_api_v2 and task_name_new and schedule_clause_v2),
                ):
                    try:
                        susp_clause = (
                            f"SUSPEND_TASK_AFTER_NUM_FAILURES = {auto_suspend_v2}"
                            if auto_suspend_v2 > 0 else ""
                        )
                        exec_sql(
                            f"CREATE OR REPLACE TASK {META}.{task_name_new} "
                            f"WAREHOUSE = {task_wh_new} "
                            f"SCHEDULE = '{schedule_clause_v2}' "
                            f"{susp_clause} "
                            f"AS CALL {META}.USP_UNIVERSAL_INGESTOR('{escape_sql_literal(target_api_v2)}')"
                        )
                        if not create_suspended_v2:
                            exec_sql(f"ALTER TASK {META}.{task_name_new} RESUME")
                        st.toast(
                            f"Task '{task_name_new}' created"
                            f"{' and running' if not create_suspended_v2 else ' (suspended)'}",
                            icon="⏱",
                        )
                        st.session_state["create_task_open"] = False
                        time.sleep(0.4); st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with ac_cancel:
                if st.button("Cancel", use_container_width=True, key="btn_cancel_task_v2"):
                    st.session_state["create_task_open"] = False
                    st.rerun()

# ─────────────────────────────────────────────
# HELP: Pipeline Overview
# ─────────────────────────────────────────────
elif nav_choice == "Pipeline Overview":
    section_label("HELP")
    st.header("Pipeline Overview")
    st.caption("End-to-end data flow — every component you manage in this app.")

    with st.container(border=True):
        st.graphviz_chart(r"""
        digraph G {
          rankdir=LR;
          bgcolor="transparent";
          node  [style="filled,rounded", shape=box, fontname="Inter", fontsize=10,
                 color="#1f1f1f", fillcolor="#111111", fontcolor="#fafafa", margin="0.18,0.10"];
          edge  [color="#3a3a3a", fontcolor="#a1a1aa", fontname="JetBrains Mono", fontsize=9, penwidth=1.2];

          cfg     [label="INGESTION_CONFIGS\n(metadata)",  fillcolor="#0f1f17", color="#00DC82", fontcolor="#00DC82"];
          eai     [label="EAI + Secrets\n(network + auth)", fillcolor="#1a1408", color="#f59e0b", fontcolor="#f59e0b"];
          proc    [label="USP_UNIVERSAL_INGESTOR\n(retry · paginate · watermark)", fillcolor="#0f0f1f", color="#58a6ff", fontcolor="#58a6ff"];
          api     [label="External REST API",  fillcolor="#0a0a0a", color="#a1a1aa"];
          raw     [label="RAW_LANDING.<TABLE>\n(JSON payloads)", fillcolor="#0f1f17", color="#00DC82", fontcolor="#00DC82"];
          log     [label="INGESTION_RESPONSE_LOG\n(per-attempt audit)", fillcolor="#0f1f17", color="#00DC82", fontcolor="#00DC82"];
          view    [label="V_<API> (flattened)\nData Explorer", fillcolor="#1c0a1a", color="#c084fc", fontcolor="#c084fc"];

          cfg  -> proc [label="reads"];
          eai  -> proc [label="grants"];
          proc -> api  [label="HTTP"];
          api  -> proc [label="JSON", style="dashed"];
          proc -> raw  [label="dedup + write"];
          proc -> log  [label="audit"];
          proc -> cfg  [label="watermark", style="dashed", color="#58a6ff"];
          raw  -> view [label="LATERAL FLATTEN"];
        }
        """)

    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    section_label("LEGEND")
    leg_c1, leg_c2, leg_c3, leg_c4 = st.columns(4)
    with leg_c1:
        st.markdown("<div class='cfg-card healthy'><div class='name' style='font-size:0.85rem;'>Framework Data</div><div class='meta'>configs · log · raw · views</div></div>", unsafe_allow_html=True)
    with leg_c2:
        st.markdown("<div class='cfg-card warning'><div class='name' style='font-size:0.85rem;'>Security</div><div class='meta'>EAI · secrets · network rules</div></div>", unsafe_allow_html=True)
    with leg_c3:
        st.markdown("<div class='cfg-card' style='border-left-color:#58a6ff;'><div class='name' style='font-size:0.85rem;'>Engine</div><div class='meta'>USP_UNIVERSAL_INGESTOR</div></div>", unsafe_allow_html=True)
    with leg_c4:
        st.markdown("<div class='cfg-card' style='border-left-color:#c084fc;'><div class='name' style='font-size:0.85rem;'>Generated</div><div class='meta'>flattened views</div></div>", unsafe_allow_html=True)
