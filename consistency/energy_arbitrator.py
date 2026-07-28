import os
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .event_schema import EnergyEvent, RISK_LEVELS, ENERGY_ACTIONS

RESULTS_DIR = Path(__file__).parent.parent / "results" / "tables"
ENERGY_ARBITRATION_LOG_PATH = RESULTS_DIR / "energy_arbitration_log.csv"
ENERGY_SUMMARY_PATH = RESULTS_DIR / "energy_summary.csv"


@dataclass
class GridState:
    grid_id: str
    total_generation_capacity: float
    total_load: float
    max_generation_capacity: float
    min_generation_capacity: float
    frequency: float = 50.0
    frequency_deadband: float = 0.2

    @property
    def current_margin(self) -> float:
        return self.total_generation_capacity - self.total_load

    @property
    def upward_reserve(self) -> float:
        return self.max_generation_capacity - self.total_generation_capacity

    @property
    def downward_reserve(self) -> float:
        return self.total_generation_capacity - self.min_generation_capacity


class EnergyArbitrator:
    def __init__(self, grid_state: Optional[GridState] = None):
        self.grid_state = grid_state
        self.total_events = 0
        self.resource_conflicts = []
        self.arbitration_log = []
        self.constraint_violations = 0

    def detect_resource_conflicts(self, events: List[EnergyEvent]) -> List[Dict[str, Any]]:
        conflicts = []
        if not events or not self.grid_state:
            return conflicts

        self.total_events = len(events)
        grid_events = [e for e in events if e.grid_id == self.grid_state.grid_id]
        if not grid_events:
            return conflicts

        total_requested_increase = 0.0
        total_requested_decrease = 0.0
        high_risk_requests = []
        generator_events = [e for e in grid_events if e.node_type == "generator"]
        consumer_events = [e for e in grid_events if e.node_type == "consumer"]

        for evt in grid_events:
            adj = evt.requested_power_adjustment
            if evt.risk_level in ("high", "critical"):
                high_risk_requests.append(evt)
            if adj > 0:
                total_requested_increase += adj
            else:
                total_requested_decrease += abs(adj)

        supply_increase_capable = self.grid_state.upward_reserve
        load_decrease_possible = self.grid_state.total_load * 0.5

        net_requested_increase = total_requested_increase - total_requested_decrease
        if net_requested_increase > supply_increase_capable * 1.1:
            conflicts.append({
                "conflict_type": "resource_conflict",
                "sub_type": "generation_capacity_exceeded",
                "severity": "high" if high_risk_requests else "medium",
                "grid_id": self.grid_state.grid_id,
                "description": (
                    f"净增功率请求 {net_requested_increase:.1f} MW 超出上调容量 "
                    f"{supply_increase_capable:.1f} MW"
                ),
                "total_requested_increase": round(total_requested_increase, 2),
                "total_requested_decrease": round(total_requested_decrease, 2),
                "net_requested_increase": round(net_requested_increase, 2),
                "available_upward_reserve": round(supply_increase_capable, 2),
                "involved_nodes": [e.node_id for e in grid_events],
                "high_risk_count": len(high_risk_requests),
            })

        total_generator_reduction = sum(
            abs(e.requested_power_adjustment)
            for e in generator_events
            if e.requested_power_adjustment < 0
        )
        total_load_reduction = sum(
            abs(e.requested_power_adjustment)
            for e in consumer_events
            if e.requested_power_adjustment < 0
        )
        net_decrease = total_generator_reduction - total_load_reduction
        if net_decrease > self.grid_state.downward_reserve * 1.1:
            conflicts.append({
                "conflict_type": "resource_conflict",
                "sub_type": "minimum_generation_violation",
                "severity": "medium",
                "grid_id": self.grid_state.grid_id,
                "description": (
                    f"净减功率请求 {net_decrease:.1f} MW 超出下调容量 "
                    f"{self.grid_state.downward_reserve:.1f} MW"
                ),
                "total_generator_reduction": round(total_generator_reduction, 2),
                "total_load_reduction": round(total_load_reduction, 2),
                "net_decrease": round(net_decrease, 2),
                "available_downward_reserve": round(self.grid_state.downward_reserve, 2),
                "involved_nodes": [e.node_id for e in grid_events],
            })

        generators_increasing = [e for e in generator_events if e.requested_power_adjustment > 0]
        loads_increasing = [e for e in consumer_events if e.requested_power_adjustment > 0]
        if len(generators_increasing) >= 2 and len(loads_increasing) >= 1:
            total_gen_increase = sum(e.requested_power_adjustment for e in generators_increasing)
            total_load_increase = sum(e.requested_power_adjustment for e in loads_increasing)
            if total_gen_increase < total_load_increase:
                conflicts.append({
                    "conflict_type": "resource_conflict",
                    "sub_type": "supply_demand_mismatch",
                    "severity": "high" if high_risk_requests else "medium",
                    "grid_id": self.grid_state.grid_id,
                    "description": (
                        f"发电侧增容 {total_gen_increase:.1f} MW < 负荷侧增长 "
                        f"{total_load_increase:.1f} MW，供需不平衡"
                    ),
                    "generator_increase": round(total_gen_increase, 2),
                    "load_increase": round(total_load_increase, 2),
                    "involved_generators": [e.node_id for e in generators_increasing],
                    "involved_loads": [e.node_id for e in loads_increasing],
                    "high_risk_count": len(high_risk_requests),
                })

        self.resource_conflicts = conflicts
        return conflicts

    def _priority_score(self, event: EnergyEvent) -> tuple:
        return (
            -event.risk_level_order(),
            -event.confidence,
            event.data_age_ms,
            -event.priority,
        )

    def arbitrate(self, events: List[EnergyEvent]) -> Dict[str, Any]:
        if not events:
            return {
                "approved_events": [],
                "denied_events": [],
                "total_conflicts": 0,
                "constraint_violations": 0,
                "arbitration_log": [],
                "final_grid_state": None,
            }

        grid_id = events[0].grid_id
        if self.grid_state is None:
            self.grid_state = GridState(
                grid_id=grid_id,
                total_generation_capacity=sum(
                    e.current_power for e in events if e.node_type == "generator"
                ),
                total_load=sum(
                    e.current_power for e in events if e.node_type == "consumer"
                ),
                max_generation_capacity=sum(
                    e.current_power * 1.2 for e in events if e.node_type == "generator"
                ),
                min_generation_capacity=sum(
                    e.current_power * 0.6 for e in events if e.node_type == "generator"
                ),
            )

        self.detect_resource_conflicts(events)

        sorted_events = sorted(events, key=self._priority_score)

        approved = []
        denied = []
        current_gen = self.grid_state.total_generation_capacity
        current_load = self.grid_state.total_load
        max_gen = self.grid_state.max_generation_capacity
        min_gen = self.grid_state.min_generation_capacity

        for evt in sorted_events:
            adj = evt.requested_power_adjustment
            approved_power = 0.0
            denied_reason = None

            if evt.node_type == "generator":
                new_gen = current_gen + adj
                if adj > 0:
                    if new_gen <= max_gen:
                        approved_power = adj
                        current_gen = new_gen
                    else:
                        available = max_gen - current_gen
                        if available > 0 and evt.risk_level in ("high", "critical"):
                            approved_power = available
                            current_gen = max_gen
                            denied_reason = "partial_approval_max_capacity"
                        else:
                            approved_power = 0.0
                            denied_reason = "max_generation_capacity_exceeded"
                elif adj < 0:
                    if new_gen >= min_gen:
                        approved_power = adj
                        current_gen = new_gen
                    else:
                        available = current_gen - min_gen
                        if available > 0 and evt.risk_level in ("high", "critical"):
                            approved_power = -available
                            current_gen = min_gen
                            denied_reason = "partial_approval_min_capacity"
                        else:
                            approved_power = 0.0
                            denied_reason = "minimum_generation_violation"
                else:
                    approved_power = 0.0

            elif evt.node_type == "consumer":
                new_load = current_load + adj
                if adj > 0:
                    net_increase = adj - 0
                    supply_margin = current_gen - current_load
                    if new_load <= current_gen:
                        approved_power = adj
                        current_load = new_load
                    else:
                        available = current_gen - current_load
                        if available > 0 and evt.risk_level in ("high", "critical"):
                            approved_power = available
                            current_load = current_gen
                            denied_reason = "partial_approval_supply_limit"
                        else:
                            approved_power = 0.0
                            denied_reason = "insufficient_generation_supply"
                elif adj < 0:
                    approved_power = adj
                    current_load = new_load
                else:
                    approved_power = 0.0

            if abs(approved_power) > 1e-6 or adj == 0:
                final_action = evt.action
                if denied_reason and denied_reason.startswith("partial"):
                    final_action = "reduce_load" if evt.node_type == "consumer" else "maintain"
                approved.append({
                    "event": evt,
                    "approved_adjustment": round(approved_power, 2),
                    "requested_adjustment": round(adj, 2),
                    "final_action": final_action,
                    "denied_reason": denied_reason,
                })
            else:
                denied.append({
                    "event": evt,
                    "requested_adjustment": round(adj, 2),
                    "denied_reason": denied_reason,
                })

            log_entry = {
                "node_id": evt.node_id,
                "node_type": evt.node_type,
                "risk_level": evt.risk_level,
                "confidence": evt.confidence,
                "priority": evt.priority,
                "requested_adjustment": round(adj, 2),
                "approved_adjustment": round(approved_power, 2),
                "final_action": evt.action if abs(approved_power) > 1e-6 else "maintain",
                "status": "approved" if abs(approved_power) > 1e-6 or adj == 0 else "denied",
                "denied_reason": denied_reason or "",
            }
            self.arbitration_log.append(log_entry)

        final_gen = current_gen
        final_load = current_load
        violations = 0
        if final_gen > max_gen + 1e-6 or final_gen < min_gen - 1e-6:
            violations += 1
        if final_load > final_gen + 1e-6:
            violations += 1
        self.constraint_violations = violations

        final_state = {
            "grid_id": grid_id,
            "final_generation": round(final_gen, 2),
            "final_load": round(final_load, 2),
            "net_imbalance": round(final_gen - final_load, 2),
            "generation_utilization": round(final_gen / max_gen * 100, 2) if max_gen > 0 else 0,
            "constraint_violations": violations,
        }

        return {
            "approved_events": approved,
            "denied_events": denied,
            "total_events": len(events),
            "approved_count": len(approved),
            "denied_count": len(denied),
            "resource_conflicts": self.resource_conflicts,
            "total_conflicts": len(self.resource_conflicts),
            "constraint_violations": violations,
            "arbitration_log": self.arbitration_log,
            "final_grid_state": final_state,
        }

    def save_results(self, result: Dict[str, Any]) -> None:
        os.makedirs(RESULTS_DIR, exist_ok=True)

        if self.arbitration_log:
            log_path = ENERGY_ARBITRATION_LOG_PATH
            fieldnames = list(self.arbitration_log[0].keys())
            with open(log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.arbitration_log)

        summary_data = {
            "total_events": result.get("total_events", 0),
            "approved_count": result.get("approved_count", 0),
            "denied_count": result.get("denied_count", 0),
            "resource_conflicts": result.get("total_conflicts", 0),
            "constraint_violations": result.get("constraint_violations", 0),
        }
        if result.get("final_grid_state"):
            summary_data.update(result["final_grid_state"])

        summary_path = ENERGY_SUMMARY_PATH
        fieldnames = list(summary_data.keys())
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(summary_data)


def main():
    print("=" * 70)
    print("能源全局仲裁模块测试")
    print("=" * 70)

    grid_state = GridState(
        grid_id="grid_a",
        total_generation_capacity=200.0,
        total_load=180.0,
        max_generation_capacity=240.0,
        min_generation_capacity=120.0,
    )

    print(f"\n电网初始状态:")
    print(f"  总发电容量: {grid_state.total_generation_capacity} MW")
    print(f"  总负荷: {grid_state.total_load} MW")
    print(f"  最大发电: {grid_state.max_generation_capacity} MW")
    print(f"  最小发电: {grid_state.min_generation_capacity} MW")
    print(f"  当前裕度: {grid_state.current_margin} MW")
    print(f"  上调备用: {grid_state.upward_reserve} MW")
    print(f"  下调备用: {grid_state.downward_reserve} MW")

    test_events = [
        EnergyEvent(
            node_id="gen_0",
            node_type="generator",
            grid_id="grid_a",
            stability_label="Stable",
            risk_level="low",
            action="increase_generation",
            confidence=0.85,
            current_power=100.0,
            requested_power_adjustment=30.0,
            source="edge",
            priority=1,
        ),
        EnergyEvent(
            node_id="gen_1",
            node_type="generator",
            grid_id="grid_a",
            stability_label="Stable",
            risk_level="medium",
            action="increase_generation",
            confidence=0.75,
            current_power=100.0,
            requested_power_adjustment=25.0,
            source="edge",
            priority=2,
        ),
        EnergyEvent(
            node_id="load_0",
            node_type="consumer",
            grid_id="grid_a",
            stability_label="Overload Risk",
            risk_level="high",
            action="reduce_load",
            confidence=0.92,
            current_power=80.0,
            requested_power_adjustment=-20.0,
            source="edge",
            priority=3,
        ),
        EnergyEvent(
            node_id="load_1",
            node_type="consumer",
            grid_id="grid_a",
            stability_label="High Demand",
            risk_level="medium",
            action="maintain",
            confidence=0.65,
            current_power=60.0,
            requested_power_adjustment=15.0,
            source="edge",
            priority=2,
        ),
        EnergyEvent(
            node_id="load_2",
            node_type="consumer",
            grid_id="grid_a",
            stability_label="Critical Equipment",
            risk_level="critical",
            action="emergency_limit",
            confidence=0.98,
            current_power=40.0,
            requested_power_adjustment=-10.0,
            source="cloud",
            priority=5,
        ),
    ]

    print(f"\n测试事件数: {len(test_events)}")
    for i, evt in enumerate(test_events):
        print(f"  [{i}] {evt.node_id} ({evt.node_type}) - {evt.risk_level} - "
              f"req={evt.requested_power_adjustment:+.1f} MW - prio={evt.priority}")

    arbitrator = EnergyArbitrator(grid_state=grid_state)

    print("\n--- 资源冲突检测 ---")
    conflicts = arbitrator.detect_resource_conflicts(test_events)
    print(f"检测到资源冲突: {len(conflicts)}")
    for i, c in enumerate(conflicts):
        print(f"  [{i}] {c['sub_type']} ({c['severity']})")
        print(f"      {c['description']}")

    print("\n--- 全局仲裁结果 ---")
    result = arbitrator.arbitrate(test_events)

    print(f"总事件数: {result['total_events']}")
    print(f"通过: {result['approved_count']}")
    print(f"拒绝: {result['denied_count']}")
    print(f"资源冲突: {result['total_conflicts']}")
    print(f"约束违反: {result['constraint_violations']}")

    print(f"\n--- 通过的事件 ---")
    for item in result["approved_events"]:
        evt = item["event"]
        status = "完全通过" if not item["denied_reason"] else "部分通过"
        print(f"  {evt.node_id}: {status}")
        print(f"    请求: {item['requested_adjustment']:+.1f} MW, "
              f"批准: {item['approved_adjustment']:+.1f} MW")
        if item["denied_reason"]:
            print(f"    原因: {item['denied_reason']}")

    if result["denied_events"]:
        print(f"\n--- 拒绝的事件 ---")
        for item in result["denied_events"]:
            evt = item["event"]
            print(f"  {evt.node_id}: {item['denied_reason']}")
            print(f"    请求: {item['requested_adjustment']:+.1f} MW")

    if result["final_grid_state"]:
        fs = result["final_grid_state"]
        print(f"\n--- 最终电网状态 ---")
        print(f"  发电量: {fs['final_generation']} MW")
        print(f"  负荷: {fs['final_load']} MW")
        print(f"  净不平衡: {fs['net_imbalance']} MW")
        print(f"  发电利用率: {fs['generation_utilization']}%")
        print(f"  约束违反: {fs['constraint_violations']}")

    arbitrator.save_results(result)
    print(f"\n仲裁日志已保存到: {ENERGY_ARBITRATION_LOG_PATH}")
    print(f"仲裁汇总已保存到: {ENERGY_SUMMARY_PATH}")

    print("\n✅ 能源全局仲裁测试通过！")


if __name__ == "__main__":
    main()
