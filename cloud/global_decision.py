import os
import json
import pandas as pd
from datetime import datetime

DECISION_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "global_decision_log.csv")


class GlobalDecisionMaker:
    def __init__(self):
        self.decision_count = 0
        self.cloud_overrule_count = 0
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        log_dir = os.path.dirname(DECISION_LOG_PATH)
        os.makedirs(log_dir, exist_ok=True)

    def make_decision(self, edge_result: dict, cloud_result: dict = None) -> dict:
        self.decision_count += 1

        final_decision = {
            "decision_id": f"decision_{int(datetime.now().timestamp() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "device_id": edge_result.get("device_id", "unknown"),
            "edge_fault_label": edge_result.get("edge_fault_label", "unknown"),
            "edge_risk_level": edge_result.get("edge_risk_level", "unknown"),
            "edge_action": edge_result.get("edge_action", "unknown"),
            "edge_confidence": edge_result.get("edge_confidence", 0.0),
            "cloud_was_called": cloud_result is not None,
            "conflict_detected": False,
            "conflict_type": "",
            "final_fault_label": edge_result.get("edge_fault_label", "unknown"),
            "final_risk_level": edge_result.get("edge_risk_level", "unknown"),
            "final_action": edge_result.get("edge_action", "unknown"),
            "final_confidence": edge_result.get("edge_confidence", 0.0),
            "decision_source": "edge",
            "reason": "边缘决策直接生效"
        }

        if cloud_result:
            final_decision.update({
                "gcm_fault_label": cloud_result.get("gcm_fault_label", "unknown"),
                "gcm_risk_level": cloud_result.get("gcm_risk_level", "unknown"),
                "gcm_action": cloud_result.get("gcm_action", "unknown"),
                "gcm_confidence": cloud_result.get("gcm_confidence", 0.0),
                "consistent_with_edge": cloud_result.get("consistent_with_edge", False),
                "cloud_latency_ms": cloud_result.get("latency_ms", 0)
            })

            edge_confidence = edge_result.get("edge_confidence", 0.0)
            gcm_confidence = cloud_result.get("gcm_confidence", 0.0)
            edge_risk_level = edge_result.get("edge_risk_level", "low")
            gcm_risk_level = cloud_result.get("gcm_risk_level", "low")
            edge_action = edge_result.get("edge_action", "")
            gcm_action = cloud_result.get("gcm_action", "")
            edge_fault = edge_result.get("edge_fault_label", "")
            gcm_fault = cloud_result.get("gcm_fault_label", "")

            risk_weights = {"low": 1, "medium": 2, "high": 3}
            edge_risk_weight = risk_weights.get(edge_risk_level, 1)

            conflict_types = []
            if edge_action != gcm_action:
                conflict_types.append("action_conflict")
            if edge_risk_level != gcm_risk_level:
                conflict_types.append("risk_level_conflict")
            if edge_fault != gcm_fault:
                conflict_types.append("fault_label_conflict")
            
            if conflict_types:
                final_decision.update({
                    "conflict_detected": True,
                    "conflict_type": ",".join(conflict_types)
                })

            if edge_confidence < 0.6 or edge_risk_weight >= 2:
                if gcm_confidence > edge_confidence + 0.1:
                    final_decision.update({
                        "final_fault_label": cloud_result["gcm_fault_label"],
                        "final_risk_level": cloud_result["gcm_risk_level"],
                        "final_action": cloud_result["gcm_action"],
                        "final_confidence": cloud_result["gcm_confidence"],
                        "decision_source": "cloud",
                        "reason": "云端置信度更高，覆盖边缘决策"
                    })
                    self.cloud_overrule_count += 1
                elif cloud_result.get("consistent_with_edge", False):
                    final_decision.update({
                        "final_confidence": min(gcm_confidence + 0.05, 0.98),
                        "decision_source": "both_consistent",
                        "reason": "云边决策一致，置信度提升"
                    })
                else:
                    final_decision.update({
                        "decision_source": "cloud",
                        "reason": f"检测到{','.join(conflict_types)}，低置信度/高风险场景采用云端决策"
                    })
                    self.cloud_overrule_count += 1
            elif not cloud_result.get("consistent_with_edge", True):
                if gcm_confidence > edge_confidence + 0.2:
                    final_decision.update({
                        "final_fault_label": cloud_result["gcm_fault_label"],
                        "final_risk_level": cloud_result["gcm_risk_level"],
                        "final_action": cloud_result["gcm_action"],
                        "final_confidence": cloud_result["gcm_confidence"],
                        "decision_source": "cloud",
                        "reason": f"检测到{','.join(conflict_types)}，云端置信度显著更高"
                    })
                    self.cloud_overrule_count += 1
                else:
                    final_decision.update({
                        "decision_source": "edge",
                        "reason": f"检测到{','.join(conflict_types)}，但边缘置信度足够，保留边缘决策"
                    })

        self._log_decision(final_decision)
        return final_decision

    def _log_decision(self, decision: dict):
        df = pd.DataFrame([decision])
        
        if os.path.exists(DECISION_LOG_PATH):
            existing_df = pd.read_csv(DECISION_LOG_PATH)
            df = pd.concat([existing_df, df], ignore_index=True)
        
        df.to_csv(DECISION_LOG_PATH, index=False)

    def get_stats(self) -> dict:
        cloud_overrule_rate = self.cloud_overrule_count / self.decision_count if self.decision_count > 0 else 0

        return {
            "total_decisions": self.decision_count,
            "cloud_overrule_count": self.cloud_overrule_count,
            "cloud_overrule_rate": round(cloud_overrule_rate, 4)
        }


def main():
    decision_maker = GlobalDecisionMaker()

    test_cases = [
        {
            "edge": {
                "device_id": "device_001",
                "edge_fault_label": "Heat Dissipation Failure",
                "edge_risk_level": "high",
                "edge_action": "shutdown",
                "edge_confidence": 0.85
            },
            "cloud": {
                "gcm_fault_label": "Heat Dissipation Failure",
                "gcm_risk_level": "high",
                "gcm_action": "shutdown",
                "gcm_confidence": 0.92,
                "consistent_with_edge": True,
                "latency_ms": 150
            }
        },
        {
            "edge": {
                "device_id": "device_002",
                "edge_fault_label": "Normal",
                "edge_risk_level": "low",
                "edge_action": "monitor",
                "edge_confidence": 0.45
            },
            "cloud": {
                "gcm_fault_label": "Sensor Failure",
                "gcm_risk_level": "medium",
                "gcm_action": "maintain",
                "gcm_confidence": 0.75,
                "consistent_with_edge": False,
                "latency_ms": 120
            }
        },
        {
            "edge": {
                "device_id": "device_003",
                "edge_fault_label": "Power Failure",
                "edge_risk_level": "high",
                "edge_action": "replace",
                "edge_confidence": 0.72
            },
            "cloud": {
                "gcm_fault_label": "Power Failure",
                "gcm_risk_level": "high",
                "gcm_action": "shutdown",
                "gcm_confidence": 0.65,
                "consistent_with_edge": False,
                "latency_ms": 180
            }
        },
        {
            "edge": {
                "device_id": "device_004",
                "edge_fault_label": "Mechanical Wear",
                "edge_risk_level": "medium",
                "edge_action": "maintain",
                "edge_confidence": 0.88
            },
            "cloud": None
        }
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n=== 测试用例 {i+1} ===")
        edge = test_case["edge"]
        cloud = test_case["cloud"]
        
        print(f"边缘结果: {json.dumps(edge, indent=2, ensure_ascii=False)}")
        if cloud:
            print(f"云端结果: {json.dumps(cloud, indent=2, ensure_ascii=False)}")
        else:
            print("云端结果: None (未调用)")
        
        result = decision_maker.make_decision(edge, cloud)
        print(f"最终决策: {json.dumps(result, indent=2, ensure_ascii=False)}")

    print(f"\n=== 统计信息 ===")
    stats = decision_maker.get_stats()
    print(json.dumps(stats, indent=2))

    print(f"\n决策日志已保存到: {DECISION_LOG_PATH}")


if __name__ == "__main__":
    main()