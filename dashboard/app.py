import os
import sys
import streamlit as st
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consistency.event_schema import build_event
from consistency.conflict_detector import ConflictDetector
from consistency.conflict_resolver import ConflictResolver, RESOLUTION_STRATEGIES

_ZH = {
    "page_title": "云边协同 AI4I 系统",
    "sidebar_title": "云边协同",
    "sidebar_subtitle": "AI4I 系统",
    "system_online": "系统在线",
    "node_status": "节点状态",
    "online": "在线",
    "standby": "待机",
    "network_sim": "网络模拟",
    "network_mode": "网络模式",
    "stable": "稳定",
    "degraded": "降级",
    "high_latency": "高延迟",
    "disconnected": "断开",
    "gcm_mode": "云端 GCM 模式",
    "module_info": "模块：一致性 + 仪表盘",
    "branch_info": "分支：feat/dashboard-consistency",
    "owner_info": "负责人：本科生五",
    "main_title": "云边分布式 AI 系统",
    "main_subtitle": "工业预测性维护 // AI4I 数据集",
    "footer": "云边协同 AI4I 系统 v1.0",
    "data_input": "数据输入",
    "data_input_sub": "设备状态参数",
    "sensor_readings": "传感器读数",
    "air_temp": "空气温度 [K]",
    "process_temp": "过程温度 [K]",
    "rot_speed": "转速 [RPM]",
    "torque": "扭矩 [Nm]",
    "tool_wear": "刀具磨损 [min]",
    "product_type": "产品类型",
    "control_panel": "控制面板",
    "target_node": "目标节点",
    "execute": "▶  执行",
    "reset": "↺  重置",
    "raw_json": "原始 JSON",
    "edge_perception": "边缘感知",
    "edge_perception_sub": "本地故障检测",
    "fault_type": "故障类型",
    "risk_level": "风险等级",
    "action": "动作建议",
    "confidence": "置信度",
    "awaiting": "等待中",
    "inference_details": "推理详情",
    "pending_integration": "待集成",
    "dynamic_routing": "动态路由",
    "dynamic_routing_sub": "边云协同调度",
    "route_decision": "路由决策",
    "network": "网络状态",
    "e2e_latency": "端到端时延",
    "pending": "待处理",
    "tbd": "待定",
    "routing_modes": "路由模式",
    "edge_only": "仅边缘",
    "cloud_only": "仅云端",
    "cloud_edge": "边云协同",
    "weaknet_auto": "弱网自适应",
    "edge_only_desc": "仅本地推理，不上云",
    "cloud_only_desc": "全部样本上传云端 GCM",
    "cloud_edge_desc": "低置信度/高风险样本上云",
    "weaknet_auto_desc": "弱网下边缘自主决策",
    "cloud_gcm_review": "云端 GCM 复核",
    "cloud_gcm_review_sub": "全局能力模型",
    "call_count": "调用次数",
    "avg_latency": "平均时延",
    "consistency": "一致性",
    "latest_review": "最新复核",
    "conflict_resolution": "冲突解决",
    "conflict_resolution_sub": "多节点一致性",
    "conflicts": "冲突数量",
    "conflict_rate": "冲突比例",
    "resolve_rate": "解决成功率",
    "arbitration_strategy": "仲裁策略",
    "highest_risk_first": "高风险优先",
    "highest_confidence_first": "高置信度优先",
    "cloud_first": "云端决策优先",
    "duplicate_window": "重复告警窗口（秒）",
    "run_detection": "运行检测",
    "conflict_details": "冲突详情",
    "resolution_log": "仲裁日志",
    "final_decision": "最终决策",
    "node": "节点",
    "resolution_strategy": "解决策略说明",
    "detection": "检测类型",
    "duplicate_alerts": "重复告警",
    "risk_level_mismatch": "风险等级不一致",
    "action_conflict": "动作建议冲突",
    "arbitration": "仲裁规则",
    "highest_risk_priority": "风险等级最高优先",
    "highest_confidence_priority": "置信度最高优先",
    "cloud_decision_priority": "云端决策优先",
    "federated_learning": "联邦学习",
    "federated_learning_sub": "Flower FedAvg",
    "round": "训练轮次",
    "global_acc": "全局准确率",
    "clients": "客户端数",
    "training_metrics": "训练指标",
    "logs_records": "日志与记录",
    "logs_records_sub": "系统审计追溯",
    "routing_log": "路由日志",
    "cloud_review_log": "云端复核日志",
    "conflict_summary": "冲突汇总",
    "no_routing_log": "暂无路由日志数据",
    "no_cloud_review": "暂无云端复核数据",
    "no_conflict_data": "暂无冲突汇总数据",
    "conflict_type": "冲突类型",
    "severity": "严重程度",
    "device_id": "设备ID",
    "description": "描述",
    "low": "低",
    "medium": "中",
    "high": "高",
    "critical": "严重",
}


def t(key):
    return _ZH.get(key, key)


st.set_page_config(
    page_title="云边协同 AI4I 系统",
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
    font-family: 'JetBrains Mono', 'Consolas', 'Microsoft YaHei', monospace;
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
    font-family: 'Orbitron', 'Microsoft YaHei', sans-serif !important;
    color: #e0f7ff !important;
    text-shadow: 0 0 10px rgba(0, 200, 255, 0.5);
    letter-spacing: 1px;
}

header[data-testid="stHeader"] {
    background: rgba(8, 12, 22, 0.85) !important;
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(0, 200, 255, 0.15) !important;
    height: 50px !important;
}

div[data-testid="stStatusWidget"] {
    display: none !important;
}

#loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: #0a0e1a;
    z-index: 999999;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 20px;
    animation: hideOverlay 0.8s ease-in-out forwards;
    animation-delay: 1.5s;
}

@keyframes hideOverlay {
    0% {
        opacity: 1;
        pointer-events: all;
    }
    100% {
        opacity: 0;
        pointer-events: none;
    }
}

.loading-spinner {
    width: 50px;
    height: 50px;
    border: 2px solid rgba(0, 200, 255, 0.2);
    border-top-color: #00d4ff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    box-shadow: 0 0 20px rgba(0, 200, 255, 0.3);
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.loading-text {
    color: #00d4ff;
    font-size: 0.9rem;
    letter-spacing: 3px;
    text-shadow: 0 0 10px rgba(0, 200, 255, 0.5);
}

div[data-testid="stToolbar"] {
    gap: 8px !important;
}

div[data-testid="stToolbar"] button {
    background: rgba(0, 100, 200, 0.1) !important;
    border: 1px solid rgba(0, 200, 255, 0.2) !important;
    border-radius: 4px !important;
    color: #6b8cae !important;
}

div[data-testid="stToolbar"] button:hover {
    background: rgba(0, 100, 200, 0.2) !important;
    border-color: rgba(0, 200, 255, 0.4) !important;
    color: #00d4ff !important;
}

div[data-testid="stToolbar"] button[kind="tertiary"] svg {
    color: #6b8cae !important;
}

h1 {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
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
    margin-top: 2rem !important;
    margin-bottom: 1rem !important;
}

h4 {
    color: #a0d8ef !important;
    font-size: 0.95rem !important;
    margin-top: 1rem !important;
    margin-bottom: 0.75rem !important;
}

div[data-testid="block-container"] {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 100% !important;
}

div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    gap: 0.75rem;
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
    font-family: 'Orbitron', 'Microsoft YaHei', sans-serif !important;
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
    font-size: 0.85rem !important;
    letter-spacing: 0.5px;
    min-height: 42px !important;
    padding: 8px 20px !important;
    border-radius: 6px 6px 0 0 !important;
    margin-right: 4px !important;
}

div[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(0, 100, 200, 0.25) !important;
    border-color: #00d4ff !important;
    border-bottom-color: transparent !important;
    color: #00d4ff !important;
    font-weight: 600 !important;
}

div[data-testid="stTabs"] [data-testid="stTabPanel"] {
    border: 1px solid rgba(0, 200, 255, 0.2) !important;
    border-radius: 0 6px 6px 6px !important;
    padding: 1rem !important;
    margin-top: -1px !important;
    background: rgba(10, 14, 26, 0.6) !important;
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
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px; padding: 10px 0;">
            <div style="font-size: 1.3rem; font-weight: 700; font-family: 'Orbitron', 'Microsoft YaHei', sans-serif; color: #e0f7ff; text-shadow: 0 0 10px rgba(0, 200, 255, 0.5); letter-spacing: 1px;">
                ⚡ {t("sidebar_title")}
            </div>
            <p style="color: #00d4ff; font-size: 0.7rem; letter-spacing: 3px; margin: 8px 0 12px 0;">{t("sidebar_subtitle")}</p>
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                <span class="status-indicator status-online"></span>
                <span style="color: #00ff88; font-size: 0.8rem; font-weight: 500;">{t("system_online")}</span>
            </div>
        </div>
        <hr style="border-color: rgba(0, 200, 255, 0.15); margin: 0 0 20px 0;">
        """, unsafe_allow_html=True)

        st.markdown(f"### 📡 {t('node_status')}")
        for i in range(5):
            status_color = "#00ff88" if i < 5 else "#ffaa00"
            status_text = t("online") if i < 5 else t("standby")
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 0.75rem;">
                <span style="color: #6b8cae;">EDGE_NODE_{i}</span>
                <span style="color: {status_color}; font-weight: 600;">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown(f"### 🌐 {t('network_sim')}")
        network_status = st.selectbox(
            t("network_mode"),
            ["normal", "weak", "high_latency", "offline"],
            index=0,
            label_visibility="collapsed",
            format_func=lambda x: {
                "normal": t("stable"),
                "weak": t("degraded"),
                "high_latency": t("high_latency"),
                "offline": t("disconnected"),
            }.get(x, x),
        )
        st.session_state.network_status = network_status

        status_map = {
            "normal": ("#00ff88", t("stable")),
            "weak": ("#ffaa00", t("degraded")),
            "high_latency": ("#ff6644", t("high_latency")),
            "offline": ("#ff4466", t("disconnected")),
        }
        color, text = status_map[network_status]
        st.markdown(f"""
        <div style="text-align: center; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; margin-top: 8px;">
            <span style="color: {color}; font-size: 0.8rem; font-weight: 600; letter-spacing: 1px;">{text}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown(f"### ⚙️ {t('gcm_mode')}")
        st.selectbox(
            t("gcm_mode"),
            ["mock", "real"],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("---")
        st.caption(t("module_info"))
        st.caption(t("branch_info"))
        st.caption(t("owner_info"))


def section_header(title, subtitle=""):
    st.markdown(f"""
    <div style="position: relative; margin: 2.5rem 0 1.25rem 0; padding-left: 12px; border-left: 3px solid #00d4ff;">
        <h2 style="margin: 0;">{title}</h2>
        {f'<p style="color: #4a6580; font-size: 0.75rem; margin: 8px 0 0 0; letter-spacing: 1px;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def data_input_section():
    section_header(t("data_input"), t("data_input_sub"))

    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        st.markdown(f"#### {t('sensor_readings')}")

        row1_col1, row1_col2, row1_col3 = st.columns(3)
        with row1_col1:
            air_temp = st.slider(t("air_temp"), 295.0, 310.0, 300.0, 0.1)
        with row1_col2:
            process_temp = st.slider(t("process_temp"), 305.0, 315.0, 308.0, 0.1)
        with row1_col3:
            rotational_speed = st.slider(t("rot_speed"), 1100.0, 2900.0, 1500.0, 10.0)

        row2_col1, row2_col2, row2_col3 = st.columns(3)
        with row2_col1:
            torque = st.slider(t("torque"), 0.0, 80.0, 40.0, 0.5)
        with row2_col2:
            tool_wear = st.slider(t("tool_wear"), 0.0, 250.0, 100.0, 1.0)
        with row2_col3:
            st.selectbox(t("product_type"), ["L", "M", "H"], index=0)

    with col2:
        st.markdown(f"#### {t('control_panel')}")

        st.selectbox(t("target_node"), [f"edge_node_{i}" for i in range(5)], index=0)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.button(t("execute"), type="primary", width="stretch")
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        st.button(t("reset"), width="stretch")

        with st.expander(f" {t('raw_json')} ", expanded=False):
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
    section_header(t("edge_perception"), t("edge_perception_sub"))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label=t("fault_type"), value="—", delta=t("awaiting"))
    with col2:
        st.metric(label=t("risk_level"), value="—", delta=t("awaiting"))
    with col3:
        st.metric(label=t("action"), value="—", delta=t("awaiting"))
    with col4:
        st.metric(label=t("confidence"), value="—", delta=t("awaiting"))

    with st.expander(f" {t('inference_details')} "):
        st.info("Module: edge/perception/infer_edge.py")
        st.code(f"Output: fault_label, risk_level, action, confidence\nStatus: {t('pending_integration')}")


def routing_section():
    section_header(t("dynamic_routing"), t("dynamic_routing_sub"))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label=t("route_decision"), value="—", delta=t("pending"))
    with col2:
        status_display = st.session_state.network_status.upper().replace("_", " ")
        status_map_cn = {
            "NORMAL": t("stable"),
            "WEAK": t("degraded"),
            "HIGH LATENCY": t("high_latency"),
            "OFFLINE": t("disconnected"),
        }
        st.metric(label=t("network"), value=status_map_cn.get(status_display, status_display))
    with col3:
        st.metric(label=t("e2e_latency"), value="—", delta=t("tbd"))

    with st.expander(f" {t('routing_modes')} "):
        st.markdown(f"""
        | Mode | Description |
        |------|-------------|
        | **{t('edge_only')}** | {t('edge_only_desc')} |
        | **{t('cloud_only')}** | {t('cloud_only_desc')} |
        | **{t('cloud_edge')}** | {t('cloud_edge_desc')} |
        | **{t('weaknet_auto')}** | {t('weaknet_auto_desc')} |
        """)
        st.info(f"Module: routing/router.py | Status: {t('pending_integration')}")


def cloud_review_section():
    section_header(t("cloud_gcm_review"), t("cloud_gcm_review_sub"))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label=t("call_count"), value="0")
    with col2:
        st.metric(label=t("avg_latency"), value="—")
    with col3:
        st.metric(label=t("consistency"), value="—")

    with st.expander(f" {t('latest_review')} "):
        st.info("Module: cloud/cloud_review.py")
        st.code(f"Output: gcm_fault_label, gcm_risk_level, gcm_action\nStatus: {t('pending_integration')}")


def generate_demo_events():
    return [
        build_event(
            node_id="edge_node_0",
            device_id="device_001",
            fault_label="Heat Dissipation Failure",
            risk_level="high",
            action="shutdown",
            confidence=0.85,
            source="edge",
        ),
        build_event(
            node_id="edge_node_1",
            device_id="device_001",
            fault_label="Heat Dissipation Failure",
            risk_level="medium",
            action="maintain",
            confidence=0.65,
            source="edge",
        ),
        build_event(
            node_id="cloud_gcm",
            device_id="device_001",
            fault_label="Heat Dissipation Failure",
            risk_level="critical",
            action="shutdown",
            confidence=0.95,
            source="cloud",
        ),
        build_event(
            node_id="edge_node_2",
            device_id="device_002",
            fault_label="Normal",
            risk_level="low",
            action="monitor",
            confidence=0.92,
            source="edge",
        ),
        build_event(
            node_id="edge_node_3",
            device_id="device_002",
            fault_label="Normal",
            risk_level="low",
            action="monitor",
            confidence=0.88,
            source="edge",
        ),
        build_event(
            node_id="edge_node_4",
            device_id="device_003",
            fault_label="Power Failure",
            risk_level="critical",
            action="replace",
            confidence=0.95,
            source="cloud",
        ),
        build_event(
            node_id="edge_node_0",
            device_id="device_003",
            fault_label="Power Failure",
            risk_level="high",
            action="shutdown",
            confidence=0.78,
            source="edge",
        ),
    ]


def consistency_section():
    section_header(t("conflict_resolution"), t("conflict_resolution_sub"))

    if "detect_result" not in st.session_state:
        st.session_state.detect_result = None
    if "resolve_result" not in st.session_state:
        st.session_state.resolve_result = None

    col1, col2, col3 = st.columns(3)

    detect_result = st.session_state.detect_result
    resolve_result = st.session_state.resolve_result

    conflict_count = detect_result["conflict_count"] if detect_result else 0
    conflict_rate = detect_result["conflict_rate"] if detect_result else 0.0
    resolve_rate = resolve_result["success_rate"] if resolve_result else 0.0

    with col1:
        st.metric(label=t("conflicts"), value=conflict_count)
    with col2:
        st.metric(label=t("conflict_rate"), value=f"{conflict_rate:.2%}")
    with col3:
        st.metric(label=t("resolve_rate"), value=f"{resolve_rate:.2%}")

    st.markdown("---")

    col_a, col_b, col_c = st.columns([2, 2, 1])

    with col_a:
        strategy = st.selectbox(
            t("arbitration_strategy"),
            RESOLUTION_STRATEGIES,
            index=0,
            format_func=lambda x: {
                "highest_risk_first": t("highest_risk_first"),
                "highest_confidence_first": t("highest_confidence_first"),
                "cloud_first": t("cloud_first"),
            }.get(x, x),
        )

    with col_b:
        time_window = st.slider(
            t("duplicate_window"),
            min_value=10,
            max_value=300,
            value=120,
            step=10,
        )

    with col_c:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button(t("run_detection"), type="primary", width="stretch"):
            events = generate_demo_events()
            detector = ConflictDetector(duplicate_time_window_s=time_window)
            st.session_state.detect_result = detector.detect(events)
            resolver = ConflictResolver(strategy=strategy)
            st.session_state.resolve_result = resolver.resolve(
                events, st.session_state.detect_result["conflict_details"]
            )
            st.rerun()

    if detect_result and detect_result["conflict_details"]:
        st.markdown(f"### {t('conflict_details')}")
        details_df = pd.DataFrame(detect_result["conflict_details"])
        display_df = details_df[[t("conflict_type"), t("severity"), t("device_id"), t("description")]].copy()
        display_df.columns = [t("conflict_type"), t("severity"), t("device_id"), t("description")]
        st.dataframe(display_df, width="stretch", height=250, hide_index=True)

    if resolve_result and resolve_result.get("resolution_log"):
        st.markdown(f"### {t('resolution_log')}")
        log_df = pd.DataFrame(resolve_result["resolution_log"])
        st.dataframe(log_df, width="stretch", height=200, hide_index=True)

    if resolve_result and resolve_result.get("final_decision"):
        fd = resolve_result["final_decision"]
        st.markdown(f"### {t('final_decision')}")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            st.metric(label=t("node"), value=fd.get("node_id", "—"))
        with col_d2:
            st.metric(label=t("risk_level"), value=fd.get("risk_level", "—"))
        with col_d3:
            st.metric(label=t("action"), value=fd.get("action", "—"))
        with col_d4:
            st.metric(label=t("confidence"), value=f"{fd.get('confidence', 0):.2f}")

    with st.expander(f" {t('resolution_strategy')} "):
        st.markdown(f"""
        **{t('detection')}:**
        - {t('duplicate_alerts')}
        - {t('risk_level_mismatch')}
        - {t('action_conflict')}

        **{t('arbitration')}:**
        - {t('highest_risk_priority')}
        - {t('highest_confidence_priority')}
        - {t('cloud_decision_priority')}
        """)
        st.info("Module: consistency/conflict_detector.py + conflict_resolver.py")


def federated_section():
    section_header(t("federated_learning"), t("federated_learning_sub"))

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label=t("round"), value="0")
    with col2:
        st.metric(label=t("global_acc"), value="—")
    with col3:
        st.metric(label=t("clients"), value="5")

    with st.expander(f" {t('training_metrics')} "):
        st.info("Module: federated/flower_server.py + flower_client.py")
        chart_data = pd.DataFrame({"accuracy": [], "loss": [], "f1_score": []})
        st.line_chart(chart_data, height=200, width="stretch")


def logs_and_results_section():
    section_header(t("logs_records"), t("logs_records_sub"))

    tab1, tab2, tab3 = st.tabs([t("routing_log"), t("cloud_review_log"), t("conflict_summary")])

    with tab1:
        log_path = LOGS_DIR / "routing_log.csv"
        if log_path.exists():
            st.dataframe(pd.read_csv(log_path), width="stretch", height=300)
        else:
            st.info(t("no_routing_log"))

    with tab2:
        review_path = RESULTS_TABLES_DIR / "cloud_review_log.csv"
        if review_path.exists():
            st.dataframe(pd.read_csv(review_path), width="stretch", height=300)
        else:
            st.info(t("no_cloud_review"))

    with tab3:
        conflict_path = RESULTS_TABLES_DIR / "conflict_summary.csv"
        if conflict_path.exists():
            st.dataframe(pd.read_csv(conflict_path), width="stretch", height=300)
        else:
            st.info(t("no_conflict_data"))


def main():
    st.markdown(TECH_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div id="loading-overlay">
        <div class="loading-spinner"></div>
        <div class="loading-text">SYSTEM LOADING</div>
    </div>
    """, unsafe_allow_html=True)

    init_session_state()
    sidebar()

    st.markdown(f"""
    <div style="position: relative; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(0, 200, 255, 0.3);">
        <h1>{t("main_title")}</h1>
        <p style="color: #6b8cae; font-size: 0.8rem; margin: 8px 0 0 0; letter-spacing: 2px;">
            {t("main_subtitle")}
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

    st.markdown(f"""
    <div style="text-align: center; margin-top: 2rem; padding: 1rem; border-top: 1px solid rgba(0, 200, 255, 0.1);">
        <p style="color: #4a6580; font-size: 0.7rem; letter-spacing: 2px;">
            ═══ {t("footer")} ═══
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
