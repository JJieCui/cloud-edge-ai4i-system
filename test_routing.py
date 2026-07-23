import sys
sys.path.insert(0, '.')

from routing import (
    NetworkStatus,
    NetworkSimulator,
    Router,
    RoutingMode,
    create_network_simulator,
    create_router
)

def test_network_simulator():
    print("=== Testing Network Simulator ===")
    
    simulator = create_network_simulator(seed=42)
    
    for status in NetworkStatus:
        simulator.set_status(status)
        stats = simulator.get_network_stats()
        print(f"\n{status.value}:")
        print(f"  Latency: {stats.latency_ms:.2f} ms")
        print(f"  Bandwidth: {stats.bandwidth_mbps:.2f} Mbps")
        print(f"  Packet Loss: {stats.packet_loss_rate:.2%}")
    
    print("\n✓ Network Simulator tests passed")

def test_router():
    print("\n=== Testing Router ===")
    
    router = create_router(confidence_threshold=0.7)
    
    test_cases = [
        {"confidence": 0.9, "risk_level": "low", "fault_prob": 0.1, "network": NetworkStatus.NORMAL, "expected": RoutingMode.EDGE_ONLY},
        {"confidence": 0.6, "risk_level": "medium", "fault_prob": 0.5, "network": NetworkStatus.NORMAL, "expected": RoutingMode.CLOUD_EDGE},
        {"confidence": 0.5, "risk_level": "high", "fault_prob": 0.75, "network": NetworkStatus.NORMAL, "expected": RoutingMode.CLOUD_EDGE},
        {"confidence": 0.9, "risk_level": "high", "fault_prob": 0.9, "network": NetworkStatus.NORMAL, "expected": RoutingMode.CLOUD_ONLY},
        {"confidence": 0.9, "risk_level": "high", "fault_prob": 0.85, "network": NetworkStatus.WEAK, "expected": RoutingMode.WEAKNET_AUTONOMY},
        {"confidence": 0.5, "risk_level": "medium", "fault_prob": 0.5, "network": NetworkStatus.HIGH_LATENCY, "expected": RoutingMode.CLOUD_EDGE},
        {"confidence": 0.8, "risk_level": "low", "fault_prob": 0.1, "network": NetworkStatus.DISCONNECTED, "expected": RoutingMode.EDGE_ONLY},
        {"confidence": 0.4, "risk_level": "high", "fault_prob": 0.7, "network": NetworkStatus.DISCONNECTED, "expected": RoutingMode.EDGE_ONLY},
        {"confidence": 0.75, "risk_level": "low", "fault_prob": 0.3, "network": NetworkStatus.NORMAL, "expected": RoutingMode.EDGE_ONLY},
        {"confidence": 0.69, "risk_level": "low", "fault_prob": 0.25, "network": NetworkStatus.NORMAL, "expected": RoutingMode.CLOUD_EDGE},
        {"confidence": 0.65, "risk_level": "low", "fault_prob": 0.3, "network": NetworkStatus.WEAK, "expected": RoutingMode.WEAKNET_AUTONOMY},
        {"confidence": 0.75, "risk_level": "medium", "fault_prob": 0.5, "network": NetworkStatus.WEAK, "expected": RoutingMode.WEAKNET_AUTONOMY},
        {"confidence": 0.8, "risk_level": "high", "fault_prob": 0.75, "network": NetworkStatus.WEAK, "expected": RoutingMode.WEAKNET_AUTONOMY},
        {"confidence": 0.95, "risk_level": "high", "fault_prob": 0.86, "network": NetworkStatus.NORMAL, "expected": RoutingMode.CLOUD_ONLY},
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases):
        router.set_network_status(test_case["network"])
        decision = router.decide(
            test_case["confidence"], 
            test_case["risk_level"],
            test_case["fault_prob"]
        )
        
        status = "✓" if decision.mode == test_case["expected"] else "✗"
        
        if decision.mode == test_case["expected"]:
            passed += 1
        else:
            failed += 1
        
        print(f"\nTest {i+1} {status}:")
        print(f"  Confidence: {test_case['confidence']}")
        print(f"  Fault Prob: {test_case['fault_prob']}")
        print(f"  Risk Level: {test_case['risk_level']}")
        print(f"  Network: {test_case['network'].value}")
        print(f"  Expected: {test_case['expected'].value}")
        print(f"  Got: {decision.mode.value}")
        print(f"  Reason: {decision.reason}")
        print(f"  Pending Review: {decision.pending_review}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ Router tests passed")
    else:
        print("✗ Some router tests failed")
    
    return failed == 0

def test_logging():
    print("\n=== Testing Logging ===")
    
    router = create_router(confidence_threshold=0.7)
    
    test_cases = [
        {"confidence": 0.9, "risk_level": "low", "fault_prob": 0.1, "network": NetworkStatus.NORMAL},
        {"confidence": 0.5, "risk_level": "high", "fault_prob": 0.75, "network": NetworkStatus.NORMAL},
        {"confidence": 0.6, "risk_level": "medium", "fault_prob": 0.5, "network": NetworkStatus.WEAK},
    ]
    
    for test_case in test_cases:
        router.set_network_status(test_case["network"])
        router.decide(test_case["confidence"], test_case["risk_level"], test_case["fault_prob"])
    
    log = router.get_log()
    print(f"Log entries: {len(log)}")
    
    for entry in log:
        print(f"  {entry['timestamp'][:19]}: {entry['mode']} - {entry['reason']}")
    
    router.save_log_to_csv("logs/routing_log.csv", append=False)
    print("\n✓ Logging tests passed")

def test_all_routing_modes():
    print("\n=== Testing All Routing Modes ===")
    
    router = create_router(confidence_threshold=0.7)
    
    mode_tests = {
        RoutingMode.EDGE_ONLY: [
            {"confidence": 0.9, "risk_level": "low", "fault_prob": 0.1, "network": NetworkStatus.NORMAL},
            {"confidence": 0.8, "risk_level": "low", "fault_prob": 0.1, "network": NetworkStatus.DISCONNECTED},
        ],
        RoutingMode.CLOUD_ONLY: [
            {"confidence": 0.9, "risk_level": "high", "fault_prob": 0.9, "network": NetworkStatus.NORMAL},
            {"confidence": 0.95, "risk_level": "high", "fault_prob": 0.86, "network": NetworkStatus.NORMAL},
        ],
        RoutingMode.CLOUD_EDGE: [
            {"confidence": 0.6, "risk_level": "medium", "fault_prob": 0.5, "network": NetworkStatus.NORMAL},
            {"confidence": 0.5, "risk_level": "high", "fault_prob": 0.75, "network": NetworkStatus.NORMAL},
        ],
        RoutingMode.WEAKNET_AUTONOMY: [
            {"confidence": 0.9, "risk_level": "high", "fault_prob": 0.85, "network": NetworkStatus.WEAK},
            {"confidence": 0.65, "risk_level": "low", "fault_prob": 0.3, "network": NetworkStatus.WEAK},
        ],
    }
    
    all_modes_covered = True
    
    for mode, test_cases in mode_tests.items():
        print(f"\n{mode.value}:")
        for test_case in test_cases:
            router.set_network_status(test_case["network"])
            decision = router.decide(
                test_case["confidence"], 
                test_case["risk_level"],
                test_case["fault_prob"]
            )
            status = "✓" if decision.mode == mode else "✗"
            if decision.mode != mode:
                all_modes_covered = False
            print(f"  {status} {decision.reason}")
    
    if all_modes_covered:
        print("\n✓ All routing modes covered")
    else:
        print("\n✗ Some routing modes not covered")
    
    return all_modes_covered

def test_end_to_end():
    print("\n=== Testing End-to-End Routing Flow ===")
    
    simulator = create_network_simulator(seed=123)
    router = create_router(confidence_threshold=0.7)
    
    device_samples = [
        {
            "device_id": "machine_001",
            "air_temperature_k": 300.5,
            "process_temperature_k": 312.0,
            "rotational_speed_rpm": 1500,
            "torque_nm": 65.2,
            "tool_wear_min": 180
        },
        {
            "device_id": "machine_002",
            "air_temperature_k": 298.3,
            "process_temperature_k": 305.0,
            "rotational_speed_rpm": 1400,
            "torque_nm": 45.0,
            "tool_wear_min": 50
        },
        {
            "device_id": "machine_003",
            "air_temperature_k": 305.0,
            "process_temperature_k": 318.0,
            "rotational_speed_rpm": 1600,
            "torque_nm": 72.5,
            "tool_wear_min": 200
        }
    ]
    
    for sample in device_samples:
        process_temp = sample["process_temperature_k"]
        torque = sample["torque_nm"]
        tool_wear = sample["tool_wear_min"]
        
        fault_prob = 0.0
        if process_temp > 310:
            fault_prob += 0.3
        if torque > 60:
            fault_prob += 0.25
        if tool_wear > 150:
            fault_prob += 0.35
        if sample["air_temperature_k"] > 300:
            fault_prob += 0.1
        
        fault_prob = min(fault_prob, 0.95)
        
        if fault_prob > 0.7:
            risk_level = "high"
            confidence = 0.8 + (fault_prob - 0.7) * 0.4
        elif fault_prob > 0.4:
            risk_level = "medium"
            confidence = 0.7 + (fault_prob - 0.4) * 0.3
        else:
            risk_level = "low"
            confidence = 0.85 + (0.4 - fault_prob) * 0.15
        
        confidence = min(confidence, 0.99)
        
        network_status = simulator.simulate_status_change(probability=0.2)
        router.set_network_status(network_status)
        
        decision = router.decide(confidence, risk_level, fault_prob)
        
        print(f"\nDevice: {sample['device_id']}")
        print(f"  Fault Probability: {fault_prob:.4f}")
        print(f"  Risk Level: {risk_level}")
        print(f"  Confidence: {confidence:.4f}")
        print(f"  Network Status: {network_status.value}")
        print(f"  Routing Mode: {decision.mode.value}")
        print(f"  Decision Reason: {decision.reason}")
        print(f"  Pending Review: {decision.pending_review}")
    
    router.save_log_to_csv("logs/routing_log.csv", append=False)
    print("\n✓ End-to-end tests passed")

if __name__ == "__main__":
    test_network_simulator()
    router_ok = test_router()
    test_logging()
    modes_ok = test_all_routing_modes()
    test_end_to_end()
    
    print("\n" + "="*50)
    if router_ok and modes_ok:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    print("="*50)