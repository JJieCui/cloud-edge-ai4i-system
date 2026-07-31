from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uvicorn
import json
import os
import sys
import time
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routing import (
    Router,
    NetworkStatus,
    NetworkSimulator,
    RoutingMode,
    create_router,
    create_network_simulator,
)
from cloud import CloudReviewer
from consistency.event_schema import (
    Observation,
    EdgeDecision,
    RouteDecision,
    CloudReview,
    FinalDecision,
    Event,
    EnergyEvent,
    RISK_LEVELS,
    ACTIONS,
    SCENES,
    ROUTES,
)
from consistency.conflict_detector import ConflictDetector
from consistency.conflict_resolver import ConflictResolver

try:
    from edge.perception.infer_edge import infer_edge
    _HAS_EDGE_MODEL = True
except ImportError:
    _HAS_EDGE_MODEL = False

app = FastAPI(title="Edge Node Service", version="3.0.0")

EDGE_NODE_ID = os.environ.get("EDGE_NODE_ID", "edge_0")

router_instance = create_router(confidence_threshold=0.7)
network_simulator = create_network_simulator(seed=42)
cloud_reviewer = CloudReviewer()
conflict_detector = ConflictDetector(duplicate_time_window_s=60, stale_threshold_ms=5000)
conflict_resolver = ConflictResolver(strategy="highest_risk_first", network_status="normal")

_pending_events: List[Event] = []
_service_log: List[Dict[str, Any]] = []


class DeviceState(BaseModel):
    product_type: str = Field("L", description="Product type: L/M/H")
    air_temperature_k: float = Field(..., description="Air temperature in Kelvin")
    process_temperature_k: float = Field(..., description="Process temperature in Kelvin")
    rotational_speed_rpm: int = Field(..., description="Rotational speed in RPM")
    torque_nm: float = Field(..., description="Torque in Nm")
    tool_wear_min: int = Field(..., description="Tool wear in minutes")


class EnergyDeviceState(BaseModel):
    node_type: str = Field("generator", description="Node type: generator/consumer")
    grid_id: str = Field("grid_a", description="Grid identifier")
    node_id: str = Field(..., description="Edge node identifier")
    reaction_time_s: float = Field(1.0, description="Node reaction time in seconds")
    power_output: float = Field(..., description="Current power output/consumption in kW")
    price_elasticity: float = Field(0.1, description="Price elasticity coefficient")
    time_step: float = Field(1.0, description="Current time step")
    local_rtt_ms: float = Field(20.0, description="Local network RTT to control center")


class RoutingInfo(BaseModel):
    mode: str
    reason: str
    network_status: str
    pending_review: bool


class CloudReviewInfo(BaseModel):
    reviewed: bool = False
    gcm_fault_label: str = ""
    gcm_risk_level: str = ""
    gcm_action: str = ""
    gcm_confidence: float = 0.0
    gcm_reason: str = ""
    consistent_with_edge: bool = False
    latency_ms: float = 0.0
    review_id: str = ""


class InferenceResult(BaseModel):
    trace_id: str
    edge_node_id: str
    device_id: str
    fault_label: int
    fault_prob: float
    risk_level: str
    action: str
    confidence: float
    inference_source: str = "model"
    model_name: str = "RandomForest"
    fallback_used: bool = False
    fallback_reason: str = ""
    inference_time_ms: float
    routing: RoutingInfo
    cloud_review: Optional[CloudReviewInfo] = None
    consistency_result: Optional[Dict[str, Any]] = None
    final_decision: str = ""
    final_action: str = ""
    final_decision_obj: Optional[Dict[str, Any]] = None
    end_to_end_ms: float = 0.0
    deadline_met: bool = True


class EnergyInferenceResult(BaseModel):
    trace_id: str
    edge_node_id: str
    node_id: str
    grid_id: str
    stability_label: str
    risk_level: str
    action: str
    confidence: float
    power_adjustment: float = 0.0
    inference_time_ms: float
    routing: RoutingInfo
    cloud_review: Optional[CloudReviewInfo] = None
    consistency_result: Optional[Dict[str, Any]] = None
    final_decision: str = ""
    final_action: str = ""
    end_to_end_ms: float = 0.0
    deadline_met: bool = True


def _risk_to_action(risk_level: str, scene: str) -> str:
    if scene == "industrial":
        mapping = {"low": "monitor", "medium": "maintain", "high": "shutdown", "critical": "replace"}
    else:
        mapping = {"low": "maintain", "medium": "reduce_load", "high": "emergency_limit", "critical": "emergency_limit"}
    return mapping.get(risk_level, "monitor" if scene == "industrial" else "maintain")


def _normalize_risk_level(risk_level: str) -> str:
    valid_levels = ["low", "medium", "high", "critical"]
    rl = risk_level.lower() if risk_level else "low"
    for vl in valid_levels:
        if vl in rl:
            return vl
    return "low"


def _normalize_action(action: str, scene: str) -> str:
    if scene == "industrial":
        valid_actions = ["monitor", "warn", "maintain", "shutdown", "replace"]
    else:
        valid_actions = ["maintain", "reduce_load", "increase_generation", "emergency_limit"]
    al = action.lower() if action else "monitor"
    for va in valid_actions:
        if va in al:
            return va
    return valid_actions[0]


def mock_inference(device_state: DeviceState) -> Dict[str, Any]:
    air_temp = device_state.air_temperature_k
    process_temp = device_state.process_temperature_k
    torque = device_state.torque_nm
    tool_wear = device_state.tool_wear_min

    fault_prob = 0.0
    if process_temp > 310:
        fault_prob += 0.3
    if torque > 60:
        fault_prob += 0.25
    if tool_wear > 150:
        fault_prob += 0.35
    if air_temp > 300:
        fault_prob += 0.1

    fault_prob = min(fault_prob, 0.95)

    if fault_prob > 0.7:
        fault_label = 1
        risk_level = "high"
        confidence = 0.8 + (fault_prob - 0.7) * 0.4
    elif fault_prob > 0.4:
        fault_label = 1
        risk_level = "medium"
        confidence = 0.7 + (fault_prob - 0.4) * 0.3
    else:
        fault_label = 0
        risk_level = "low"
        confidence = 0.85 + (0.4 - fault_prob) * 0.15

    confidence = min(confidence, 0.99)

    return {
        "fault_label": fault_label,
        "fault_label_name": "Fault Detected" if fault_label == 1 else "Normal",
        "fault_prob": round(fault_prob, 4),
        "risk_level": risk_level,
        "action": _risk_to_action(risk_level, "industrial"),
        "confidence": round(confidence, 4),
    }


def mock_energy_inference(device_state: EnergyDeviceState) -> Dict[str, Any]:
    power = device_state.power_output
    rtt = device_state.local_rtt_ms

    stability_prob = 0.9
    if power > 150:
        stability_prob -= 0.3
    if rtt > 100:
        stability_prob -= 0.2
    stability_prob = max(stability_prob, 0.3)

    if stability_prob > 0.7:
        stability_label = "Stable"
        risk_level = "low"
    elif stability_prob > 0.5:
        stability_label = "Warning"
        risk_level = "medium"
    else:
        stability_label = "Critical"
        risk_level = "high"

    action = _risk_to_action(risk_level, "energy")
    power_adjustment = (1.0 - stability_prob) * 30.0

    return {
        "stability_label": stability_label,
        "risk_level": risk_level,
        "action": action,
        "confidence": round(stability_prob, 4),
        "power_adjustment": round(power_adjustment, 2),
    }


def perform_cloud_review(
    device_id: str,
    result: Dict[str, Any],
    trace_id: str,
    scene: str,
) -> CloudReview:
    edge_summary = {
        "device_id": device_id,
        "edge_fault_label": result.get("fault_label_name", result.get("stability_label", "")),
        "edge_risk_level": result["risk_level"],
        "edge_action": result["action"],
        "edge_confidence": result["confidence"],
    }

    try:
        review_result = cloud_reviewer.review(edge_summary)
        return CloudReview(
            trace_id=trace_id,
            reviewed_label=review_result.get("gcm_fault_label", "Unknown"),
            risk_level=_normalize_risk_level(review_result.get("gcm_risk_level", "low")),
            action=_normalize_action(review_result.get("gcm_action", "monitor"), scene),
            confidence=review_result.get("gcm_confidence", 0.0),
            model=review_result.get("used_model", "mock"),
            reason=review_result.get("gcm_reason", ""),
            latency_ms=review_result.get("latency_ms", 0.0),
            fallback_used=review_result.get("fallback_used", False),
        )
    except Exception as e:
        return CloudReview(
            trace_id=trace_id,
            reviewed_label="Unknown",
            risk_level="low",
            action="monitor" if scene == "industrial" else "maintain",
            confidence=0.0,
            model="fallback",
            reason=f"云端复核失败: {str(e)}",
            latency_ms=0.0,
            fallback_used=True,
        )


def perform_consistency_check(
    events: List[Event],
    network_status: str,
) -> Dict[str, Any]:
    if len(events) < 2:
        return {
            "conflict_detected": False,
            "conflict_count": 0,
            "final_decision_obj": None,
            "resolution_log": [],
        }

    detect_result = conflict_detector.detect(events)
    resolver = ConflictResolver(
        strategy="highest_risk_first",
        network_status=network_status,
    )
    resolve_result = resolver.resolve(events, detect_result["conflict_details"])

    final_decision_obj = resolve_result.get("final_decision_obj")
    final_decision_dict = final_decision_obj.to_dict() if final_decision_obj else None

    return {
        "conflict_detected": detect_result["conflict_count"] > 0,
        "conflict_count": detect_result["conflict_count"],
        "conflict_rate": detect_result["conflict_rate"],
        "conflict_details": detect_result["conflict_details"],
        "final_decision_obj": final_decision_dict,
        "final_decision_dict": final_decision_dict,
        "resolution_log": resolve_result.get("resolution_log", []),
        "effective_strategy": resolve_result.get("effective_strategy", "highest_risk_first"),
        "success_rate": resolve_result.get("success_rate", 0.0),
    }


def _log_request(trace_id: str, result: Dict[str, Any]) -> None:
    _service_log.append({
        "trace_id": trace_id,
        "timestamp": datetime.now().isoformat(),
        **result,
    })


def _route_mode_to_string(mode: RoutingMode) -> str:
    mapping = {
        RoutingMode.EDGE_ONLY: "EdgeOnly",
        RoutingMode.CLOUD_ONLY: "CloudOnly",
        RoutingMode.CLOUD_EDGE: "EdgeCloud",
        RoutingMode.WEAKNET_AUTONOMY: "SafeFallback",
    }
    return mapping.get(mode, "EdgeOnly")


def _string_to_route_mode(route_str: str) -> RoutingMode:
    mapping = {
        "EdgeOnly": RoutingMode.EDGE_ONLY,
        "CloudOnly": RoutingMode.CLOUD_ONLY,
        "EdgeCloud": RoutingMode.CLOUD_EDGE,
        "SafeFallback": RoutingMode.WEAKNET_AUTONOMY,
        "DeferredReview": RoutingMode.WEAKNET_AUTONOMY,
    }
    return mapping.get(route_str, RoutingMode.EDGE_ONLY)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "edge_node_id": EDGE_NODE_ID,
        "version": "3.0.0",
        "supported_scenes": SCENES,
        "supported_routing_modes": [m.value for m in RoutingMode],
        "has_edge_model": _HAS_EDGE_MODEL,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/predict", response_model=InferenceResult)
async def predict(device_state: DeviceState, device_id: Optional[str] = None):
    start_time = time.time()
    trace_id = f"trace-{uuid.uuid4().hex[:12]}"
    device_id = device_id or f"{EDGE_NODE_ID}_{int(time.time())}"

    network_status_val = network_simulator.simulate_status_change(probability=0.1)
    router_instance.set_network_status(network_status_val)
    network_stats = network_simulator.get_network_stats()
    network_status_str = network_status_val.value

    try:
        try:
            result = infer_edge(
                {
                    "product_type": device_state.product_type,
                    "air_temperature_k": device_state.air_temperature_k,
                    "process_temperature_k": device_state.process_temperature_k,
                    "rotational_speed_rpm": device_state.rotational_speed_rpm,
                    "torque_nm": device_state.torque_nm,
                    "tool_wear_min": device_state.tool_wear_min,
                }
            )
            inference_source = "model"
            model_name = "RandomForest"
            fallback_used = False
            fallback_reason = ""
        except Exception as e:
            result = mock_inference(device_state)
            inference_source = "mock"
            model_name = "mock_inference"
            fallback_used = True
            fallback_reason = str(e)

        inference_time_ms = round((time.time() - start_time) * 1000, 2)

        obs = Observation(
            scene="industrial",
            node_id=EDGE_NODE_ID,
            object_id=device_id,
            payload={
                "product_type": device_state.product_type,
                "air_temperature_k": device_state.air_temperature_k,
                "process_temperature_k": device_state.process_temperature_k,
                "rotational_speed_rpm": device_state.rotational_speed_rpm,
                "torque_nm": device_state.torque_nm,
                "tool_wear_min": device_state.tool_wear_min,
            },
            network={
                "rtt_ms": network_stats.latency_ms,
                "packet_loss": network_stats.packet_loss_rate,
                "connected": network_status_val != NetworkStatus.DISCONNECTED,
            },
            trace_id=trace_id,
        )

        ed = EdgeDecision(
            event_id=obs.event_id,
            trace_id=trace_id,
            scene="industrial",
            node_id=EDGE_NODE_ID,
            predicted_label=result["fault_label_name"],
            risk_level=_normalize_risk_level(result["risk_level"]),
            action=_normalize_action(result["action"], "industrial"),
            confidence=result["confidence"],
            model_version=model_name,
            reason=f"ProcessTemp={device_state.process_temperature_k}K, Torque={device_state.torque_nm}Nm",
            inference_ms=inference_time_ms,
            data_age_ms=0,
        )

        routing_decision = router_instance.decide(
            confidence=result["confidence"],
            risk_level=result["risk_level"],
            fault_prob=result["fault_prob"],
            network_stats=network_stats,
        )

        route_decision = RouteDecision(
            trace_id=trace_id,
            route=_route_mode_to_string(routing_decision.mode),
            reason_codes=[routing_decision.reason] if routing_decision.reason else [],
            estimated_total_ms=inference_time_ms + network_stats.latency_ms,
            remaining_deadline_ms=max(200 - inference_time_ms - network_stats.latency_ms, 0),
        )

        routing_info = RoutingInfo(
            mode=routing_decision.mode.value,
            reason=routing_decision.reason,
            network_status=routing_decision.network_status,
            pending_review=routing_decision.pending_review,
        )

        cloud_review_info = None
        cloud_review_obj = None
        if routing_decision.mode in [RoutingMode.CLOUD_EDGE, RoutingMode.CLOUD_ONLY]:
            cloud_review_obj = perform_cloud_review(
                device_id, result, trace_id, "industrial"
            )
            cloud_review_info = CloudReviewInfo(
                reviewed=True,
                gcm_fault_label=cloud_review_obj.reviewed_label,
                gcm_risk_level=cloud_review_obj.risk_level,
                gcm_action=cloud_review_obj.action,
                gcm_confidence=cloud_review_obj.confidence,
                gcm_reason=cloud_review_obj.reason,
                consistent_with_edge=(
                    cloud_review_obj.action == ed.action
                    and cloud_review_obj.risk_level == ed.risk_level
                ),
                latency_ms=cloud_review_obj.latency_ms,
                review_id=trace_id,
            )

        edge_event = Event.from_edge_decision(ed)
        events_for_consistency = [edge_event]

        if cloud_review_obj:
            cloud_event = Event.from_cloud_review(cloud_review_obj)
            events_for_consistency.append(cloud_event)

        consistency_result = perform_consistency_check(events_for_consistency, network_status_str)

        if consistency_result["final_decision_obj"]:
            fd = consistency_result["final_decision_obj"]
            final_decision_source = fd.get("decision_source", "consistency_resolved")
            final_action = fd.get("final_action", ed.action)
        else:
            routing_mode = routing_decision.mode
            if routing_mode == RoutingMode.EDGE_ONLY:
                final_decision_source = "edge_only"
                final_action = ed.action
            elif routing_mode == RoutingMode.CLOUD_ONLY and cloud_review_obj:
                final_decision_source = "cloud_only"
                final_action = cloud_review_obj.action
            elif routing_mode == RoutingMode.CLOUD_EDGE and cloud_review_obj:
                if cloud_review_obj.action == ed.action:
                    final_decision_source = "cloud_reviewed"
                else:
                    final_decision_source = "cloud_reviewed"
                final_action = cloud_review_obj.action
            else:
                final_decision_source = "safe_fallback"
                final_action = ed.action

        final_decision_str = final_decision_source

        end_to_end_ms = round((time.time() - start_time) * 1000, 2)
        deadline_met = end_to_end_ms <= 200

        result_dict = InferenceResult(
            trace_id=trace_id,
            edge_node_id=EDGE_NODE_ID,
            device_id=device_id,
            fault_label=result["fault_label"],
            fault_prob=result["fault_prob"],
            risk_level=result["risk_level"],
            action=result["action"],
            confidence=result["confidence"],
            inference_source=inference_source,
            model_name=model_name,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            inference_time_ms=inference_time_ms,
            routing=routing_info,
            cloud_review=cloud_review_info,
            consistency_result=consistency_result,
            final_decision=final_decision_str,
            final_action=final_action,
            final_decision_obj=(
                consistency_result["final_decision_obj"]
                if consistency_result.get("final_decision_obj")
                else None
            ),
            end_to_end_ms=end_to_end_ms,
            deadline_met=deadline_met,
        )

        _log_request(trace_id, result_dict.model_dump())

        return result_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/energy", response_model=EnergyInferenceResult)
async def predict_energy(device_state: EnergyDeviceState):
    start_time = time.time()
    trace_id = f"trace-{uuid.uuid4().hex[:12]}"

    network_status_val = network_simulator.simulate_status_change(probability=0.1)
    router_instance.set_network_status(network_status_val)
    network_stats = network_simulator.get_network_stats()
    network_status_str = network_status_val.value

    try:
        result = mock_energy_inference(device_state)
        inference_time_ms = round((time.time() - start_time) * 1000, 2)

        obs = Observation(
            scene="energy",
            node_id=device_state.node_id,
            object_id=f"{device_state.grid_id}_{device_state.node_id}",
            payload={
                "node_type": device_state.node_type,
                "power_output": device_state.power_output,
                "local_rtt_ms": device_state.local_rtt_ms,
            },
            network={
                "rtt_ms": network_stats.latency_ms,
                "packet_loss": network_stats.packet_loss_rate,
                "connected": network_status_val != NetworkStatus.DISCONNECTED,
            },
            trace_id=trace_id,
        )

        ed = EdgeDecision(
            event_id=obs.event_id,
            trace_id=trace_id,
            scene="energy",
            node_id=device_state.node_id,
            predicted_label=result["stability_label"],
            risk_level=_normalize_risk_level(result["risk_level"]),
            action=_normalize_action(result["action"], "energy"),
            confidence=result["confidence"],
            model_version="energy_mock_v1",
            reason=f"Power={device_state.power_output}kW, RTT={device_state.local_rtt_ms}ms",
            inference_ms=inference_time_ms,
            data_age_ms=0,
        )

        routing_decision = router_instance.decide(
            confidence=result["confidence"],
            risk_level=result["risk_level"],
            fault_prob=1.0 - result["confidence"],
            network_stats=network_stats,
        )

        route_decision = RouteDecision(
            trace_id=trace_id,
            route=_route_mode_to_string(routing_decision.mode),
            reason_codes=[routing_decision.reason] if routing_decision.reason else [],
            estimated_total_ms=inference_time_ms + network_stats.latency_ms,
            remaining_deadline_ms=max(200 - inference_time_ms - network_stats.latency_ms, 0),
        )

        routing_info = RoutingInfo(
            mode=routing_decision.mode.value,
            reason=routing_decision.reason,
            network_status=routing_decision.network_status,
            pending_review=routing_decision.pending_review,
        )

        energy_event = EnergyEvent(
            node_id=device_state.node_id,
            node_type=device_state.node_type,
            grid_id=device_state.grid_id,
            stability_label=result["stability_label"],
            risk_level=_normalize_risk_level(result["risk_level"]),
            action=_normalize_action(result["action"], "energy"),
            confidence=result["confidence"],
            current_power=device_state.power_output,
            requested_power_adjustment=result["power_adjustment"],
            source="edge",
            trace_id=trace_id,
        )

        edge_event = Event.from_edge_decision(ed)
        consistency_result = perform_consistency_check([edge_event], network_status_str)

        if consistency_result["final_decision_obj"]:
            fd = consistency_result["final_decision_obj"]
            final_decision_source = fd.get("decision_source", "consistency_resolved")
            final_action = fd.get("final_action", ed.action)
        else:
            final_decision_source = "edge_only"
            final_action = ed.action

        end_to_end_ms = round((time.time() - start_time) * 1000, 2)
        deadline_met = end_to_end_ms <= 200

        result_dict = EnergyInferenceResult(
            trace_id=trace_id,
            edge_node_id=EDGE_NODE_ID,
            node_id=device_state.node_id,
            grid_id=device_state.grid_id,
            stability_label=result["stability_label"],
            risk_level=result["risk_level"],
            action=result["action"],
            confidence=result["confidence"],
            power_adjustment=result["power_adjustment"],
            inference_time_ms=inference_time_ms,
            routing=routing_info,
            cloud_review=None,
            consistency_result=consistency_result,
            final_decision=final_decision_source,
            final_action=final_action,
            end_to_end_ms=end_to_end_ms,
            deadline_met=deadline_met,
        )

        _log_request(trace_id, result_dict.model_dump())

        return result_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    return {
        "edge_node_id": EDGE_NODE_ID,
        "supported_scenes": SCENES,
        "supported_features": [
            "fault_detection",
            "risk_assessment",
            "action_suggestion",
            "dynamic_routing",
            "cloud_review",
            "consistency_check",
            "energy_scene",
            "traceability",
        ],
        "routing_modes": [mode.value for mode in RoutingMode],
        "actions": ACTIONS,
        "energy_actions": ["maintain", "reduce_load", "increase_generation", "emergency_limit"],
        "model_type": "edge_perception_with_mock_fallback",
        "version": "3.0.0",
        "cloud_review_available": True,
        "consistency_available": True,
        "has_edge_model": _HAS_EDGE_MODEL,
    }


@app.get("/network/status")
async def get_network_status():
    network_stats = network_simulator.get_network_stats()
    return {
        "status": network_stats.status.value,
        "latency_ms": network_stats.latency_ms,
        "bandwidth_mbps": network_stats.bandwidth_mbps,
        "packet_loss_rate": network_stats.packet_loss_rate,
        "timestamp": network_stats.timestamp,
    }


@app.post("/network/set_status")
async def set_network_status(status: str):
    try:
        network_status = NetworkStatus(status)
        network_simulator.set_status(network_status)
        router_instance.set_network_status(network_status)
        conflict_resolver.network_status = status
        return {"success": True, "status": status}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid network status: {status}")


@app.get("/routing/log")
async def get_routing_log():
    return router_instance.get_log()


@app.post("/routing/save_log")
async def save_routing_log(file_path: str = "logs/routing_log.csv"):
    try:
        router_instance.save_log_to_csv(file_path, append=False)
        return {"success": True, "file_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cloud/stats")
async def get_cloud_stats():
    return cloud_reviewer.get_stats()


@app.get("/service/log")
async def get_service_log(limit: int = 100):
    return {
        "total_entries": len(_service_log),
        "entries": _service_log[-limit:],
    }


@app.post("/consistency/check")
async def check_consistency(events_payload: List[Dict[str, Any]]):
    try:
        events = [Event.from_dict(e) for e in events_payload]
        network_status_str = network_simulator.get_status().value
        result = perform_consistency_check(events, network_status_str)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
