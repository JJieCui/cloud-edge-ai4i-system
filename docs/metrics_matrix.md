# 云边智控：面向工业与能源场景的云边协同感知与决策系统

## 赛题指标与实验矩阵

- 版本：v0.1 指标冻结版
- 日期：2026 年 7 月 22 日
- 原则：先冻结定义，再运行实验；报告中的每个数字必须能追溯到原始日志

## 1. 基线系统

| 编号 | 基线 | 定义 | 作用 |
|---|---|---|---|
| B1 | CloudOnly | 原始输入或必要数据全部上传云端处理 | 集中式基线，衡量云端精度、时延和通信压力 |
| B2 | EdgeOnly | 所有任务仅使用边缘模型，不调用云端 | 测量边缘实时性、离线可用性和精度上限 |
| B3 | StaticEdgeCloud | 按固定置信度与风险阈值选择是否上云 | 传统级联基线 |
| B4 | AdaptiveEdgeCloud | 综合置信度、风险、网络和 deadline 动态路由 | 推荐方案 |

## 2. 网络实验条件

| 编号 | 网络状态 | 建议参数 | 用途 |
|---|---|---|---|
| N1 | normal | RTT 20ms，丢包率 0%，云端可用 | 正常性能 |
| N2 | weak | RTT 100ms，丢包率 1%，轻微抖动 | 一般弱网 |
| N3 | degraded | RTT 300ms，丢包率 5%，明显抖动 | 严重弱网 |
| N4 | offline | 云端不可达 | 边缘自治 |
| N5 | cloud_overload | 云端额外排队或处理延迟 | 非平稳负载 |
| N6 | node_failure | 单个边缘节点不可用或返回过期状态 | 稳定性与一致性 |

网络模拟必须使用固定随机种子。最终至少完成 N1—N4，N5—N6 作为稳定性增强实验。

## 3. 赛题硬指标矩阵

| 赛题要求 | 指标定义 | 计算方法 | 对照基线 | 数据来源 | 目标 |
|---|---|---|---|---|---|
| 边缘轻量大模型能力保持 | Capability Retention | 边缘量化模型任务得分 ÷ 参考全量模型同任务得分 ×100% | 未量化同源模型，同时补充云端教师结果 | 固定数学、代码、自然语言测试集 | 80%—90% 或以上 |
| TTFT 改进 | TTFT Reduction |（基线 TTFT−方案 TTFT）÷基线 TTFT×100% | CloudOnly 或未量化模型，必须注明 | 请求级性能日志 | ≥75% |
| 边缘内存 | Peak Memory | 单次推理过程中进程峰值 RSS 或显存峰值 | BF16、量化模型分别记录 | 系统监控日志 | ≤1.5GB |
| 弱网基本业务保持 | Basic Function Retention | 弱网下在 deadline 内返回合法安全决策的请求数 ÷请求总数 | N1 正常网络 | N2、N3、N4 请求日志 | ≥90% |
| 双场景端到端时延 | Mean E2E Latency | 从观测进入系统到最终决策产生的平均时间 | B1—B4 全部比较 | trace 日志 | 每场景及总体均 <200ms |
| 决策冲突比例 | Final Conflict Rate | 正常工作负载下未解决冲突窗口数 ÷关联任务窗口总数 | 无仲裁或简单仲裁 | 一致性日志 | ≤5% |
| 冲突解决成功率 | Resolution Success Rate | 成功产生满足安全和资源约束结果的冲突数 ÷检测到的冲突总数 | 无仲裁 | 故障注入日志 | ≥90% |

### 3.1 口径补充

- 如果系统先返回边缘即时决策、随后异步云端复核，必须分别报告 initial_response_ms 和 final_review_ms。
- 赛题 0.2 秒指标按最终同步决策计算；异步复核不能冒充最终端到端时延。
- 能力保持率必须注明参考模型、模型精度、测试集版本、提示词和评分脚本。
- JSON 合法率只属于接口可靠性，不能代替准确率或能力保持率。
- 弱网功能成功必须同时满足：响应合法、动作安全、未超过该任务 deadline。

## 4. 感知与决策效果指标

| 指标 | 公式或说明 | 工业场景 | 能源场景 |
|---|---|---|---|
| Accuracy | 正确预测数 ÷样本总数 | 辅助指标 | 稳定性分类指标 |
| Precision | TP ÷（TP+FP） | 故障告警准确性 | 不稳定告警准确性 |
| Recall | TP ÷（TP+FN） | 核心指标，避免漏报故障 | 核心指标，避免漏报不稳定 |
| F1 | Precision 与 Recall 调和平均 | 核心指标 | 核心指标 |
| ROC-AUC | 不同阈值下分类排序能力 | 核心指标 | 核心指标 |
| PR-AUC | 类别不平衡下的查准查全表现 | 核心指标 | 可选 |
| Action Accuracy | 最终动作与标注或规则最优动作一致比例 | 维护动作 | 控制动作 |
| Constraint Satisfaction | 满足安全和资源约束的最终动作比例 | 安全规则 | 供需与容量约束 |
| Task Utility | 正确收益减去误动作成本 | 可选综合指标 | 推荐综合指标 |

工业数据类别不平衡，模型选择不能只依据 Accuracy，应优先比较 Recall、F1、PR-AUC 和安全误动作代价。

## 5. 置信度质量指标

| 指标 | 计算方法 | 目的 |
|---|---|---|
| Brier Score | 预测概率与真实标签平方误差均值 | 评估概率准确性 |
| ECE | 各概率分箱置信度与真实准确率差异的加权平均 | 评估校准程度 |
| Reliability Diagram | 置信度分箱与实际准确率曲线 | 可视化校准 |
| Selective Accuracy | 只处理高置信任务时的准确率 | 验证边缘快速路径 |
| Cloud Escalation Recall | 应当上云的高风险或错误边缘任务中实际上云的比例 | 验证路由安全性 |

路由器必须使用校准后的置信度，不能直接使用未经验证的模型 softmax 概率。

## 6. 实时性指标

| 指标 | 起止点 | 统计方式 |
|---|---|---|
| Edge Inference | 边缘模型输入到 EdgeDecision | mean、P50、P95、P99 |
| Routing Latency | RouteState 完成到 RouteDecision | mean、P95 |
| Network Latency | 云端请求发出到首字节或响应返回 | RTT、mean、P95 |
| Cloud Review | 云端收到请求到 CloudReview | mean、P95、P99 |
| Arbitration | 冲突集合输入到 FinalDecision | mean、P95 |
| End-to-End | Observation 接收到 FinalDecision | mean、P50、P95、P99 |
| TTFT | 请求发出到大模型第一个有效 token | mean、P95 |

除赛题要求的平均时延外，报告必须增加 P95，避免平均值掩盖少量严重超时。

## 7. 资源与通信效率指标

| 指标 | 计算方法 | 对照 |
|---|---|---|
| Upload Bytes | 所有请求实际上传字节总和 | CloudOnly |
| Traffic Reduction | 1−方案上传字节 ÷ CloudOnly 上传字节 | CloudOnly |
| Cloud Call Rate | 云端调用次数 ÷任务总数 | B1—B4 |
| Cloud Load Reduction | 1−方案云端处理任务数 ÷ CloudOnly 任务数 | CloudOnly |
| Edge CPU Usage | 推理期间平均与峰值 CPU | 各边缘模型 |
| Edge Peak Memory | 进程峰值 RSS 或显存峰值 | BF16 与量化模型 |
| Tokens per Second | 生成 token 数 ÷生成阶段耗时 | 不同推理后端 |

## 8. 稳定性指标

| 指标 | 计算方法 | 目标或说明 |
|---|---|---|
| Request Success Rate | 成功响应请求数 ÷总请求数 | 越高越好 |
| Deadline Meet Rate | deadline 内完成的请求数 ÷总请求数 | 重点指标 |
| Basic Function Retention | 弱网下合法且安全的及时决策比例 | ≥90% |
| Fallback Success Rate | 云端不可用时本地成功决策数 ÷需降级请求数 | 越高越好 |
| Recovery Success Rate | 网络恢复后成功同步且未重复执行的事件比例 | 越高越好 |
| Availability | 服务可用时间 ÷实验总时间 | 报告正常与故障条件 |
| Performance Jitter | 多轮实验时延或性能的波动范围 | 越小越稳定 |

## 9. 一致性指标

| 指标 | 计算方法 | 数据集 |
|---|---|---|
| Raw Conflict Rate | 仲裁前冲突窗口数 ÷关联任务窗口总数 | 正常与故障注入分别统计 |
| Final Conflict Rate | 仲裁后未解决冲突窗口数 ÷关联任务窗口总数 | 正常工作负载目标 ≤5% |
| Resolution Success Rate | 成功解决冲突数 ÷检测到冲突数 | 故障注入目标 ≥90% |
| False Escalation Rate | 无需升级但被升级为高风险动作的比例 | 工业和能源 |
| Unsafe Downgrade Rate | 高风险动作被错误降低安全等级的比例 | 目标为 0 |
| Duplicate Execution Rate | 重复事件导致重复控制的比例 | 目标为 0 |
| Constraint Violation Rate | 最终动作违反安全或资源约束的比例 | 目标为 0 |

正常工作负载用于证明冲突比例满足要求；故障注入工作负载用于产生足够多冲突并检验解决能力，两者不得混为一个数字。

## 10. 联邦学习指标

| 指标 | 说明 |
|---|---|
| Global F1/AUC | 每轮全局模型在公共测试集上的表现 |
| Worst Client F1 | 最差客户端性能，反映公平性 |
| Mean Client F1 | 所有客户端本地测试性能均值 |
| Client Std | 客户端性能标准差 |
| Convergence Round | 达到目标性能所需轮次 |
| Communication Bytes | 各轮模型更新通信量 |
| Local-to-Global Gain | 全局模型相对 Local Only 的提升 |

最少比较 Local Only、Centralized、FedAvg。P1 阶段增加 FedProx。FedAvg-LoRA 不作为 P0。

## 11. 完整实验矩阵

### 11.1 P0 矩阵

- 场景：industrial、energy。
- 路由：B1、B2、B3、B4。
- 网络：N1、N2、N3、N4。
- 重复次数：每组至少 3 次。

总组合数：

2 个场景 × 4 种路由 × 4 种网络 × 3 次重复 = 96 次实验。

### 11.2 稳定性增强矩阵

- 在 B4 下增加 N5 云端过载。
- 在 B4 下增加 N6 单节点故障。
- 工业和能源各运行不少于 100 个故障注入事件。

### 11.3 消融实验

| 编号 | 移除模块 | 验证问题 |
|---|---|---|
| A1 | 无置信度校准 | 校准是否提升路由可靠性 |
| A2 | 无网络感知 | 网络特征是否降低超时 |
| A3 | 无风险约束 | 风险权重是否减少危险误判 |
| A4 | 无冲突仲裁 | 仲裁是否降低最终冲突和约束违反 |

## 12. 统一日志字段

每条请求必须记录以下字段：

- run_id。
- repeat_id。
- trace_id。
- event_id。
- scene。
- node_id。
- baseline。
- network_profile。
- model_version。
- policy_version。
- ground_truth。
- edge_prediction。
- edge_confidence_raw。
- edge_confidence_calibrated。
- edge_action。
- edge_inference_ms。
- route。
- route_reason。
- upload_bytes。
- cloud_called。
- cloud_prediction。
- cloud_action。
- cloud_latency_ms。
- conflict_detected。
- conflict_type。
- final_prediction。
- final_action。
- final_confidence。
- end_to_end_ms。
- deadline_ms。
- deadline_met。
- fallback_used。
- success。

## 13. 结果文件约定

| 文件 | 内容 |
|---|---|
| results/tables/model_baselines.csv | 工业和能源模型基线 |
| results/tables/routing_experiments.csv | 96 组核心实验汇总 |
| results/tables/network_stability.csv | 弱网和断网结果 |
| results/tables/conflict_metrics.csv | 冲突与仲裁结果 |
| results/tables/federated_metrics.csv | 联邦每轮和客户端指标 |
| results/tables/llm_benchmark.csv | 边缘 LLM 能力、TTFT、内存 |
| results/raw_logs/requests.jsonl | 请求级原始日志 |
| results/figures/ | 报告使用的可复现图表 |

结果表只能由实验脚本生成，不允许手工填写核心指标。
