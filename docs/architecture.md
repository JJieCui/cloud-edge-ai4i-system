# 云边智控：面向工业与能源场景的云边协同感知与决策系统

## 系统架构设计

- 版本：v0.1 范围冻结版
- 日期：2026 年 7 月 22 日
- 设计目标：以同一套云边协同控制面承载工业和能源两类场景

## 1. 总体架构

~~~mermaid
flowchart LR
    subgraph S["场景层"]
        I["工业 AI4I 设备节点"]
        E["能源四节点电网"]
    end

    subgraph EDGE["边缘层"]
        P["场景感知插件"]
        M["边缘轻量模型"]
        L["边缘 Qwen / 规则决策"]
        U["置信度与风险校准"]
        F["离线安全策略"]
    end

    subgraph CONTROL["云边协同控制层"]
        N["网络状态监测"]
        R["风险—时延路由器"]
        B["超时、重试与熔断"]
    end

    subgraph CLOUD["云端层"]
        C["GCM 复杂样本复核"]
        G["全局约束与决策"]
        H["困难样本池"]
    end

    subgraph CONSISTENCY["一致性层"]
        D["事件聚合与去重"]
        X["冲突检测"]
        A["安全仲裁"]
    end

    subgraph UPDATE["持续更新与展示"]
        FL["Flower 联邦聚合"]
        V["Streamlit 可视化"]
        O["指标、日志与审计"]
    end

    I --> P
    E --> P
    P --> M --> L --> U
    U --> R
    N --> R
    R -->|EdgeOnly| D
    R -->|EdgeCloud / CloudOnly| B --> C --> G --> D
    R -->|SafeFallback| F --> D
    D --> X --> A
    A --> O
    A --> V
    A --> H
    H --> FL
    FL --> M
~~~

## 2. 架构原则

1. **场景插件化**：工业和能源只替换数据适配、感知模型、动作规则和全局约束。
2. **接口统一**：所有模块使用统一事件与决策对象通信。
3. **边缘优先**：能够在边缘安全完成的任务不上传云端。
4. **高风险复核**：低置信度、高风险和分布外任务优先调用云端。
5. **断网可用**：网络不可用时执行场景相关的安全降级策略。
6. **决策可追溯**：每个最终动作能够追踪到输入、模型、路由原因和仲裁过程。
7. **实验可复现**：网络故障、mock 行为和数据划分使用固定随机种子。

## 3. 运行时处理流程

### 3.1 EdgeOnly 快速路径

1. 接收工业或能源观测。
2. 边缘感知模型输出类别、风险和置信度。
3. 置信度校准器修正概率。
4. 路由器判断任务为低风险、高置信且满足 deadline。
5. 边缘决策进入事件聚合与冲突检测。
6. 仲裁器输出最终动作。
7. 记录端到端时延和决策来源。

### 3.2 EdgeCloud 复核路径

1. 边缘模型完成初判。
2. 路由器检测到低置信、高风险或分布外输入。
3. 只上传特征摘要、边缘判断和必要上下文。
4. 云端 GCM 或复核模型返回结构化意见。
5. 一致性层比较边缘和云端结果。
6. 仲裁器依据安全规则与全局约束生成最终动作。

### 3.3 SafeFallback 弱网路径

1. 路由器检测到断网、超时或 deadline 不足。
2. 工业场景执行保守维护、降载或停机策略。
3. 能源场景执行保持、安全限载或维持稳定区间策略。
4. 本地记录待同步事件。
5. 网络恢复后上传摘要，但不重复执行已经完成的控制动作。

### 3.4 联邦更新路径

1. 每个边缘客户端保留本地训练数据。
2. Flower 下发当前全局模型参数。
3. 客户端执行固定本地 epoch。
4. 客户端仅上传模型更新和样本量。
5. 服务端执行 FedAvg，P1 阶段增加 FedProx。
6. 新模型通过版本检查后按需下发。

## 4. 统一接口对象

### 4.1 Observation

~~~json
{
  "event_id": "evt-uuid",
  "trace_id": "trace-uuid",
  "scene": "industrial",
  "node_id": "industrial-client-1",
  "object_id": "machine-001",
  "timestamp": "2026-07-22T10:00:00+08:00",
  "deadline_ms": 200,
  "payload": {},
  "network": {
    "rtt_ms": 20,
    "packet_loss": 0.0,
    "connected": true
  }
}
~~~

scene 的合法值为 industrial 或 energy。payload 由场景适配器验证。

### 4.2 EdgeDecision

~~~json
{
  "event_id": "evt-uuid",
  "trace_id": "trace-uuid",
  "scene": "industrial",
  "node_id": "industrial-client-1",
  "predicted_label": "machine_failure",
  "risk_level": "high",
  "action": "shutdown",
  "confidence": 0.91,
  "reason": "高风险故障且扭矩异常",
  "model_version": "industrial-edge-v1",
  "inference_ms": 18.5,
  "data_age_ms": 5
}
~~~

### 4.3 RouteDecision

~~~json
{
  "trace_id": "trace-uuid",
  "route": "EdgeCloud",
  "reason_codes": [
    "HIGH_RISK",
    "LOW_CONFIDENCE"
  ],
  "estimated_total_ms": 145,
  "remaining_deadline_ms": 170,
  "policy_version": "router-v1"
}
~~~

route 的合法值为 EdgeOnly、EdgeCloud、CloudOnly、SafeFallback、DeferredReview。

### 4.4 CloudReview

~~~json
{
  "trace_id": "trace-uuid",
  "reviewed_label": "machine_failure",
  "risk_level": "high",
  "action": "shutdown",
  "confidence": 0.95,
  "reason": "云端复核确认高风险故障",
  "model": "qwen3.5-35b-a3b",
  "latency_ms": 120,
  "fallback_used": false
}
~~~

### 4.5 FinalDecision

~~~json
{
  "decision_id": "decision-uuid",
  "trace_id": "trace-uuid",
  "scene": "industrial",
  "final_label": "machine_failure",
  "final_risk_level": "high",
  "final_action": "shutdown",
  "confidence": 0.95,
  "decision_source": "cloud_edge_arbitrated",
  "conflict_detected": false,
  "arbitration_reason": "边缘与云端一致",
  "end_to_end_ms": 158,
  "deadline_met": true
}
~~~

## 5. 动态路由设计

### 5.1 路由输入

- 校准后的边缘置信度。
- 预测熵或分类 margin。
- 业务风险等级。
- 网络 RTT、抖动和丢包率。
- 是否连接云端。
- 边缘和云端队列长度。
- 请求 deadline。
- 预计上传字节数。
- 数据新鲜度。

### 5.2 第一阶段规则

| 条件 | 路径 |
|---|---|
| 断网或预计云端返回超过 deadline | SafeFallback |
| 高置信、低风险、边缘结果通过约束检查 | EdgeOnly |
| 高风险或低置信，且网络满足 deadline | EdgeCloud |
| 边缘模型不可用，且云端可用 | CloudOnly |
| 需要立即响应但允许后续修正 | DeferredReview |

### 5.3 路由效用

路由器的实验目标定义为：

效用 = 决策正确收益 − 时延代价 − 通信代价 − deadline 违约代价 − 错误控制风险

第一阶段使用可解释规则和网格搜索确定参数。只有 P0 完成后，才考虑 LinUCB 或其他学习型路由。

## 6. 一致性设计

### 6.1 冲突类型

- label_conflict：预测类别不同。
- risk_conflict：风险等级不同。
- action_conflict：控制动作不同。
- resource_conflict：多个能源节点请求超过全局容量。
- stale_state_conflict：节点状态已经过期。
- duplicate_event：相同事件重复到达。

### 6.2 工业仲裁规则

- shutdown 的安全等级高于 reduce_load、maintain 和 monitor。
- 低置信度结果不能降低已经确认的高风险动作。
- 数据过期时不得直接解除停机或限载。
- 云端超时不影响边缘安全动作生效。

### 6.3 能源仲裁规则

- 最终动作必须满足供需平衡和容量约束。
- 高风险稳定性事件优先于经济性目标。
- 数据过期节点的资源请求降低优先级或进入安全限额。
- 多节点竞争资源时，按照风险、置信度、数据新鲜度和业务优先级排序。

## 7. 代码目录与模块映射

| 架构模块 | 计划代码位置 | 2026-07-22 状态 |
|---|---|---|
| AI4I 数据与非 IID 划分 | data/ | 已实现主要划分流程 |
| 能源数据适配 | data/energy/ | 未建立 |
| 工业感知模型 | edge/perception/ | TODO |
| 能源感知模型 | edge/energy/ | 未建立 |
| 统一决策模型 | edge/llm_decision/ | 仅有简单结构 |
| 边缘服务 | edge/edge_node_service.py | TODO |
| 网络状态模拟 | routing/network_simulator.py | TODO |
| 静态与动态路由 | routing/policy.py、routing/router.py | TODO |
| 云端复核接口 | cloud/ | 已有雏形，需要确定性和统一 Schema |
| 冲突检测与仲裁 | consistency/ | Schema 简单，核心逻辑 TODO |
| Flower 联邦学习 | federated/ | TODO |
| 可视化 | dashboard/app.py | 仅有占位页面 |
| 结果与日志 | results/、logs/ | 部分目录和示例结果已存在 |

## 8. 部署拓扑

比赛第一阶段采用单机多进程仿真：

- 5 个工业虚拟边缘节点。
- 4 个能源虚拟边缘节点。
- 1 个路由与网络模拟服务。
- 1 个云端复核服务。
- 1 个一致性与全局决策服务。
- 1 个 Flower 服务端。
- 1 个 Streamlit 仪表盘。

所有服务通过 localhost 不同端口或进程内适配器通信。完成 P0 后再考虑 Docker Compose，不以 Kubernetes 为交付前提。

## 9. 可观测性要求

每个请求至少记录：

- trace_id、event_id、scene、node_id。
- 模型版本和路由策略版本。
- 边缘推理时延。
- 网络状态和上传字节数。
- 云端调用时延与是否降级。
- 冲突类型和仲裁理由。
- 最终动作、端到端时延和 deadline 是否满足。

日志用于自动生成指标，不允许手工填写最终实验数字。
