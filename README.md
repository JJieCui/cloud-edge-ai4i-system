# 云边智控：面向工业与能源场景的云边协同感知与决策系统

面向工业设备预测性维护与分布式能源稳定控制的云边协同感知、推理、决策和联邦持续学习原型系统。

## 项目目标

本项目包含两个应用场景：工业场景使用 AI4I 设备预测性维护数据模拟 5 个非 IID 边缘节点；能源场景使用分布式电网稳定性数据模拟多节点局部感知与全局控制。系统包含边缘实时感知、边缘轻量决策、云端大模型复核、风险—时延动态路由、联邦学习聚合、多节点决策一致性和可视化展示。

## 核心模块

- data：工业与能源数据、客户端划分结果
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

## 使用 VS Code 打开

推荐直接打开根目录下的 cloud-edge-ai4i-system.code-workspace。首次打开时，VS Code
会提示安装项目推荐扩展。

1. 在 VS Code 中选择“文件 → 打开工作区”，选择 cloud-edge-ai4i-system.code-workspace。
2. 使用 Python 扩展创建或选择项目根目录下的 .venv 虚拟环境。
3. 在终端中复制 .env.example 为 .env，并填写本地 GCM 配置；不要提交 .env。
4. 运行任务“环境：安装项目依赖”。
5. 在“运行和调试”中选择“系统：云端 API + 仪表盘”。

项目已提供：

- .vscode/extensions.json：推荐扩展。
- .vscode/settings.json：Python、Ruff、测试、Git 和文件编码设置。
- .vscode/tasks.json：依赖安装、数据检查、测试和服务启动任务。
- .vscode/launch.json：FastAPI、Streamlit 和当前文件调试配置。

当前系统若未安装 Python 3.11，需要先安装 Python，再创建 .venv。

## AI4I 边缘感知模块

### 模块功能

AI4I 边缘感知模块负责工业设备预测性维护场景中的边缘侧故障检测流程，包括 AI4I 原始数据检查、非 IID client 划分、本地 baseline 训练、结果图表生成、单条设备状态推理，以及边缘服务 `/predict` 接口接入。

模块主要文件包括：

- `data/read_ai4i.py`：读取和检查 AI4I 原始数据。
- `data/split_clients.py`：划分 5 个非 IID client，并生成统一测试集 `global_test.csv`。
- `edge/perception/models.py`：定义 LogisticRegression、RandomForest、MLP baseline Pipeline。
- `edge/perception/train_local_model.py`：训练 5 个 client 的本地 baseline，输出 `perception_baseline.csv`，并保存 RandomForest Pipeline。
- `edge/perception/plot_baseline_results.py`：生成 Accuracy、Precision、Recall、F1 指标图表。
- `edge/perception/infer_edge.py`：加载边缘模型，对单条设备状态进行推理。
- `edge/edge_node_service.py`：通过 `/predict` 接口优先调用边缘感知模型，失败时 fallback 到 mock 推理。

### 运行顺序

在项目根目录依次运行：

```bash
python data/read_ai4i.py
python data/split_clients.py
python edge/perception/train_local_model.py
python edge/perception/plot_baseline_results.py
python edge/perception/infer_edge.py
uvicorn edge.edge_node_service:app --reload
```

### 输出结果

- `results/tables/client_distribution.csv`：5 个非 IID client 的样本数、故障率和关键特征统计。
- `data/ai4i/clients/client_1.csv` 至 `data/ai4i/clients/client_5.csv`：边缘节点本地训练数据。
- `data/ai4i/test/global_test.csv`：统一公共测试集。
- `results/tables/perception_baseline.csv`：LogisticRegression、RandomForest、MLP 在 5 个 client 上的 Accuracy、Precision、Recall、F1。
- `results/models/perception/client_i_randomforest.joblib`：可被 `infer_edge.py` 加载的 RandomForest Pipeline。
- `results/figures/perception_accuracy_by_model.png`
- `results/figures/perception_precision_by_model.png`
- `results/figures/perception_recall_by_model.png`
- `results/figures/perception_f1_by_model.png`

### 推理与服务

`edge/perception/infer_edge.py` 默认加载 `results/models/perception/client_1_randomforest.joblib`，输入单条设备状态后输出故障标签、故障概率、风险等级、建议动作和置信度。

启动 `uvicorn edge.edge_node_service:app --reload` 后，可以通过 FastAPI 的 `/predict` 接口调用边缘感知结果。在依赖已正确安装且服务成功启动的前提下，若 `/predict` 推理阶段出现模型文件缺失或模型推理异常，接口会 fallback 到 `mock_inference`，避免单次模型异常中断边缘推理流程。
