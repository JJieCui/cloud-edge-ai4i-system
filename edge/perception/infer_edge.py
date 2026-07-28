from pathlib import Path
from typing import Any

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "results" / "models" / "perception"

FEATURE_COLUMNS = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

ACTION_BY_RISK = {
    "low": "正常运行",
    "medium": "建议维护并持续监控",
    "high": "紧急停机并上报云端",
}


def model_path_for(client_id: str, model_name: str) -> Path:
    normalized_model_name = model_name.strip().lower().replace("_", "").replace("-", "")
    aliases = {
        "randomforest": "randomforest",
        "randomforestclassifier": "randomforest",
    }
    if normalized_model_name not in aliases:
        raise ValueError(f"Unsupported model_name: {model_name}")
    return MODEL_DIR / f"{client_id}_{aliases[normalized_model_name]}.joblib"


def device_state_to_frame(device_state: dict[str, Any]) -> pd.DataFrame:
    row = {
        "Type": device_state.get("Type", device_state.get("product_type", "L")),
        "Air temperature [K]": device_state.get("air_temperature_k"),
        "Process temperature [K]": device_state.get("process_temperature_k"),
        "Rotational speed [rpm]": device_state.get("rotational_speed_rpm"),
        "Torque [Nm]": device_state.get("torque_nm"),
        "Tool wear [min]": device_state.get("tool_wear_min"),
    }

    missing_fields = [
        column for column, value in row.items() if column != "Type" and value is None
    ]
    if missing_fields:
        raise ValueError(f"Missing device_state fields for: {missing_fields}")

    row["Type"] = str(row["Type"]).upper()
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def risk_level_from_prob(fault_prob: float) -> str:
    if fault_prob < 0.3:
        return "low"
    if fault_prob < 0.7:
        return "medium"
    return "high"


def infer_edge(
    device_state: dict,
    client_id: str = "client_1",
    model_name: str = "RandomForest",
) -> dict:
    model_path = model_path_for(client_id=client_id, model_name=model_name)
    if not model_path.exists():
        raise FileNotFoundError(f"Missing edge perception model: {model_path}")

    model = joblib.load(model_path)
    input_df = device_state_to_frame(device_state)
    probabilities = model.predict_proba(input_df)[0]
    class_labels = list(model.classes_)
    fault_index = class_labels.index(1) if 1 in class_labels else len(probabilities) - 1
    fault_prob = float(probabilities[fault_index])
    fault_label = int(fault_prob >= 0.5)
    risk_level = risk_level_from_prob(fault_prob)
    confidence = fault_prob if fault_label == 1 else 1.0 - fault_prob

    return {
        "fault_label": fault_label,
        "fault_label_name": "Fault Detected" if fault_label == 1 else "Normal",
        "fault_prob": round(fault_prob, 4),
        "risk_level": risk_level,
        "action": ACTION_BY_RISK[risk_level],
        "confidence": round(confidence, 4),
    }


def main() -> None:
    sample_state = {
        "product_type": "L",
        "air_temperature_k": 300.5,
        "process_temperature_k": 310.8,
        "rotational_speed_rpm": 1400,
        "torque_nm": 45.0,
        "tool_wear_min": 120,
    }
    print(infer_edge(sample_state))


if __name__ == "__main__":
    main()
