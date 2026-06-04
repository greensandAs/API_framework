"""Tiger SnowSync — Run Ingestion page (3-phase: select → configure → execute/monitor)."""
import time

import streamlit as st
import pandas as pd

from tiger.db import (
    META, run_query, exec_sql,
    is_safe_name, escape_sql_literal,
    get_allowed_hosts, check_host_allowed,
)
from tiger.helpers import (
    section_label, empty_state, dd_tile, cfg_card, styled_dataframe,
)


def render(default_warehouse: str = "COMPUTE_WH") -> None:
    """Render the Run Ingestion page.

    Args:
        default_warehouse: fallback warehouse name (typically the current session warehouse).
    """
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
        return

    api_list = pre_run_df["API_NAME"].tolist()

    # ─────────────────────────────────────
    # PHASE 1 — SELECT
    # ─────────────────────────────────────
    section_label("PHASE 1 · SELECT")

    if "ri_selection" not in st.session_state:
        st.session_state["ri_selection"] = []

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

    selected_apis = st.multiselect(
        "Selected APIs",
        api_list,
        key="ri_selection",
    )

    if selected_apis:
        sel_chips = "".join(f"<span class='chip active'>{a}</span>" for a in selected_apis)
        st.markdown(
            f"<div class='chip-bar'>"
            f"<span class='chip warn'>✓ {len(selected_apis)} SELECTED</span>"
            f"{sel_chips}"
            f"</div>",
            unsafe_allow_html=True,
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

    modes_info = {
        "Sequential": ("⏯  One at a time, with live log. Best for **1-5 APIs** or debugging. "
                       "Keep the browser open."),
        "Parallel":   ("⚡ Fire all selected via persistent Snowflake tasks. Best for **production / 10+ APIs**. "
                       "Safe to close the browser."),
        "Dry Run":    ("🧪 Validate configs and network rules — no data movement. Best for **new APIs**."),
    }
    st.caption(modes_info[run_mode])

    run_warehouse = None
    if run_mode == "Parallel":
        try:
            wh_df = run_query("SHOW WAREHOUSES")
            wh_df.columns = [c.upper() for c in wh_df.columns]
            wh_options = wh_df["NAME"].tolist() if not wh_df.empty else [default_warehouse]
        except Exception:
            wh_options = [default_warehouse]
        pref_wh = st.session_state.get("pref_warehouse", default_warehouse)
        run_warehouse = st.selectbox(
            "Warehouse for parallel tasks",
            wh_options,
            index=wh_options.index(pref_wh) if pref_wh in wh_options else 0,
            key="ri_wh",
        )
        st.caption("Tip: Tasks are persistent. They appear in the **Scheduler** tab so you can re-fire them.")

    st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    # PHASE 3 — EXECUTE / MONITOR
    # ─────────────────────────────────────
    section_label("PHASE 3 · EXECUTE")

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
            unsafe_allow_html=True,
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
            allowed_entries = get_allowed_hosts()
            results = []
            for api in selected_apis:
                try:
                    endpoint = run_query(
                        f"SELECT ENDPOINT_URL FROM {META}.INGESTION_CONFIGS WHERE API_NAME = ?",
                        params=[api],
                    )
                    url = endpoint["ENDPOINT_URL"].iloc[0] if not endpoint.empty else ""
                    ok, matched, reason = check_host_allowed(str(url), allowed_entries)
                    results.append({
                        "API_NAME": api, "URL": url,
                        "NETWORK_OK": "✓" if ok else "✗",
                        "DETAIL": matched if ok else reason,
                    })
                except Exception as e:
                    results.append({"API_NAME": api, "URL": "—", "NETWORK_OK": "✗", "DETAIL": str(e)})
            styled_dataframe(pd.DataFrame(results))
            ok_count = sum(1 for r in results if r["NETWORK_OK"] == "✓")
            st.toast(f"Dry run complete · {ok_count}/{len(results)} OK", icon="🧪")

        elif run_mode == "Sequential":
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
                            existing = run_query(f"SHOW TASKS LIKE '{task_name}' IN SCHEMA {META}")
                            if existing.empty:
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
    # LIVE MONITORING
    # ─────────────────────────────────────
    if st.session_state.get("ri_last_fired_tasks"):
        st.markdown("<div style='height: 1.0rem;'></div>", unsafe_allow_html=True)
        section_label("LIVE MONITOR")
        mon_col1, _mon_col2 = st.columns([1, 5])
        with mon_col1:
            st.button("🔄 Refresh", use_container_width=True, key="ri_mon_refresh")

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
