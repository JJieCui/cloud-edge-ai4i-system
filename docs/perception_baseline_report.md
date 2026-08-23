# AI4I Edge Perception Baseline Report

## 1. 实验目的

本实验面向 AI4I 设备预测性维护场景，构建边缘侧本地感知 baseline。实验目标是比较不同分类模型在非 IID 边缘节点数据上的故障识别能力，并为边缘推理接口提供可部署模型。该模块输出的边缘侧感知结果可作为后续云边协同路由、云端复核和可视化展示的基础输入。

## 2. 数据与特征

训练数据来自 `data/ai4i/clients/client_1.csv` 至 `data/ai4i/clients/client_5.csv`，分别表示 5 个非 IID 边缘节点的本地数据。测试数据来自 `data/ai4i/test/global_test.csv`，用于对所有本地模型进行统一评估。

输入特征包括：

- `Type`
- `Air temperature [K]`
- `Process temperature [K]`
- `Rotational speed [rpm]`
- `Torque [Nm]`
- `Tool wear [min]`

标签为 `Machine failure`。该任务是类别不均衡的二分类故障检测任务，其中故障样本占比较低。

## 3. 模块架构

AI4I 边缘感知模块的数据流和文件职责如下：

- `data/read_ai4i.py`：读取和检查 AI4I 原始数据，包括字段、缺失值、重复行和标签分布。
- `data/split_clients.py`：划分非 IID client 数据和统一测试集，生成 `client_1.csv` 至 `client_5.csv` 以及 `global_test.csv`。
- `edge/perception/models.py`：定义模型 Pipeline，包括特征预处理、编码方式和 baseline 模型配置。
- `edge/perception/train_local_model.py`：读取 client 数据，训练和评估 baseline，输出指标表格，并保存 RandomForest Pipeline。
- `edge/perception/plot_baseline_results.py`：读取 baseline 指标表格，生成 Accuracy、Precision、Recall 和 F1 图表。
- `edge/perception/infer_edge.py`：加载已保存的边缘模型，对单条设备状态进行推理。
- `edge/edge_node_service.py`：通过 `/predict` 接口接入边缘推理结果，并保留模型异常时的 mock fallback 机制。

## 4. 模型与训练流程

实验包含三个 baseline 模型：

- `LogisticRegression`：线性分类模型，数值特征使用 `StandardScaler` 标准化，并设置 `class_weight="balanced"`。
- `RandomForest`：树模型 baseline，设置 `class_weight="balanced"`，并保存完整 Pipeline 供边缘推理加载。
- `MLP`：多层感知机 baseline，数值特征使用 `StandardScaler` 标准化，并对少数类训练样本进行上采样。

类别特征 `Type` 使用 `OneHotEncoder` 编码。所有模型均在每个 client 的本地训练数据上单独训练，并在同一个 `global_test.csv` 上测试。该设置用于观察不同非 IID 边缘节点数据对本地模型表现的影响。

## 5. 评价指标

实验使用以下评价指标：

- `Accuracy`：整体预测正确率。
- `Precision`：预测为故障的样本中真实故障样本的比例，用于观察误报控制能力。
- `Recall`：真实故障样本中被模型成功检出的比例，用于观察故障检出能力。
- `F1`：Precision 和 Recall 的调和平均，用于观察二者的综合平衡。

故障检测任务不能只看 Accuracy。由于故障样本比例较低，模型即使大多预测正常也可能得到较高 Accuracy，因此需要结合 Recall 和 F1 分析故障识别能力。

## 6. 实验结果与图表分析

实验指标表格保存在 `results/tables/perception_baseline.csv`。图表文件如下：

- `../results/figures/perception_accuracy_by_model.png`
- `../results/figures/perception_precision_by_model.png`
- `../results/figures/perception_recall_by_model.png`
- `../results/figures/perception_f1_by_model.png`

Accuracy 图用于观察不同 client 上各模型的整体预测正确率。Precision 图用于观察误报控制能力。Recall 图用于观察故障检出能力。F1 图用于观察 Precision 和 Recall 的综合平衡。

根据当前图表结果，可以进行以下谨慎分析：

- `LogisticRegression` 通常 Recall 较高，但 Precision 较低，说明该模型更容易检出故障，但误报更多。
- `RandomForest` 通常 Precision 较高，但 Recall 偏低，说明该模型预测为故障时较可靠，但可能漏掉部分故障。
- `MLP` 在 F1 上相对更均衡，可作为重要 baseline 对比。

由于 5 个 client 的数据分布不同，各指标在不同 client 间存在波动。该现象反映了非 IID 边缘数据对本地模型训练和故障检测表现的影响。

## 7. 边缘推理部署

训练阶段保留多个 baseline，是为了比较不同模型在非 IID client 上的表现。部署阶段需要选择一个默认模型供 `/predict` 接口调用，因此当前暂选 `RandomForest` 作为边缘侧默认部署模型。

选择 `RandomForest` 的原因包括：

- Pipeline 保存和加载简单。
- 推理流程稳定。
- Precision 较高，适合作为第一版边缘推理默认模型。

`LogisticRegression` 和 `MLP` 仍然作为 baseline 对比模型保留在实验结果中，用于后续模型对比和系统展示。

## 8. 结论

本实验完成了从 AI4I 数据读取、非 IID client 划分、本地 baseline 训练、指标表格输出、图表生成，到边缘推理接口调用的完整流程。实验结果为云边协同路由、云端复核和 Dashboard 展示提供了边缘侧感知结果基础。
