"""Tiger SnowSync — pure UI helpers (no DB dependencies)."""
import re
import streamlit as st
import pandas as pd


# ─────────────────────────────────────────────
# Section label
# ─────────────────────────────────────────────
def section_label(text: str) -> None:
    st.markdown(f"<p class='section-label'>{text}</p>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Empty state
# ─────────────────────────────────────────────
def empty_state(icon: str, title: str, subtitle: str) -> None:
    """Reusable illustrated empty-state card."""
    st.markdown(f"""
    <div style="background: var(--bg-card); border: 1px dashed var(--border-strong); border-radius: 10px; padding: 32px; text-align: center; margin: 18px 0;">
        <div style="font-size: 2rem; margin-bottom: 8px;">{icon}</div>
        <div style="font-family: var(--font-display); font-weight: 800; color: var(--text-primary); font-size: 1.05rem;">{title}</div>
        <div style="color: var(--text-secondary); font-size: 0.82rem; margin-top: 6px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SVG sparkline
# ─────────────────────────────────────────────
def make_sparkline_svg(values, color: str = "#29B5E8", width: int = 200, height: int = 28) -> str:
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


# ─────────────────────────────────────────────
# dd_tile (Datadog/Vercel-style metric tile)
# ─────────────────────────────────────────────
def dd_tile(label, value, delta=None, delta_dir="flat", live=False,
            spark_data=None, spark_color=None, size="default", glow=None,
            status_pill=None):
    """Datadog/Vercel-style metric tile."""
    # Sanitize NaN/None values
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
    if live:
        classes.append("live")
    if size == "hero":
        classes.append("hero")
    if glow in ("ok", "warn", "err"):
        classes.append(f"glow-{glow}")
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


# ─────────────────────────────────────────────
# cfg_card (Configuration Registry card)
# ─────────────────────────────────────────────
def cfg_card(name, endpoint, badges=None, meta=None, status="healthy", hover_stats=None):
    """Configuration Registry card. status ∈ {healthy, warning, error, inactive}."""
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


# ─────────────────────────────────────────────
# styled_dataframe
# ─────────────────────────────────────────────
def styled_dataframe(df, height: int = 400) -> None:
    h_css = f"max-height:{height}px;overflow-y:auto;"
    html = df.to_html(index=False, escape=True, classes="ct-table")
    st.markdown(f'''<div style="{h_css}overflow-x:auto;border:1px solid rgba(255,255,255,0.1);border-radius:8px;">
    <style>
    .ct-table {{width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:0.76rem;}}
    .ct-table th {{background:#161b22;color:#e6edf3;padding:8px 12px;text-align:left;border-bottom:2px solid rgba(255,255,255,0.12);font-weight:600;font-size:0.72rem;position:sticky;top:0;z-index:1;}}
    .ct-table td {{background:#0d1117;color:#e6edf3;padding:6px 12px;border-bottom:1px solid rgba(255,255,255,0.06);}}
    .ct-table tr:hover td {{background:#1c2333;}}
    </style>{html}</div>''', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# stitch_row + active_pill
# ─────────────────────────────────────────────
def stitch_row(title, subtitle, status_code) -> None:
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


def active_pill(is_active: bool) -> str:
    if is_active:
        return "<span class='stitch-pill pill-active'>ACTIVE</span>"
    return "<span class='stitch-pill pill-inactive'>INACTIVE</span>"


def paginated_items(items, page_key: str, page_size: int = 10):
    """Paginate a list and render prev/next controls.
    Returns the current page slice. Use like:
        for item in paginated_items(my_list, "my_page_key"):
            render_card(item)
    """
    total = len(items)
    if total <= page_size:
        return items

    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    current_page = st.session_state[page_key]
    total_pages = max(1, -(-total // page_size))
    current_page = min(current_page, total_pages - 1)
    st.session_state[page_key] = current_page

    start = current_page * page_size
    page_items = items[start:start + page_size]

    st.markdown(
        f"<div style='font-family:var(--font-mono);font-size:0.68rem;color:var(--text-muted);"
        f"margin-bottom:8px;'>Showing {start+1}–{start+len(page_items)} of {total}</div>",
        unsafe_allow_html=True
    )
    return page_items


def paginated_controls(items, page_key: str, page_size: int = 10):
    """Render pagination buttons after the items. Call after your item loop."""
    total = len(items)
    if total <= page_size:
        return
    total_pages = max(1, -(-total // page_size))
    current_page = st.session_state.get(page_key, 0)

    pg1, pg2, pg3 = st.columns([1, 3, 1])
    with pg1:
        if st.button("← Prev", use_container_width=True, key=f"{page_key}_prev",
                     disabled=(current_page == 0)):
            st.session_state[page_key] = current_page - 1
            st.rerun()
    with pg2:
        st.markdown(
            f"<div style='text-align:center;font-family:var(--font-mono);font-size:0.72rem;"
            f"color:var(--text-muted);padding-top:8px;'>"
            f"Page {current_page + 1} of {total_pages}</div>",
            unsafe_allow_html=True
        )
    with pg3:
        if st.button("Next →", use_container_width=True, key=f"{page_key}_next",
                     disabled=(current_page >= total_pages - 1)):
            st.session_state[page_key] = current_page + 1
            st.rerun()
