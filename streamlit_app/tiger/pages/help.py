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
"""


def render() -> None:
    """Render the Pipeline Overview help page."""
    section_label("HELP")
    st.header("Pipeline Overview")
    st.caption("End-to-end data flow — every component you manage in this app.")

    with st.container(border=True):
        st.graphviz_chart(_PIPELINE_DOT)

    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    section_label("LEGEND")
    leg_c1, leg_c2, leg_c3, leg_c4 = st.columns(4)
    with leg_c1:
        st.markdown(
            "<div class='cfg-card healthy'>"
            "<div class='name' style='font-size:0.85rem;'>Framework Data</div>"
            "<div class='meta'>configs · log · raw · views</div></div>",
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
            "<div class='meta'>USP_UNIVERSAL_INGESTOR</div></div>",
            unsafe_allow_html=True,
        )
    with leg_c4:
        st.markdown(
            "<div class='cfg-card' style='border-left-color:#c084fc;'>"
            "<div class='name' style='font-size:0.85rem;'>Generated</div>"
            "<div class='meta'>flattened views</div></div>",
            unsafe_allow_html=True,
        )
