import pandas as pd
from pathlib import Path


DATA_PATH = Path("data/ai4i/raw/ai4i2020.csv")

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

NUMERIC_FEATURES = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

FAULT_COLUMNS = ["TWF", "HDF", "PWF", "OSF", "RNF"]


def load_ai4i(path: Path = DATA_PATH) -> pd.DataFrame:
    """读取并检查 AI4I 数据。"""
    if not path.exists():
        raise FileNotFoundError(
            f"找不到数据文件：{path}\n"
            "请确认当前终端位于项目根目录，并且 ai4i2020.csv 已放入 data/ai4i/raw/。"
        )

    df = pd.read_csv(path)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"数据缺少必要字段：{missing_columns}")

    return df


def print_value_distribution(df: pd.DataFrame, column: str) -> None:
    """同时输出某一列的数量和比例。"""
    counts = df[column].value_counts(dropna=False).sort_index()
    rates = (df[column].value_counts(normalize=True, dropna=False).sort_index() * 100).round(2)

    distribution = pd.DataFrame(
        {
            "count": counts,
            "rate_percent": rates,
        }
    )
    print(distribution)


def main() -> None:
    df = load_ai4i()

    print("=" * 70)
    print("AI4I 数据读取与检查")
    print("=" * 70)

    print("\n1. 数据维度（行数，列数）：")
    print(df.shape)

    print("\n2. 字段名称与数据类型：")
    print(df.dtypes)

    print("\n3. 前 5 行数据：")
    print(df.head())

    print("\n4. 缺失值统计：")
    print(df.isna().sum())

    print("\n5. 完全重复行数量：")
    print(int(df.duplicated().sum()))

    print("\n6. UDI 是否唯一：")
    print(df["UDI"].is_unique)

    print("\n7. 产品类型 Type 分布：")
    print_value_distribution(df, "Type")

    print("\n8. 总故障标签 Machine failure 分布：")
    print_value_distribution(df, "Machine failure")

    print("\n9. 五种具体故障数量：")
    print(df[FAULT_COLUMNS].sum().astype(int))

    print("\n10. 关键数值特征描述统计：")
    print(df[NUMERIC_FEATURES].describe().round(4))

    # 该检查只用于发现标签之间是否存在不一致，不直接删除数据。
    any_specific_fault = df[FAULT_COLUMNS].max(axis=1)
    inconsistent_count = int((df["Machine failure"] != any_specific_fault).sum())

    print("\n11. Machine failure 与五种具体故障标签不一致的记录数：")
    print(inconsistent_count)
    if inconsistent_count > 0:
        print("说明：这里只报告不一致记录，不自动删除或修改原始数据。")

    print("\n数据检查完成。")


if __name__ == "__main__":
    main()