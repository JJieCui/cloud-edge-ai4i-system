"""
路由模块冒烟测试
运行方式: python -m routing.test_router
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_network_simulator():
    from routing import NetworkStatus, NetworkSimulator, create_network_simulator

    print("[1/5] 测试 network_simulator.py ...", end=" ")
    try:
        sim = create_network_simulator(seed=42)

        for status in NetworkStatus:
            sim.set_status(status)
            stats = sim.get_network_stats()

            if status == NetworkStatus.NORMAL:
                assert 10 <= stats.latency_ms <= 50, f"Normal latency {stats.latency_ms} out of range"
                assert stats.packet_loss_rate < 0.01, f"Normal packet loss {stats.packet_loss_rate} too high"
            elif status == NetworkStatus.WEAK:
                assert 100 <= stats.latency_ms <= 300, f"Weak latency {stats.latency_ms} out of range"
                assert stats.packet_loss_rate >= 0.05, f"Weak packet loss {stats.packet_loss_rate} too low"
            elif status == NetworkStatus.HIGH_LATENCY:
                assert 500 <= stats.latency_ms <= 2000, f"High latency {stats.latency_ms} out of range"
            elif status == NetworkStatus.DISCONNECTED:
                assert stats.latency_ms == float('inf'), f"Disconnected latency should be inf"
                assert stats.packet_loss_rate == 1.0, f"Disconnected loss should be 1.0"

        history = sim.get_history()
        assert len(history) == 4, f"Expected 4 history entries, got {len(history)}"

        sim.reset()
        assert sim.get_status() == NetworkStatus.NORMAL
        assert len(sim.get_history()) == 0

        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_routing_policy():
    from routing import (
        ConfidenceThresholdPolicy,
        RiskLevelPolicy,
        NetworkAwarePolicy,
        CriticalRiskPolicy,
        CompositePolicy,
        NetworkStatus,
    )

    print("[2/5] 测试 policy.py ...", end=" ")
    try:
        conf_policy = ConfidenceThresholdPolicy(threshold=0.7)
        assert conf_policy.should_route_to_cloud(0.5, "low", 0.3, NetworkStatus.NORMAL)
        assert not conf_policy.should_route_to_cloud(0.9, "low", 0.1, NetworkStatus.NORMAL)

        risk_policy = RiskLevelPolicy(high_risk_threshold=0.6)
        assert risk_policy.should_route_to_cloud(0.9, "high", 0.8, NetworkStatus.NORMAL)
        assert not risk_policy.should_route_to_cloud(0.9, "low", 0.1, NetworkStatus.NORMAL)

        net_policy = NetworkAwarePolicy(allow_cloud_on_high_latency=True)
        assert not net_policy.should_route_to_cloud(0.5, "high", 0.7, NetworkStatus.DISCONNECTED)
        assert not net_policy.should_route_to_cloud(0.5, "high", 0.7, NetworkStatus.WEAK)
        assert net_policy.should_route_to_cloud(0.5, "high", 0.7, NetworkStatus.HIGH_LATENCY)

        critical_policy = CriticalRiskPolicy(critical_threshold=0.85)
        assert critical_policy.should_route_to_cloud(0.9, "high", 0.9, NetworkStatus.NORMAL)
        assert not critical_policy.should_route_to_cloud(0.9, "high", 0.5, NetworkStatus.NORMAL)

        composite = CompositePolicy([critical_policy, conf_policy])
        assert composite.should_route_to_cloud(0.9, "low", 0.9, NetworkStatus.NORMAL)
        assert composite.should_route_to_cloud(0.5, "low", 0.3, NetworkStatus.NORMAL)
        assert not composite.should_route_to_cloud(0.9, "low", 0.3, NetworkStatus.NORMAL)

        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_router_decision():
    from routing import Router, NetworkStatus, RoutingMode

    print("[3/5] 测试 router.py 决策逻辑 ...", end=" ")
    try:
        router = Router(confidence_threshold=0.7, critical_risk_threshold=0.85)

        router.set_network_status(NetworkStatus.NORMAL)
        d = router.decide(0.9, "low", 0.1)
        assert d.mode == RoutingMode.EDGE_ONLY, f"Expected EDGE_ONLY, got {d.mode}"

        d = router.decide(0.5, "low", 0.3)
        assert d.mode == RoutingMode.CLOUD_EDGE, f"Expected CLOUD_EDGE for low confidence, got {d.mode}"

        d = router.decide(0.9, "high", 0.75)
        assert d.mode == RoutingMode.CLOUD_EDGE, f"Expected CLOUD_EDGE for high risk, got {d.mode}"

        d = router.decide(0.9, "low", 0.9)
        assert d.mode == RoutingMode.CLOUD_ONLY, f"Expected CLOUD_ONLY for critical fault_prob, got {d.mode}"

        router.set_network_status(NetworkStatus.DISCONNECTED)
        d = router.decide(0.5, "high", 0.7)
        assert d.mode == RoutingMode.EDGE_ONLY, f"Expected EDGE_ONLY when disconnected, got {d.mode}"

        router.set_network_status(NetworkStatus.WEAK)
        d = router.decide(0.5, "high", 0.7)
        assert d.mode == RoutingMode.WEAKNET_AUTONOMY, f"Expected WEAKNET_AUTONOMY, got {d.mode}"
        assert d.pending_review is True

        router.set_network_status(NetworkStatus.WEAK)
        d = router.decide(0.9, "low", 0.1)
        assert d.mode == RoutingMode.EDGE_ONLY, f"Expected EDGE_ONLY for low risk on weak net, got {d.mode}"

        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_router_logging():
    from routing import Router, NetworkStatus

    print("[4/5] 测试 router.py 日志与CSV ...", end=" ")
    try:
        router = Router(confidence_threshold=0.7)

        router.decide(0.9, "low", 0.1)
        router.decide(0.5, "high", 0.7)
        router.decide(0.6, "medium", 0.5)

        log = router.get_log()
        assert len(log) == 3, f"Expected 3 log entries, got {len(log)}"

        router.save_log_to_csv(file_path="logs/test_routing_log.csv", append=False)
        router.clear_log()
        assert len(router.get_log()) == 0

        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_routing_end_to_end():
    from routing import Router, NetworkStatus, NetworkSimulator, RoutingMode, create_router, create_network_simulator

    print("[5/5] 测试路由端到端流程 ...", end=" ")
    try:
        sim = create_network_simulator(seed=123)
        router = create_router(confidence_threshold=0.7)

        scenarios = [
            (NetworkStatus.NORMAL, 0.9, "low", 0.1, RoutingMode.EDGE_ONLY),
            (NetworkStatus.NORMAL, 0.5, "medium", 0.4, RoutingMode.CLOUD_EDGE),
            (NetworkStatus.WEAK, 0.9, "high", 0.85, RoutingMode.WEAKNET_AUTONOMY),
            (NetworkStatus.HIGH_LATENCY, 0.3, "high", 0.75, RoutingMode.CLOUD_EDGE),
            (NetworkStatus.DISCONNECTED, 0.2, "critical", 0.95, RoutingMode.EDGE_ONLY),
        ]

        for net_status, conf, risk, fault_prob, expected_mode in scenarios:
            sim.set_status(net_status)
            router.set_network_status(net_status)
            stats = sim.get_network_stats()
            decision = router.decide(conf, risk, fault_prob, network_stats=stats)
            assert decision.mode == expected_mode, (
                f"Network={net_status.value}, Conf={conf}, Risk={risk}, FaultProb={fault_prob}: "
                f"Expected {expected_mode}, got {decision.mode}"
            )

        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    print("=" * 60)
    print("路由模块冒烟测试")
    print("=" * 60)

    tests = [
        test_network_simulator,
        test_routing_policy,
        test_router_decision,
        test_router_logging,
        test_routing_end_to_end,
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
        print("✅ 所有路由模块测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()