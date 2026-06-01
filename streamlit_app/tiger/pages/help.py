"""Tiger SnowSync — Pipeline Overview help page."""
import streamlit as st

from tiger.helpers import section_label


_PIPELINE_DOT = r"""
digraph G {
  rankdir=LR;
  bgcolor="transparent";
  node  [style="filled,rounded", shape=box, fontname="Inter", fontsize=10,
         color="#1f1f1f", fillcolor="#111111", fontcolor="#fafafa", margin="0.18,0.10"];
  edge  [color="#3a3a3a", fontcolor="#a1a1aa", fontname="JetBrains Mono", fontsize=9, penwidth=1.2];

  cfg     [label="INGESTION_CONFIGS\n(metadata · filters · pagination\n· cursor · body · watermark)",  fillcolor="#0f1f17", color="#00DC82", fontcolor="#00DC82"];
  eai     [label="EAI + Secrets\n(network rules · OAuth · API keys)", fillcolor="#1a1408", color="#f59e0b", fontcolor="#f59e0b"];
  proc    [label="USP_UNIVERSAL_INGESTOR\n(GET/POST · retry · paginate\n· PAGE/OFFSET/CURSOR/LINK\n· dedup · watermark)", fillcolor="#0f0f1f", color="#58a6ff", fontcolor="#58a6ff"];
  api     [label="External REST API\n(any JSON endpoint)",  fillcolor="#0a0a0a", color="#a1a1aa"];
  raw     [label="RAW_LANDING.<TABLE>\n(chunked JSON payloads)", fillcolor="#0f1f17", color="#00DC82", fontcolor="#00DC82"];
  log     [label="INGESTION_RESPONSE_LOG\n(per-attempt audit)", fillcolor="#0f1f17", color="#00DC82", fontcolor="#00DC82"];
  summary [label="INGESTION_RUN_SUMMARY\n(one row per run)", fillcolor="#0f1f17", color="#00DC82", fontcolor="#00DC82"];
  views   [label="V_LATEST_RUNS\nV_ACTIVE_API_STATUS\nV_ERROR_SUMMARY_7D", fillcolor="#1c0a1a", color="#c084fc", fontcolor="#c084fc"];
  flat    [label="V_<API> (flattened)\nData Explorer", fillcolor="#1c0a1a", color="#c084fc", fontcolor="#c084fc"];
  task    [label="TASK_INGEST_<API>\n(Snowflake Task\n· CRON/interval)", fillcolor="#0f0f1f", color="#58a6ff", fontcolor="#58a6ff"];

  cfg  -> proc [label="reads config"];
  eai  -> proc [label="grants access"];
  proc -> api  [label="HTTP GET/POST"];
  api  -> proc [label="JSON response", style="dashed"];
  proc -> raw  [label="dedup + chunk + write"];
  proc -> log  [label="per-attempt log"];
  proc -> summary [label="run summary"];
  proc -> cfg  [label="watermark update", style="dashed", color="#58a6ff"];
  raw  -> flat [label="LATERAL FLATTEN"];
  log  -> views [label="aggregated"];
  summary -> views [label="latest run"];
  task -> proc [label="CALL (scheduled)"];
}
"""


def render() -> None:
    section_label("HELP")
    st.header("Pipeline Overview")
    st.caption("End-to-end data flow — every component you manage in this app.")

    with st.container(border=True):
        st.graphviz_chart(_PIPELINE_DOT)

    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    section_label("LEGEND")
    leg_c1, leg_c2, leg_c3, leg_c4, leg_c5 = st.columns(5)
    with leg_c1:
        st.markdown(
            "<div class='cfg-card healthy'>"
            "<div class='name' style='font-size:0.85rem;'>Framework Data</div>"
            "<div class='meta'>configs · log · summary · raw</div></div>",
            unsafe_allow_html=True,
        )
    with leg_c2:
        st.markdown(
            "<div class='cfg-card warning'>"
            "<div class='name' style='font-size:0.85rem;'>Security</div>"
            "<div class='meta'>EAI · secrets · network rules</div></div>",
            unsafe_allow_html=True,
        )
    with leg_c3:
        st.markdown(
            "<div class='cfg-card' style='border-left-color:#58a6ff;'>"
            "<div class='name' style='font-size:0.85rem;'>Engine</div>"
            "<div class='meta'>USP_UNIVERSAL_INGESTOR · Tasks</div></div>",
            unsafe_allow_html=True,
        )
    with leg_c4:
        st.markdown(
            "<div class='cfg-card' style='border-left-color:#c084fc;'>"
            "<div class='name' style='font-size:0.85rem;'>Views</div>"
            "<div class='meta'>flattened · status · errors</div></div>",
            unsafe_allow_html=True,
        )
    with leg_c5:
        st.markdown(
            "<div class='cfg-card' style='border-left-color:#a1a1aa;'>"
            "<div class='name' style='font-size:0.85rem;'>External</div>"
            "<div class='meta'>REST APIs (any JSON)</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)
    section_label("CAPABILITIES")
    cap_c1, cap_c2, cap_c3 = st.columns(3)
    with cap_c1:
        st.markdown("""
        **Pagination**
        - `PAGE` — ?page=1,2,3
        - `OFFSET` — ?offset=0,100,200
        - `CURSOR` — next_token based
        - `LINK` — follows Link header (GitHub/GitLab)
        - `has_more` / `total_pages` termination
        - `MAX_PAGES` safety ceiling
        """)
    with cap_c2:
        st.markdown("""
        **Authentication**
        - `NONE` — public APIs
        - `API_KEY` — header-based key
        - `OAUTH2_BASIC` — client credentials
        - `OAUTH2_INTEGRATION` — Snowflake-managed OAuth

        **Resilience**
        - Configurable retries + delay
        - `Retry-After` header for 429
        - Fast-fail on non-retryable 4xx
        """)
    with cap_c3:
        st.markdown("""
        **Data Strategy**
        - Configurable `RECORDS_PATH`
        - `FILTER_PARAMS` (static query filters)
        - `REQUEST_BODY_JSON` (POST queries)
        - Incremental watermark sync
        - Content-hash deduplication
        - Auto-create landing tables
        - Chunked writes (2500 records/chunk)
        """)
