from pathlib import Path

ROOT = Path(".")

dirs = [
    "data/ai4i/raw",
    "data/ai4i/clients",
    "data/ai4i/instruction_mixed",

    "edge/perception",
    "edge/llm_decision",

    "federated",
    "cloud",
    "routing",
    "consistency",
    "dashboard",

    "logs",
    "results/tables",
    "results/figures",
    "docs",
]

files = {
    "README.md": """# cloud-edge-ai4i-system

面向云边协同场景的 AI4I 分布式感知、云边协同推理与联邦持续学习原型系统。

## 项目目标

本项目基于 AI4I 设备预测维护数据集，模拟多个非 IID 边缘节点，构建一个包含边缘实时感知、云端大模型复核、云边动态路由、联邦学习聚合、多节点决策一致性和可视化展示的挑战杯比赛原型系统。

## 核心模块

- data：AI4I 数据与客户端划分结果
- edge：边缘节点本地感知与轻量推理
- federated：Flower 联邦学习实验
- cloud：云端 GCM / 大模型复核接口
- routing：云边协同动态路由
- consistency：多边缘节点冲突检测与仲裁
- dashboard：可视化展示页面
- results：实验结果表格和图
- docs：文档、任务分工、实验日志

## 开发规范

所有人不要直接修改 main 分支。每个人在自己的功能分支开发，完成后提交 Pull Request。
""",

    ".gitignore": """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.ipynb_checkpoints/

# Environments
.venv/
venv/
env/
.env
*.env

# IDE
.vscode/
.idea/

# Logs
logs/*.log

# Model weights / checkpoints
models/
checkpoints/
*.pt
*.pth
*.bin
*.safetensors
llm_adapt/outputs/

# Large temporary files
*.zip
*.rar
*.7z

# OS
.DS_Store
Thumbs.db
""",

    "requirements.txt": """pandas
numpy
scikit-learn
matplotlib
tqdm
fastapi
uvicorn
requests
streamlit
flwr
torch
""",

    "docker-compose.yml": """version: "3.9"

services:
  dashboard:
    build: .
    command: streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
    ports:
      - "8501:8501"
""",

    "edge/perception/train_local_model.py": """# 本科生1：训练 AI4I 边缘本地感知模型
# TODO: 读取 data/ai4i/clients/client_i.csv，训练本地分类模型
""",

    "edge/perception/models.py": """# 本科生1：定义边缘感知模型
# TODO: MLP / RandomForest / LightGBM / PyTorch 模型
""",

    "edge/perception/infer_edge.py": """# 本科生1：边缘模型推理接口
# TODO: 输入一条设备状态，输出 fault_prob / risk_level / action
""",

    "edge/llm_decision/call_edge_lora.py": """# 研究生/本科生辅助：调用边缘 Qwen3-0.6B + LoRA
# TODO: 后续接入已经训练好的 LoRA adapter
""",

    "edge/llm_decision/decision_schema.py": """# 统一边缘决策输出格式

def build_decision(fault_label, risk_level, action, confidence, reason):
    return {
        "fault_label": fault_label,
        "risk_level": risk_level,
        "action": action,
        "confidence": confidence,
        "reason": reason,
    }
""",

    "edge/edge_node_service.py": """# 本科生3：边缘节点 FastAPI 服务
# TODO: /predict 接口，接收设备状态并返回边缘判断
""",

    "federated/flower_server.py": """# 本科生2：Flower 联邦学习服务器
# TODO: 启动 FedAvg server
""",

    "federated/flower_client.py": """# 本科生2：Flower 联邦学习客户端
# TODO: 每个 client 读取自己的 AI4I 数据并参与训练
""",

    "federated/fedavg_experiment.py": """# 本科生2：FedAvg 实验入口
# TODO: 运行 AI4I 联邦学习实验并保存结果
""",

    "federated/metrics.py": """# 联邦学习指标统计
# TODO: accuracy / precision / recall / F1 / AUC
""",

    "cloud/gcm_api.py": """# 本科生4：云端 GCM API 调用
# TODO: 封装 Qwen3.5-35B / Qwen3-14B OpenAI-compatible API
""",

    "cloud/cloud_review.py": """# 本科生4：云端复核模块
# TODO: 对边缘低置信度/高风险样本进行云端复核
""",

    "cloud/global_decision.py": """# 云端全局决策模块
# TODO: 汇总边缘与云端结果，输出最终决策
""",

    "routing/router.py": """# 本科生3：云边动态路由
# TODO: 根据风险等级、置信度、网络状态选择 EdgeOnly / CloudOnly / CloudEdge
""",

    "routing/network_simulator.py": """# 本科生3：网络状态模拟器
# TODO: 模拟正常网络、弱网、高延迟、断网
""",

    "routing/policy.py": """# 路由策略
# TODO: 写规则策略，例如低置信度上云、高风险上云、断网本地自治
""",

    "consistency/event_schema.py": """# 本科生5：统一事件对象

def build_event(node_id, timestamp, device_id, risk_level, action, confidence, source):
    return {
        "node_id": node_id,
        "timestamp": timestamp,
        "device_id": device_id,
        "risk_level": risk_level,
        "action": action,
        "confidence": confidence,
        "source": source,
    }
""",

    "consistency/conflict_detector.py": """# 本科生5：冲突检测
# TODO: 检测风险等级不一致、动作建议冲突、重复告警
""",

    "consistency/conflict_resolver.py": """# 本科生5：冲突仲裁
# TODO: 高风险优先、高置信度优先、云端复核优先
""",

    "dashboard/app.py": """# 本科生5：Streamlit 可视化页面

import streamlit as st

st.title("Cloud-Edge AI4I System")
st.write("云边协同分布式感知、推理与决策原型系统")

st.header("系统模块")
st.write("- 边缘实时感知")
st.write("- 云端 GCM 复核")
st.write("- 云边动态路由")
st.write("- Flower 联邦学习")
st.write("- 多节点冲突检测与仲裁")
""",

    "docs/task_assignment.md": """# 本科生任务分工

## 本科生1：AI4I 数据与边缘感知模型
负责 data 与 edge/perception。

## 本科生2：Flower 联邦学习
负责 federated。

## 本科生3：边缘服务与动态路由
负责 edge_node_service 与 routing。

## 本科生4：云端 GCM 复核
负责 cloud。

## 本科生5：冲突一致性与可视化
负责 consistency 与 dashboard。

## 开发规范

每个人使用自己的分支开发，不直接提交 main。
""",

    "docs/experiment_log.md": """# 实验日志

## Day 1

初始化项目仓库，建立云边协同 AI4I 系统目录结构。
""",
}

for d in dirs:
    path = ROOT / d
    path.mkdir(parents=True, exist_ok=True)
    keep = path / ".gitkeep"
    if not any(path.iterdir()):
        keep.write_text("", encoding="utf-8")

for file_path, content in files.items():
    path = ROOT / file_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

print("项目结构创建完成。")