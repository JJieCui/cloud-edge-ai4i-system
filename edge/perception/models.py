from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CATEGORICAL_FEATURES = ["Type"]
NUMERIC_FEATURES = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def build_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_preprocessor(scale_numeric: bool) -> ColumnTransformer:
    numeric_transformer = StandardScaler() if scale_numeric else "passthrough"

    return ColumnTransformer(
        transformers=[
            ("type", build_one_hot_encoder(), CATEGORICAL_FEATURES),
            ("numeric", numeric_transformer, NUMERIC_FEATURES),
        ]
    )


def build_model_configs() -> list[dict[str, object]]:
    return [
        {
            "name": "LogisticRegression",
            "upsample_minority": False,
            "pipeline": Pipeline(
                steps=[
                    ("preprocess", build_preprocessor(scale_numeric=True)),
                    (
                        "model",
                        LogisticRegression(
                            max_iter=1000,
                            class_weight="balanced",
                            random_state=42,
                        ),
                    ),
                ]
            ),
        },
        {
            "name": "RandomForest",
            "upsample_minority": False,
            "pipeline": Pipeline(
                steps=[
                    ("preprocess", build_preprocessor(scale_numeric=False)),
                    (
                        "model",
                        RandomForestClassifier(
                            n_estimators=200,
                            random_state=42,
                            class_weight="balanced",
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
        },
        {
            "name": "MLP",
            "upsample_minority": True,
            "pipeline": Pipeline(
                steps=[
                    ("preprocess", build_preprocessor(scale_numeric=True)),
                    (
                        "model",
                        MLPClassifier(
                            hidden_layer_sizes=(64, 32),
                            max_iter=500,
                            early_stopping=False,
                            random_state=42,
                        ),
                    ),
                ]
            ),
        },
    ]
