"""Tiger SnowSync — Data Explorer page."""
import json
import re
from collections import defaultdict

import streamlit as st
import pandas as pd

from tiger.helpers import (
    section_label, empty_state, dd_tile, styled_dataframe, cfg_card,
)
from tiger.knowledge import (
    _ds_infer_type, _ds_walk, _ds_collect_records, _ds_parse_payload,
)
from tiger.db import (
    DB, RAW, META,
    is_safe_name, escape_sql_literal,
    run_query, exec_sql,
)


def render() -> None:
    section_label("DATA EXPLORER")
    st.header("Browse, Discover, Model")
    st.caption("Persistent context · dual-pane payload inspector · field-level SQL builder.")

    if "de_api" not in st.session_state:
        st.session_state["de_api"] = "All"
    if "browse_page" not in st.session_state:
        st.session_state["browse_page"] = 0
    if "selected_hash" not in st.session_state:
        st.session_state["selected_hash"] = None

    if "de_table" not in st.session_state:
        st.session_state["de_table"] = "API_RAW_DATA"

    left_ctx, right_work = st.columns([1, 3], gap="large")

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

        current_table = st.session_state["de_table"]
        table_idx = landing_tables.index(current_table) if current_table in landing_tables else 0
        picked_table = st.selectbox(
            "Landing Table",
            landing_tables,
            index=table_idx,
            key="de_table_picker",
        )
        if picked_table != st.session_state["de_table"]:
            st.session_state["de_table"] = picked_table
            st.session_state["de_api"] = "All"
            st.session_state["browse_page"] = 0
            st.session_state["selected_hash"] = None
            st.session_state.pop("ds_schema_df", None)
            st.rerun()
        de_table = st.session_state["de_table"]

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

        if "de_api" not in st.session_state:
            st.session_state["de_api"] = "All"

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
        new_api = "All" if picked_label.startswith("All APIs") else picked_label.rsplit(" (", 1)[0]
        if new_api != st.session_state["de_api"]:
            st.session_state["de_api"] = new_api
            st.session_state["browse_page"] = 0
            st.session_state["selected_hash"] = None
            st.rerun()
        de_api = st.session_state["de_api"]

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

    with right_work:
        if de_api != "All":
            try:
                exp_status = run_query(
                    f"SELECT ic.EXPORT_ENABLED, "
                    f"  (SELECT COUNT(*) FROM {META}.EXPORT_CONFIGS ec "
                    f"   WHERE ec.API_NAME = ic.API_NAME AND ec.ACTIVE_FLAG = TRUE) AS EXPORT_COUNT "
                    f"FROM {META}.INGESTION_CONFIGS ic WHERE ic.API_NAME = ?",
                    params=[de_api]
                )
                if not exp_status.empty:
                    _en = bool(exp_status["EXPORT_ENABLED"].iloc[0])
                    _cnt = int(exp_status["EXPORT_COUNT"].iloc[0] or 0)
                    if _en and _cnt == 0:
                        st.markdown(
                            "<div style='background:rgba(41,181,232,0.06);border:1px solid rgba(41,181,232,0.25);"
                            "border-left:4px solid #29B5E8;border-radius:8px;padding:14px 18px;margin-bottom:1rem;'>"
                            "<div style='font-family:var(--font-display);font-weight:800;color:var(--text-primary);"
                            "font-size:0.9rem;'>📤 Export enabled — ready to configure</div>"
                            "<div style='color:var(--text-secondary);font-size:0.8rem;margin-top:6px;'>"
                            "Run <strong>Schema Discovery</strong>, select your fields in <strong>SQL Builder</strong>, "
                            "then scroll to <strong>Export to S3 / ADLS</strong> to set up the destination. "
                            "Field names auto-populate from the actual API response.</div></div>",
                            unsafe_allow_html=True
                        )
            except Exception:
                pass

        tab_browse, tab_schema, tab_builder = st.tabs([
            "🗂  Browse Payloads", "🔬  Schema Discovery", "🔧  SQL Builder",
        ])

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
                try:
                    summary_q = run_query(
                        f"SELECT COUNT(*) AS TOTAL_RECS, "
                        f"SUM(CASE WHEN STATUS_CODE = 200 THEN 1 ELSE 0 END) AS OK_RECS, "
                        f"ROUND(AVG(LENGTH(PAYLOAD::STRING))/1024, 1) AS AVG_KB, "
                        f"ROUND(MAX(LENGTH(PAYLOAD::STRING))/1024, 1) AS MAX_KB "
                        f"FROM {RAW}.{de_table} {api_where}",
                        params=api_params,
                    )
                    total_recs = int(summary_q["TOTAL_RECS"].iloc[0]) if not pd.isna(summary_q["TOTAL_RECS"].iloc[0]) else 0
                    ok_recs = int(summary_q["OK_RECS"].iloc[0]) if not pd.isna(summary_q["OK_RECS"].iloc[0]) else 0
                    avg_kb = float(summary_q["AVG_KB"].iloc[0]) if not pd.isna(summary_q["AVG_KB"].iloc[0]) else 0.0
                    max_kb = float(summary_q["MAX_KB"].iloc[0]) if not pd.isna(summary_q["MAX_KB"].iloc[0]) else 0.0
                except Exception:
                    total_recs = len(records_df)
                    ok_recs = 0
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
                                payload_size_kb = len(payload_str) / 1024
                                if payload_size_kb > 200:
                                    preview = {
                                        "_chunk_meta": payload_obj.get("_chunk_meta", {}),
                                        "data": f"[{len(payload_obj.get('data', []))} records — download for full payload]",
                                    }
                                    st.json(preview, expanded=2)
                                    st.info(f"Full payload: {len(payload_obj.get('data', []))} records ({payload_size_kb:.0f} KB). Use download button.")
                                elif payload_size_kb > 50:
                                    st.json(payload_obj, expanded=1)
                                else:
                                    st.json(payload_obj, expanded=2)
                            except Exception:
                                st.code(payload_str[:5000] + ("..." if len(payload_str) > 5000 else ""), language="json")

                            st.download_button(
                                "⬇ Download Payload JSON",
                                data=payload_str,
                                file_name=f"{str(sel_h)[:12]}.json",
                                mime="application/json",
                                use_container_width=True,
                                key=f"dl_payload_{sel_h}",
                            )

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
                        total_records_local = 0
                        for _, srow in sample_df.iterrows():
                            payload = _ds_parse_payload(srow["PAYLOAD"])
                            if payload is None:
                                continue
                            records = _ds_collect_records(payload, (ds_records_path or "").strip())
                            for rec in records:
                                total_records_local += 1
                                for path, val in _ds_walk(rec):
                                    t = _ds_infer_type(val)
                                    path_types.setdefault(path, set()).add(t)
                                    path_counts[path] = path_counts.get(path, 0) + 1
                        if total_records_local == 0:
                            st.warning("No records found at the given path.")
                        else:
                            schema_rows = []
                            for path, types in sorted(path_types.items()):
                                preferred = ["TIMESTAMP_TZ", "BOOLEAN", "NUMBER", "FLOAT", "OBJECT", "ARRAY", "STRING"]
                                chosen = next((t for t in preferred if t in types), "VARIANT")
                                coverage_pct = round(100.0 * path_counts[path] / total_records_local, 1)
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
                            st.session_state["ds_schema_total"] = total_records_local
                            quality = {}
                            for path, types in path_types.items():
                                vals_seen = path_counts.get(path, 0)
                                null_rate = 1 - (vals_seen / max(total_records_local, 1))
                                quality[path] = {
                                    "null_rate": round(null_rate * 100, 1),
                                    "type_conflict": len(types) > 1,
                                    "types": sorted(types),
                                }
                            st.session_state["ds_quality"] = quality
                            st.success(
                                f"Discovered **{len(schema_rows)} fields** across "
                                f"**{total_records_local:,} records** from {ds_sample} payloads."
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

        with tab_builder:
            section_label("FLATTENED VIEW GENERATOR")

            has_schema = (
                "ds_schema_df" in st.session_state
                and not st.session_state["ds_schema_df"].empty
                and st.session_state.get("ds_schema_api") == de_api
                and st.session_state.get("ds_schema_table") == de_table
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

                sel_state_key = f"ds_field_sel__{de_api}__{de_table}"
                if sel_state_key not in st.session_state:
                    st.session_state[sel_state_key] = {str(p): True for p in sch_df["PATH"].tolist()}
                for p in sch_df["PATH"].tolist():
                    st.session_state[sel_state_key].setdefault(str(p), True)

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
                                    key=f"field_form_{de_table}_{de_api}_{path}",
                                )

                    apply_clicked = st.form_submit_button(
                        "Apply Selection",
                        type="primary",
                        use_container_width=True,
                    )

                if apply_clicked:
                    for k, v in pending_selection.items():
                        st.session_state[sel_state_key][k] = v
                    st.toast("Field selection applied — SQL regenerated below.", icon="✅")

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

                # ── EXPORT TO S3 / ADLS ──────────────────────────────
                if de_api != "All":
                    st.divider()
                    section_label("EXPORT TO S3 / ADLS")

                    try:
                        existing_exports = run_query(
                            f"SELECT * FROM {META}.EXPORT_CONFIGS WHERE API_NAME = ? AND ACTIVE_FLAG = TRUE",
                            params=[de_api]
                        )
                    except Exception:
                        existing_exports = pd.DataFrame()

                    if not existing_exports.empty:
                        for _, exp_row in existing_exports.iterrows():
                            last_exp = str(exp_row.get("LAST_EXPORT_UTC") or "never")[:16]
                            cfg_card(
                                name=exp_row.get("EXPORT_NAME", "—"),
                                endpoint=f"@{exp_row.get('STAGE_NAME', '')} / {exp_row.get('EXPORT_PATH', '')}",
                                badges=[
                                    {"text": exp_row.get("EXPORT_FORMAT", "PARQUET"), "cls": "accent"},
                                    {"text": exp_row.get("LOAD_MODE", "INCREMENTAL"), "cls": "accent"},
                                    {"text": f"last: {last_exp}", "cls": ""},
                                ],
                                meta=f"path: {exp_row.get('EXPORT_PATH', '')}",
                                status="healthy",
                            )
                            er_a1, er_a2 = st.columns([1, 5])
                            with er_a1:
                                with st.popover("🗑 Remove", use_container_width=True):
                                    st.warning(f"Remove '{exp_row.get('EXPORT_NAME')}'?")
                                    if st.button("Confirm", key=f"de_del_exp_{exp_row.get('EXPORT_ID')}", type="primary"):
                                        exec_sql(f"UPDATE {META}.EXPORT_CONFIGS SET ACTIVE_FLAG = FALSE WHERE EXPORT_ID = ?",
                                                 params=[int(exp_row.get("EXPORT_ID"))])
                                        st.toast("Export removed", icon="🗑")
                                        st.rerun()

                    with st.expander("＋ Add Export Destination", expanded=existing_exports.empty):
                        ed_c1, ed_c2 = st.columns(2)
                        with ed_c1:
                            exp_name = st.text_input("Export Name", value=f"{de_api}_S3_EXPORT", key=f"de_exp_name_{de_api}")
                            try:
                                stages_df = run_query("SHOW STAGES IN DATABASE API_DATA_PIPELINE")
                                stages_df.columns = [c.upper() for c in stages_df.columns]
                                stage_opts = [f"{r['DATABASE_NAME']}.{r['SCHEMA_NAME']}.{r['NAME']}"
                                              for _, r in stages_df.iterrows()] if not stages_df.empty else []
                            except Exception:
                                stage_opts = ["API_DATA_PIPELINE.PUBLIC.STG_S3_EXPORTS"]
                            stage_name = st.selectbox("Target Stage", stage_opts, key=f"de_exp_stage_{de_api}")
                            export_path = st.text_input("Path Prefix", value=f"{de_api.lower().replace('_','-')}/", key=f"de_exp_path_{de_api}")
                        with ed_c2:
                            exp_format = st.selectbox("Format", ["PARQUET", "CSV", "JSON"], key=f"de_exp_fmt_{de_api}")
                            load_mode = st.selectbox("Load Mode", ["INCREMENTAL", "FULL", "SNAPSHOT"], key=f"de_exp_mode_{de_api}")
                            partition_by = st.checkbox("Partition by date", value=True, key=f"de_exp_part_{de_api}")
                            max_file_mb = st.select_slider("Max file size", options=[64, 128, 256, 512, 1024], value=256,
                                                           format_func=lambda x: f"{x} MB", key=f"de_exp_maxfile_{de_api}")

                        flatten_mode = st.radio("Fields to export",
                                                ["All fields (full VARIANT)", "Selected fields (flattened)"],
                                                key=f"de_exp_flatten_{de_api}")
                        exp_flatten_json = None
                        if "Selected fields" in flatten_mode:
                            if selected_fields:
                                st.info(f"✓ Using the **{len(selected_fields)} fields** selected above in Field Selection.")
                                exp_flatten_json = json.dumps([f["PATH"] for f in selected_fields])
                            else:
                                st.warning("No fields selected above. Tick fields in Field Selection first.")

                        if st.button("💾 Save Export Config", type="primary", key=f"de_save_exp_{de_api}",
                                     disabled=not (exp_name and stage_name and export_path)):
                            try:
                                exec_sql(
                                    f"INSERT INTO {META}.EXPORT_CONFIGS "
                                    "(API_NAME, EXPORT_NAME, STAGE_NAME, EXPORT_PATH, EXPORT_FORMAT, "
                                    " LOAD_MODE, PARTITION_BY_DATE, MAX_FILE_SIZE_MB, FLATTEN_FIELDS, RECORDS_PATH, ACTIVE_FLAG) "
                                    "SELECT ?, ?, ?, ?, ?, ?, ?, ?, TRY_PARSE_JSON(?), ?, TRUE",
                                    params=[de_api, exp_name, stage_name, export_path, exp_format,
                                            load_mode, bool(partition_by), max_file_mb, exp_flatten_json,
                                            st.session_state.get("ds_schema_records_path", "data")]
                                )
                                exec_sql(f"UPDATE {META}.INGESTION_CONFIGS SET EXPORT_ENABLED = TRUE WHERE API_NAME = ?",
                                         params=[de_api])
                                st.toast(f"Export config '{exp_name}' saved — runs after each ingestion", icon="📤")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
