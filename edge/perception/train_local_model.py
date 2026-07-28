from pathlib import Path
import sys

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from edge.perception.models import FEATURE_COLUMNS, build_model_configs

CLIENT_DIR = PROJECT_ROOT / "data" / "ai4i" / "clients"
TEST_PATH = PROJECT_ROOT / "data" / "ai4i" / "test" / "global_test.csv"
RESULT_PATH = PROJECT_ROOT / "results" / "tables" / "perception_baseline.csv"
MODEL_DIR = PROJECT_ROOT / "results" / "models" / "perception"

CLIENT_IDS = [f"client_{i}" for i in range(1, 6)]

LABEL_COLUMN = "Machine failure"


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")

    df = pd.read_csv(path)
    missing_columns = [
        column for column in FEATURE_COLUMNS + [LABEL_COLUMN] if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(f"{path} is missing required columns: {missing_columns}")

    return df


def upsample_minority_class(train_df: pd.DataFrame) -> pd.DataFrame:
    class_counts = train_df[LABEL_COLUMN].value_counts()
    if len(class_counts) < 2:
        return train_df.copy()

    majority_label = class_counts.idxmax()
    minority_label = class_counts.idxmin()
    majority_df = train_df[train_df[LABEL_COLUMN] == majority_label]
    minority_df = train_df[train_df[LABEL_COLUMN] == minority_label]

    minority_upsampled = minority_df.sample(
        n=len(majority_df),
        replace=True,
        random_state=42,
    )

    balanced_df = pd.concat([majority_df, minority_upsampled], ignore_index=True)
    return balanced_df.sample(frac=1.0, random_state=42).reset_index(drop=True)


def evaluate_model(
    client_id: str,
    model_name: str,
    model: Pipeline,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    upsample_minority: bool,
) -> dict[str, float | int | str]:
    fit_df = upsample_minority_class(train_df) if upsample_minority else train_df
    x_train = fit_df[FEATURE_COLUMNS]
    y_train = fit_df[LABEL_COLUMN]
    x_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[LABEL_COLUMN]

    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)

    if model_name == "RandomForest":
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODEL_DIR / f"{client_id}_randomforest.joblib"
        joblib.dump(model, model_path)

    return {
        "client_id": client_id,
        "model": model_name,
        "train_sample_count": int(len(train_df)),
        "train_failure_count": int(train_df[LABEL_COLUMN].sum()),
        "train_failure_rate": round(float(train_df[LABEL_COLUMN].mean()), 6),
        "test_sample_count": int(len(test_df)),
        "test_failure_count": int(y_test.sum()),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 6),
        "precision": round(
            float(precision_score(y_test, y_pred, zero_division=0)),
            6,
        ),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 6),
    }


def run_experiment() -> pd.DataFrame:
    test_df = load_dataset(TEST_PATH)
    rows = []

    for client_id in CLIENT_IDS:
        train_path = CLIENT_DIR / f"{client_id}.csv"
        train_df = load_dataset(train_path)

        for model_config in build_model_configs():
            rows.append(
                evaluate_model(
                    client_id=client_id,
                    model_name=model_config["name"],
                    model=model_config["pipeline"],
                    train_df=train_df,
                    test_df=test_df,
                    upsample_minority=model_config["upsample_minority"],
                )
            )

    return pd.DataFrame(rows)


def main() -> None:
    result_df = run_experiment()

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(RESULT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 100)
    print("AI4I edge perception baseline finished")
    print("=" * 100)
    print(result_df.to_string(index=False))
    print(f"\nSaved result table: {RESULT_PATH}")


if __name__ == "__main__":
    main()
