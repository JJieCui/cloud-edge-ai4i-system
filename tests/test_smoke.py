"""项目最小闭环冒烟测试。"""

from pathlib import Path

from cloud import gcm_api
from cloud.cloud_service import app, health_check
from data.read_ai4i import REQUIRED_COLUMNS, load_ai4i


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI4I_PATH = PROJECT_ROOT / "data" / "ai4i" / "raw" / "ai4i2020.csv"


def test_ai4i_dataset_is_available_and_valid() -> None:
    """确认比赛主数据可以读取，并包含预期字段与标签。"""
    dataframe = load_ai4i(AI4I_PATH)

    assert dataframe.shape == (10_000, 14)
    assert set(REQUIRED_COLUMNS).issubset(dataframe.columns)
    assert set(dataframe["Machine failure"].unique()).issubset({0, 1})


def test_cloud_service_health_endpoint_is_registered() -> None:
    """确认云端服务可导入，且健康检查路由已经注册。"""
    registered_paths = {route.path for route in app.routes}

    assert "/health" in registered_paths
    assert health_check() == {"status": "healthy", "service": "cloud_gcm_review"}


def test_mock_gcm_returns_structured_decision(monkeypatch) -> None:
    """固定随机源，确认 mock GCM 始终返回可验证的结构化结果。"""
    monkeypatch.setattr(gcm_api.random, "random", lambda: 0.0)
    monkeypatch.setattr(gcm_api.random, "uniform", lambda _low, _high: 0.1)
    monkeypatch.setattr(gcm_api.random, "randint", lambda _low, _high: 100)

    edge_summary = {
        "device_id": "device_smoke_001",
        "edge_fault_label": "Normal",
        "edge_risk_level": "low",
        "edge_action": "monitor",
        "edge_confidence": 0.85,
    }
    result = gcm_api.mock_gcm_response(edge_summary)

    assert result == {
        "gcm_fault_label": "Normal",
        "gcm_risk_level": "low",
        "gcm_action": "monitor",
        "gcm_confidence": 0.95,
        "gcm_reason": "Mock GCM review completed",
        "consistent_with_edge": True,
        "latency_ms": 100,
    }
