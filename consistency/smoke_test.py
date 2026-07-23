"""
一致性模块冒烟测试
运行方式: python -m consistency.smoke_test
"""
import sys
import time


def test_event_schema():
    from consistency.event_schema import (
        Event, EdgeDecision, CloudReview, FinalDecision,
        Observation, RouteDecision, EnergyEvent,
        RISK_LEVELS, ACTIONS, SCENES,
    )

    print("[1/5] 测试 event_schema.py ...", end=" ")
    try:
        obs = Observation(
            scene="industrial", node_id="n1", object_id="d1",
            payload={"x": 1}, deadline_ms=200,
        )
        ed = EdgeDecision(
            event_id=obs.event_id, trace_id=obs.trace_id,
            scene="industrial", node_id="n1",
            predicted_label="Fault", risk_level="high",
            action="shutdown", confidence=0.9,
            model_version="v1",
        )
        cr = CloudReview(
            trace_id=obs.trace_id, reviewed_label="Fault",
            risk_level="high", action="shutdown", confidence=0.95,
            model="gcm-test",
        )
        fd = FinalDecision(
            trace_id=obs.trace_id, scene="industrial",
            final_label="Fault", final_risk_level="high",
            final_action="shutdown", confidence=0.95,
            decision_source="arbitrated",
        )
        evt = Event.from_edge_decision(ed)
        evt2 = Event.from_cloud_review(cr)
        rd = RouteDecision(trace_id=obs.trace_id, route="EdgeCloud")
        ee = EnergyEvent(
            node_id="g1", node_type="generator", grid_id="grid_a",
            stability_label="Stable", risk_level="low",
            action="maintain", confidence=0.9,
            current_power=100.0, requested_power_adjustment=10.0,
            source="edge",
        )
        assert len(RISK_LEVELS) == 4
        assert len(ACTIONS) == 5
        assert len(SCENES) == 2
        assert evt.risk_level == "high"
        assert evt2.source == "cloud"
        assert fd.decision_source == "arbitrated"
        assert ee.node_type == "generator"
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_conflict_detector():
    from consistency.event_schema import build_event
    from consistency.conflict_detector import ConflictDetector

    print("[2/5] 测试 conflict_detector.py ...", end=" ")
    try:
        events = [
            build_event("n1", "d1", "Fault", "high", "shutdown", 0.9, "edge"),
            build_event("n2", "d1", "Fault", "medium", "maintain", 0.7, "edge"),
            build_event("n3", "d2", "Normal", "low", "monitor", 0.95, "edge"),
            build_event("n4", "d2", "Power Failure", "high", "shutdown", 0.8, "edge"),
        ]
        detector = ConflictDetector(duplicate_time_window_s=60)
        result = detector.detect(events)
        assert result["total_events"] == 4
        assert result["conflict_count"] >= 2
        assert "label_conflict" in result["conflict_type_counts"]
        assert "action_conflict" in result["conflict_type_counts"]
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_conflict_resolver():
    from consistency.event_schema import build_event
    from consistency.conflict_resolver import ConflictResolver

    print("[3/5] 测试 conflict_resolver.py ...", end=" ")
    try:
        events = [
            build_event("n1", "d1", "Fault", "high", "shutdown", 0.9, "edge"),
            build_event("n2", "d1", "Fault", "medium", "maintain", 0.7, "edge"),
        ]
        resolver = ConflictResolver(strategy="highest_risk_first")
        result = resolver.resolve(events)
        assert result["final_decision"] is not None
        assert result["final_decision_obj"] is not None
        assert result["final_decision_obj"].final_risk_level == "high"
        assert result["final_decision_obj"].decision_source == "arbitrated"
        assert result["success_rate"] >= 0.0
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_energy_arbitrator():
    from consistency.energy_arbitrator import EnergyArbitrator, GridState
    from consistency.event_schema import EnergyEvent

    print("[4/5] 测试 energy_arbitrator.py ...", end=" ")
    try:
        grid = GridState(
            grid_id="grid_a",
            total_generation_capacity=200.0,
            total_load=180.0,
            max_generation_capacity=240.0,
            min_generation_capacity=120.0,
        )
        events = [
            EnergyEvent("g1", "generator", "grid_a", "Stable", "low",
                        "increase_generation", 0.85, 100.0, 30.0, "edge", priority=1),
            EnergyEvent("l1", "consumer", "grid_a", "Overload", "high",
                        "reduce_load", 0.92, 80.0, -20.0, "edge", priority=3),
        ]
        arbitrator = EnergyArbitrator(grid_state=grid)
        result = arbitrator.arbitrate(events)
        assert result["total_events"] == 2
        assert result["approved_count"] >= 1
        assert result["constraint_violations"] == 0
        assert result["final_grid_state"] is not None
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_csv_output():
    import os
    from pathlib import Path

    print("[5/5] 测试 CSV 结果文件生成 ...", end=" ")
    try:
        results_dir = Path(__file__).parent.parent / "results" / "tables"
        expected_files = [
            "conflict_summary.csv",
            "conflict_details.csv",
            "resolution_summary.csv",
            "resolution_log.csv",
            "energy_summary.csv",
            "energy_arbitration_log.csv",
        ]
        for f in expected_files:
            assert (results_dir / f).exists(), f"缺少文件: {f}"
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    print("=" * 60)
    print("一致性模块冒烟测试")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tests = [
        test_event_schema,
        test_conflict_detector,
        test_conflict_resolver,
        test_energy_arbitrator,
        test_csv_output,
    ]

    passed = 0
    failed = 0
    start_time = time.time()

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    elapsed = time.time() - start_time

    print("-" * 60)
    print(f"通过: {passed}/{len(tests)}, 失败: {failed}")
    print(f"总耗时: {elapsed:.2f} 秒")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("✅ 所有冒烟测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()
