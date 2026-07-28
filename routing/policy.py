from abc import ABC, abstractmethod
from typing import Optional
from .network_simulator import NetworkStatus, NetworkStats

class RoutingPolicy(ABC):
    @abstractmethod
    def should_route_to_cloud(self, confidence: float, risk_level: str, 
                               fault_prob: float, network_status: NetworkStatus,
                               network_stats: Optional[NetworkStats] = None) -> bool:
        pass
    
    @abstractmethod
    def get_policy_name(self) -> str:
        pass

class ConfidenceThresholdPolicy(RoutingPolicy):
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
    
    def should_route_to_cloud(self, confidence: float, risk_level: str, 
                               fault_prob: float, network_status: NetworkStatus,
                               network_stats: Optional[NetworkStats] = None) -> bool:
        return confidence < self.threshold
    
    def get_policy_name(self) -> str:
        return f"ConfidenceThreshold({self.threshold})"

class RiskLevelPolicy(RoutingPolicy):
    def __init__(self, high_risk_threshold: float = 0.6):
        self.high_risk_threshold = high_risk_threshold
    
    def should_route_to_cloud(self, confidence: float, risk_level: str, 
                               fault_prob: float, network_status: NetworkStatus,
                               network_stats: Optional[NetworkStats] = None) -> bool:
        return risk_level in ["high", "medium"]
    
    def get_policy_name(self) -> str:
        return f"RiskLevelPolicy({self.high_risk_threshold})"

class NetworkAwarePolicy(RoutingPolicy):
    def __init__(self, allow_cloud_on_high_latency: bool = True):
        self.allow_cloud_on_high_latency = allow_cloud_on_high_latency
    
    def should_route_to_cloud(self, confidence: float, risk_level: str, 
                               fault_prob: float, network_status: NetworkStatus,
                               network_stats: Optional[NetworkStats] = None) -> bool:
        if network_status == NetworkStatus.DISCONNECTED:
            return False
        if network_status == NetworkStatus.WEAK:
            return False
        if network_status == NetworkStatus.HIGH_LATENCY:
            return self.allow_cloud_on_high_latency
        return True
    
    def get_policy_name(self) -> str:
        return f"NetworkAwarePolicy(allow_high_latency={self.allow_cloud_on_high_latency})"

class CriticalRiskPolicy(RoutingPolicy):
    def __init__(self, critical_threshold: float = 0.85):
        self.critical_threshold = critical_threshold
    
    def should_route_to_cloud(self, confidence: float, risk_level: str, 
                               fault_prob: float, network_status: NetworkStatus,
                               network_stats: Optional[NetworkStats] = None) -> bool:
        return fault_prob >= self.critical_threshold
    
    def get_policy_name(self) -> str:
        return f"CriticalRiskPolicy({self.critical_threshold})"

class CompositePolicy(RoutingPolicy):
    def __init__(self, policies: list[RoutingPolicy]):
        self.policies = policies
    
    def should_route_to_cloud(self, confidence: float, risk_level: str, 
                               fault_prob: float, network_status: NetworkStatus,
                               network_stats: Optional[NetworkStats] = None) -> bool:
        for policy in self.policies:
            if policy.should_route_to_cloud(confidence, risk_level, fault_prob, 
                                             network_status, network_stats):
                return True
        return False
    
    def get_policy_name(self) -> str:
        return f"CompositePolicy({[p.get_policy_name() for p in self.policies]})"

def create_default_policy() -> RoutingPolicy:
    return CompositePolicy([
        CriticalRiskPolicy(critical_threshold=0.85),
        ConfidenceThresholdPolicy(threshold=0.7),
        RiskLevelPolicy(high_risk_threshold=0.6),
    ])

def create_network_aware_policy() -> RoutingPolicy:
    return CompositePolicy([
        NetworkAwarePolicy(allow_cloud_on_high_latency=True),
        CriticalRiskPolicy(critical_threshold=0.85),
        ConfidenceThresholdPolicy(threshold=0.7),
        RiskLevelPolicy(high_risk_threshold=0.6),
    ])