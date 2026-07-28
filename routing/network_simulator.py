# 本科生3：网络状态模拟器
# TODO: 模拟正常网络、弱网、高延迟、断网
from typing import Literal, Optional, Dict, Any
import random
import time
from enum import Enum
from datetime import datetime

class NetworkStatus(Enum):
    NORMAL = "normal"
    WEAK = "weak"
    HIGH_LATENCY = "high_latency"
    DISCONNECTED = "disconnected"

class NetworkStats:
    def __init__(self):
        self.latency_ms: float = 0.0
        self.bandwidth_mbps: float = 0.0
        self.packet_loss_rate: float = 0.0
        self.status: NetworkStatus = NetworkStatus.NORMAL
        self.timestamp: str = ""

class NetworkSimulator:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)
        self._current_status = NetworkStatus.NORMAL
        self._status_history: list[Dict[str, Any]] = []
    
    def get_status(self) -> NetworkStatus:
        return self._current_status
    
    def get_network_stats(self) -> NetworkStats:
        stats = NetworkStats()
        stats.timestamp = datetime.now().isoformat()
        stats.status = self._current_status
        
        if self._current_status == NetworkStatus.NORMAL:
            stats.latency_ms = random.uniform(10, 50)
            stats.bandwidth_mbps = random.uniform(100, 1000)
            stats.packet_loss_rate = random.uniform(0, 0.01)
        elif self._current_status == NetworkStatus.WEAK:
            stats.latency_ms = random.uniform(100, 300)
            stats.bandwidth_mbps = random.uniform(1, 10)
            stats.packet_loss_rate = random.uniform(0.05, 0.2)
        elif self._current_status == NetworkStatus.HIGH_LATENCY:
            stats.latency_ms = random.uniform(500, 2000)
            stats.bandwidth_mbps = random.uniform(10, 50)
            stats.packet_loss_rate = random.uniform(0.02, 0.1)
        elif self._current_status == NetworkStatus.DISCONNECTED:
            stats.latency_ms = float('inf')
            stats.bandwidth_mbps = 0.0
            stats.packet_loss_rate = 1.0
        
        return stats
    
    def set_status(self, status: NetworkStatus) -> None:
        prev_status = self._current_status
        self._current_status = status
        
        self._status_history.append({
            "timestamp": datetime.now().isoformat(),
            "from_status": prev_status.value,
            "to_status": status.value
        })
    
    def simulate_status_change(self, probability: float = 0.1) -> NetworkStatus:
        if random.random() < probability:
            statuses = list(NetworkStatus)
            new_status = random.choice([s for s in statuses if s != self._current_status])
            self.set_status(new_status)
        
        return self._current_status
    
    def simulate_network_delay(self) -> float:
        stats = self.get_network_stats()
        
        if stats.status == NetworkStatus.DISCONNECTED:
            raise ConnectionError("Network is disconnected")
        
        delay_seconds = stats.latency_ms / 1000.0
        
        if stats.status == NetworkStatus.WEAK:
            delay_seconds *= random.uniform(1.5, 2.5)
        elif stats.status == NetworkStatus.HIGH_LATENCY:
            delay_seconds *= random.uniform(2, 4)
        
        time.sleep(delay_seconds)
        
        return delay_seconds * 1000
    
    def get_history(self, limit: Optional[int] = None) -> list[Dict[str, Any]]:
        if limit is None:
            return self._status_history
        return self._status_history[-limit:]
    
    def reset(self) -> None:
        self._current_status = NetworkStatus.NORMAL
        self._status_history = []
        if self.seed is not None:
            random.seed(self.seed)

def create_network_simulator(seed: Optional[int] = None) -> NetworkSimulator:
    return NetworkSimulator(seed)

def get_network_status_description(status: NetworkStatus) -> str:
    descriptions = {
        NetworkStatus.NORMAL: "网络正常，低延迟高带宽",
        NetworkStatus.WEAK: "弱网状态，低带宽高丢包",
        NetworkStatus.HIGH_LATENCY: "高延迟状态，响应缓慢",
        NetworkStatus.DISCONNECTED: "网络断开，无法通信"
    }
    return descriptions[status]

if __name__ == "__main__":
    simulator = NetworkSimulator(seed=42)
    
    print("=== Network Simulator Test ===")
    
    for status in NetworkStatus:
        simulator.set_status(status)
        stats = simulator.get_network_stats()
        print(f"\n{status.value}:")
        print(f"  Latency: {stats.latency_ms:.2f} ms")
        print(f"  Bandwidth: {stats.bandwidth_mbps:.2f} Mbps")
        print(f"  Packet Loss: {stats.packet_loss_rate:.2%}")
    
    print("\n=== Simulating status changes ===")
    for i in range(10):
        status = simulator.simulate_status_change(probability=0.3)
        stats = simulator.get_network_stats()
        print(f"Step {i+1}: {status.value}, Latency={stats.latency_ms:.2f}ms")
