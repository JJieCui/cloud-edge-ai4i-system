import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, List


RISK_LEVELS = ["low", "medium", "high", "critical"]
ACTIONS = ["monitor", "warn", "maintain", "shutdown", "replace"]
SOURCES = ["edge", "cloud", "federated"]
SCENES = ["industrial", "energy"]
ROUTES = ["EdgeOnly", "EdgeCloud", "CloudOnly", "SafeFallback", "DeferredReview"]
DECISION_SOURCES = [
    "edge_only",
    "cloud_only",
    "cloud_reviewed",
    "arbitrated",
    "safe_fallback",
]

ENERGY_NODE_TYPES = ["generator", "consumer"]
ENERGY_ACTIONS = ["maintain", "reduce_load", "increase_generation", "emergency_limit"]


class Observation:
    def __init__(
        self,
        scene: str,
        node_id: str,
        object_id: str,
        payload: Dict[str, Any],
        network: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        deadline_ms: int = 200,
    ):
        self.event_id = event_id or f"evt-{uuid.uuid4().hex[:12]}"
        self.trace_id = trace_id or f"trace-{uuid.uuid4().hex[:12]}"
        self.scene = scene
        self.node_id = node_id
        self.object_id = object_id
        self.timestamp = timestamp or datetime.now().isoformat()
        self.deadline_ms = deadline_ms
        self.payload = payload
        self.network = network or {
            "rtt_ms": 20,
            "packet_loss": 0.0,
            "connected": True,
        }
        self._validate()

    def _validate(self):
        if self.scene not in SCENES:
            raise ValueError(f"scene 必须是 {SCENES} 之一，当前值: {self.scene}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "scene": self.scene,
            "node_id": self.node_id,
            "object_id": self.object_id,
            "timestamp": self.timestamp,
            "deadline_ms": self.deadline_ms,
            "payload": self.payload,
            "network": self.network,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Observation":
        return cls(
            event_id=data.get("event_id"),
            trace_id=data.get("trace_id"),
            scene=data["scene"],
            node_id=data["node_id"],
            object_id=data["object_id"],
            timestamp=data.get("timestamp"),
            deadline_ms=data.get("deadline_ms", 200),
            payload=data.get("payload", {}),
            network=data.get("network"),
        )

    def __repr__(self) -> str:
        return (
            f"Observation(id={self.event_id[:12]}..., scene={self.scene}, "
            f"node={self.node_id}, object={self.object_id})"
        )


class EdgeDecision:
    def __init__(
        self,
        event_id: str,
        trace_id: str,
        scene: str,
        node_id: str,
        predicted_label: str,
        risk_level: str,
        action: str,
        confidence: float,
        model_version: str,
        reason: Optional[str] = None,
        inference_ms: float = 0.0,
        data_age_ms: int = 0,
    ):
        self.event_id = event_id
        self.trace_id = trace_id
        self.scene = scene
        self.node_id = node_id
        self.predicted_label = predicted_label
        self.risk_level = risk_level
        self.action = action
        self.confidence = confidence
        self.reason = reason or ""
        self.model_version = model_version
        self.inference_ms = inference_ms
        self.data_age_ms = data_age_ms
        self._validate()

    def _validate(self):
        if self.scene not in SCENES:
            raise ValueError(f"scene 必须是 {SCENES} 之一，当前值: {self.scene}")
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"risk_level 必须是 {RISK_LEVELS} 之一，当前值: {self.risk_level}")
        if self.action not in ACTIONS:
            raise ValueError(f"action 必须是 {ACTIONS} 之一，当前值: {self.action}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence 必须在 [0, 1] 范围内，当前值: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "scene": self.scene,
            "node_id": self.node_id,
            "predicted_label": self.predicted_label,
            "risk_level": self.risk_level,
            "action": self.action,
            "confidence": self.confidence,
            "reason": self.reason,
            "model_version": self.model_version,
            "inference_ms": self.inference_ms,
            "data_age_ms": self.data_age_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EdgeDecision":
        return cls(
            event_id=data["event_id"],
            trace_id=data["trace_id"],
            scene=data["scene"],
            node_id=data["node_id"],
            predicted_label=data["predicted_label"],
            risk_level=data["risk_level"],
            action=data["action"],
            confidence=data["confidence"],
            reason=data.get("reason"),
            model_version=data.get("model_version", "unknown"),
            inference_ms=data.get("inference_ms", 0.0),
            data_age_ms=data.get("data_age_ms", 0),
        )

    def risk_level_order(self) -> int:
        return RISK_LEVELS.index(self.risk_level)

    def __repr__(self) -> str:
        return (
            f"EdgeDecision(node={self.node_id}, label={self.predicted_label}, "
            f"risk={self.risk_level}, action={self.action}, conf={self.confidence:.2f})"
        )


class RouteDecision:
    def __init__(
        self,
        trace_id: str,
        route: str,
        reason_codes: Optional[List[str]] = None,
        estimated_total_ms: float = 0.0,
        remaining_deadline_ms: float = 0.0,
        policy_version: str = "router-v1",
    ):
        self.trace_id = trace_id
        self.route = route
        self.reason_codes = reason_codes or []
        self.estimated_total_ms = estimated_total_ms
        self.remaining_deadline_ms = remaining_deadline_ms
        self.policy_version = policy_version
        self._validate()

    def _validate(self):
        if self.route not in ROUTES:
            raise ValueError(f"route 必须是 {ROUTES} 之一，当前值: {self.route}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "route": self.route,
            "reason_codes": self.reason_codes,
            "estimated_total_ms": self.estimated_total_ms,
            "remaining_deadline_ms": self.remaining_deadline_ms,
            "policy_version": self.policy_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouteDecision":
        return cls(
            trace_id=data["trace_id"],
            route=data["route"],
            reason_codes=data.get("reason_codes"),
            estimated_total_ms=data.get("estimated_total_ms", 0.0),
            remaining_deadline_ms=data.get("remaining_deadline_ms", 0.0),
            policy_version=data.get("policy_version", "router-v1"),
        )

    def __repr__(self) -> str:
        return f"RouteDecision(route={self.route}, reasons={self.reason_codes})"


class CloudReview:
    def __init__(
        self,
        trace_id: str,
        reviewed_label: str,
        risk_level: str,
        action: str,
        confidence: float,
        model: str,
        reason: Optional[str] = None,
        latency_ms: float = 0.0,
        fallback_used: bool = False,
    ):
        self.trace_id = trace_id
        self.reviewed_label = reviewed_label
        self.risk_level = risk_level
        self.action = action
        self.confidence = confidence
        self.reason = reason or ""
        self.model = model
        self.latency_ms = latency_ms
        self.fallback_used = fallback_used
        self._validate()

    def _validate(self):
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"risk_level 必须是 {RISK_LEVELS} 之一，当前值: {self.risk_level}")
        if self.action not in ACTIONS:
            raise ValueError(f"action 必须是 {ACTIONS} 之一，当前值: {self.action}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence 必须在 [0, 1] 范围内，当前值: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "reviewed_label": self.reviewed_label,
            "risk_level": self.risk_level,
            "action": self.action,
            "confidence": self.confidence,
            "reason": self.reason,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "fallback_used": self.fallback_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CloudReview":
        return cls(
            trace_id=data["trace_id"],
            reviewed_label=data["reviewed_label"],
            risk_level=data["risk_level"],
            action=data["action"],
            confidence=data["confidence"],
            model=data.get("model", "unknown"),
            reason=data.get("reason"),
            latency_ms=data.get("latency_ms", 0.0),
            fallback_used=data.get("fallback_used", False),
        )

    def risk_level_order(self) -> int:
        return RISK_LEVELS.index(self.risk_level)

    def __repr__(self) -> str:
        return (
            f"CloudReview(model={self.model}, label={self.reviewed_label}, "
            f"risk={self.risk_level}, action={self.action})"
        )


class FinalDecision:
    def __init__(
        self,
        trace_id: str,
        scene: str,
        final_label: str,
        final_risk_level: str,
        final_action: str,
        confidence: float,
        decision_source: str,
        decision_id: Optional[str] = None,
        conflict_detected: bool = False,
        arbitration_reason: Optional[str] = None,
        end_to_end_ms: float = 0.0,
        deadline_met: bool = True,
    ):
        self.decision_id = decision_id or f"decision-{uuid.uuid4().hex[:12]}"
        self.trace_id = trace_id
        self.scene = scene
        self.final_label = final_label
        self.final_risk_level = final_risk_level
        self.final_action = final_action
        self.confidence = confidence
        self.decision_source = decision_source
        self.conflict_detected = conflict_detected
        self.arbitration_reason = arbitration_reason or ""
        self.end_to_end_ms = end_to_end_ms
        self.deadline_met = deadline_met
        self._validate()

    def _validate(self):
        if self.scene not in SCENES:
            raise ValueError(f"scene 必须是 {SCENES} 之一，当前值: {self.scene}")
        if self.final_risk_level not in RISK_LEVELS:
            raise ValueError(f"final_risk_level 必须是 {RISK_LEVELS} 之一，当前值: {self.final_risk_level}")
        if self.final_action not in ACTIONS:
            raise ValueError(f"final_action 必须是 {ACTIONS} 之一，当前值: {self.final_action}")
        if self.decision_source not in DECISION_SOURCES:
            raise ValueError(f"decision_source 必须是 {DECISION_SOURCES} 之一，当前值: {self.decision_source}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence 必须在 [0, 1] 范围内，当前值: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "trace_id": self.trace_id,
            "scene": self.scene,
            "final_label": self.final_label,
            "final_risk_level": self.final_risk_level,
            "final_action": self.final_action,
            "confidence": self.confidence,
            "decision_source": self.decision_source,
            "conflict_detected": self.conflict_detected,
            "arbitration_reason": self.arbitration_reason,
            "end_to_end_ms": self.end_to_end_ms,
            "deadline_met": self.deadline_met,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FinalDecision":
        return cls(
            decision_id=data.get("decision_id"),
            trace_id=data["trace_id"],
            scene=data["scene"],
            final_label=data["final_label"],
            final_risk_level=data["final_risk_level"],
            final_action=data["final_action"],
            confidence=data["confidence"],
            decision_source=data["decision_source"],
            conflict_detected=data.get("conflict_detected", False),
            arbitration_reason=data.get("arbitration_reason"),
            end_to_end_ms=data.get("end_to_end_ms", 0.0),
            deadline_met=data.get("deadline_met", True),
        )

    def __repr__(self) -> str:
        return (
            f"FinalDecision(id={self.decision_id[:12]}..., source={self.decision_source}, "
            f"label={self.final_label}, action={self.final_action})"
        )


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
        trace_id: Optional[str] = None,
        scene: Optional[str] = None,
        model_version: Optional[str] = None,
        inference_ms: Optional[float] = None,
        data_age_ms: Optional[int] = None,
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
        self.trace_id = trace_id or f"trace-{uuid.uuid4().hex[:8]}"
        self.scene = scene or "industrial"
        self.model_version = model_version or "unknown"
        self.inference_ms = inference_ms or 0.0
        self.data_age_ms = data_age_ms or 0
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
            "trace_id": self.trace_id,
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
            "scene": self.scene,
            "model_version": self.model_version,
            "inference_ms": self.inference_ms,
            "data_age_ms": self.data_age_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_id=data.get("event_id"),
            trace_id=data.get("trace_id"),
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
            scene=data.get("scene"),
            model_version=data.get("model_version"),
            inference_ms=data.get("inference_ms"),
            data_age_ms=data.get("data_age_ms"),
        )

    @classmethod
    def from_edge_decision(cls, ed: EdgeDecision) -> "Event":
        return cls(
            event_id=ed.event_id,
            trace_id=ed.trace_id,
            node_id=ed.node_id,
            device_id=ed.node_id + "-" + ed.event_id[:8],
            fault_label=ed.predicted_label,
            risk_level=ed.risk_level,
            action=ed.action,
            confidence=ed.confidence,
            source="edge",
            reason=ed.reason,
            scene=ed.scene,
            model_version=ed.model_version,
            inference_ms=ed.inference_ms,
            data_age_ms=ed.data_age_ms,
            routing_path="EdgeOnly",
        )

    @classmethod
    def from_cloud_review(cls, cr: CloudReview, node_id: str = "cloud") -> "Event":
        return cls(
            event_id=cr.trace_id,
            trace_id=cr.trace_id,
            node_id=node_id,
            device_id=node_id + "-" + cr.trace_id[:8],
            fault_label=cr.reviewed_label,
            risk_level=cr.risk_level,
            action=cr.action,
            confidence=cr.confidence,
            source="cloud",
            reason=cr.reason,
            model_version=cr.model,
            routing_path="CloudOnly",
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


class EnergyEvent:
    def __init__(
        self,
        node_id: str,
        node_type: str,
        grid_id: str,
        stability_label: str,
        risk_level: str,
        action: str,
        confidence: float,
        current_power: float,
        requested_power_adjustment: float,
        source: str,
        timestamp: Optional[str] = None,
        event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        reason: Optional[str] = None,
        priority: int = 0,
        data_age_ms: int = 0,
        capacity_margin: float = 0.0,
    ):
        self.event_id = event_id or f"energy_evt_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        self.trace_id = trace_id or f"trace-{uuid.uuid4().hex[:8]}"
        self.timestamp = timestamp or datetime.now().isoformat()
        self.node_id = node_id
        self.node_type = node_type
        self.grid_id = grid_id
        self.stability_label = stability_label
        self.risk_level = risk_level
        self.action = action
        self.confidence = confidence
        self.current_power = current_power
        self.requested_power_adjustment = requested_power_adjustment
        self.source = source
        self.reason = reason or ""
        self.priority = priority
        self.data_age_ms = data_age_ms
        self.capacity_margin = capacity_margin
        self._validate()

    def _validate(self):
        if self.node_type not in ENERGY_NODE_TYPES:
            raise ValueError(f"node_type 必须是 {ENERGY_NODE_TYPES} 之一，当前值: {self.node_type}")
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"risk_level 必须是 {RISK_LEVELS} 之一，当前值: {self.risk_level}")
        if self.action not in ENERGY_ACTIONS:
            raise ValueError(f"action 必须是 {ENERGY_ACTIONS} 之一，当前值: {self.action}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence 必须在 [0, 1] 范围内，当前值: {self.confidence}")

    def risk_level_order(self) -> int:
        return RISK_LEVELS.index(self.risk_level)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "grid_id": self.grid_id,
            "stability_label": self.stability_label,
            "risk_level": self.risk_level,
            "action": self.action,
            "confidence": self.confidence,
            "current_power": self.current_power,
            "requested_power_adjustment": self.requested_power_adjustment,
            "source": self.source,
            "reason": self.reason,
            "priority": self.priority,
            "data_age_ms": self.data_age_ms,
            "capacity_margin": self.capacity_margin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnergyEvent":
        return cls(
            event_id=data.get("event_id"),
            trace_id=data.get("trace_id"),
            timestamp=data.get("timestamp"),
            node_id=data["node_id"],
            node_type=data["node_type"],
            grid_id=data["grid_id"],
            stability_label=data["stability_label"],
            risk_level=data["risk_level"],
            action=data["action"],
            confidence=data["confidence"],
            current_power=data["current_power"],
            requested_power_adjustment=data["requested_power_adjustment"],
            source=data["source"],
            reason=data.get("reason"),
            priority=data.get("priority", 0),
            data_age_ms=data.get("data_age_ms", 0),
            capacity_margin=data.get("capacity_margin", 0.0),
        )

    def __repr__(self) -> str:
        return (
            f"EnergyEvent(node={self.node_id}, type={self.node_type}, "
            f"risk={self.risk_level}, action={self.action}, "
            f"power={self.current_power:.1f}, req_adj={self.requested_power_adjustment:+.1f})"
        )


def build_energy_event(
    node_id: str,
    node_type: str,
    grid_id: str,
    stability_label: str,
    risk_level: str,
    action: str,
    confidence: float,
    current_power: float,
    requested_power_adjustment: float,
    source: str,
    **kwargs,
) -> EnergyEvent:
    return EnergyEvent(
        node_id=node_id,
        node_type=node_type,
        grid_id=grid_id,
        stability_label=stability_label,
        risk_level=risk_level,
        action=action,
        confidence=confidence,
        current_power=current_power,
        requested_power_adjustment=requested_power_adjustment,
        source=source,
        **kwargs,
    )


def main():
    print("=== Event Schema 测试 ===")
    print(f"支持的风险等级: {RISK_LEVELS}")
    print(f"支持的动作: {ACTIONS}")
    print(f"支持的来源: {SOURCES}")
    print(f"支持的场景: {SCENES}")
    print(f"支持的路由: {ROUTES}")
    print(f"支持的决策来源: {DECISION_SOURCES}")

    print("\n--- 1. Observation 测试 ---")
    obs = Observation(
        scene="industrial",
        node_id="edge_node_0",
        object_id="machine-001",
        payload={"Air temperature [K]": 305.2, "Torque [Nm]": 45.2},
        deadline_ms=200,
    )
    print(f"创建: {obs}")
    print(f"字典转换: {len(obs.to_dict())} 个字段")

    print("\n--- 2. EdgeDecision 测试 ---")
    ed = EdgeDecision(
        event_id=obs.event_id,
        trace_id=obs.trace_id,
        scene="industrial",
        node_id="edge_node_0",
        predicted_label="Heat Dissipation Failure",
        risk_level="high",
        action="shutdown",
        confidence=0.85,
        model_version="industrial-edge-v1",
        reason="温度过高",
        inference_ms=18.5,
    )
    print(f"创建: {ed}")
    print(f"风险等级排序值: {ed.risk_level_order()}")

    print("\n--- 3. RouteDecision 测试 ---")
    rd = RouteDecision(
        trace_id=obs.trace_id,
        route="EdgeCloud",
        reason_codes=["HIGH_RISK", "LOW_CONFIDENCE"],
        estimated_total_ms=145,
        remaining_deadline_ms=170,
    )
    print(f"创建: {rd}")

    print("\n--- 4. CloudReview 测试 ---")
    cr = CloudReview(
        trace_id=obs.trace_id,
        reviewed_label="Heat Dissipation Failure",
        risk_level="high",
        action="shutdown",
        confidence=0.95,
        model="qwen3.5-35b-a3b",
        reason="云端复核确认",
        latency_ms=120,
    )
    print(f"创建: {cr}")

    print("\n--- 5. FinalDecision 测试 ---")
    fd = FinalDecision(
        trace_id=obs.trace_id,
        scene="industrial",
        final_label="Heat Dissipation Failure",
        final_risk_level="high",
        final_action="shutdown",
        confidence=0.95,
        decision_source="cloud_reviewed",
        conflict_detected=False,
        arbitration_reason="边缘与云端一致",
        end_to_end_ms=158,
        deadline_met=True,
    )
    print(f"创建: {fd}")

    print("\n--- 6. Event 与 EdgeDecision/CloudReview 转换测试 ---")
    event_from_edge = Event.from_edge_decision(ed)
    print(f"从 EdgeDecision 转 Event: {event_from_edge}")
    event_from_cloud = Event.from_cloud_review(cr)
    print(f"从 CloudReview 转 Event: {event_from_cloud}")

    print("\n--- 7. 原有 Event 兼容性测试 ---")
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
        },
        routing_path="CloudEdge",
    )
    print(f"原有方式创建: {test_event}")
    restored = Event.from_dict(test_event.to_dict())
    print(f"从字典恢复: {restored}")

    print("\n--- 8. EnergyEvent 能源事件测试 ---")
    print(f"能源节点类型: {ENERGY_NODE_TYPES}")
    print(f"能源动作: {ENERGY_ACTIONS}")
    gen_event = build_energy_event(
        node_id="gen_node_0",
        node_type="generator",
        grid_id="grid_a",
        stability_label="Stable",
        risk_level="low",
        action="maintain",
        confidence=0.92,
        current_power=100.0,
        requested_power_adjustment=20.0,
        source="edge",
        priority=1,
    )
    print(f"发电节点事件: {gen_event}")
    con_event = build_energy_event(
        node_id="con_node_0",
        node_type="consumer",
        grid_id="grid_a",
        stability_label="Overload",
        risk_level="high",
        action="reduce_load",
        confidence=0.88,
        current_power=50.0,
        requested_power_adjustment=-15.0,
        source="edge",
        priority=3,
    )
    print(f"消费节点事件: {con_event}")
    restored_energy = EnergyEvent.from_dict(con_event.to_dict())
    print(f"从字典恢复: {restored_energy}")

    print("\n✅ 所有测试通过！")


if __name__ == "__main__":
    main()
