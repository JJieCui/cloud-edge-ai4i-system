import json
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path

from .event_schema import Event, RISK_LEVELS, FinalDecision
from .conflict_detector import ConflictDetector, CONFLICT_SUMMARY_PATH

RESOLUTION_STRATEGIES = [
    "highest_risk_first",
    "highest_confidence_first",
    "cloud_first",
    "edge_first",
]

NETWORK_STATUSES = ["normal", "weak", "high_latency", "disconnected"]


class ConflictResolver:
    def __init__(self, strategy: str = "highest_risk_first", network_status: str = "normal"):
        if strategy not in RESOLUTION_STRATEGIES:
            raise ValueError(f"strategy 必须是 {RESOLUTION_STRATEGIES} 之一")
        if network_status not in NETWORK_STATUSES:
            raise ValueError(f"network_status 必须是 {NETWORK_STATUSES} 之一")
        self.strategy = strategy
        self.network_status = network_status
        self.total_resolutions = 0
        self.successful_resolutions = 0

    def resolve(self, events: List[Event], conflicts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if len(events) == 0:
            return {"final_decision": None, "resolved_conflicts": 0, "strategy": self.strategy}

        if conflicts is None:
            detector = ConflictDetector()
            detect_result = detector.detect(events)
            conflicts = detect_result["conflict_details"]

        self.total_resolutions = len(conflicts)
        resolved_events = []
        resolution_log = []

        device_events = {}
        for event in events:
            key = event.device_id
            if key not in device_events:
                device_events[key] = []
            device_events[key].append(event)

        for device_id, evts in device_events.items():
            if len(evts) == 1:
                resolved_events.append(evts[0])
                continue

            effective_strategy = self._get_effective_strategy()
            winning_event = self._apply_strategy(evts, effective_strategy)
            resolved_events.append(winning_event)

            device_conflicts = [c for c in conflicts if c["device_id"] == device_id]
            if device_conflicts:
                resolution_log.append({
                    "device_id": device_id,
                    "strategy": effective_strategy,
                    "network_status": self.network_status,
                    "conflict_types": [c["conflict_type"] for c in device_conflicts],
                    "winner_node": winning_event.node_id,
                    "winner_risk_level": winning_event.risk_level,
                    "winner_action": winning_event.action,
                    "winner_confidence": winning_event.confidence,
                    "winner_source": winning_event.source,
                })
                self.successful_resolutions += 1

        final_decision_event = None
        if resolved_events:
            effective_strategy = self._get_effective_strategy()
            final_decision_event = self._apply_strategy(resolved_events, effective_strategy)

        success_rate = (
            self.successful_resolutions / self.total_resolutions
            if self.total_resolutions > 0 else 1.0
        )

        final_decision_obj = None
        if final_decision_event:
            has_conflict = self.total_resolutions > 0
            decision_source = "arbitrated" if has_conflict else (
                "cloud_only" if final_decision_event.source == "cloud" else "edge_only"
            )
            final_decision_obj = FinalDecision(
                trace_id=final_decision_event.trace_id,
                scene=final_decision_event.scene,
                final_label=final_decision_event.fault_label,
                final_risk_level=final_decision_event.risk_level,
                final_action=final_decision_event.action,
                confidence=final_decision_event.confidence,
                decision_source=decision_source,
                conflict_detected=has_conflict,
                arbitration_reason=self._build_arbitration_reason(effective_strategy) if has_conflict else "无冲突，直接采用",
            )

        return {
            "final_decision": final_decision_event.to_dict() if final_decision_event else None,
            "final_decision_obj": final_decision_obj,
            "resolved_events": [e.to_dict() for e in resolved_events],
            "resolution_log": resolution_log,
            "total_conflicts": self.total_resolutions,
            "resolved_count": self.successful_resolutions,
            "success_rate": round(success_rate, 4),
            "strategy": self.strategy,
            "effective_strategy": effective_strategy,
            "network_status": self.network_status,
        }

    def _get_effective_strategy(self) -> str:
        if self.network_status in ["weak", "disconnected"]:
            return "edge_first"
        return self.strategy

    def _build_arbitration_reason(self, effective_strategy: str) -> str:
        base_reason = f"使用 {effective_strategy} 策略仲裁结果"
        if self.network_status in ["weak", "disconnected"]:
            network_desc = "网络断开" if self.network_status == "disconnected" else "弱网"
            base_reason += f"（{network_desc}，自动切换为边缘优先）"
        return base_reason

    def _apply_strategy(self, events: List[Event], strategy: str = None) -> Event:
        s = strategy or self.strategy
        if s == "highest_risk_first":
            return max(events, key=lambda e: (e.risk_level_order(), e.confidence))
        elif s == "highest_confidence_first":
            return max(events, key=lambda e: (e.confidence, e.risk_level_order()))
        elif s == "cloud_first":
            cloud_events = [e for e in events if e.source == "cloud"]
            if cloud_events:
                return max(cloud_events, key=lambda e: (e.risk_level_order(), e.confidence))
            return max(events, key=lambda e: (e.risk_level_order(), e.confidence))
        elif s == "edge_first":
            edge_events = [e for e in events if e.source == "edge"]
            if edge_events:
                return max(edge_events, key=lambda e: (e.risk_level_order(), e.confidence))
            return max(events, key=lambda e: (e.risk_level_order(), e.confidence))
        else:
            return events[0]

    def save_resolution_log(self, result: Dict[str, Any], output_dir: Path = CONFLICT_SUMMARY_PATH.parent) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "resolution_log.csv"

        if result["resolution_log"]:
            df = pd.DataFrame(result["resolution_log"])
            df.to_csv(output_path, index=False, encoding="utf-8-sig")

        summary_path = output_dir / "resolution_summary.csv"
        summary_rows = [
            {"metric": "strategy", "value": result["strategy"], "description": "仲裁策略"},
            {"metric": "total_conflicts", "value": result["total_conflicts"], "description": "总冲突数"},
            {"metric": "resolved_count", "value": result["resolved_count"], "description": "已解决数"},
            {"metric": "success_rate", "value": result["success_rate"], "description": "解决成功率"},
        ]
        pd.DataFrame(summary_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")

        return output_path


def main():
    print("=" * 70)
    print("冲突仲裁模块测试")
    print("=" * 70)

    from .event_schema import build_event

    test_events = [
        build_event(
            node_id="edge_node_0",
            device_id="device_001",
            fault_label="Heat Dissipation Failure",
            risk_level="high",
            action="shutdown",
            confidence=0.85,
            source="edge",
        ),
        build_event(
            node_id="edge_node_1",
            device_id="device_001",
            fault_label="Heat Dissipation Failure",
            risk_level="medium",
            action="maintain",
            confidence=0.65,
            source="edge",
        ),
        build_event(
            node_id="cloud_gcm",
            device_id="device_001",
            fault_label="Heat Dissipation Failure",
            risk_level="critical",
            action="shutdown",
            confidence=0.95,
            source="cloud",
        ),
        build_event(
            node_id="edge_node_2",
            device_id="device_002",
            fault_label="Normal",
            risk_level="low",
            action="monitor",
            confidence=0.92,
            source="edge",
        ),
    ]

    detector = ConflictDetector()
    detect_result = detector.detect(test_events)

    print(f"\n=== 冲突检测 ===")
    print(f"总事件数: {detect_result['total_events']}")
    print(f"冲突总数: {detect_result['conflict_count']}")

    for strategy in RESOLUTION_STRATEGIES:
        print(f"\n{'='*50}")
        print(f"仲裁策略: {strategy}")
        print("=" * 50)

        resolver = ConflictResolver(strategy=strategy)
        result = resolver.resolve(test_events, detect_result["conflict_details"])

        print(f"\n总冲突数: {result['total_conflicts']}")
        print(f"已解决数: {result['resolved_count']}")
        print(f"解决成功率: {result['success_rate']:.2%}")
        print(f"生效策略: {result.get('effective_strategy', strategy)}")
        print(f"网络状态: {result.get('network_status', 'normal')}")

    # 测试路由感知仲裁（弱网/断网场景）
    print(f"\n{'='*50}")
    print("路由感知仲裁测试")
    print("=" * 50)

    for network_status in ["normal", "weak", "disconnected"]:
        print(f"\n--- 网络状态: {network_status} ---")
        resolver = ConflictResolver(strategy="cloud_first", network_status=network_status)
        result = resolver.resolve(test_events, detect_result["conflict_details"])

        print(f"配置策略: cloud_first")
        print(f"生效策略: {result.get('effective_strategy')}")
        print(f"解决成功率: {result['success_rate']:.2%}")

        if result["final_decision_obj"]:
            fd = result["final_decision_obj"]
            print(f"最终动作: {fd.final_action}")
            print(f"决策来源: {fd.decision_source}")
            print(f"仲裁理由: {fd.arbitration_reason}")

        if result["final_decision_obj"]:
            fd = result["final_decision_obj"]
            print(f"\n最终决策 (FinalDecision):")
            print(f"  决策ID: {fd.decision_id}")
            print(f"  追踪ID: {fd.trace_id}")
            print(f"  场景: {fd.scene}")
            print(f"  故障: {fd.final_label}")
            print(f"  风险: {fd.final_risk_level}")
            print(f"  动作: {fd.final_action}")
            print(f"  置信度: {fd.confidence:.2f}")
            print(f"  决策来源: {fd.decision_source}")
            print(f"  检测到冲突: {fd.conflict_detected}")
            print(f"  仲裁理由: {fd.arbitration_reason}")

        if result["resolution_log"]:
            print(f"\n仲裁详情:")
            for log in result["resolution_log"]:
                print(f"  设备 {log['device_id']}: "
                      f"胜出 {log['winner_node']} "
                      f"(风险={log['winner_risk_level']}, "
                      f"动作={log['winner_action']}, "
                      f"置信度={log['winner_confidence']:.2f})")

    print(f"\n{'='*70}")
    print("保存结果...")

    default_resolver = ConflictResolver(strategy="highest_risk_first")
    default_result = default_resolver.resolve(test_events, detect_result["conflict_details"])
    log_path = default_resolver.save_resolution_log(default_result)
    print(f"仲裁日志已保存到: {log_path}")
    print(f"仲裁汇总已保存到: {log_path.parent / 'resolution_summary.csv'}")


if __name__ == "__main__":
    main()
