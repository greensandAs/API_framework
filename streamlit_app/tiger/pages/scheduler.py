"""Tiger SnowSync — Task Scheduler page (6-zone redesign)."""
import time
from datetime import datetime

import streamlit as st
import pandas as pd

try:
    import plotly.graph_objects as go
    _PLOTLY_OK = True
except Exception:
    _PLOTLY_OK = False

from tiger.db import (
    META, run_query, exec_sql,
    is_safe_name, escape_sql_literal,
)
from tiger.helpers import (
    section_label, empty_state, dd_tile, cfg_card, styled_dataframe,
)
from tiger.knowledge import (
    _humanize_schedule, _humanize_cron, _parse_next_runs,
)


def render(default_warehouse: str = "COMPUTE_WH") -> None:
    """Render the Task Scheduler page."""
    section_label("AUTOMATION CONTROLS")
    st.header("Task Scheduler")
    st.caption("Monitor → manage → create. Bulk actions, schedule timeline, conflict detection.")

    # ─── Load tasks ───
    try:
        tasks_df = run_query(f"SHOW TASKS IN SCHEMA {META}")
        if not tasks_df.empty:
            tasks_df.columns = [c.upper() for c in tasks_df.columns]
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
        wh_options = wh_q["NAME"].tolist() if not wh_q.empty else [default_warehouse]
    except Exception:
        wh_options = [default_warehouse]

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
                st.caption("")

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
                pref_wh_v2 = st.session_state.get("pref_warehouse", default_warehouse)
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
