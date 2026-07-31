"""
系统集成测试
运行方式: python -m test_integration
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_industrial_pipeline():
    """工业场景完整流水线：Observation → EdgeDecision → RouteDecision → CloudReview → FinalDecision"""
    print("[1/4] 测试工业场景完整流水线 ...", end=" ")
    try:
        from consistency.event_schema import (
            Observation, EdgeDecision, RouteDecision,
            CloudReview, FinalDecision, Event, build_event,
        )
        from consistency.conflict_detector import ConflictDetector
        from consistency.conflict_resolver import ConflictResolver
        from routing import Router, NetworkStatus, NetworkSimulator, create_router, create_network_simulator, RoutingMode

        trace_id = "trace-integration-test-001"

        def _route_to_string(mode):
            mapping = {
                RoutingMode.EDGE_ONLY: "EdgeOnly",
                RoutingMode.CLOUD_ONLY: "CloudOnly",
                RoutingMode.CLOUD_EDGE: "EdgeCloud",
                RoutingMode.WEAKNET_AUTONOMY: "SafeFallback",
            }
            return mapping.get(mode, "EdgeOnly")

        router = create_router(confidence_threshold=0.7)
        sim = create_network_simulator(seed=42)

        obs = Observation(
            scene="industrial",
            node_id="edge_0",
            object_id="device_001",
            payload={
                "product_type": "L",
                "air_temperature_k": 305.0,
                "process_temperature_k": 312.0,
                "rotational_speed_rpm": 1450,
                "torque_nm": 55.0,
                "tool_wear_min": 180,
            },
            trace_id=trace_id,
            deadline_ms=200,
        )

        assert obs.scene == "industrial"
        assert obs.trace_id == trace_id
        assert obs.event_id.startswith("evt-")

        ed = EdgeDecision(
            event_id=obs.event_id,
            trace_id=trace_id,
            scene="industrial",
            node_id="edge_0",
            predicted_label="Heat Dissipation Failure",
            risk_level="high",
            action="shutdown",
            confidence=0.85,
            model_version="RandomForest-v1",
            reason="ProcessTemp=312K > 310K threshold",
            inference_ms=15.5,
        )

        assert ed.scene == "industrial"
        assert ed.risk_level == "high"
        assert ed.action == "shutdown"

        sim.set_status(NetworkStatus.NORMAL)
        router.set_network_status(NetworkStatus.NORMAL)
        stats = sim.get_network_stats()

        route_decision = router.decide(
            confidence=ed.confidence,
            risk_level=ed.risk_level,
            fault_prob=0.8,
            network_stats=stats,
        )

        route = RouteDecision(
            trace_id=trace_id,
            route=_route_to_string(route_decision.mode),
            reason_codes=[route_decision.reason],
            estimated_total_ms=15.5 + stats.latency_ms,
            remaining_deadline_ms=max(200 - 15.5 - stats.latency_ms, 0),
        )

        assert route.route in ["EdgeOnly", "EdgeCloud", "CloudOnly", "SafeFallback"]

        cloud_review = CloudReview(
            trace_id=trace_id,
            reviewed_label="Heat Dissipation Failure",
            risk_level="high",
            action="shutdown",
            confidence=0.92,
            model="qwen3.5-35b",
            reason="云端复核确认高风险故障",
            latency_ms=85.0,
        )

        edge_event = Event.from_edge_decision(ed)
        cloud_event = Event.from_cloud_review(cloud_review)

        assert edge_event.source == "edge"
        assert cloud_event.source == "cloud"

        detector = ConflictDetector(duplicate_time_window_s=60, stale_threshold_ms=5000)
        detect_result = detector.detect([edge_event, cloud_event])

        assert detect_result["total_events"] == 2
        assert detect_result["conflict_count"] >= 0

        resolver = ConflictResolver(strategy="highest_risk_first", network_status="normal")
        resolve_result = resolver.resolve([edge_event, cloud_event], detect_result["conflict_details"])

        assert resolve_result["final_decision_obj"] is not None
        fd = resolve_result["final_decision_obj"]
        assert isinstance(fd, FinalDecision)
        assert fd.trace_id == trace_id
        assert fd.final_action in ["monitor", "warn", "maintain", "shutdown", "replace"]

        print("OK")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAIL: {e}")
        return False


def test_weaknet_fallback():
    """弱网自治路径测试"""
    print("[2/4] 测试弱网自治路径 ...", end=" ")
    try:
        from routing import Router, NetworkStatus, create_router, create_network_simulator
        from consistency.event_schema import Event, build_event
        from consistency.conflict_detector import ConflictDetector
        from consistency.conflict_resolver import ConflictResolver

        router = create_router(confidence_threshold=0.7)
        sim = create_network_simulator(seed=99)

        sim.set_status(NetworkStatus.WEAK)
        router.set_network_status(NetworkStatus.WEAK)
        stats = sim.get_network_stats()

        d = router.decide(confidence=0.4, risk_level="high", fault_prob=0.7, network_stats=stats)
        assert d.mode.value == "WeakNetAutonomy"
        assert d.pending_review is True

        d2 = router.decide(confidence=0.9, risk_level="low", fault_prob=0.1, network_stats=stats)
        assert d2.mode.value == "EdgeOnly"

        sim.set_status(NetworkStatus.DISCONNECTED)
        router.set_network_status(NetworkStatus.DISCONNECTED)
        stats2 = sim.get_network_stats()

        d3 = router.decide(confidence=0.3, risk_level="critical", fault_prob=0.95, network_stats=stats2)
        assert d3.mode.value == "EdgeOnly"

        events = [
            build_event("edge_0", "device_001", "Fault", "high", "shutdown", 0.85, "edge"),
            build_event("edge_1", "device_001", "Fault", "medium", "maintain", 0.70, "edge"),
        ]

        resolver = ConflictResolver(strategy="cloud_first", network_status="weak")
        result = resolver.resolve(events)
        assert result["effective_strategy"] == "edge_first"

        resolver2 = ConflictResolver(strategy="cloud_first", network_status="disconnected")
        result2 = resolver2.resolve(events)
        assert result2["effective_strategy"] == "edge_first"

        print("OK")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAIL: {e}")
        return False


def test_energy_scene_pipeline():
    """能源场景流水线测试"""
    print("[3/4] 测试能源场景流水线 ...", end=" ")
    try:
        from consistency.event_schema import (
            Observation, EdgeDecision, Event, EnergyEvent,
        )
        from consistency.conflict_detector import ConflictDetector
        from consistency.conflict_resolver import ConflictResolver

        obs = Observation(
            scene="energy",
            node_id="generator_1",
            object_id="grid_a",
            payload={
                "node_type": "generator",
                "power_output": 180.0,
                "local_rtt_ms": 30.0,
            },
            trace_id="trace-energy-test-001",
        )

        assert obs.scene == "energy"

        ed = EdgeDecision(
            event_id=obs.event_id,
            trace_id=obs.trace_id,
            scene="energy",
            node_id="generator_1",
            predicted_label="Stable",
            risk_level="low",
            action="maintain",
            confidence=0.88,
            model_version="energy_mock_v1",
            reason="Power output within stable range",
            inference_ms=8.0,
        )

        assert ed.scene == "energy"
        assert ed.action == "maintain"

        energy_event = EnergyEvent(
            node_id="generator_1",
            node_type="generator",
            grid_id="grid_a",
            stability_label="Stable",
            risk_level="low",
            action="maintain",
            confidence=0.88,
            current_power=180.0,
            requested_power_adjustment=0.0,
            source="edge",
            trace_id=obs.trace_id,
        )

        assert energy_event.node_type == "generator"
        assert energy_event.grid_id == "grid_a"

        consumer_event = EnergyEvent(
            node_id="consumer_1",
            node_type="consumer",
            grid_id="grid_a",
            stability_label="Warning",
            risk_level="medium",
            action="reduce_load",
            confidence=0.72,
            current_power=90.0,
            requested_power_adjustment=-10.0,
            source="edge",
            trace_id=obs.trace_id,
        )

        events = [
            Event.from_edge_decision(ed),
        ]

        detector = ConflictDetector()
        result = detector.detect(events)
        assert result["total_events"] == 1

        print("OK")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAIL: {e}")
        return False


def test_consistency_integration():
    """一致性与路由集成测试"""
    print("[4/4] 测试一致性与路由集成 ...", end=" ")
    try:
        from consistency.event_schema import build_event
        from consistency.conflict_detector import ConflictDetector
        from consistency.conflict_resolver import ConflictResolver
        from routing import Router, NetworkStatus, create_router, create_network_simulator

        events = [
            build_event("edge_0", "device_001", "Heat Dissipation Failure", "high", "shutdown", 0.85, "edge"),
            build_event("edge_1", "device_001", "Normal", "low", "monitor", 0.92, "edge"),
            build_event("cloud_gcm", "device_001", "Heat Dissipation Failure", "critical", "shutdown", 0.95, "cloud"),
        ]

        detector = ConflictDetector()
        detect_result = detector.detect(events)

        assert detect_result["conflict_count"] >= 2
        assert detect_result["conflict_type_counts"]["label_conflict"] >= 1
        assert detect_result["conflict_type_counts"]["action_conflict"] >= 1

        for strategy in ["highest_risk_first", "highest_confidence_first", "cloud_first", "edge_first"]:
            resolver = ConflictResolver(strategy=strategy)
            result = resolver.resolve(events, detect_result["conflict_details"])
            assert result["final_decision_obj"] is not None
            fd = result["final_decision_obj"]
            assert fd.final_action in ["monitor", "warn", "maintain", "shutdown", "replace"]
            assert fd.decision_source in ["edge_only", "cloud_only", "arbitrated"]

        router = create_router(confidence_threshold=0.7)
        sim = create_network_simulator(seed=42)

        for net_status in [NetworkStatus.NORMAL, NetworkStatus.WEAK, NetworkStatus.DISCONNECTED]:
            sim.set_status(net_status)
            router.set_network_status(net_status)
            stats = sim.get_network_stats()

            d = router.decide(confidence=0.5, risk_level="high", fault_prob=0.75, network_stats=stats)

            resolver = ConflictResolver(strategy="cloud_first", network_status=net_status.value)
            result = resolver.resolve(events, detect_result["conflict_details"])

            assert result["effective_strategy"] is not None

        print("OK")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAIL: {e}")
        return False


def main():
    print("=" * 60)
    print("系统集成测试")
    print("=" * 60)

    tests = [
        test_industrial_pipeline,
        test_weaknet_fallback,
        test_energy_scene_pipeline,
        test_consistency_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"通过: {passed}/{len(tests)}, 失败: {failed}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("✅ 所有集成测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()