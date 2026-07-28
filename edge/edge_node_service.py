from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routing import (
    Router,
    NetworkStatus,
    NetworkSimulator,
    RoutingMode,
    create_router,
    create_network_simulator
)
from cloud import CloudReviewer
from edge.perception.infer_edge import infer_edge

app = FastAPI(title="Edge Node Service", version="1.0.0")

EDGE_NODE_ID = os.environ.get("EDGE_NODE_ID", "edge_0")

router_instance = create_router(confidence_threshold=0.7)
network_simulator = create_network_simulator(seed=42)
cloud_reviewer = CloudReviewer()

class DeviceState(BaseModel):
    product_type: str = Field("L", description="Product type: L/M/H")
    air_temperature_k: float = Field(..., description="Air temperature in Kelvin")
    process_temperature_k: float = Field(..., description="Process temperature in Kelvin")
    rotational_speed_rpm: int = Field(..., description="Rotational speed in RPM")
    torque_nm: float = Field(..., description="Torque in Nm")
    tool_wear_min: int = Field(..., description="Tool wear in minutes")

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
    final_decision: str = ""
    final_action: str = ""

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
        action = "紧急停机并上报云端"
        confidence = 0.8 + (fault_prob - 0.7) * 0.4
    elif fault_prob > 0.4:
        fault_label = 1
        risk_level = "medium"
        action = "建议维护并持续监控"
        confidence = 0.7 + (fault_prob - 0.4) * 0.3
    else:
        fault_label = 0
        risk_level = "low"
        action = "正常运行"
        confidence = 0.85 + (0.4 - fault_prob) * 0.15
    
    confidence = min(confidence, 0.99)
    
    fault_label_names = {
        0: "Normal",
        1: "Fault Detected"
    }
    
    return {
        "fault_label": fault_label,
        "fault_label_name": fault_label_names[fault_label],
        "fault_prob": round(fault_prob, 4),
        "risk_level": risk_level,
        "action": action,
        "confidence": round(confidence, 4)
    }

def perform_cloud_review(device_id: str, result: Dict[str, Any], device_state: DeviceState) -> CloudReviewInfo:
    cloud_review_info = CloudReviewInfo()
    
    edge_summary = {
        "device_id": device_id,
        "edge_fault_label": result["fault_label_name"],
        "edge_risk_level": result["risk_level"],
        "edge_action": result["action"],
        "edge_confidence": result["confidence"],
        "device_features": {
            "air_temperature_k": device_state.air_temperature_k,
            "process_temperature_k": device_state.process_temperature_k,
            "rotational_speed_rpm": device_state.rotational_speed_rpm,
            "torque_nm": device_state.torque_nm,
            "tool_wear_min": device_state.tool_wear_min
        }
    }
    
    try:
        review_result = cloud_reviewer.review(edge_summary)
        
        cloud_review_info.reviewed = True
        cloud_review_info.review_id = review_result.get("review_id", "")
        cloud_review_info.gcm_fault_label = review_result.get("gcm_fault_label", "")
        cloud_review_info.gcm_risk_level = review_result.get("gcm_risk_level", "")
        cloud_review_info.gcm_action = review_result.get("gcm_action", "")
        cloud_review_info.gcm_confidence = review_result.get("gcm_confidence", 0.0)
        cloud_review_info.gcm_reason = review_result.get("gcm_reason", "")
        cloud_review_info.consistent_with_edge = review_result.get("consistent_with_edge", False)
        cloud_review_info.latency_ms = review_result.get("latency_ms", 0.0)
    except Exception as e:
        cloud_review_info.reviewed = False
        cloud_review_info.gcm_reason = f"云端复核失败: {str(e)}"
    
    return cloud_review_info

def make_final_decision(routing_mode: RoutingMode, edge_result: Dict[str, Any], 
                         cloud_review: Optional[CloudReviewInfo]) -> tuple[str, str]:
    if routing_mode == RoutingMode.EDGE_ONLY:
        return "edge", edge_result["action"]
    elif routing_mode == RoutingMode.CLOUD_ONLY:
        if cloud_review and cloud_review.reviewed:
            return "cloud", cloud_review.gcm_action
        return "edge", edge_result["action"]
    elif routing_mode == RoutingMode.CLOUD_EDGE:
        if cloud_review and cloud_review.reviewed:
            if cloud_review.consistent_with_edge:
                return "consensus", edge_result["action"]
            else:
                return "cloud_disagrees", f"边缘: {edge_result['action']}, 云端: {cloud_review.gcm_action}"
        return "edge", edge_result["action"]
    elif routing_mode == RoutingMode.WEAKNET_AUTONOMY:
        return "edge_autonomy", edge_result["action"]
    else:
        return "edge", edge_result["action"]

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "edge_node_id": EDGE_NODE_ID,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict", response_model=InferenceResult)
async def predict(device_state: DeviceState, device_id: Optional[str] = None):
    start_time = time.time()
    device_id = device_id or f"{EDGE_NODE_ID}_{int(time.time())}"
    
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
        
        network_status = network_simulator.simulate_status_change(probability=0.1)
        router_instance.set_network_status(network_status)
        network_stats = network_simulator.get_network_stats()
        
        routing_decision = router_instance.decide(
            confidence=result["confidence"],
            risk_level=result["risk_level"],
            fault_prob=result["fault_prob"],
            network_stats=network_stats
        )
        
        routing_info = RoutingInfo(
            mode=routing_decision.mode.value,
            reason=routing_decision.reason,
            network_status=routing_decision.network_status,
            pending_review=routing_decision.pending_review
        )
        
        cloud_review = None
        if routing_decision.mode in [RoutingMode.CLOUD_EDGE, RoutingMode.CLOUD_ONLY]:
            cloud_review = perform_cloud_review(device_id, result, device_state)
        
        final_decision, final_action = make_final_decision(
            routing_decision.mode, result, cloud_review
        )
        
        return InferenceResult(
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
            cloud_review=cloud_review,
            final_decision=final_decision,
            final_action=final_action
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config():
    return {
        "edge_node_id": EDGE_NODE_ID,
        "supported_features": ["fault_detection", "risk_assessment", "action_suggestion", "dynamic_routing", "cloud_review"],
        "routing_modes": [mode.value for mode in RoutingMode],
        "model_type": "edge_perception_model_with_mock_fallback",
        "version": "2.0.0",
        "cloud_review_available": True
    }

@app.get("/network/status")
async def get_network_status():
    network_stats = network_simulator.get_network_stats()
    return {
        "status": network_stats.status.value,
        "latency_ms": network_stats.latency_ms,
        "bandwidth_mbps": network_stats.bandwidth_mbps,
        "packet_loss_rate": network_stats.packet_loss_rate,
        "timestamp": network_stats.timestamp
    }

@app.post("/network/set_status")
async def set_network_status(status: str):
    try:
        network_status = NetworkStatus(status)
        network_simulator.set_status(network_status)
        router_instance.set_network_status(network_status)
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
