# 本科生3：边缘节点 FastAPI 服务
# TODO: /predict 接口，接收设备状态并返回边缘判断
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uvicorn
import json
import os
import sys
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

app = FastAPI(title="Edge Node Service", version="1.0.0")

EDGE_NODE_ID = os.environ.get("EDGE_NODE_ID", "edge_0")

router_instance = create_router(confidence_threshold=0.7)
network_simulator = create_network_simulator(seed=42)

class DeviceState(BaseModel):
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

class InferenceResult(BaseModel):
    edge_node_id: str
    fault_label: int
    fault_prob: float
    risk_level: str
    action: str
    confidence: float
    inference_time_ms: float
    routing: RoutingInfo

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
    
    return {
        "fault_label": fault_label,
        "fault_prob": round(fault_prob, 4),
        "risk_level": risk_level,
        "action": action,
        "confidence": round(confidence, 4)
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "edge_node_id": EDGE_NODE_ID,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict", response_model=InferenceResult)
async def predict(device_state: DeviceState):
    import time
    start_time = time.time()
    
    try:
        result = mock_inference(device_state)
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
        
        return InferenceResult(
            edge_node_id=EDGE_NODE_ID,
            fault_label=result["fault_label"],
            fault_prob=result["fault_prob"],
            risk_level=result["risk_level"],
            action=result["action"],
            confidence=result["confidence"],
            inference_time_ms=inference_time_ms,
            routing=routing_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config():
    return {
        "edge_node_id": EDGE_NODE_ID,
        "supported_features": ["fault_detection", "risk_assessment", "action_suggestion", "dynamic_routing"],
        "routing_modes": [mode.value for mode in RoutingMode],
        "model_type": "mock_baseline",
        "version": "1.0.0"
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")