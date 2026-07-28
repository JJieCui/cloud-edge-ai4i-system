import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path

from .event_schema import Event, RISK_LEVELS

CONFLICT_SUMMARY_PATH = Path(__file__).parent.parent / "results" / "tables" / "conflict_summary.csv"

CONFLICT_TYPES = [
    "duplicate_alert",
    "label_conflict",
    "risk_level_mismatch",
    "action_conflict",
]


class ConflictDetector:
    def __init__(self, duplicate_time_window_s: int = 60):
        self.duplicate_time_window_s = duplicate_time_window_s
        self.total_events = 0
        self.conflict_count = 0
        self.conflict_details = []

    def detect(self, events: List[Event]) -> Dict[str, Any]:
        self.total_events = len(events)
        self.conflict_count = 0
        self.conflict_details = []

        if len(events) < 2:
            return self._build_result()

        duplicate_conflicts = self._detect_duplicate_alerts(events)
        label_conflicts = self._detect_label_conflict(events)
        risk_conflicts = self._detect_risk_level_mismatch(events)
        action_conflicts = self._detect_action_conflict(events)

        all_conflicts = duplicate_conflicts + label_conflicts + risk_conflicts + action_conflicts
        self.conflict_count = len(all_conflicts)
        self.conflict_details = all_conflicts

        return self._build_result()

    def _detect_duplicate_alerts(self, events: List[Event]) -> List[Dict[str, Any]]:
        conflicts = []
        seen = {}

        for event in events:
            key = (event.device_id, event.fault_label)
            ts = event.timestamp

            if key in seen:
                prev_ts = seen[key]["timestamp"]
                try:
                    t1 = datetime.fromisoformat(ts)
                    t2 = datetime.fromisoformat(prev_ts)
                    diff = abs((t1 - t2).total_seconds())
                except (ValueError, TypeError):
                    diff = 0

                if diff <= self.duplicate_time_window_s:
                    conflicts.append({
                        "conflict_type": "duplicate_alert",
                        "severity": "low",
                        "device_id": event.device_id,
                        "fault_label": event.fault_label,
                        "involved_nodes": [seen[key]["node_id"], event.node_id],
                        "description": f"设备 {event.device_id} 在 {diff:.0f}s 内重复上报 {event.fault_label}",
                        "time_diff_s": round(diff, 2),
                    })
            else:
                seen[key] = {"node_id": event.node_id, "timestamp": ts}

        return conflicts

    def _detect_label_conflict(self, events: List[Event]) -> List[Dict[str, Any]]:
        conflicts = []
        device_events = {}

        for event in events:
            key = event.device_id
            if key not in device_events:
                device_events[key] = []
            device_events[key].append(event)

        for device_id, evts in device_events.items():
            if len(evts) < 2:
                continue

            labels = set(e.fault_label for e in evts)
            if len(labels) <= 1:
                continue

            label_list = sorted(labels)
            has_normal = any(e.fault_label.lower() in ("normal", "no_fault", "ok") for e in evts)
            has_fault = any(e.fault_label.lower() not in ("normal", "no_fault", "ok") for e in evts)

            if has_normal and has_fault:
                severity = "high"
            else:
                severity = "medium"

            conflicts.append({
                "conflict_type": "label_conflict",
                "severity": severity,
                "device_id": device_id,
                "fault_label": label_list[-1],
                "involved_nodes": [e.node_id for e in evts],
                "description": (
                    f"设备 {device_id} 预测类别不一致: {', '.join(label_list)} "
                    f"(涉及 {len(evts)} 个节点)"
                ),
                "conflicting_labels": label_list,
                "label_count": len(label_list),
            })

        return conflicts

    def _detect_risk_level_mismatch(self, events: List[Event]) -> List[Dict[str, Any]]:
        conflicts = []
        device_events = {}

        for event in events:
            key = event.device_id
            if key not in device_events:
                device_events[key] = []
            device_events[key].append(event)

        for device_id, evts in device_events.items():
            if len(evts) < 2:
                continue

            risk_levels = set(e.risk_level for e in evts)
            if len(risk_levels) <= 1:
                continue

            max_risk = max(evts, key=lambda e: e.risk_level_order())
            min_risk = min(evts, key=lambda e: e.risk_level_order())
            level_diff = max_risk.risk_level_order() - min_risk.risk_level_order()

            severity = "high" if level_diff >= 2 else "medium"

            conflicts.append({
                "conflict_type": "risk_level_mismatch",
                "severity": severity,
                "device_id": device_id,
                "fault_label": max_risk.fault_label,
                "involved_nodes": [e.node_id for e in evts],
                "description": (
                    f"设备 {device_id} 风险等级不一致: "
                    f"{min_risk.risk_level}({min_risk.node_id}) vs "
                    f"{max_risk.risk_level}({max_risk.node_id}), "
                    f"相差 {level_diff} 级"
                ),
                "min_risk_level": min_risk.risk_level,
                "max_risk_level": max_risk.risk_level,
                "level_diff": level_diff,
            })

        return conflicts

    def _detect_action_conflict(self, events: List[Event]) -> List[Dict[str, Any]]:
        conflicts = []
        device_events = {}

        for event in events:
            key = event.device_id
            if key not in device_events:
                device_events[key] = []
            device_events[key].append(event)

        for device_id, evts in device_events.items():
            if len(evts) < 2:
                continue

            actions = set(e.action for e in evts)
            if len(actions) <= 1:
                continue

            action_list = list(actions)
            high_risk_events = [e for e in evts if e.risk_level in ("high", "critical")]
            severity = "high" if high_risk_events else "medium"

            conflicts.append({
                "conflict_type": "action_conflict",
                "severity": severity,
                "device_id": device_id,
                "fault_label": evts[0].fault_label,
                "involved_nodes": [e.node_id for e in evts],
                "description": (
                    f"设备 {device_id} 动作建议冲突: {', '.join(action_list)} "
                    f"(涉及 {len(evts)} 个节点)"
                ),
                "conflicting_actions": action_list,
                "action_count": len(action_list),
            })

        return conflicts

    def _build_result(self) -> Dict[str, Any]:
        conflict_rate = self.conflict_count / self.total_events if self.total_events > 0 else 0.0

        type_counts = {t: 0 for t in CONFLICT_TYPES}
        for c in self.conflict_details:
            if c["conflict_type"] in type_counts:
                type_counts[c["conflict_type"]] += 1

        severity_counts = {"low": 0, "medium": 0, "high": 0}
        for c in self.conflict_details:
            sev = c.get("severity", "low")
            if sev in severity_counts:
                severity_counts[sev] += 1

        return {
            "total_events": self.total_events,
            "conflict_count": self.conflict_count,
            "conflict_rate": round(conflict_rate, 4),
            "conflict_details": self.conflict_details,
            "conflict_type_counts": type_counts,
            "severity_counts": severity_counts,
        }

    def save_summary(self, result: Dict[str, Any], output_path: Path = CONFLICT_SUMMARY_PATH) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary_rows = []
        summary_rows.append({
            "metric": "total_events",
            "value": result["total_events"],
            "description": "总事件数",
        })
        summary_rows.append({
            "metric": "conflict_count",
            "value": result["conflict_count"],
            "description": "冲突总数",
        })
        summary_rows.append({
            "metric": "conflict_rate",
            "value": result["conflict_rate"],
            "description": "冲突比例",
        })

        for ctype, count in result["conflict_type_counts"].items():
            summary_rows.append({
                "metric": f"type_{ctype}",
                "value": count,
                "description": f"{ctype} 类型冲突数",
            })

        for sev, count in result["severity_counts"].items():
            summary_rows.append({
                "metric": f"severity_{sev}",
                "value": count,
                "description": f"{sev} 严重程度冲突数",
            })

        df = pd.DataFrame(summary_rows)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        detail_path = output_path.parent / "conflict_details.csv"
        if result["conflict_details"]:
            detail_df = pd.DataFrame(result["conflict_details"])
            detail_df.to_csv(detail_path, index=False, encoding="utf-8-sig")

        return output_path


def main():
    print("=" * 70)
    print("冲突检测模块测试")
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
            node_id="edge_node_2",
            device_id="device_002",
            fault_label="Normal",
            risk_level="low",
            action="monitor",
            confidence=0.92,
            source="edge",
        ),
        build_event(
            node_id="edge_node_3",
            device_id="device_002",
            fault_label="Power Failure",
            risk_level="high",
            action="shutdown",
            confidence=0.78,
            source="edge",
        ),
        build_event(
            node_id="edge_node_4",
            device_id="device_003",
            fault_label="Power Failure",
            risk_level="critical",
            action="replace",
            confidence=0.95,
            source="cloud",
        ),
        build_event(
            node_id="edge_node_0",
            device_id="device_003",
            fault_label="Overstrain Failure",
            risk_level="high",
            action="shutdown",
            confidence=0.78,
            source="edge",
        ),
        build_event(
            node_id="edge_node_1",
            device_id="device_004",
            fault_label="Normal",
            risk_level="low",
            action="monitor",
            confidence=0.95,
            source="edge",
        ),
        build_event(
            node_id="edge_node_2",
            device_id="device_004",
            fault_label="Normal",
            risk_level="low",
            action="monitor",
            confidence=0.91,
            source="edge",
        ),
    ]

    print(f"\n测试事件数: {len(test_events)}")
    for i, e in enumerate(test_events):
        print(f"  [{i}] {e.node_id} - {e.device_id} - {e.risk_level} - {e.action}")

    detector = ConflictDetector(duplicate_time_window_s=120)
    result = detector.detect(test_events)

    print(f"\n--- 检测结果 ---")
    print(f"总事件数: {result['total_events']}")
    print(f"冲突总数: {result['conflict_count']}")
    print(f"冲突比例: {result['conflict_rate']:.2%}")

    print(f"\n--- 按类型统计 ---")
    for ctype, count in result["conflict_type_counts"].items():
        print(f"  {ctype}: {count}")

    print(f"\n--- 按严重程度统计 ---")
    for sev, count in result["severity_counts"].items():
        print(f"  {sev}: {count}")

    print(f"\n--- 冲突详情 ---")
    for i, c in enumerate(result["conflict_details"]):
        print(f"\n[{i}] {c['conflict_type']} ({c['severity']})")
        print(f"    {c['description']}")

    output_path = detector.save_summary(result)
    print(f"\n冲突统计已保存到: {output_path}")
    print(f"冲突详情已保存到: {output_path.parent / 'conflict_details.csv'}")


if __name__ == "__main__":
    main()
