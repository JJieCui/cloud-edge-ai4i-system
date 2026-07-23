from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
import csv
import os
from .network_simulator import NetworkStatus, NetworkStats
from .policy import (
    RoutingPolicy,
    CompositePolicy,
    CriticalRiskPolicy,
    ConfidenceThresholdPolicy,
    RiskLevelPolicy,
    NetworkAwarePolicy,
    create_network_aware_policy
)

class RoutingMode(Enum):
    EDGE_ONLY = "EdgeOnly"
    CLOUD_ONLY = "CloudOnly"
    CLOUD_EDGE = "CloudEdge"
    WEAKNET_AUTONOMY = "WeakNetAutonomy"

class RoutingDecision:
    def __init__(self):
        self.mode: RoutingMode = RoutingMode.EDGE_ONLY
        self.reason: str = ""
        self.confidence_threshold: float = 0.0
        self.risk_level: str = ""
        self.network_status: str = ""
        self.timestamp: str = ""
        self.latency_ms: float = 0.0
        self.pending_review: bool = False

class Router:
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 high_risk_threshold: float = 0.6,
                 critical_risk_threshold: float = 0.85,
                 network_status: NetworkStatus = NetworkStatus.NORMAL,
                 policy: Optional[RoutingPolicy] = None):
        self.confidence_threshold = confidence_threshold
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold
        self.network_status = network_status
        self.policy = policy or create_network_aware_policy()
        self._routing_log: list[Dict[str, Any]] = []
    
    def set_network_status(self, status: NetworkStatus) -> None:
        self.network_status = status
    
    def decide(self, 
               confidence: float, 
               risk_level: str,
               fault_prob: float = 0.0,
               network_stats: Optional[NetworkStats] = None) -> RoutingDecision:
        
        decision = RoutingDecision()
        decision.confidence_threshold = self.confidence_threshold
        decision.risk_level = risk_level
        decision.network_status = self.network_status.value
        decision.timestamp = datetime.now().isoformat()
        decision.pending_review = False
        
        if network_stats is not None:
            decision.latency_ms = network_stats.latency_ms
        
        if self.network_status == NetworkStatus.DISCONNECTED:
            decision.mode = RoutingMode.EDGE_ONLY
            decision.reason = "网络断开，边缘自治"
        elif self.network_status == NetworkStatus.WEAK:
            if risk_level == "high":
                decision.mode = RoutingMode.WEAKNET_AUTONOMY
                decision.reason = "弱网高风险，边缘自治并记录告警待后续上报"
                decision.pending_review = True
            elif confidence < self.confidence_threshold:
                decision.mode = RoutingMode.WEAKNET_AUTONOMY
                decision.reason = "弱网低置信度，边缘自治并标记待复核"
                decision.pending_review = True
            elif risk_level == "medium":
                decision.mode = RoutingMode.WEAKNET_AUTONOMY
                decision.reason = "弱网中等风险，边缘自治并记录"
                decision.pending_review = True
            else:
                decision.mode = RoutingMode.EDGE_ONLY
                decision.reason = "弱网低风险，边缘独立处理"
        elif fault_prob >= self.critical_risk_threshold and self.network_status == NetworkStatus.NORMAL:
            decision.mode = RoutingMode.CLOUD_ONLY
            decision.reason = "极高风险，完全由云端处理"
        elif risk_level == "high":
            if self.network_status in [NetworkStatus.NORMAL, NetworkStatus.HIGH_LATENCY]:
                decision.mode = RoutingMode.CLOUD_EDGE
                decision.reason = "高风险，需要云端复核"
            else:
                decision.mode = RoutingMode.EDGE_ONLY
                decision.reason = "高风险但网络不佳，边缘自治"
        elif confidence < self.confidence_threshold:
            if self.network_status in [NetworkStatus.NORMAL, NetworkStatus.HIGH_LATENCY]:
                decision.mode = RoutingMode.CLOUD_EDGE
                decision.reason = "低置信度，需要云端复核"
            else:
                decision.mode = RoutingMode.EDGE_ONLY
                decision.reason = "低置信度但网络不佳，边缘自治"
        elif risk_level == "medium":
            if self.network_status in [NetworkStatus.NORMAL, NetworkStatus.HIGH_LATENCY]:
                decision.mode = RoutingMode.CLOUD_EDGE
                decision.reason = "中等风险，云端辅助决策"
            else:
                decision.mode = RoutingMode.EDGE_ONLY
                decision.reason = "中等风险但网络不佳，边缘处理"
        else:
            decision.mode = RoutingMode.EDGE_ONLY
            decision.reason = "低风险高置信度，边缘独立处理"
        
        self._log_decision(decision, confidence, fault_prob)
        
        return decision
    
    def _log_decision(self, decision: RoutingDecision, confidence: float, fault_prob: float = 0.0) -> None:
        self._routing_log.append({
            "timestamp": decision.timestamp,
            "mode": decision.mode.value,
            "reason": decision.reason,
            "confidence": confidence,
            "fault_prob": fault_prob,
            "confidence_threshold": decision.confidence_threshold,
            "risk_level": decision.risk_level,
            "network_status": decision.network_status,
            "latency_ms": decision.latency_ms,
            "pending_review": decision.pending_review
        })
    
    def get_log(self) -> list[Dict[str, Any]]:
        return self._routing_log
    
    def clear_log(self) -> None:
        self._routing_log = []
    
    def save_log_to_csv(self, file_path: str = "logs/routing_log.csv", append: bool = False) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        fieldnames = [
            "timestamp", "mode", "reason", "confidence", "fault_prob",
            "confidence_threshold", "risk_level", "network_status", "latency_ms", "pending_review"
        ]
        
        mode = 'a' if append else 'w'
        
        with open(file_path, mode=mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if mode == 'w' or not os.path.exists(file_path):
                writer.writeheader()
            for entry in self._routing_log:
                writer.writerow(entry)
        
        print(f"Routing log saved to {file_path}")

def create_router(confidence_threshold: float = 0.7,
                  high_risk_threshold: float = 0.6,
                  critical_risk_threshold: float = 0.85,
                  policy: Optional[RoutingPolicy] = None) -> Router:
    return Router(confidence_threshold, high_risk_threshold, critical_risk_threshold, policy=policy)

def get_routing_mode_description(mode: RoutingMode) -> str:
    descriptions = {
        RoutingMode.EDGE_ONLY: "仅边缘处理：本地模型独立完成推理和决策",
        RoutingMode.CLOUD_ONLY: "仅云端处理：将数据上传至云端由大模型推理",
        RoutingMode.CLOUD_EDGE: "云边协同：边缘先推理，高风险/低置信度时云端复核",
        RoutingMode.WEAKNET_AUTONOMY: "弱网自治：弱网时边缘独立决策，记录告警待网络恢复后上报"
    }
    return descriptions[mode]

if __name__ == "__main__":
    router = Router(confidence_threshold=0.7)
    
    test_cases = [
        {"confidence": 0.9, "risk_level": "low", "fault_prob": 0.1, "network": NetworkStatus.NORMAL},
        {"confidence": 0.6, "risk_level": "medium", "fault_prob": 0.5, "network": NetworkStatus.NORMAL},
        {"confidence": 0.5, "risk_level": "high", "fault_prob": 0.75, "network": NetworkStatus.NORMAL},
        {"confidence": 0.9, "risk_level": "high", "fault_prob": 0.9, "network": NetworkStatus.NORMAL},
        {"confidence": 0.9, "risk_level": "high", "fault_prob": 0.85, "network": NetworkStatus.WEAK},
        {"confidence": 0.5, "risk_level": "medium", "fault_prob": 0.5, "network": NetworkStatus.HIGH_LATENCY},
        {"confidence": 0.8, "risk_level": "low", "fault_prob": 0.1, "network": NetworkStatus.DISCONNECTED},
        {"confidence": 0.4, "risk_level": "high", "fault_prob": 0.7, "network": NetworkStatus.DISCONNECTED},
        {"confidence": 0.65, "risk_level": "low", "fault_prob": 0.3, "network": NetworkStatus.WEAK},
    ]
    
    print("=== Router Test ===")
    
    for i, test_case in enumerate(test_cases):
        router.set_network_status(test_case["network"])
        decision = router.decide(
            test_case["confidence"], 
            test_case["risk_level"],
            test_case["fault_prob"]
        )
        print(f"\nTest {i+1}:")
        print(f"  Confidence: {test_case['confidence']}")
        print(f"  Fault Prob: {test_case['fault_prob']}")
        print(f"  Risk Level: {test_case['risk_level']}")
        print(f"  Network: {test_case['network'].value}")
        print(f"  Mode: {decision.mode.value}")
        print(f"  Reason: {decision.reason}")
        print(f"  Pending Review: {decision.pending_review}")
    
    router.save_log_to_csv(append=False)
    
    print("\n=== Routing Log ===")
    for entry in router.get_log():
        print(f"{entry['timestamp'][:19]}: {entry['mode']} - {entry['reason']}")