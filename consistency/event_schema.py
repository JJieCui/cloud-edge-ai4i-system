import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any


RISK_LEVELS = ["low", "medium", "high", "critical"]
ACTIONS = ["monitor", "warn", "maintain", "shutdown", "replace"]
SOURCES = ["edge", "cloud", "federated"]


class Event:
    def __init__(
        self,
        node_id: str,
        device_id: str,
        fault_label: str,
        risk_level: str,
        action: str,
        confidence: float,
        source: str,
        timestamp: Optional[str] = None,
        event_id: Optional[str] = None,
        reason: Optional[str] = None,
        device_features: Optional[Dict[str, Any]] = None,
        routing_path: Optional[str] = None,
    ):
        self.event_id = event_id or f"event_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        self.timestamp = timestamp or datetime.now().isoformat()
        self.node_id = node_id
        self.device_id = device_id
        self.fault_label = fault_label
        self.risk_level = risk_level
        self.action = action
        self.confidence = confidence
        self.source = source
        self.reason = reason or ""
        self.device_features = device_features or {}
        self.routing_path = routing_path or "unknown"

        self._validate()

    def _validate(self):
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"risk_level 必须是 {RISK_LEVELS} 之一，当前值: {self.risk_level}")
        if self.action not in ACTIONS:
            raise ValueError(f"action 必须是 {ACTIONS} 之一，当前值: {self.action}")
        if self.source not in SOURCES:
            raise ValueError(f"source 必须是 {SOURCES} 之一，当前值: {self.source}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence 必须在 [0, 1] 范围内，当前值: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "device_id": self.device_id,
            "fault_label": self.fault_label,
            "risk_level": self.risk_level,
            "action": self.action,
            "confidence": self.confidence,
            "source": self.source,
            "reason": self.reason,
            "routing_path": self.routing_path,
            "device_features": self.device_features,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_id=data.get("event_id"),
            timestamp=data.get("timestamp"),
            node_id=data["node_id"],
            device_id=data["device_id"],
            fault_label=data["fault_label"],
            risk_level=data["risk_level"],
            action=data["action"],
            confidence=data["confidence"],
            source=data["source"],
            reason=data.get("reason"),
            device_features=data.get("device_features"),
            routing_path=data.get("routing_path"),
        )

    def risk_level_order(self) -> int:
        return RISK_LEVELS.index(self.risk_level)

    def __repr__(self) -> str:
        return (
            f"Event(id={self.event_id[:12]}..., node={self.node_id}, "
            f"device={self.device_id}, risk={self.risk_level}, "
            f"action={self.action}, conf={self.confidence:.2f})"
        )


def build_event(
    node_id: str,
    device_id: str,
    fault_label: str,
    risk_level: str,
    action: str,
    confidence: float,
    source: str,
    **kwargs,
) -> Event:
    return Event(
        node_id=node_id,
        device_id=device_id,
        fault_label=fault_label,
        risk_level=risk_level,
        action=action,
        confidence=confidence,
        source=source,
        **kwargs,
    )


def main():
    print("=== Event Schema 测试 ===")
    print(f"支持的风险等级: {RISK_LEVELS}")
    print(f"支持的动作: {ACTIONS}")
    print(f"支持的来源: {SOURCES}")

    test_event = build_event(
        node_id="edge_node_0",
        device_id="device_001",
        fault_label="Heat Dissipation Failure",
        risk_level="high",
        action="shutdown",
        confidence=0.85,
        source="edge",
        reason="温度过高，散热系统异常",
        device_features={
            "Air temperature [K]": 305.2,
            "Process temperature [K]": 310.0,
            "Rotational speed [rpm]": 1450,
            "Torque [Nm]": 45.2,
            "Tool wear [min]": 150,
        },
        routing_path="CloudEdge",
    )

    print(f"\n创建事件: {test_event}")
    print(f"\n事件字典:")
    import json
    print(json.dumps(test_event.to_dict(), indent=2, ensure_ascii=False))

    event_dict = test_event.to_dict()
    restored_event = Event.from_dict(event_dict)
    print(f"\n从字典恢复: {restored_event}")

    print(f"\n风险等级排序值: {test_event.risk_level_order()}")

    try:
        build_event(
            node_id="edge_node_0",
            device_id="device_001",
            fault_label="Normal",
            risk_level="invalid",
            action="monitor",
            confidence=0.5,
            source="edge",
        )
    except ValueError as e:
        print(f"\n字段验证工作正常: {e}")


if __name__ == "__main__":
    main()
