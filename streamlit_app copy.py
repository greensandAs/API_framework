import streamlit as st
import pandas as pd
import re
import time
import json
from datetime import datetime

st.set_page_config(page_title="API Data Extract", layout="wide")

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
        --border-active: rgba(0,220,130,0.3);
        --text-primary: #fafafa;
        --text-secondary: #a1a1aa;
        --text-muted: #52525b;
        --accent-green: #00DC82;
        --accent-green-glow: rgba(0,220,130,0.08);
        --accent-red: #ef4444;
        --accent-blue: #58a6ff;
        --accent-amber: #f59e0b;
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
        background: linear-gradient(180deg, #111111 0%, #0d0d0d 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.18s cubic-bezier(.22,1,.36,1);
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .dd-tile:hover {
        border-color: var(--border-strong);
        transform: translateY(-1px);
        box-shadow: 0 8px 24px rgba(0,220,130,0.04);
    }
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
        0%   { box-shadow: 0 0 0 0 rgba(0,220,130,0.7); }
        70%  { box-shadow: 0 0 0 8px rgba(0,220,130,0); }
        100% { box-shadow: 0 0 0 0 rgba(0,220,130,0); }
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

def make_sparkline_svg(values, color="#00DC82", width=200, height=28):
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

def dd_tile(label, value, delta=None, delta_dir="flat", live=False, spark_data=None, spark_color=None):
    """Datadog/Vercel-style metric tile with optional inline sparkline."""
    live_cls = " live" if live else ""
    pulse = "<span class='pulse'></span>" if live else ""
    delta_html = ""
    if delta:
        arrow = {"up": "↑", "down": "↓", "flat": "→"}.get(delta_dir, "→")
        delta_html = f"<div class='delta {delta_dir}'>{arrow} {delta}</div>"
    spark_html = ""
    if spark_data is not None:
        color_default = {"up": "#00DC82", "down": "#ef4444", "flat": "#a1a1aa"}.get(delta_dir, "#00DC82")
        color = spark_color or color_default
        svg = make_sparkline_svg(list(spark_data), color=color)
        if svg:
            spark_html = f"<div class='spark'>{svg}</div>"
    st.markdown(f"""
    <div class='dd-tile{live_cls}'>
      <div class='label'>{pulse}{label}</div>
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

st.markdown(f"""
<div class='topbar'>
  <div class='topbar-brand'>
    <span class='topbar-icon'>⚡</span>
    <div>
      <span class='topbar-title'>API Pipeline</span>
      <span class='topbar-sub'>Snowflake API Ingestion Framework</span>
    </div>
  </div>
  <div class='topbar-meta'>
    <span class='pill'>👤 {_user}</span>
    <span class='pill'>🛡 {_role}</span>
    <span class='pill accent'>🏢 {_wh}</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Manage API Configs",
    "Manage Secrets & EAI",
    "Run Ingestion",
    "Ingestion Console",
    "Data Explorer",
    "Task Scheduler"
])

# ─────────────────────────────────────────────
# TAB 1: Manage API Configs
# ─────────────────────────────────────────────
with tab1:
    section_label("CONFIGURATION REGISTRY")
    st.header("API Configurations")
    st.caption("Central registry for all managed API endpoints and their ingestion parameters.")

    configs = run_query(f"SELECT * FROM {META}.INGESTION_CONFIGS ORDER BY API_NAME")

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

        m1, m2, m3, m4 = st.columns(4)
        with m1: dd_tile("REGISTERED APIs", len(configs), live=True)
        with m2: dd_tile("ACTIVE", active_count, f"{inactive_count} inactive", "flat")
        with m3: dd_tile("INCREMENTAL", incremental_count, f"of {len(configs)}", "flat")
        with m4:
            delta_dir = "down" if gap_count > 0 else "up"
            dd_tile("NETWORK GAPS", gap_count, "needs rule" if gap_count else "all covered", delta_dir)

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

        # ─── Per-API rollup stats (used in card hover) ───
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
        except Exception:
            pass

        # ─── Filter chips ───
        filter_choice = st.radio(
            "Filter",
            ["All", "Active", "Inactive", "Network Gap"],
            horizontal=True,
            label_visibility="collapsed",
            key="cfg_filter",
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

        if view_df.empty:
            st.info("No configs match this filter.")
        else:
            for _, r in view_df.iterrows():
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
                badges.append({"text": auth, "cls": "accent" if auth != "NONE" else ""})
                pag = (r.get("PAGINATION_TYPE") or "NONE")
                badges.append({"text": pag, "cls": ""})
                if bool(r.get("INCREMENTAL_FLAG", False)):
                    badges.append({"text": "INCREMENTAL", "cls": "accent"})
                if has_gap:
                    badges.append({"text": "NETWORK GAP", "cls": "warn"})
                if not is_active:
                    badges.append({"text": "INACTIVE", "cls": ""})

                meta_parts = []
                lt = r.get("LANDING_TABLE")
                if lt and not pd.isna(lt):
                    meta_parts.append(f"→ {lt}")
                else:
                    meta_parts.append("→ API_RAW_DATA (default)")
                lsv = r.get("LAST_SYNC_VALUE")
                if lsv and not pd.isna(lsv):
                    meta_parts.append(f"watermark: {lsv}")
                api_id = r.get("API_ID")
                if api_id and not pd.isna(api_id):
                    meta_parts.append(f"id: {int(api_id)}")
                meta = " · ".join(meta_parts)

                # Build hover stats from 7-day rollup
                hov = []
                stats = api_stats.get(name)
                if stats and stats["total"] > 0:
                    err_rate = ((stats["total"] - stats["ok"]) / stats["total"]) * 100
                    err_cls = "ok" if err_rate < 1 else ("err" if err_rate >= 5 else "")
                    last_run = stats["last_run"]
                    last_run_str = pd.to_datetime(last_run).strftime("%Y-%m-%d %H:%M") if last_run is not None and not pd.isna(last_run) else "—"
                    hov = [
                        {"label": "last run", "value": last_run_str},
                        {"label": "7d calls", "value": f"{stats['total']:,}"},
                        {"label": "err", "value": f"{err_rate:.1f}%", "cls": err_cls},
                    ]
                else:
                    hov = [{"label": "status", "value": "never run"}]

                cfg_card(name, endpoint, badges=badges, meta=meta, status=status, hover_stats=hov)
    else:
        st.markdown(f"""
        <div style="background: var(--bg-card); border: 1px dashed var(--border-strong); border-radius: 10px; padding: 32px; text-align: center; margin: 18px 0;">
            <div style="font-size: 2rem; margin-bottom: 8px;">🪐</div>
            <div style="font-family: var(--font-display); font-weight: 800; color: var(--text-primary); font-size: 1.05rem;">No API configurations yet</div>
            <div style="color: var(--text-secondary); font-size: 0.82rem; margin-top: 6px;">Register your first API endpoint below to start ingesting.</div>
            <div style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.7rem; margin-top: 14px;">▼ open <strong>New Endpoint</strong> below to begin</div>
        </div>
        """, unsafe_allow_html=True)

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

    st.divider()

    with st.expander("New Endpoint", expanded=False):
        section_label("NEW ENDPOINT")
        st.subheader("Add New API Config")

        if "form_version" not in st.session_state:
            st.session_state.form_version = 0
        fv = st.session_state.form_version

        api_name = st.text_input("API_NAME (unique key)", key=f"new_api_name_{fv}")

        existing_apis = set(configs["API_NAME"].tolist()) if not configs.empty else set()
        if api_name and api_name in existing_apis:
            st.warning(f"'{api_name}' already exists. Choose a different name.")

        endpoint_url = st.text_input("ENDPOINT_URL", key=f"new_url_{fv}")

        # Live network-rule coverage validation
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

        st.divider()
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

        st.divider()
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
            landing_table = ""
        else:
            landing_table = landing_choice

        pagination_type = st.selectbox("PAGINATION_TYPE", ["NONE", "PAGE", "OFFSET"], key=f"new_pag_type_{fv}")
        page_param = None
        start_index = 1

        if pagination_type != "NONE":
            page_param = st.text_input("PAGE_PARAM", key=f"new_page_param_{fv}")
            start_index = st.number_input("START_INDEX", value=1, min_value=0, key=f"new_start_idx_{fv}")

        st.divider()
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

        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            max_retries = st.number_input("MAX_RETRIES", value=6, min_value=1, key=f"new_retries_{fv}")
        with c2:
            retry_delay = st.number_input("RETRY_DELAY", value=15, min_value=1, key=f"new_delay_{fv}")
        with c3:
            timeout_sec = st.number_input("TIMEOUT", value=30, min_value=5, key=f"new_timeout_{fv}")

        if st.button("Add Config", type="primary"):
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
                            landing_table or None,
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
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(str(e))

    with st.expander("Endpoint Control", expanded=True):
        section_label("ENDPOINT CONTROL")
        st.subheader("Manage Existing API")

        if not configs.empty:
            selected_api = st.selectbox("Select API to Manage", configs["API_NAME"].tolist(), key="manage_api")

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
                    st.warning(f"Are you sure you want to permanently delete the configuration for **{selected_api}**? This cannot be undone.")
                    st.markdown('<div class="danger-red-confirm">', unsafe_allow_html=True)
                    if st.button("Yes, Delete Completely", use_container_width=True, key="btn_danger_delete_confirm"):
                        exec_sql(
                            f"DELETE FROM {META}.INGESTION_CONFIGS WHERE API_NAME = ?",
                            params=[selected_api]
                        )
                        rebuild_msg = rebuild_ingestor()
                        st.success(f"Deleted '{selected_api}' — {rebuild_msg}")
                        time.sleep(1.5)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No API configurations available to manage.")

# ─────────────────────────────────────────────
# TAB 2: Manage Secrets & EAI
# ─────────────────────────────────────────────
with tab2:
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
# TAB 3: Run Ingestion
# ─────────────────────────────────────────────
with tab3:
    section_label("DATA HARVESTING")
    st.header("Run Ingestion")
    st.caption("Execute API synchronization for selected or all active endpoints.")

    section_label("SELECTIVE EXECUTION")
    st.subheader("Run API Ingestion")
    active_apis = run_query(
        f"SELECT API_NAME FROM {META}.INGESTION_CONFIGS WHERE ACTIVE_FLAG = TRUE ORDER BY API_NAME"
    )
    if not active_apis.empty:
        api_list = active_apis["API_NAME"].tolist()
        selected_apis = st.multiselect("Select APIs to ingest", api_list)

        if st.button("Run Ingestion"):
            if selected_apis:
                progress = st.progress(0)
                results_container = st.container()
                for i, api in enumerate(selected_apis):
                    with st.spinner(f"Ingesting {api}..."):
                        try:
                            result = run_query(
                                f"CALL {META}.USP_UNIVERSAL_INGESTOR(?)",
                                params=[api]
                            )
                            msg = result.iloc[0, 0]
                            if "Success" in msg:
                                results_container.success(f"{api}: {msg}")
                            else:
                                results_container.error(f"{api}: {msg}")
                        except Exception as e:
                            results_container.error(f"{api}: {str(e)}")
                    progress.progress((i + 1) / len(selected_apis))
            else:
                st.warning("Select at least one API.")
    else:
        st.info("No active APIs configured.")

    st.divider()
    col_run_all, col_run_parallel = st.columns(2)

    with col_run_all:
        section_label("BATCH SEQUENTIAL")
        st.subheader("Run All (Sequential)")
        if st.button("Run All"):
            active = run_query(
                f"SELECT API_NAME FROM {META}.INGESTION_CONFIGS WHERE ACTIVE_FLAG = TRUE ORDER BY API_NAME"
            )
            if not active.empty:
                all_apis = active["API_NAME"].tolist()
                progress = st.progress(0)
                for i, api in enumerate(all_apis):
                    with st.spinner(f"Ingesting {api}..."):
                        try:
                            result = run_query(
                                f"CALL {META}.USP_UNIVERSAL_INGESTOR(?)",
                                params=[api]
                            )
                            msg = result.iloc[0, 0]
                            if "Success" in msg:
                                st.success(f"{api}: {msg}")
                            else:
                                st.error(f"{api}: {msg}")
                        except Exception as e:
                            st.error(f"{api}: {str(e)}")
                    progress.progress((i + 1) / len(all_apis))
            else:
                st.info("No active APIs.")

    with col_run_parallel:
        section_label("BATCH PARALLEL")
        st.subheader("Run All (Parallel via Tasks)")
        st.caption("Creates temporary Snowflake tasks to run all active APIs in parallel.")
        parallel_wh = st.text_input("Warehouse for parallel tasks", value="COMPUTE_WH", key="parallel_wh")
        if st.button("Run All Parallel"):
            if not is_safe_name(parallel_wh):
                st.error("Invalid warehouse name.")
            else:
                active = run_query(
                    f"SELECT API_NAME FROM {META}.INGESTION_CONFIGS WHERE ACTIVE_FLAG = TRUE ORDER BY API_NAME"
                )
                if not active.empty:
                    all_apis = active["API_NAME"].tolist()
                    task_names = []
                    with st.spinner("Creating parallel tasks..."):
                        for api in all_apis:
                            if not is_safe_name(api):
                                st.error(f"Skipping API with unsafe name: {api}")
                                continue
                            task_name = f"TASK_INGEST_{api}"
                            try:
                                escaped_api = escape_sql_literal(api)
                                exec_sql(
                                    f"CREATE OR REPLACE TASK {META}.{task_name} "
                                    f"WAREHOUSE = {parallel_wh} "
                                    f"AS CALL {META}.USP_UNIVERSAL_INGESTOR('{escaped_api}')"
                                )
                                exec_sql(f"EXECUTE TASK {META}.{task_name}")
                                task_names.append(task_name)
                            except Exception as e:
                                st.error(f"Failed to create/execute task for {api}: {str(e)}")

                    if task_names:
                        st.success(f"Launched {len(task_names)} parallel tasks: {', '.join(task_names)}")
                        st.info("Monitor progress in the 'Ingestion Console' tab.")

                        with st.spinner("Waiting for tasks to complete before cleanup..."):
                            max_wait = 300
                            poll_interval = 10
                            elapsed = 0
                            while elapsed < max_wait:
                                time.sleep(poll_interval)
                                elapsed += poll_interval
                                still_running = []
                                for tn in task_names:
                                    try:
                                        history = run_query(
                                            f"SELECT STATE FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY("
                                            f"TASK_NAME=>'{tn}', "
                                            f"SCHEDULED_TIME_RANGE_START=>DATEADD('MINUTE', -5, CURRENT_TIMESTAMP())"
                                            f"))"
                                        )
                                        if history.empty or history["STATE"].iloc[0] not in ("SUCCEEDED", "FAILED"):
                                            still_running.append(tn)
                                    except Exception:
                                        still_running.append(tn)
                                if not still_running:
                                    break

                            for tn in task_names:
                                try:
                                    exec_sql(f"DROP TASK IF EXISTS {META}.{tn}")
                                except Exception:
                                    pass

                            if still_running:
                                st.warning(f"Timeout reached. Some tasks may still be running: {', '.join(still_running)}")
                            else:
                                st.success("All tasks completed. Cleanup done.")
                else:
                    st.info("No active APIs.")

# ─────────────────────────────────────────────
# TAB 4: Ingestion Console (Stitch Sentinel)
# ─────────────────────────────────────────────
with tab4:
    section_label("SYSTEM TELEMETRY")
    st.header("Ingestion Console")
    st.caption("Global operational control for data synchronization and API harvesting.")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        log_apis = run_query(f"SELECT DISTINCT API_NAME FROM {META}.INGESTION_RESPONSE_LOG ORDER BY API_NAME")
        api_filter = st.multiselect("Filter by API", log_apis["API_NAME"].tolist() if not log_apis.empty else [])
    with col_f2:
        status_filter = st.multiselect("Filter by Status", ["200", "Non-200", "NULL (Error)"])
    with col_f3:
        limit_val = st.slider("Max rows", 50, 1000, 200, step=50)

    where_clauses = []
    filter_params = []
    if api_filter:
        placeholders = ", ".join(["?" for _ in api_filter])
        where_clauses.append(f"API_NAME IN ({placeholders})")
        filter_params.extend(api_filter)
    if status_filter:
        status_parts = []
        if "200" in status_filter:
            status_parts.append("STATUS_CODE = 200")
        if "Non-200" in status_filter:
            status_parts.append("(STATUS_CODE IS NOT NULL AND STATUS_CODE != 200)")
        if "NULL (Error)" in status_filter:
            status_parts.append("STATUS_CODE IS NULL")
        where_clauses.append("(" + " OR ".join(status_parts) + ")")

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    logs = run_query(
        f"SELECT * FROM {META}.INGESTION_RESPONSE_LOG WHERE {where_sql} "
        f"ORDER BY INSERT_DATETIME_UTC DESC LIMIT {limit_val}",
        params=filter_params if filter_params else None
    )

    if not logs.empty:
        success_count = len(logs[logs["STATUS_CODE"] == 200]) if "STATUS_CODE" in logs.columns else 0
        fail_count = len(logs) - success_count
        avg_time = logs["RESPONSE_TIME_SECONDS"].mean() if "RESPONSE_TIME_SECONDS" in logs.columns else 0
        success_rate = (success_count / len(logs) * 100) if len(logs) > 0 else 0

        # Build sparkline series from the in-window logs (oldest → newest)
        spark_calls = None
        spark_latency = None
        if "INSERT_DATETIME_UTC" in logs.columns:
            try:
                ts_logs = logs.copy()
                ts_logs["INSERT_DATETIME_UTC"] = pd.to_datetime(ts_logs["INSERT_DATETIME_UTC"])
                ts_logs = ts_logs.sort_values("INSERT_DATETIME_UTC")
                ts_logs["BUCKET"] = ts_logs["INSERT_DATETIME_UTC"].dt.floor("H")
                grp = ts_logs.groupby("BUCKET")
                spark_calls = grp.size().tolist()[-24:]
                if "RESPONSE_TIME_SECONDS" in ts_logs.columns:
                    spark_latency = grp["RESPONSE_TIME_SECONDS"].mean().tolist()[-24:]
            except Exception:
                pass

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            dd_tile("TOTAL CALLS", f"{len(logs):,}", live=True, spark_data=spark_calls)
        with m2:
            sr_dir = "up" if success_rate >= 95 else ("flat" if success_rate >= 80 else "down")
            dd_tile("SUCCESS RATE", f"{success_rate:.1f}%", f"{success_count} ok", sr_dir)
        with m3:
            avg_disp = f"{avg_time * 1000:.0f}ms" if avg_time < 1 else f"{avg_time:.2f}s"
            dd_tile("AVG RESPONSE", avg_disp, spark_data=spark_latency)
        with m4:
            err_dir = "down" if fail_count > 0 else "flat"
            dd_tile("FAILED / ERRORS", fail_count, f"of {len(logs)}", err_dir)

        st.divider()

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            section_label("DISTRIBUTION")
            st.subheader("Calls by API")
            api_counts = logs.groupby("API_NAME").size().reset_index(name="COUNT")
            st.bar_chart(api_counts.set_index("API_NAME"))

        with chart_col2:
            section_label("STATUS CODES")
            st.subheader("Status Distribution")
            logs["STATUS_LABEL"] = logs["STATUS_CODE"].apply(
                lambda x: str(int(x)) if pd.notna(x) else "ERROR"
            )
            status_counts = logs.groupby("STATUS_LABEL").size().reset_index(name="COUNT")
            st.bar_chart(status_counts.set_index("STATUS_LABEL"))

        st.divider()

        section_label("SYSTEM HEALTH")
        st.subheader("Recent Activity")
        recent = logs.head(15)
        for _, row in recent.iterrows():
            api_name = row.get("API_NAME", "Unknown")
            api_url = row.get("API_URL", "")
            status = row.get("STATUS_CODE", None)
            stitch_row(api_name, api_url or "—", status)

        st.divider()
        section_label("RETRY DRILL-DOWN")
        st.subheader("Pages That Required More Than One Attempt")
        st.caption("Each retry attempt is logged individually. This panel shows pages where the framework had to retry — including transient errors that eventually succeeded.")

        if "ATTEMPT_NUMBER" in logs.columns and "PAGE_NUMBER" in logs.columns:
            # Identify pages with >1 attempt within the filtered window
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
                    LIMIT 100
                    """,
                    params=filter_params if filter_params else None
                )
            except Exception as e:
                retry_summary = pd.DataFrame()
                st.caption(f"Drill-down unavailable: {str(e)}")

            if retry_summary.empty:
                st.info("No multi-attempt pages found in the current filter window. (Either no retries happened, or the schema migration hasn't been applied yet.)")
            else:
                rec_count = int((retry_summary["OUTCOME"] == "Recovered").sum()) if "OUTCOME" in retry_summary.columns else 0
                exh_count = int((retry_summary["OUTCOME"] == "Exhausted").sum()) if "OUTCOME" in retry_summary.columns else 0
                avg_attempts = retry_summary["ATTEMPTS"].mean() if "ATTEMPTS" in retry_summary.columns else 0

                rm1, rm2, rm3 = st.columns(3)
                with rm1:
                    dd_tile("PAGES WITH RETRIES", len(retry_summary))
                with rm2:
                    rec_dir = "up" if rec_count > 0 else "flat"
                    dd_tile("RECOVERED", rec_count, "transient → 200", rec_dir)
                with rm3:
                    exh_dir = "down" if exh_count > 0 else "flat"
                    dd_tile("EXHAUSTED (FAILED)", exh_count, "all attempts failed" if exh_count else "none", exh_dir)

                st.caption(f"Average attempts per retried page: **{avg_attempts:.2f}**")
                styled_dataframe(retry_summary)

                # Row picker for full attempt detail
                retry_summary["LABEL"] = (
                    retry_summary["API_NAME"].astype(str) + " — page " +
                    retry_summary["PAGE_NUMBER"].astype(str) + " (" +
                    retry_summary["ATTEMPTS"].astype(str) + " attempts, " +
                    retry_summary["OUTCOME"].fillna("—").astype(str) + ")"
                )
                pick = st.selectbox(
                    "Inspect attempt history for a specific page",
                    [""] + retry_summary["LABEL"].tolist(),
                    key="retry_pick"
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
                    except Exception as e:
                        st.error(f"Could not load attempt history: {str(e)}")
        else:
            st.info("Per-attempt logging columns are not present yet. Apply the migration in `DDL/setup.sql` and redeploy `USP_REBUILD_INGESTOR` + `USP_UNIVERSAL_INGESTOR`.")

        st.divider()
        section_label("FULL ARCHIVE")
        st.subheader("Log Details")
        styled_dataframe(logs)

        errors_only = logs[logs["ERROR_MESSAGE_TEXT"].notna() & (logs["ERROR_MESSAGE_TEXT"] != "") & (logs["ERROR_MESSAGE_TEXT"] != "None")]
        if not errors_only.empty:
            st.divider()
            section_label("INCIDENT REPORT")
            st.subheader("Error Details")
            styled_dataframe(
                errors_only[["API_NAME", "API_URL", "STATUS_CODE", "ERROR_MESSAGE_TEXT", "RETRY_COUNT", "INSERT_DATETIME_UTC"]]
            )
    else:
        st.info("No log entries found matching the filters.")

# ─────────────────────────────────────────────
# TAB 5: View Raw Data
# ─────────────────────────────────────────────
with tab5:
    section_label("DATA EXPLORER")
    st.header("Browse, Discover, Model")
    st.caption("Inspect raw landed payloads and one-click generate flattened SQL views.")

    # ─── Shared selectors (apply to both inner tabs) ───
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

    de_c1, de_c2 = st.columns([2, 2])
    with de_c1:
        de_table = st.selectbox("Landing Table", landing_tables, key="de_table")
    with de_c2:
        try:
            de_apis = run_query(f"SELECT DISTINCT API_NAME FROM {RAW}.{de_table} ORDER BY API_NAME")
            de_api_options = ["All"] + (de_apis["API_NAME"].tolist() if not de_apis.empty else [])
        except Exception:
            de_api_options = ["All"]
        de_api = st.selectbox("Filter by API", de_api_options, key="de_api")

    inner_raw, inner_schema = st.tabs(["Raw Payloads", "Schema Discovery"])

    # ─── Inner Tab: Raw Payloads ───
    with inner_raw:
        section_label("RAW PAYLOADS")
        rc1, rc2 = st.columns([1, 1])
        with rc1:
            raw_limit = st.slider("Max rows", 10, 500, 50, step=10, key="raw_limit")
        with rc2:
            show_payload = st.checkbox("Show full payload", value=False, key="raw_show_payload")

        raw_where = "WHERE API_NAME = ?" if de_api != "All" else ""
        raw_params = [de_api] if de_api != "All" else None
        payload_col = "PAYLOAD" if show_payload else "LEFT(PAYLOAD::STRING, 200) AS PAYLOAD_PREVIEW"

        raw_data = run_query(
            f"SELECT API_NAME, STATUS_CODE, INGEST_TS, PAYLOAD_HASH, URL_ATTEMPTED, {payload_col} "
            f"FROM {RAW}.{de_table} {raw_where} "
            f"ORDER BY INGEST_TS DESC LIMIT {raw_limit}",
            params=raw_params
        )

        if not raw_data.empty:
            col_rm1, col_rm2, col_rm3 = st.columns(3)
            with col_rm1:
                dd_tile("RECORDS SHOWN", len(raw_data))
            with col_rm2:
                total = run_query(f"SELECT COUNT(*) AS CNT FROM {RAW}.{de_table} {raw_where}", params=raw_params)
                dd_tile("TOTAL RECORDS", f"{int(total['CNT'].iloc[0]):,}", live=True)
            with col_rm3:
                distinct_apis = run_query(f"SELECT COUNT(DISTINCT API_NAME) AS CNT FROM {RAW}.{de_table}")
                dd_tile("DISTINCT APIs", int(distinct_apis["CNT"].iloc[0]))

            styled_dataframe(raw_data)

            if de_api != "All":
                st.divider()
                section_label("PAYLOAD INSPECTOR")
                st.subheader("Expand a Record")
                selected_hash = st.selectbox("Select by PAYLOAD_HASH", raw_data["PAYLOAD_HASH"].tolist(), key="raw_inspect_hash")
                if st.button("Show Full Payload", key="btn_raw_show_full"):
                    full = run_query(
                        f"SELECT PAYLOAD FROM {RAW}.{de_table} WHERE PAYLOAD_HASH = ?",
                        params=[selected_hash]
                    )
                    if not full.empty:
                        st.json(str(full["PAYLOAD"].iloc[0]))
        else:
            st.markdown("""
            <div style="background: var(--bg-card); border: 1px dashed var(--border-strong); border-radius: 10px; padding: 28px; text-align: center; margin: 14px 0;">
                <div style="font-size: 1.6rem; margin-bottom: 6px;">📭</div>
                <div style="font-family: var(--font-display); font-weight: 800; color: var(--text-primary);">No raw data found</div>
                <div style="color: var(--text-secondary); font-size: 0.78rem; margin-top: 6px;">Run an ingestion in the <strong>Run Ingestion</strong> tab, then come back here to inspect payloads.</div>
            </div>
            """, unsafe_allow_html=True)

    # ─── Inner Tab: Schema Discovery + View Generator ───
    with inner_schema:
        section_label("SCHEMA DISCOVERY & VIEW GENERATION")
        st.caption("Inspect the JSON shape of landed records and one-click generate flattened SQL views.")

        sc_c1, sc_c2 = st.columns([2, 1])
        with sc_c1:
            ds_records_path = st.text_input(
                "Records JSON Path",
                value="data",
                key="ds_records_path",
                help="Dotted path inside PAYLOAD that holds the record array. Default 'data' matches the framework's chunking format. Leave blank if PAYLOAD itself is the record."
            )
        with sc_c2:
            ds_sample = st.number_input("Sample Size", min_value=10, max_value=2000, value=100, step=10, key="ds_sample")

        default_view = f"V_{de_api}" if de_api != "All" else f"V_{de_table}_FLAT"
        ds_view_name = st.text_input(
            "Target View Name",
            value=default_view,
            key="ds_view_name",
            help="View will be created in API_DATA_PIPELINE.RAW_LANDING."
        )

        if st.button("Discover Schema", type="primary", key="btn_ds_discover"):
            try:
                where_clause = ""
                params = []
                if de_api != "All":
                    where_clause = "WHERE API_NAME = ?"
                    params = [de_api]
                sample_df = run_query(
                    f"SELECT PAYLOAD FROM {RAW}.{de_table} {where_clause} LIMIT {int(ds_sample)}",
                    params=params if params else None
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
                        st.warning(
                            "Sample returned PAYLOADs but no records were found at the given path. "
                            "Try clearing the 'Records JSON Path' field or checking the payload structure."
                        )
                    else:
                        schema_rows = []
                        for path, types in sorted(path_types.items()):
                            preferred_order = ["TIMESTAMP_TZ", "BOOLEAN", "NUMBER", "FLOAT", "OBJECT", "ARRAY", "STRING"]
                            chosen = next((t for t in preferred_order if t in types), "VARIANT")
                            coverage_pct = round(100.0 * path_counts[path] / total_records, 1)
                            schema_rows.append({
                                "PATH": path,
                                "TYPE": chosen,
                                "COVERAGE_%": coverage_pct,
                                "OBSERVED_TYPES": ", ".join(sorted(types))
                            })
                        schema_df = pd.DataFrame(schema_rows)
                        st.session_state["ds_schema_df"] = schema_df
                        st.session_state["ds_schema_table"] = de_table
                        st.session_state["ds_schema_api"] = de_api
                        st.session_state["ds_schema_records_path"] = (ds_records_path or "").strip()
                        st.session_state["ds_schema_total"] = total_records
                        st.success(f"Discovered {len(schema_df)} field(s) across {total_records} record(s).")
            except Exception as e:
                st.error(f"Schema discovery failed: {str(e)}")

        if "ds_schema_df" in st.session_state and not st.session_state["ds_schema_df"].empty:
            st.divider()
            section_label("DISCOVERED SCHEMA")

            sch_df = st.session_state["ds_schema_df"]
            m_c1, m_c2, m_c3 = st.columns(3)
            with m_c1:
                dd_tile("FIELDS DETECTED", len(sch_df))
            with m_c2:
                dd_tile("RECORDS SAMPLED", st.session_state.get("ds_schema_total", 0))
            with m_c3:
                full_coverage = int((sch_df["COVERAGE_%"] >= 99.9).sum())
                pct = (full_coverage / max(1, len(sch_df))) * 100
                cov_dir = "up" if pct == 100 else ("flat" if pct >= 80 else "down")
                dd_tile("100% COVERAGE", full_coverage, f"{pct:.0f}% of fields", cov_dir)

            styled_dataframe(sch_df)

            partial = sch_df[sch_df["COVERAGE_%"] < 100].copy()
            if not partial.empty:
                with st.expander("Quality Check — Fields with Partial Coverage", expanded=False):
                    st.caption(
                        "Fields below appear in some — but not all — records of the sample. "
                        "If a previously required field has dropped below 100%, the upstream API may have changed."
                    )
                    styled_dataframe(partial[["PATH", "TYPE", "COVERAGE_%"]])

            st.divider()
            section_label("GENERATE FLATTENED VIEW")

            gen_c1, gen_c2 = st.columns([3, 1])
            with gen_c1:
                include_meta = st.checkbox(
                    "Include framework columns (INGEST_TS, API_NAME, STATUS_CODE, URL_ATTEMPTED)",
                    value=True,
                    key="ds_include_meta"
                )
            with gen_c2:
                type_strategy = st.selectbox(
                    "Type Strategy",
                    ["Inferred", "All STRING (safe)"],
                    key="ds_type_strategy",
                    help="Inferred: cast to detected types. All STRING: cast everything to STRING (no cast errors)."
                )

            type_map = {
                "STRING": "STRING",
                "NUMBER": "NUMBER",
                "FLOAT": "FLOAT",
                "BOOLEAN": "BOOLEAN",
                "TIMESTAMP_TZ": "TIMESTAMP_TZ",
                "OBJECT": "VARIANT",
                "ARRAY": "ARRAY",
                "VARIANT": "VARIANT",
            }
            cols_sql = []
            if include_meta:
                cols_sql.append("    base.INGEST_TS")
                cols_sql.append("    base.API_NAME")
                cols_sql.append("    base.STATUS_CODE")
                cols_sql.append("    base.URL_ATTEMPTED")
            for _, srow in sch_df.iterrows():
                path = srow["PATH"]
                type_alias = type_map.get(srow["TYPE"], "STRING") if type_strategy == "Inferred" else "STRING"
                access = "rec.value"
                for part in path.split("."):
                    access += f":{part}"
                col_alias = re.sub(r"[^A-Za-z0-9_]", "_", path).upper()
                cols_sql.append(f"    {access}::{type_alias} AS {col_alias}")

            records_path_used = st.session_state.get("ds_schema_records_path", "")
            if records_path_used:
                from_clause = (
                    f"FROM {RAW}.{st.session_state['ds_schema_table']} base,\n"
                    f"     LATERAL FLATTEN(input => base.PAYLOAD:{records_path_used}) rec"
                )
            else:
                from_clause = (
                    f"FROM {RAW}.{st.session_state['ds_schema_table']} base,\n"
                    f"     LATERAL FLATTEN(input => base.PAYLOAD) rec"
                )

            api_filter = ""
            if st.session_state.get("ds_schema_api", "All") != "All":
                api_filter = f"\nWHERE base.API_NAME = '{escape_sql_literal(st.session_state['ds_schema_api'])}'"

            safe_view_name = re.sub(r"[^A-Za-z0-9_]", "_", ds_view_name) if ds_view_name else "V_FLAT"
            view_ddl = (
                f"CREATE OR REPLACE VIEW {RAW}.{safe_view_name} AS\n"
                f"SELECT\n"
                + ",\n".join(cols_sql) + "\n"
                + from_clause + api_filter
            )

            st.code(view_ddl, language="sql")

            ddl_c1, ddl_c2 = st.columns(2)
            with ddl_c1:
                if st.button("Create / Replace View", type="primary", key="btn_ds_create_view"):
                    if not is_safe_name(safe_view_name):
                        st.error("Invalid view name.")
                    else:
                        try:
                            exec_sql(view_ddl)
                            st.success(f"View {RAW}.{safe_view_name} created.")
                        except Exception as e:
                            st.error(f"Create view failed: {str(e)}")
            with ddl_c2:
                st.download_button(
                    "Download DDL",
                    view_ddl,
                    file_name=f"{safe_view_name}.sql",
                    mime="text/sql",
                    use_container_width=True,
                    key="btn_ds_download_ddl"
                )

# ─────────────────────────────────────────────
# TAB 6: Task Scheduler
# ─────────────────────────────────────────────
with tab6:
    section_label("AUTOMATION CONTROLS")
    st.header("Task Scheduler")
    st.caption("Manage Snowflake native tasks to automate API ingestion routines.")

    with st.expander("New Schedule", expanded=False):
        col_t1, col_t2 = st.columns(2)

        with col_t1:
            active_apis = run_query(f"SELECT API_NAME FROM {META}.INGESTION_CONFIGS WHERE ACTIVE_FLAG = TRUE ORDER BY API_NAME")
            api_options = active_apis["API_NAME"].tolist() if not active_apis.empty else []

            target_api = st.selectbox("Target API", api_options, key="sch_api")

            default_task_name = f"TASK_INGEST_{target_api}" if target_api else "TASK_INGEST_API"
            task_name = st.text_input("Task Name", value=default_task_name, key="sch_name")

            task_wh = st.text_input("Warehouse", value="COMPUTE_WH", key="sch_wh")

            sched_suspend_after = st.number_input("Auto-suspend after N failures", min_value=0, value=0, key="sch_suspend", help="0 = never auto-suspend")

        with col_t2:
            schedule_type = st.selectbox("Schedule Type", ["INTERVAL (Minutes)", "CRON"], key="sch_type")

            if schedule_type == "INTERVAL (Minutes)":
                interval_mins = st.number_input("Run every X minutes", min_value=1, value=60, key="sch_min")
                schedule_clause = f"{interval_mins} MINUTE"
                st.caption(f"SQL: `SCHEDULE = '{interval_mins} MINUTE'`")
            else:
                cron_expr = st.text_input("CRON Expression", value="0 2 * * *", key="sch_cron")
                cron_tz = st.text_input("Timezone", value="UTC", key="sch_tz")
                schedule_clause = f"USING CRON {cron_expr} {cron_tz}"
                st.caption(f"SQL: `SCHEDULE = 'USING CRON {cron_expr} {cron_tz}'`")
                st.markdown("[CRON formatting guide](https://crontab.guru/)", unsafe_allow_html=True)

        create_suspended = st.checkbox("Create as SUSPENDED (recommended for testing first)", value=True, key="sch_susp")

        if st.button("Create Scheduled Task", type="primary", key="btn_create_sched"):
            if not target_api:
                st.error("Please select a target API.")
            elif not is_safe_name(task_name):
                st.error("Invalid task name. Use only letters, digits, and underscores.")
            elif not is_safe_name(task_wh):
                st.error("Invalid warehouse name.")
            else:
                try:
                    escaped_api = escape_sql_literal(target_api)
                    suspend_clause = f" SUSPEND_TASK_AFTER_NUM_FAILURES = {sched_suspend_after}" if sched_suspend_after > 0 else ""

                    create_sql = (
                        f"CREATE OR REPLACE TASK {META}.{task_name} "
                        f"WAREHOUSE = {task_wh} "
                        f"SCHEDULE = '{schedule_clause}'"
                        f"{suspend_clause} "
                        f"AS CALL {META}.USP_UNIVERSAL_INGESTOR('{escaped_api}')"
                    )
                    exec_sql(create_sql)

                    msg = f"Task '{task_name}' created"
                    if not create_suspended:
                        exec_sql(f"ALTER TASK {META}.{task_name} RESUME")
                        msg += " and started."
                    else:
                        msg += " (suspended — resume when ready)."

                    st.toast(msg, icon="⏱")

                    keys_to_clear = ["sch_api", "sch_name", "sch_wh", "sch_type", "sch_min", "sch_cron", "sch_tz", "sch_susp", "sch_suspend"]
                    for k in keys_to_clear:
                        if k in st.session_state:
                            del st.session_state[k]

                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to create task: {str(e)}")

    section_label("ACTIVE SCHEDULES")
    try:
        tasks_df = run_query(f"SHOW TASKS IN SCHEMA {META}")
        if not tasks_df.empty:
            tasks_df.columns = [c.upper() for c in tasks_df.columns]

            t_m1, t_m2, t_m3 = st.columns(3)
            started = len(tasks_df[tasks_df["STATE"] == "started"]) if "STATE" in tasks_df.columns else 0
            suspended = len(tasks_df[tasks_df["STATE"] == "suspended"]) if "STATE" in tasks_df.columns else 0
            with t_m1:
                dd_tile("TOTAL TASKS", len(tasks_df), live=True)
            with t_m2:
                dd_tile("RUNNING", started, "live & scheduled" if started else "none", "up" if started else "flat")
            with t_m3:
                dd_tile("SUSPENDED", suspended, "paused" if suspended else "none", "down" if suspended else "flat")

            st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

            # ─── Card grid for tasks ───
            for _, t in tasks_df.iterrows():
                t_name = t.get("NAME", "—")
                t_state = (t.get("STATE") or "").lower()
                t_sched = t.get("SCHEDULE") or "—"
                t_wh = t.get("WAREHOUSE") or "—"
                t_last = t.get("LAST_COMMITTED_ON")

                if t_state == "started":
                    status = "healthy"
                    state_badge = {"text": "RUNNING", "cls": "accent"}
                elif t_state == "suspended":
                    status = "inactive"
                    state_badge = {"text": "SUSPENDED", "cls": ""}
                else:
                    status = "warning"
                    state_badge = {"text": t_state.upper() or "UNKNOWN", "cls": "warn"}

                badges = [
                    state_badge,
                    {"text": f"WH: {t_wh}", "cls": ""},
                    {"text": f"⏱ {t_sched}", "cls": ""},
                ]
                meta_parts = []
                if t_last and not pd.isna(t_last):
                    meta_parts.append(f"last run: {t_last}")
                meta = " · ".join(meta_parts) if meta_parts else "never run"

                cfg_card(t_name, f"CALL {META}.USP_UNIVERSAL_INGESTOR(...)", badges=badges, meta=meta, status=status)

            with st.expander("Show Full Task Details (table view)", expanded=False):
                display_cols = [c for c in ["NAME", "STATE", "SCHEDULE", "WAREHOUSE", "CONDITION", "LAST_COMMITTED_ON"] if c in tasks_df.columns]
                styled_dataframe(tasks_df[display_cols])

            task_names = tasks_df["NAME"].tolist()

            st.divider()
            section_label("TASK CONTROLS")
            c_action1, c_action2 = st.columns(2)
            with c_action1:
                selected_task = st.selectbox("Select Task to Manage", task_names, key="manage_task")
            with c_action2:
                st.write("")
                st.write("")
                task_row = tasks_df[tasks_df["NAME"] == selected_task].iloc[0]
                task_state = task_row.get("STATE", "unknown")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if task_state == "suspended":
                        if st.button("Resume", use_container_width=True, key="btn_resume_task"):
                            try:
                                exec_sql(f"ALTER TASK {META}.{selected_task} RESUME")
                                st.toast(f"Resumed {selected_task}", icon="▶")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    else:
                        if st.button("Suspend", use_container_width=True, key="btn_suspend_task"):
                            try:
                                exec_sql(f"ALTER TASK {META}.{selected_task} SUSPEND")
                                st.toast(f"Suspended {selected_task}", icon="⏸")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                with col_b:
                    if st.button("Run Now", use_container_width=True, key="btn_run_task"):
                        try:
                            exec_sql(f"EXECUTE TASK {META}.{selected_task}")
                            st.toast(f"Task `{selected_task}` triggered.", icon="🚀")
                        except Exception as e:
                            st.error(str(e))
                with col_c:
                    if st.button("Drop", use_container_width=True, key="btn_drop_task"):
                        try:
                            exec_sql(f"DROP TASK IF EXISTS {META}.{selected_task}")
                            st.toast(f"Dropped {selected_task}", icon="🗑")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

            st.divider()
            section_label("EXECUTION TELEMETRY")
            st.subheader("Task Run History")
            st.caption("Monitor the native execution status of your scheduled Snowflake tasks over the last 7 days.")

            col_h1, col_h2, col_h3 = st.columns([1, 1, 2])
            with col_h1:
                history_task_filter = st.selectbox("Filter by Task", ["All"] + task_names, key="hist_task_filter")
            with col_h2:
                history_state_filter = st.selectbox("Filter by State", ["All", "SUCCEEDED", "FAILED", "RUNNING", "SCHEDULED"], key="hist_state_filter")
            with col_h3:
                history_limit = st.slider("Result Limit", 10, 500, 50, step=10, key="hist_limit")

            base_history_sql = (
                "SELECT "
                "NAME, STATE, SCHEDULED_TIME, COMPLETED_TIME, "
                "TIMESTAMPDIFF(SECOND, SCHEDULED_TIME, COMPLETED_TIME) AS DURATION_SEC, "
                "ERROR_CODE, ERROR_MESSAGE "
                "FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY("
                "SCHEDULED_TIME_RANGE_START=>DATEADD('DAY', -7, CURRENT_TIMESTAMP()), "
                f"RESULT_LIMIT=>{history_limit}))"
            )

            hist_where = []
            if history_task_filter != "All":
                hist_where.append(f"NAME = '{escape_sql_literal(history_task_filter)}'")
            if history_state_filter != "All":
                hist_where.append(f"STATE = '{history_state_filter}'")

            if hist_where:
                base_history_sql += " WHERE " + " AND ".join(hist_where)

            base_history_sql += " ORDER BY SCHEDULED_TIME DESC"

            try:
                task_history_df = run_query(base_history_sql)

                if not task_history_df.empty:
                    failed_count = len(task_history_df[task_history_df["STATE"] == "FAILED"])
                    succeeded_count = len(task_history_df[task_history_df["STATE"] == "SUCCEEDED"])
                    running_count = len(task_history_df[task_history_df["STATE"] == "RUNNING"])

                    m1, m2, m3 = st.columns(3)
                    with m1:
                        dd_tile("SUCCESSFUL RUNS", succeeded_count, "last 7d", "up" if succeeded_count else "flat")
                    with m2:
                        dd_tile("CURRENTLY RUNNING", running_count, live=running_count > 0)
                    with m3:
                        dd_tile("FAILED RUNS", failed_count, "needs attention" if failed_count else "none", "down" if failed_count else "flat")

                    if "SCHEDULED_TIME" in task_history_df.columns:
                        task_history_df["SCHEDULED_TIME"] = pd.to_datetime(task_history_df["SCHEDULED_TIME"]).dt.strftime('%Y-%m-%d %H:%M:%S')
                    if "COMPLETED_TIME" in task_history_df.columns:
                        task_history_df["COMPLETED_TIME"] = pd.to_datetime(task_history_df["COMPLETED_TIME"]).dt.strftime('%Y-%m-%d %H:%M:%S')

                    styled_dataframe(task_history_df)

                    errors_only = task_history_df[task_history_df["STATE"] == "FAILED"]
                    if not errors_only.empty:
                        st.divider()
                        section_label("TASK FAILURES")
                        for _, row in errors_only.iterrows():
                            err_title = f"{row['NAME']} (Failed at {row['SCHEDULED_TIME']})"
                            err_sub = row['ERROR_MESSAGE'] if pd.notna(row['ERROR_MESSAGE']) else "Unknown Error"
                            stitch_row(err_title, err_sub, 500)

                else:
                    st.info("No task history found for the selected filters in the last 7 days.")

            except Exception as e:
                st.error(f"Could not load task history: {str(e)}")
                st.caption("Note: Ensure the role running this app has the MONITOR EXECUTION privilege on the account to view task history.")

        else:
            st.info("No scheduled tasks found.")
            task_names = []
    except Exception as e:
        st.warning(f"Could not load tasks: {e}")
        task_names = []

    # st.divider()
    # section_label("BULK SCHEDULER")
    # st.subheader("Schedule All Active APIs")
    # st.caption("Creates one task per active API with the same interval.")

    # bulk_col1, bulk_col2 = st.columns(2)
    # with bulk_col1:
    #     bulk_interval = st.number_input("Interval (minutes) for all", min_value=1, max_value=1440, value=60, key="bulk_interval")
    # with bulk_col2:
    #     bulk_wh = st.text_input("Warehouse for all", value="COMPUTE_WH", key="bulk_wh")

    # bulk_suspended = st.checkbox("Create all as SUSPENDED", value=True, key="bulk_susp")

    # if st.button("Schedule All Active APIs", key="btn_bulk_sched"):
    #     if not is_safe_name(bulk_wh):
    #         st.error("Invalid warehouse name.")
    #     elif not api_options:
    #         st.warning("No active APIs to schedule.")
    #     else:
    #         results = []
    #         for api in api_options:
    #             t_name = f"TASK_INGEST_{api}"
    #             try:
    #                 exec_sql(
    #                     f"CREATE OR REPLACE TASK {META}.{t_name} "
    #                     f"WAREHOUSE = {bulk_wh} "
    #                     f"SCHEDULE = '{bulk_interval} MINUTE' "
    #                     f"AS CALL {META}.USP_UNIVERSAL_INGESTOR('{escape_sql_literal(api)}')"
    #                 )
    #                 if not bulk_suspended:
    #                     exec_sql(f"ALTER TASK {META}.{t_name} RESUME")
    #                     results.append((api, "Created & Resumed"))
    #                 else:
    #                     results.append((api, "Created (suspended)"))
    #             except Exception as e:
    #                 results.append((api, f"Error: {str(e)}"))
    #         for api, msg in results:
    #             if "Error" in msg:
    #                 st.error(f"{api}: {msg}")
    #             else:
    #                 st.success(f"{api}: {msg}")
    #         time.sleep(1)
    #         st.rerun()
