import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routing import (
    NetworkStatus,
    create_network_simulator,
    create_router,
    RoutingMode
)

class MockDeviceState:
    def __init__(self, air_temperature_k, process_temperature_k, rotational_speed_rpm, torque_nm, tool_wear_min):
        self.air_temperature_k = air_temperature_k
        self.process_temperature_k = process_temperature_k
        self.rotational_speed_rpm = rotational_speed_rpm
        self.torque_nm = torque_nm
        self.tool_wear_min = tool_wear_min

class MockCloudReviewer:
    def __init__(self):
        self.cloud_call_count = 0
        self.consistent_count = 0
    
    def review(self, edge_summary):
        self.cloud_call_count += 1
        edge_confidence = edge_summary.get("edge_confidence", 0.5)
        edge_action = edge_summary.get("edge_action", "")
        
        if edge_confidence > 0.8:
            agree_prob = 0.85
        elif edge_confidence > 0.5:
            agree_prob = 0.6
        else:
            agree_prob = 0.3
        
        import random
        consistent = random.random() < agree_prob
        if consistent:
            self.consistent_count += 1
        
        return {
            "review_id": f"review_{self.cloud_call_count}",
            "gcm_fault_label": edge_summary.get("edge_fault_label", "Normal"),
            "gcm_risk_level": edge_summary.get("edge_risk_level", "medium"),
            "gcm_action": edge_action if consistent else random.choice(["maintain", "replace", "monitor", "shutdown"]),
            "gcm_confidence": min(edge_confidence + 0.1, 0.98),
            "gcm_reason": "Mock GCM review completed",
            "consistent_with_edge": consistent,
            "latency_ms": random.randint(50, 200)
        }
    
    def get_stats(self):
        return {
            "cloud_call_count": self.cloud_call_count,
            "consistent_count": self.consistent_count,
            "edge_cloud_consistency": self.consistent_count / self.cloud_call_count if self.cloud_call_count > 0 else 0
        }

def mock_inference(device_state):
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
    
    fault_label_names = {0: "Normal", 1: "Fault Detected"}
    
    return {
        "fault_label": fault_label,
        "fault_label_name": fault_label_names[fault_label],
        "fault_prob": round(fault_prob, 4),
        "risk_level": risk_level,
        "action": action,
        "confidence": round(confidence, 4)
    }

def perform_cloud_review(device_id, result, device_state, cloud_reviewer):
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
        return {
            "reviewed": True,
            "review_id": review_result.get("review_id", ""),
            "gcm_fault_label": review_result.get("gcm_fault_label", ""),
            "gcm_risk_level": review_result.get("gcm_risk_level", ""),
            "gcm_action": review_result.get("gcm_action", ""),
            "gcm_confidence": review_result.get("gcm_confidence", 0.0),
            "gcm_reason": review_result.get("gcm_reason", ""),
            "consistent_with_edge": review_result.get("consistent_with_edge", False),
            "latency_ms": review_result.get("latency_ms", 0.0)
        }
    except Exception as e:
        return {
            "reviewed": False,
            "gcm_reason": f"云端复核失败: {str(e)}"
        }

def make_final_decision(routing_mode, edge_result, cloud_review):
    if routing_mode == RoutingMode.EDGE_ONLY:
        return "edge", edge_result["action"]
    elif routing_mode == RoutingMode.CLOUD_ONLY:
        if cloud_review and cloud_review["reviewed"]:
            return "cloud", cloud_review["gcm_action"]
        return "edge", edge_result["action"]
    elif routing_mode == RoutingMode.CLOUD_EDGE:
        if cloud_review and cloud_review["reviewed"]:
            if cloud_review["consistent_with_edge"]:
                return "consensus", edge_result["action"]
            else:
                return "cloud_disagrees", f"边缘: {edge_result['action']}, 云端: {cloud_review['gcm_action']}"
        return "edge", edge_result["action"]
    elif routing_mode == RoutingMode.WEAKNET_AUTONOMY:
        return "edge_autonomy", edge_result["action"]
    else:
        return "edge", edge_result["action"]

def test_edge_cloud_flow():
    print("="*60)
    print("云边协同系统集成测试 (Mock模式)")
    print("="*60)
    
    simulator = create_network_simulator(seed=123)
    router = create_router(confidence_threshold=0.7)
    cloud_reviewer = MockCloudReviewer()
    
    test_scenarios = [
        {
            "name": "场景1: 低风险高置信度正常网络 - 边缘独立处理",
            "device": MockDeviceState(298.0, 305.0, 1400, 45.0, 50),
            "network": NetworkStatus.NORMAL,
            "manual_edge_result": None,
            "expected_mode": RoutingMode.EDGE_ONLY
        },
        {
            "name": "场景2: 高风险正常网络(故障概率0.7) - 云边协同",
            "device": MockDeviceState(303.0, 312.0, 1500, 62.0, 155),
            "network": NetworkStatus.NORMAL,
            "manual_edge_result": {
                "fault_label": 1,
                "fault_label_name": "Fault Detected",
                "fault_prob": 0.70,
                "risk_level": "high",
                "action": "紧急停机并上报云端",
                "confidence": 0.88
            },
            "expected_mode": RoutingMode.CLOUD_EDGE
        },
        {
            "name": "场景3: 极高风险正常网络(故障概率0.95) - 仅云端处理",
            "device": MockDeviceState(310.0, 325.0, 1800, 85.0, 250),
            "network": NetworkStatus.NORMAL,
            "manual_edge_result": None,
            "expected_mode": RoutingMode.CLOUD_ONLY
        },
        {
            "name": "场景4: 弱网高风险 - 边缘自治",
            "device": MockDeviceState(305.0, 315.0, 1550, 68.0, 180),
            "network": NetworkStatus.WEAK,
            "manual_edge_result": None,
            "expected_mode": RoutingMode.WEAKNET_AUTONOMY
        },
        {
            "name": "场景5: 网络断开 - 边缘自治",
            "device": MockDeviceState(302.0, 312.0, 1500, 65.0, 160),
            "network": NetworkStatus.DISCONNECTED,
            "manual_edge_result": None,
            "expected_mode": RoutingMode.EDGE_ONLY
        },
        {
            "name": "场景6: 低置信度正常网络 - 云边协同",
            "device": MockDeviceState(300.0, 308.0, 1450, 55.0, 120),
            "network": NetworkStatus.NORMAL,
            "manual_edge_result": {
                "fault_label": 1,
                "fault_label_name": "Fault Detected",
                "fault_prob": 0.45,
                "risk_level": "medium",
                "action": "建议维护并持续监控",
                "confidence": 0.65
            },
            "expected_mode": RoutingMode.CLOUD_EDGE
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\n{'─'*50}")
        print(f"测试 {i+1}: {scenario['name']}")
        print(f"{'─'*50}")
        
        device_id = f"test_device_{i+1}"
        
        if scenario.get("manual_edge_result"):
            edge_result = scenario["manual_edge_result"]
        else:
            edge_result = mock_inference(scenario["device"])
        print(f"\n📊 边缘推理结果:")
        print(f"  故障标签: {edge_result['fault_label_name']}")
        print(f"  故障概率: {edge_result['fault_prob']:.4f}")
        print(f"  风险等级: {edge_result['risk_level']}")
        print(f"  建议动作: {edge_result['action']}")
        print(f"  置信度: {edge_result['confidence']:.4f}")
        
        simulator.set_status(scenario["network"])
        router.set_network_status(scenario["network"])
        network_stats = simulator.get_network_stats()
        
        routing_decision = router.decide(
            confidence=edge_result["confidence"],
            risk_level=edge_result["risk_level"],
            fault_prob=edge_result["fault_prob"],
            network_stats=network_stats
        )
        
        print(f"\n🔀 路由决策:")
        print(f"  网络状态: {scenario['network'].value}")
        print(f"  路由模式: {routing_decision.mode.value}")
        print(f"  决策原因: {routing_decision.reason}")
        print(f"  待复核: {routing_decision.pending_review}")
        
        cloud_review = None
        if routing_decision.mode in [RoutingMode.CLOUD_EDGE, RoutingMode.CLOUD_ONLY]:
            print(f"\n☁️  云端复核中...")
            cloud_review = perform_cloud_review(device_id, edge_result, scenario["device"], cloud_reviewer)
            
            print(f"  已复核: {cloud_review['reviewed']}")
            if cloud_review['reviewed']:
                print(f"  GCM故障标签: {cloud_review['gcm_fault_label']}")
                print(f"  GCM风险等级: {cloud_review['gcm_risk_level']}")
                print(f"  GCM建议动作: {cloud_review['gcm_action']}")
                print(f"  GCM置信度: {cloud_review['gcm_confidence']:.4f}")
                print(f"  与边缘一致: {cloud_review['consistent_with_edge']}")
                print(f"  复核延迟: {cloud_review['latency_ms']}ms")
            else:
                print(f"  失败原因: {cloud_review.get('gcm_reason', '未知')}")
        
        final_decision, final_action = make_final_decision(
            routing_decision.mode, edge_result, cloud_review
        )
        
        print(f"\n✅ 最终决策:")
        print(f"  决策来源: {final_decision}")
        print(f"  执行动作: {final_action}")
        
        mode_correct = routing_decision.mode == scenario["expected_mode"]
        results.append({
            "name": scenario["name"],
            "mode": routing_decision.mode.value,
            "expected_mode": scenario["expected_mode"].value,
            "mode_correct": mode_correct,
            "cloud_reviewed": cloud_review is not None and cloud_review.get("reviewed", False),
            "final_decision": final_decision
        })
        
        status = "✓" if mode_correct else "✗"
        print(f"\n{status} 路由模式验证: 期望 {scenario['expected_mode'].value}, 实际 {routing_decision.mode.value}")
    
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    
    mode_results = [r["mode_correct"] for r in results]
    passed = sum(mode_results)
    total = len(mode_results)
    
    print(f"\n路由模式验证: {passed}/{total} 通过")
    
    cloud_reviewed_count = sum(1 for r in results if r["cloud_reviewed"])
    print(f"云端复核调用: {cloud_reviewed_count} 次成功")
    
    cloud_stats = cloud_reviewer.get_stats()
    print(f"\n云端复核统计:")
    print(f"  总调用次数: {cloud_stats['cloud_call_count']}")
    print(f"  边云一致性: {cloud_stats['edge_cloud_consistency']:.4f}")
    
    print(f"\n路由决策日志:")
    for entry in router.get_log():
        print(f"  {entry['timestamp'][:19]}: {entry['mode']} - {entry['reason']}")
    
    router.save_log_to_csv("logs/integration_test_log.csv", append=False)
    
    print(f"\n{'='*60}")
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  {total - passed} 个测试失败")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_edge_cloud_flow()