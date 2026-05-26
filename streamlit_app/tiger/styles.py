"""Tiger SnowSync — global theme / CSS injection."""
import streamlit as st


_TIGER_CSS = """
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
    .dd-tile.hero { min-height: 150px; padding: 22px 26px; }
    .dd-tile.hero .value { font-size: 2.4rem; }
    .dd-tile.hero .label { font-size: 0.7rem; }

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

    .dd-tile .spark { margin-top: 10px; opacity: 0.85; line-height: 0; }
    .dd-tile .spark svg { display: block; width: 100%; height: 28px; }

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

    .stCodeBlock pre, code[class*="language-"] {
        background: #0d0d0d !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        font-family: var(--font-mono) !important;
        font-size: 0.78rem !important;
    }

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
"""


def inject_styles() -> None:
    """Inject the Tiger SnowSync theme/CSS into the current Streamlit page."""
    st.markdown(_TIGER_CSS, unsafe_allow_html=True)
