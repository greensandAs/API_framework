"""Tiger SnowSync — Ingestion Console page."""
import streamlit as st
import pandas as pd

try:
    import plotly.graph_objects as go
    _PLOTLY_OK = True
except Exception:
    _PLOTLY_OK = False

from tiger.helpers import (
    section_label, empty_state, dd_tile, cfg_card,
    styled_dataframe, stitch_row,
)
from tiger.knowledge import ERROR_KNOWLEDGE
from tiger.db import META, run_query


def render() -> None:
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
              AND (API_URL IS NULL OR API_URL != '__PROGRESS__')
            """,
            params=params if params else None
        ).iloc[0]
        total = int(kpi["TOTAL_CALLS"]) if not pd.isna(kpi["TOTAL_CALLS"]) else 0
        ok = int(kpi["OK_CALLS"]) if not pd.isna(kpi["OK_CALLS"]) else 0
        fails = int(kpi["FAIL_CALLS"]) if not pd.isna(kpi["FAIL_CALLS"]) else 0
        avg_rt = float(kpi["AVG_RT"]) if not pd.isna(kpi["AVG_RT"]) else 0.0
        max_rt = float(kpi["MAX_RT"]) if not pd.isna(kpi["MAX_RT"]) else 0.0
        active_apis = int(kpi["ACTIVE_APIS"]) if not pd.isna(kpi["ACTIVE_APIS"]) else 0
        apis_err = int(kpi["APIS_WITH_ERRORS"]) if not pd.isna(kpi["APIS_WITH_ERRORS"]) else 0
        active_buckets = int(kpi["ACTIVE_BUCKETS"] or 1)
        sr = (ok / max(total, 1)) * 100
    except Exception as _e:
        st.error(f"Failed to load KPIs: {_e}")
        total = ok = fails = active_apis = apis_err = active_buckets = 0
        avg_rt = max_rt = 0.0
        sr = 0.0

    if total == 0:
        empty_state("📭", "No log entries", f"Nothing recorded in the last {time_range} window.")
        return

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

    tab_feed, tab_health, tab_runs, tab_retries, tab_errors, tab_intel = st.tabs([
        "📡  Activity Feed", "🏥  Per-API Health", "📊  Run Summary", "🔁  Retry Analysis", "🚨  Incidents", "🧠  Error Intelligence",
    ])

    with tab_feed:
        log_limit = st.slider("Show last N rows", 25, 500, 100, step=25, key="feed_limit")
        try:
            feed_logs = run_query(
                f"""
                SELECT API_NAME, API_URL, STATUS_CODE, RESPONSE_TIME_SECONDS,
                       INSERT_DATETIME_UTC, ERROR_MESSAGE_TEXT
                FROM {META}.INGESTION_RESPONSE_LOG
                WHERE {where_sql}
                  AND (API_URL IS NULL OR API_URL != '__PROGRESS__')
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
                  AND (API_URL IS NULL OR API_URL != '__PROGRESS__')
                GROUP BY API_NAME
                ORDER BY (OK / NULLIF(CALLS, 0)) ASC NULLS FIRST
                """,
                params=params if params else None
            )
        except Exception as _e:
            health_df = pd.DataFrame()
            st.caption(f"Health unavailable: {_e}")

        latest_runs = {}
        try:
            lr_df = run_query(f"SELECT * FROM {META}.V_LATEST_RUNS")
            for _, lr in lr_df.iterrows():
                latest_runs[lr["API_NAME"]] = lr.to_dict()
        except Exception:
            pass

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

                lr_info = latest_runs.get(h["API_NAME"], {})
                lr_records = lr_info.get("RECORDS_INGESTED")
                lr_status = lr_info.get("STATUS", "")
                lr_duration = lr_info.get("DURATION_SEC")

                meta_parts = [f"last run: {last_run_s}"]
                if lr_records is not None and not pd.isna(lr_records):
                    meta_parts.append(f"last ingested: {int(lr_records):,} records")
                if lr_duration is not None and not pd.isna(lr_duration):
                    meta_parts.append(f"duration: {int(lr_duration)}s")

                badges = [
                    {"text": f"✓ {int(h['OK']):,}", "cls": "accent"},
                    {"text": f"✗ {int(h['FAILS']):,}", "cls": "danger" if h["FAILS"] > 0 else ""},
                ]
                if lr_status and lr_status != "SUCCESS":
                    badges.append({"text": f"LAST: {lr_status}", "cls": "warn"})

                cfg_card(
                    h["API_NAME"],
                    f"{sr_v}% success · {int(h['CALLS']):,} calls · avg {h['AVG_RT']}s · max {h['MAX_RT']}s",
                    badges=badges,
                    meta=" · ".join(meta_parts),
                    status=h_status,
                )
                st.markdown(
                    f"<div style='width:100%;height:3px;background:#1f1f1f;border-radius:2px;margin:-4px 0 8px;'>"
                    f"<div style='width:{sr_v}%;height:3px;background:{bar_color};border-radius:2px;'></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

    with tab_runs:
        st.caption("One row per ingestion run — aggregated from INGESTION_RUN_SUMMARY.")
        try:
            runs_df = run_query(
                f"""
                SELECT API_NAME, STATUS, RUN_START_UTC, RUN_END_UTC,
                       TIMESTAMPDIFF(SECOND, RUN_START_UTC, RUN_END_UTC) AS DURATION_SEC,
                       PAGES_PROCESSED, RECORDS_INGESTED, RECORDS_SKIPPED,
                       WATERMARK_FROM, WATERMARK_TO, FINAL_PAGE_TYPE, ERROR_MESSAGE
                FROM {META}.INGESTION_RUN_SUMMARY
                WHERE RUN_START_UTC >= DATEADD('{_unit}', -{_amt}, CURRENT_TIMESTAMP())
                ORDER BY RUN_START_UTC DESC
                LIMIT 200
                """
            )
        except Exception as _e:
            runs_df = pd.DataFrame()
            st.caption(f"Run summary unavailable: {_e}")

        if runs_df.empty:
            empty_state("📊", "No run summaries yet", "Runs will appear here after the enhanced procedure executes.")
        else:
            success_runs = int((runs_df["STATUS"] == "SUCCESS").sum())
            error_runs = int((runs_df["STATUS"] == "ERROR").sum())
            warning_runs = int((runs_df["STATUS"] == "WARNING").sum())
            total_records = int(runs_df["RECORDS_INGESTED"].fillna(0).sum())

            rs1, rs2, rs3, rs4 = st.columns(4)
            with rs1:
                dd_tile("TOTAL RUNS", len(runs_df), f"last {time_range}", "flat")
            with rs2:
                dd_tile("SUCCESS", success_runs, f"{round(success_runs/max(len(runs_df),1)*100)}%",
                        "up" if success_runs == len(runs_df) else "flat", glow="ok" if error_runs == 0 else None)
            with rs3:
                dd_tile("ERRORS", error_runs, "need attention" if error_runs else "clean",
                        "down" if error_runs else "flat", glow="err" if error_runs else None)
            with rs4:
                dd_tile("RECORDS INGESTED", f"{total_records:,}", f"across {len(runs_df)} runs", "flat")

            st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

            run_tab_detail, run_tab_errors = st.tabs(["📋 All Runs", "🚨 Failed Runs"])
            with run_tab_detail:
                styled_dataframe(runs_df.drop(columns=["ERROR_MESSAGE"], errors="ignore"))
            with run_tab_errors:
                failed_runs = runs_df[runs_df["STATUS"].isin(["ERROR", "WARNING"])]
                if failed_runs.empty:
                    empty_state("✅", "No failed runs", f"All runs succeeded in the last {time_range}.")
                else:
                    for _, fr in failed_runs.iterrows():
                        err_msg = str(fr.get("ERROR_MESSAGE") or "Unknown")
                        ts = str(fr.get("RUN_START_UTC") or "")[:16]
                        pages = fr.get("PAGES_PROCESSED") or 0
                        cfg_card(
                            name=f"{fr['API_NAME']} — {fr['STATUS']}",
                            endpoint=err_msg[:200],
                            badges=[
                                {"text": fr["STATUS"], "cls": "danger" if fr["STATUS"] == "ERROR" else "warn"},
                                {"text": f"{pages} pages", "cls": ""},
                            ],
                            meta=f"started: {ts} · type: {fr.get('FINAL_PAGE_TYPE', '—')}",
                            status="error" if fr["STATUS"] == "ERROR" else "warning"
                        )

    with tab_retries:
        st.caption("Pages where the framework had to retry — including transient errors that eventually succeeded.")
        try:
            retry_summary = run_query(
                f"""
                WITH base AS (
                    SELECT COALESCE(RUN_ID, API_NAME || '_' || DATE_TRUNC('HOUR', INSERT_DATETIME_UTC)::STRING) AS RUN_ID,
                           API_NAME, PAGE_NUMBER, ATTEMPT_NUMBER, STATUS_CODE,
                           ERROR_MESSAGE_TEXT, RESPONSE_TIME_SECONDS, IS_FINAL_ATTEMPT,
                           INSERT_DATETIME_UTC, API_URL
                    FROM {META}.INGESTION_RESPONSE_LOG
                    WHERE {where_sql}
                      AND PAGE_NUMBER IS NOT NULL
                      AND ATTEMPT_NUMBER IS NOT NULL
                      AND (API_URL IS NULL OR API_URL != '__PROGRESS__')
                ),
                grouped AS (
                    SELECT RUN_ID, API_NAME, PAGE_NUMBER,
                           MIN(INSERT_DATETIME_UTC) AS RUN_STARTED_UTC,
                           MAX(INSERT_DATETIME_UTC) AS RUN_ENDED_UTC,
                           COUNT(*) AS ATTEMPTS,
                           MAX(CASE WHEN IS_FINAL_ATTEMPT THEN STATUS_CODE END) AS FINAL_STATUS,
                           MAX(CASE WHEN IS_FINAL_ATTEMPT AND STATUS_CODE = 200 THEN 'Recovered'
                                    WHEN IS_FINAL_ATTEMPT THEN 'Exhausted'
                                    ELSE NULL END) AS OUTCOME
                    FROM base
                    GROUP BY RUN_ID, API_NAME, PAGE_NUMBER
                    HAVING COUNT(*) > 1
                )
                SELECT RUN_ID, API_NAME, PAGE_NUMBER, ATTEMPTS, FINAL_STATUS, OUTCOME,
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
                retry_summary["RUN_ID"].astype(str).str[:8] + " · " +
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
                sel_run_id = sel_row["RUN_ID"]
                try:
                    run_filter = "AND RUN_ID = ?" if sel_run_id else ""
                    run_params = [sel_api, sel_page] + ([sel_run_id] if sel_run_id else [])
                    attempts_df = run_query(
                        f"SELECT RUN_ID, ATTEMPT_NUMBER, IS_FINAL_ATTEMPT, STATUS_CODE, "
                        f"RESPONSE_TIME_SECONDS, ERROR_MESSAGE_TEXT, INSERT_DATETIME_UTC, API_URL "
                        f"FROM {META}.INGESTION_RESPONSE_LOG "
                        f"WHERE API_NAME = ? AND PAGE_NUMBER = ? {run_filter} "
                        f"ORDER BY ATTEMPT_NUMBER",
                        params=run_params
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

    with tab_errors:
        try:
            errors_df = run_query(
                f"""
                SELECT API_NAME, STATUS_CODE, ERROR_MESSAGE_TEXT,
                       API_URL, INSERT_DATETIME_UTC, RETRY_COUNT
                FROM {META}.INGESTION_RESPONSE_LOG
                WHERE {where_sql}
                  AND (STATUS_CODE != 200 OR STATUS_CODE IS NULL)
                  AND (API_URL IS NULL OR API_URL != '__PROGRESS__')
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

    with tab_intel:
        st.caption("Each error code grouped, ranked, and explained. Click any code for likely causes, actions, and a deep-link to the affected API config.")

        try:
            error_freq_df = run_query(
                f"""
                SELECT
                    COALESCE(STATUS_CODE::STRING, 'NULL') AS CODE,
                    SUM(OCCURRENCES)                       AS OCCURRENCES,
                    COUNT(DISTINCT API_NAME)               AS APIS_AFFECTED,
                    MAX(LAST_SEEN)                         AS LAST_SEEN
                FROM {META}.V_ERROR_SUMMARY_7D
                GROUP BY 1
                ORDER BY OCCURRENCES DESC
                """
            )
        except Exception:
            try:
                error_freq_df = run_query(
                    f"""
                    SELECT
                        COALESCE(STATUS_CODE::STRING, 'NULL') AS CODE,
                        COUNT(*)                              AS OCCURRENCES,
                        COUNT(DISTINCT API_NAME)              AS APIS_AFFECTED,
                        MAX(INSERT_DATETIME_UTC)              AS LAST_SEEN
                    FROM {META}.INGESTION_RESPONSE_LOG
                    WHERE {where_sql}
                      AND (STATUS_CODE != 200 OR STATUS_CODE IS NULL)
                      AND (API_URL IS NULL OR API_URL != '__PROGRESS__')
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
                    OCCURRENCES,
                    LAST_SEEN,
                    SAMPLE_ERROR AS SAMPLE_MESSAGE
                FROM {META}.V_ERROR_SUMMARY_7D
                ORDER BY 1, OCCURRENCES DESC
                """
            )
        except Exception:
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
                      AND (API_URL IS NULL OR API_URL != '__PROGRESS__')
                    GROUP BY 1, 2
                    ORDER BY 1, OCCURRENCES DESC
                    """,
                    params=params if params else None
                )
            except Exception:
                error_api_df = pd.DataFrame()
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
