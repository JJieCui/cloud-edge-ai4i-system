import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split


DATA_PATH = Path("data/ai4i/raw/ai4i2020.csv")
CLIENT_DIR = Path("data/ai4i/clients")
TEST_PATH = Path("data/ai4i/test/global_test.csv")
RESULT_PATH = Path("results/tables/client_distribution.csv")

RANDOM_STATE = 42
TEST_SIZE = 0.20
CLIENT_NAMES = [f"client_{i}" for i in range(1, 6)]

REQUIRED_COLUMNS = [
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
]

FEATURE_COLUMNS = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

FAULT_COLUMNS = ["TWF", "HDF", "PWF", "OSF", "RNF"]

# 针对“产品类型 + 是否故障”分别设置五个客户端的分配权重。
# 正常样本突出 Type 分布差异；故障样本向后几个客户端适度倾斜，
# 以同时形成 feature skew（特征偏移）和 label skew（标签偏移）。
WEIGHT_TABLE = {
    ("L", 0): [0.32, 0.26, 0.20, 0.14, 0.08],
    ("M", 0): [0.08, 0.14, 0.20, 0.26, 0.32],
    ("H", 0): [0.05, 0.10, 0.20, 0.30, 0.35],
    ("L", 1): [0.18, 0.20, 0.22, 0.22, 0.18],
    ("M", 1): [0.08, 0.14, 0.20, 0.27, 0.31],
    ("H", 1): [0.05, 0.10, 0.15, 0.30, 0.40],
}


def load_and_validate_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"找不到数据文件：{DATA_PATH}\n"
            "请从项目根目录运行本脚本，并确认原始 CSV 已放入 data/ai4i/raw/。"
        )

    df = pd.read_csv(DATA_PATH)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"数据缺少必要字段：{missing_columns}")

    if not df["UDI"].is_unique:
        raise ValueError("UDI 列存在重复值，无法可靠检查客户端之间是否有重复样本。")

    invalid_types = sorted(set(df["Type"].dropna()) - {"L", "M", "H"})
    if invalid_types:
        raise ValueError(f"Type 列出现未知类型：{invalid_types}")

    invalid_labels = sorted(set(df["Machine failure"].dropna()) - {0, 1})
    if invalid_labels:
        raise ValueError(f"Machine failure 列出现非 0/1 标签：{invalid_labels}")

    return df


def split_global_test(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    先保留 20% 公共测试集。
    使用 Type 与 Machine failure 的组合进行分层，尽量保持测试集具有代表性。
    """
    stratify_key = (
        df["Type"].astype(str)
        + "_"
        + df["Machine failure"].astype(str)
    )

    federated_df, test_df = train_test_split(
        df,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=stratify_key,
    )

    return federated_df.copy(), test_df.copy()


def integer_counts(total: int, weights: list[float]) -> np.ndarray:
    """把比例转换为整数样本数，并保证总数严格等于 total。"""
    weight_array = np.asarray(weights, dtype=float)

    if len(weight_array) != len(CLIENT_NAMES):
        raise ValueError("每组权重数量必须与客户端数量相同。")

    if not np.isclose(weight_array.sum(), 1.0):
        raise ValueError(f"客户端分配权重之和必须为 1，当前为 {weight_array.sum()}。")

    raw_counts = total * weight_array
    counts = np.floor(raw_counts).astype(int)
    remainder = total - int(counts.sum())

    if remainder > 0:
        fractional_order = np.argsort(-(raw_counts - counts))
        counts[fractional_order[:remainder]] += 1

    return counts


def assign_non_iid_clients(federated_df: pd.DataFrame) -> pd.DataFrame:
    """
    将联邦训练数据划分为 5 个非 IID 客户端。

    划分依据：
    1. 不同客户端的 L/M/H 产品类型比例不同；
    2. 不同客户端的正常/故障样本比例不同；
    3. 每个客户端仍保留多种产品类型和正常、故障样本，
       避免划分过于极端而导致本地模型无法训练。
    """
    rng = np.random.default_rng(RANDOM_STATE)
    client_parts: list[pd.DataFrame] = []

    grouped = federated_df.groupby(["Type", "Machine failure"], sort=True)

    for (product_type, failure_label), group_df in grouped:
        key = (str(product_type), int(failure_label))
        if key not in WEIGHT_TABLE:
            raise ValueError(f"没有为数据组 {key} 设置客户端分配权重。")

        random_state = int(rng.integers(0, 2**31 - 1))
        shuffled_group = group_df.sample(
            frac=1.0,
            random_state=random_state,
        ).copy()

        counts = integer_counts(len(shuffled_group), WEIGHT_TABLE[key])

        start = 0
        for client_name, count in zip(CLIENT_NAMES, counts):
            end = start + int(count)
            part = shuffled_group.iloc[start:end].copy()
            part["client_id"] = client_name
            client_parts.append(part)
            start = end

        if start != len(shuffled_group):
            raise RuntimeError(f"数据组 {key} 未被完整划分。")

    assigned_df = pd.concat(client_parts, ignore_index=False)

    # 打乱每个客户端内部的样本顺序，避免保存后的数据仍按分组排列。
    shuffled_clients = []
    for i, client_name in enumerate(CLIENT_NAMES):
        client_df = assigned_df[assigned_df["client_id"] == client_name]
        client_df = client_df.sample(
            frac=1.0,
            random_state=RANDOM_STATE + i,
        )
        shuffled_clients.append(client_df)

    assigned_df = pd.concat(shuffled_clients, ignore_index=True)
    return assigned_df


def validate_partition(
    original_df: pd.DataFrame,
    federated_df: pd.DataFrame,
    test_df: pd.DataFrame,
    assigned_df: pd.DataFrame,
) -> None:
    """检查是否存在样本遗漏、重复或测试集泄漏。"""
    original_ids = set(original_df["UDI"])
    train_ids = set(federated_df["UDI"])
    test_ids = set(test_df["UDI"])
    assigned_ids = set(assigned_df["UDI"])

    if train_ids & test_ids:
        raise RuntimeError("联邦训练集与公共测试集存在重复样本。")

    if assigned_df["UDI"].duplicated().any():
        raise RuntimeError("不同客户端之间存在重复样本。")

    if assigned_ids != train_ids:
        missing = train_ids - assigned_ids
        unexpected = assigned_ids - train_ids
        raise RuntimeError(
            f"客户端划分不完整：遗漏 {len(missing)} 条，多出 {len(unexpected)} 条。"
        )

    if train_ids | test_ids != original_ids:
        raise RuntimeError("训练集和测试集合并后与原始数据不一致。")

    for client_name in CLIENT_NAMES:
        client_df = assigned_df[assigned_df["client_id"] == client_name]
        labels = set(client_df["Machine failure"].unique())
        if labels != {0, 1}:
            raise RuntimeError(
                f"{client_name} 没有同时包含正常与故障样本，当前标签为：{sorted(labels)}"
            )


def build_client_summary(assigned_df: pd.DataFrame) -> pd.DataFrame:
    """统计每个客户端的样本数、故障率、产品类型和关键特征均值。"""
    rows = []

    for client_name in CLIENT_NAMES:
        client_df = assigned_df[assigned_df["client_id"] == client_name]

        row = {
            "client_id": client_name,
            "sample_count": len(client_df),
            "normal_count": int((client_df["Machine failure"] == 0).sum()),
            "failure_count": int((client_df["Machine failure"] == 1).sum()),
            "failure_rate": round(float(client_df["Machine failure"].mean()), 6),
            "type_L_count": int((client_df["Type"] == "L").sum()),
            "type_M_count": int((client_df["Type"] == "M").sum()),
            "type_H_count": int((client_df["Type"] == "H").sum()),
            "type_L_rate": round(float((client_df["Type"] == "L").mean()), 6),
            "type_M_rate": round(float((client_df["Type"] == "M").mean()), 6),
            "type_H_rate": round(float((client_df["Type"] == "H").mean()), 6),
        }

        for feature in FEATURE_COLUMNS:
            column_name = (
                feature.lower()
                .replace(" [k]", "")
                .replace(" [rpm]", "")
                .replace(" [nm]", "")
                .replace(" [min]", "")
                .replace(" ", "_")
            )
            row[f"{column_name}_mean"] = round(float(client_df[feature].mean()), 6)

        for fault_col in FAULT_COLUMNS:
            row[f"{fault_col}_count"] = int(client_df[fault_col].sum())

        rows.append(row)

    return pd.DataFrame(rows)


def save_outputs(
    assigned_df: pd.DataFrame,
    test_df: pd.DataFrame,
    summary_df: pd.DataFrame,
) -> None:
    CLIENT_DIR.mkdir(parents=True, exist_ok=True)
    TEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)

    for client_name in CLIENT_NAMES:
        client_df = assigned_df[assigned_df["client_id"] == client_name].copy()
        output_path = CLIENT_DIR / f"{client_name}.csv"
        client_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    test_df.to_csv(TEST_PATH, index=False, encoding="utf-8-sig")
    summary_df.to_csv(RESULT_PATH, index=False, encoding="utf-8-sig")


def main() -> None:
    original_df = load_and_validate_data()
    federated_df, test_df = split_global_test(original_df)
    assigned_df = assign_non_iid_clients(federated_df)

    validate_partition(
        original_df=original_df,
        federated_df=federated_df,
        test_df=test_df,
        assigned_df=assigned_df,
    )

    summary_df = build_client_summary(assigned_df)
    save_outputs(assigned_df, test_df, summary_df)

    print("=" * 100)
    print("AI4I 非 IID 客户端划分完成")
    print("=" * 100)
    print(f"原始样本数：{len(original_df)}")
    print(f"联邦训练样本数：{len(federated_df)}")
    print(f"公共测试样本数：{len(test_df)}")
    print("\n客户端分布：")
    print(
        summary_df[
            [
                "client_id",
                "sample_count",
                "normal_count",
                "failure_count",
                "failure_rate",
                "type_L_rate",
                "type_M_rate",
                "type_H_rate",
            ]
        ].to_string(index=False)
    )

    print(f"\n客户端数据目录：{CLIENT_DIR}")
    print(f"公共测试集：{TEST_PATH}")
    print(f"客户端统计表：{RESULT_PATH}")


if __name__ == "__main__":
    main()