import os
import sys
import streamlit as st
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Cloud-Edge AI4I System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOGS_DIR = Path("logs")
RESULTS_TABLES_DIR = Path("results/tables")
RESULTS_FIGURES_DIR = Path("results/figures")


TECH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Orbitron:wght@400;500;600;700;800;900&display=swap');

* {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.stApp {
    background: #0a0e1a;
    background-image:
        linear-gradient(rgba(0, 200, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 200, 255, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
}

.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(ellipse at top, rgba(0, 150, 255, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at bottom right, rgba(0, 255, 200, 0.05) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1321 0%, #0a0e1a 100%);
    border-right: 1px solid rgba(0, 200, 255, 0.15);
    box-shadow: 4px 0 20px rgba(0, 150, 255, 0.05);
}

section[data-testid="stSidebar"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #00d4ff, #00ffcc, transparent);
    animation: scanLine 3s ease-in-out infinite;
}

@keyframes scanLine {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
}

h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    color: #e0f7ff !important;
    text-shadow: 0 0 10px rgba(0, 200, 255, 0.5);
    letter-spacing: 1px;
}

h1 {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    border-bottom: 1px solid rgba(0, 200, 255, 0.3);
    padding-bottom: 0.5rem;
    position: relative;
}

h1::after {
    content: '● LIVE';
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.7rem;
    color: #00ff88;
    text-shadow: 0 0 8px #00ff88;
    animation: blink 1.5s ease-in-out infinite;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

h2 {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    padding-left: 12px;
    border-left: 3px solid #00d4ff;
    margin-top: 1.5rem !important;
}

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(13, 19, 33, 0.9) 0%, rgba(10, 14, 26, 0.9) 100%);
    border: 1px solid rgba(0, 200, 255, 0.2);
    border-radius: 6px;
    padding: 12px 16px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}

div[data-testid="stMetric"]:hover {
    border-color: rgba(0, 200, 255, 0.5);
    box-shadow: 0 0 20px rgba(0, 150, 255, 0.15);
    transform: translateY(-2px);
}

div[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00d4ff, transparent);
    opacity: 0.5;
}

div[data-testid="stMetricValue"] {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #00d4ff !important;
    text-shadow: 0 0 15px rgba(0, 200, 255, 0.6);
}

div[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    color: #6b8cae !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}

div[data-testid="stMetricDelta"] {
    font-size: 0.7rem !important;
}

.stButton > button {
    background: linear-gradient(135deg, rgba(0, 100, 200, 0.2) 0%, rgba(0, 150, 255, 0.1) 100%) !important;
    border: 1px solid rgba(0, 200, 255, 0.4) !important;
    color: #00d4ff !important;
    border-radius: 4px !important;
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    transition: all 0.3s ease !important;
    text-transform: uppercase !important;
    font-size: 0.8rem !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0, 150, 255, 0.3) 0%, rgba(0, 200, 255, 0.2) 100%) !important;
    border-color: #00d4ff !important;
    box-shadow: 0 0 20px rgba(0, 150, 255, 0.4) !important;
    color: #ffffff !important;
}

.stButton > button:active {
    transform: scale(0.98);
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0066aa 0%, #0099cc 100%) !important;
    border-color: #00d4ff !important;
    color: #ffffff !important;
    box-shadow: 0 0 15px rgba(0, 150, 255, 0.4);
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #0077bb 0%, #00aadd 100%) !important;
    box-shadow: 0 0 25px rgba(0, 200, 255, 0.6);
}

div[data-baseweb="slider"] > div > div > div {
    background: linear-gradient(90deg, #00d4ff, #00ffcc) !important;
}

div[data-baseweb="slider"] > div > div > div > div {
    background: #00d4ff !important;
    box-shadow: 0 0 10px #00d4ff !important;
}

.stSlider > div > label {
    color: #6b8cae !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

div[data-testid="stSelectbox"] > div > div {
    background: rgba(13, 19, 33, 0.8) !important;
    border: 1px solid rgba(0, 200, 255, 0.2) !important;
    color: #e0f7ff !important;
    border-radius: 4px !important;
}

div[data-testid="stSelectbox"] label {
    color: #6b8cae !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.streamlit-expanderHeader {
    background: rgba(13, 19, 33, 0.6) !important;
    border: 1px solid rgba(0, 200, 255, 0.15) !important;
    border-radius: 4px !important;
    color: #00d4ff !important;
    font-size: 0.85rem !important;
}

.streamlit-expanderContent {
    background: rgba(10, 14, 26, 0.8) !important;
    border: 1px solid rgba(0, 200, 255, 0.1) !important;
    border-top: none !important;
    border-radius: 0 0 4px 4px !important;
}

div[data-testid="stTabs"] [data-testid="stTab"] {
    background: rgba(13, 19, 33, 0.6) !important;
    border: 1px solid rgba(0, 200, 255, 0.15) !important;
    color: #6b8cae !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.5px;
}

div[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(0, 100, 200, 0.2) !important;
    border-color: #00d4ff !important;
    color: #00d4ff !important;
    border-bottom: 2px solid #00d4ff !important;
}

.stDataFrame {
    border: 1px solid rgba(0, 200, 255, 0.2) !important;
    border-radius: 4px !important;
}

.stInfo {
    background: rgba(0, 100, 200, 0.1) !important;
    border: 1px solid rgba(0, 200, 255, 0.3) !important;
    border-left: 4px solid #00d4ff !important;
    color: #8ab4d8 !important;
    border-radius: 4px !important;
    font-size: 0.85rem !important;
}

.stCodeBlock {
    background: rgba(5, 8, 15, 0.9) !important;
    border: 1px solid rgba(0, 200, 255, 0.15) !important;
    border-radius: 4px !important;
}

.stCodeBlock pre {
    color: #00ffcc !important;
    font-size: 0.8rem !important;
}

hr {
    border-color: rgba(0, 200, 255, 0.1) !important;
    margin: 1rem 0 !important;
}

div[data-testid="stSidebar"] h1 {
    font-size: 1rem !important;
    border-bottom: none;
    text-align: center;
}

div[data-testid="stSidebar"] h1::after {
    display: none;
}

div[data-testid="stSidebar"] .stMarkdown p {
    color: #6b8cae !important;
    font-size: 0.8rem !important;
}

div[data-testid="stSidebar"] .stCaption {
    color: #4a6580 !important;
    font-size: 0.7rem !important;
}

div[data-testid="stJson"] {
    background: rgba(5, 8, 15, 0.8) !important;
    border: 1px solid rgba(0, 200, 255, 0.15) !important;
    border-radius: 4px !important;
}

div[role="progressbar"] {
    color: #00d4ff !important;
}

div[data-testid="stCaptionContainer"] {
    color: #4a6580 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.5px;
}

.stMarkdown p {
    color: #8ab4d8 !important;
    line-height: 1.7;
}

.stMarkdown strong {
    color: #00d4ff !important;
    font-weight: 600;
}

::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: #0a0e1a;
}

::-webkit-scrollbar-thumb {
    background: rgba(0, 150, 255, 0.3);
    border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 200, 255, 0.5);
}

div[data-testid="stSidebarUserContent"] {
    padding-top: 1.5rem;
}

.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
    animation: pulse 2s ease-in-out infinite;
}

.status-online {
    background: #00ff88;
    box-shadow: 0 0 10px #00ff88;
}

.status-warning {
    background: #ffaa00;
    box-shadow: 0 0 10px #ffaa00;
}

.status-error {
    background: #ff4466;
    box-shadow: 0 0 10px #ff4466;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
}

.data-grid-corner {
    background: linear-gradient(135deg, #0d1321 0%, #0a0e1a 100%);
    position: relative;
}

.corner-deco-tl, .corner-deco-tr, .corner-deco-bl, .corner-deco-br {
    position: absolute;
    width: 15px;
    height: 15px;
    border-color: #00d4ff;
    border-style: solid;
    opacity: 0.6;
}

.corner-deco-tl { top: 0; left: 0; border-width: 2px 0 0 2px; }
.corner-deco-tr { top: 0; right: 0; border-width: 2px 2px 0 0; }
.corner-deco-bl { bottom: 0; left: 0; border-width: 0 0 2px 2px; }
.corner-deco-br { bottom: 0; right: 0; border-width: 0 2px 2px 0; }

.grid-container {
    position: relative;
    padding: 20px;
    background: rgba(10, 14, 26, 0.6);
    border: 1px solid rgba(0, 200, 255, 0.1);
    border-radius: 4px;
}
</style>
"""


def init_session_state():
    if "current_sample" not in st.session_state:
        st.session_state.current_sample = None
    if "edge_result" not in st.session_state:
        st.session_state.edge_result = None
    if "cloud_result" not in st.session_state:
        st.session_state.cloud_result = None
    if "routing_decision" not in st.session_state:
        st.session_state.routing_decision = None
    if "conflict_result" not in st.session_state:
        st.session_state.conflict_result = None
    if "network_status" not in st.session_state:
        st.session_state.network_status = "normal"
    if "system_uptime" not in st.session_state:
        st.session_state.system_uptime = 0


def sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-size: 1.2rem; margin: 0;">⚡ CLOUD-EDGE</h1>
            <p style="color: #00d4ff; font-size: 0.7rem; letter-spacing: 3px; margin: 5px 0 0 0;">AI4I SYSTEM</p>
            <div style="margin-top: 10px;">
                <span class="status-indicator status-online"></span>
                <span style="color: #00ff88; font-size: 0.75rem;">SYSTEM ONLINE</span>
            </div>
        </div>
        <hr style="border-color: rgba(0, 200, 255, 0.15);">
        """, unsafe_allow_html=True)

        st.markdown("### 📡 NODE STATUS")
        for i in range(5):
            status_color = "#00ff88" if i < 5 else "#ffaa00"
            status_text = "ONLINE" if i < 5 else "STANDBY"
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 0.75rem;">
                <span style="color: #6b8cae;">EDGE_NODE_{i}</span>
                <span style="color: {status_color}; font-weight: 600;">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### 🌐 NETWORK SIM")
        network_status = st.selectbox(
            "Network Mode",
            ["normal", "weak", "high_latency", "offline"],
            index=0,
            label_visibility="collapsed",
        )
        st.session_state.network_status = network_status

        status_map = {
            "normal": ("#00ff88", "STABLE"),
            "weak": ("#ffaa00", "DEGRADED"),
            "high_latency": ("#ff6644", "HIGH LATENCY"),
            "offline": ("#ff4466", "DISCONNECTED"),
        }
        color, text = status_map[network_status]
        st.markdown(f"""
        <div style="text-align: center; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; margin-top: 8px;">
            <span style="color: {color}; font-size: 0.8rem; font-weight: 600; letter-spacing: 1px;">{text}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### ⚙️ GCM MODE")
        st.selectbox(
            "GCM Mode",
            ["mock", "real"],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("---")
        st.caption("MODULE: CONSISTENCY + DASHBOARD")
        st.caption("BRANCH: feat/dashboard-consistency")
        st.caption("OWNER: UNDERGRAD 5")


def section_header(title, subtitle=""):
    st.markdown(f"""
    <div style="position: relative; margin: 1.5rem 0 1rem 0;">
        <h2 style="margin: 0;">{title}</h2>
        {f'<p style="color: #4a6580; font-size: 0.7rem; margin: 4px 0 0 15px; letter-spacing: 1px;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def data_input_section():
    section_header("DATA INPUT", "DEVICE STATUS PARAMETERS")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("#### SENSOR READINGS")

        row1_col1, row1_col2, row1_col3 = st.columns(3)
        with row1_col1:
            air_temp = st.slider("AIR TEMP [K]", 295.0, 310.0, 300.0, 0.1)
        with row1_col2:
            process_temp = st.slider("PROCESS TEMP [K]", 305.0, 315.0, 308.0, 0.1)
        with row1_col3:
            rotational_speed = st.slider("ROT SPEED [RPM]", 1100.0, 2900.0, 1500.0, 10.0)

        row2_col1, row2_col2, row2_col3 = st.columns(3)
        with row2_col1:
            torque = st.slider("TORQUE [NM]", 0.0, 80.0, 40.0, 0.5)
        with row2_col2:
            tool_wear = st.slider("TOOL WEAR [MIN]", 0.0, 250.0, 100.0, 1.0)
        with row2_col3:
            st.selectbox("PRODUCT TYPE", ["L", "M", "H"], index=0)

    with col2:
        st.markdown("#### CONTROL PANEL")

        st.selectbox("TARGET NODE", [f"edge_node_{i}" for i in range(5)], index=0)

        st.markdown("<br>", unsafe_allow_html=True)
        st.button("▶  EXECUTE", type="primary", width="stretch")
        st.button("↺  RESET", width="stretch")

        with st.expander(" RAW JSON ", expanded=False):
            st.json(
                {
                    "air_temp": air_temp,
                    "process_temp": process_temp,
                    "rot_speed": rotational_speed,
                    "torque": torque,
                    "tool_wear": tool_wear,
                }
            )


def edge_inference_section():
    section_header("EDGE PERCEPTION", "LOCAL FAULT DETECTION")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="FAULT TYPE", value="—", delta="AWAITING")
    with col2:
        st.metric(label="RISK LEVEL", value="—", delta="AWAITING")
    with col3:
        st.metric(label="ACTION", value="—", delta="AWAITING")
    with col4:
        st.metric(label="CONFIDENCE", value="—", delta="AWAITING")

    with st.expander(" INFERENCE DETAILS "):
        st.info("Module: edge/perception/infer_edge.py")
        st.code("Output: fault_label, risk_level, action, confidence\nStatus: PENDING INTEGRATION")


def routing_section():
    section_header("DYNAMIC ROUTING", "EDGE-CLOUD ORCHESTRATION")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="ROUTE DECISION", value="—", delta="PENDING")
    with col2:
        status_display = st.session_state.network_status.upper().replace("_", " ")
        st.metric(label="NETWORK", value=status_display)
    with col3:
        st.metric(label="E2E LATENCY", value="—", delta="TBD")

    with st.expander(" ROUTING MODES "):
        st.markdown("""
        | Mode | Description |
        |------|-------------|
        | **EdgeOnly** | Local inference only, no cloud offload |
        | **CloudOnly** | All samples sent to cloud GCM |
        | **CloudEdge** | Low confidence / high risk offloaded |
        | **WeakNet Auto** | Edge autonomy on poor connectivity |
        """)
        st.info("Module: routing/router.py | Status: PENDING INTEGRATION")


def cloud_review_section():
    section_header("CLOUD GCM REVIEW", "GLOBAL CAPABILITY MODEL")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="CALL COUNT", value="0")
    with col2:
        st.metric(label="AVG LATENCY", value="—")
    with col3:
        st.metric(label="CONSISTENCY", value="—")

    with st.expander(" LATEST REVIEW "):
        st.info("Module: cloud/cloud_review.py")
        st.code("Output: gcm_fault_label, gcm_risk_level, gcm_action\nStatus: PENDING INTEGRATION")


def consistency_section():
    section_header("CONFLICT RESOLUTION", "MULTI-NODE CONSISTENCY")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="CONFLICTS", value="0")
    with col2:
        st.metric(label="CONFLICT RATE", value="0.00%")
    with col3:
        st.metric(label="RESOLVE RATE", value="—")

    with st.expander(" RESOLUTION STRATEGY "):
        st.markdown("""
        **Detection:**
        - Duplicate alerts
        - Risk level mismatch
        - Action recommendation conflict

        **Arbitration:**
        - Highest risk priority
        - Highest confidence priority
        - Cloud decision priority
        """)
        st.info("Module: consistency/conflict_detector.py + conflict_resolver.py")


def federated_section():
    section_header("FEDERATED LEARNING", "FLOWER FEDAVG")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="ROUND", value="0")
    with col2:
        st.metric(label="GLOBAL ACC", value="—")
    with col3:
        st.metric(label="CLIENTS", value="5")

    with st.expander(" TRAINING METRICS "):
        st.info("Module: federated/flower_server.py + flower_client.py")
        chart_data = pd.DataFrame({"accuracy": [], "loss": [], "f1_score": []})
        st.line_chart(chart_data, height=200, width="stretch")


def logs_and_results_section():
    section_header("LOGS & RECORDS", "SYSTEM AUDIT TRAIL")

    tab1, tab2, tab3 = st.tabs(["ROUTING LOG", "CLOUD REVIEW LOG", "CONFLICT SUMMARY"])

    with tab1:
        log_path = LOGS_DIR / "routing_log.csv"
        if log_path.exists():
            st.dataframe(pd.read_csv(log_path), width="stretch", height=300)
        else:
            st.info("No routing log data available")

    with tab2:
        review_path = RESULTS_TABLES_DIR / "cloud_review_log.csv"
        if review_path.exists():
            st.dataframe(pd.read_csv(review_path), width="stretch", height=300)
        else:
            st.info("No cloud review data available")

    with tab3:
        conflict_path = RESULTS_TABLES_DIR / "conflict_summary.csv"
        if conflict_path.exists():
            st.dataframe(pd.read_csv(conflict_path), width="stretch", height=300)
        else:
            st.info("No conflict summary data available")


def main():
    st.markdown(TECH_CSS, unsafe_allow_html=True)
    init_session_state()
    sidebar()

    st.markdown("""
    <div style="position: relative;">
        <h1>CLOUD-EDGE DISTRIBUTED AI SYSTEM</h1>
        <p style="color: #6b8cae; font-size: 0.8rem; margin-top: -10px; letter-spacing: 2px;">
            INDUSTRIAL PREDICTIVE MAINTENANCE // AI4I DATASET
        </p>
    </div>
    """, unsafe_allow_html=True)

    data_input_section()
    edge_inference_section()
    routing_section()
    cloud_review_section()
    consistency_section()
    federated_section()
    logs_and_results_section()

    st.markdown("""
    <div style="text-align: center; margin-top: 2rem; padding: 1rem; border-top: 1px solid rgba(0, 200, 255, 0.1);">
        <p style="color: #4a6580; font-size: 0.7rem; letter-spacing: 2px;">
            ═══ CLOUD-EDGE AI4I SYSTEM v1.0 ═══
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
