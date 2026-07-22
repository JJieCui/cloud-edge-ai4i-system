# 实验日志

## 历史记录

已初始化云边协同 AI4I 系统目录结构，并完成 AI4I 数据划分与部分云端接口雏形。

## 2026-07-22：范围与指标冻结

### 今日目标

围绕正式项目名称“云边智控：面向工业与能源场景的云边协同感知与决策系统”，完成比赛范围、总体架构、指标定义和后续验收口径冻结。

### 已完成

1. 固定工业和能源两个应用场景，不再增加第三场景。
2. 工业场景使用 AI4I 预测性维护数据和现有 5 客户端非 IID 划分。
3. 能源场景优先使用 UCI 四节点电网稳定性数据，模拟一个发电节点和三个消费节点。
4. 固定系统主链路：边缘感知、结构化决策、动态路由、云端复核、冲突仲裁、联邦更新和可视化。
5. 将功能划分为 P0、P1、P2，并设置阶段止损规则。
6. 固定 CloudOnly、EdgeOnly、StaticEdgeCloud、AdaptiveEdgeCloud 四种基线。
7. 固定正常、弱网、高延迟和断网四类核心网络实验。
8. 明确能力保持率、TTFT、峰值内存、弱网业务保持率、端到端时延、冲突率和解决成功率的测量方法。
9. 建立统一日志字段和结果文件命名约定。

### 今日输出

- docs/project_scope.md
- docs/architecture.md
- docs/metrics_matrix.md
- docs/云边智控_学习与研发计划.md

### 现有资产

- data/ai4i/raw/ai4i2020.csv
- data/ai4i/clients/client_1.csv 至 client_5.csv
- data/ai4i/test/global_test.csv
- results/tables/client_distribution.csv
- cloud/ 下的 GCM、复核和全局决策代码雏形
- 已训练的 5 个 Local-LoRA 及已有测试结论

### 主要风险

1. 工业边缘模型、能源场景、动态路由、网络模拟、冲突仲裁和 Flower 仍未实现。
2. 当前目录存在 .git 文件夹但不是可用的 Git 仓库，版本管理状态需要确认。
3. docker-compose.yml 使用 build 配置，但当前没有 Dockerfile。
4. requirements.txt 尚未固定依赖版本。
5. 现有 GCM mock 包含随机行为，不能直接用于最终实验。

### 决策

- 当前不启动 FedAvg-LoRA 和 GCM 个性化聚合。
- JSON 合法率作为接口可靠性指标，不能代替决策能力指标。
- 先完成双场景小模型和统一接口，再接入边缘 Qwen 与真实 GCM。
- 报告数字必须由实验脚本和请求日志自动生成。

### 下一步

2026 年 7 月 23 日完成统一 Observation、EdgeDecision、RouteDecision、CloudReview 和 FinalDecision 数据模型，以及对应的 Schema 校验测试。
