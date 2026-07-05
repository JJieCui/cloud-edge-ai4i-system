import os
import json
import time
import pandas as pd
from datetime import datetime
from .gcm_api import call_gcm_api

REVIEW_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results", "tables", "cloud_review_log.csv")


class CloudReviewer:
    def __init__(self):
        self.cloud_call_count = 0
        self.total_latency_ms = 0
        self.consistent_count = 0
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        log_dir = os.path.dirname(REVIEW_LOG_PATH)
        os.makedirs(log_dir, exist_ok=True)

    def review(self, edge_summary: dict) -> dict:
        self.cloud_call_count += 1
        start_time = time.time()

        required_fields = ["device_id", "edge_fault_label", "edge_risk_level", "edge_action", "edge_confidence"]
        for field in required_fields:
            if field not in edge_summary:
                raise ValueError(f"缺少必填字段: {field}")

        gcm_result = call_gcm_api(edge_summary)

        latency_ms = gcm_result.get("latency_ms", int((time.time() - start_time) * 1000))
        self.total_latency_ms += latency_ms

        if gcm_result.get("consistent_with_edge", False):
            self.consistent_count += 1

        review_result = {
            "review_id": f"review_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "device_id": edge_summary["device_id"],
            "edge_fault_label": edge_summary["edge_fault_label"],
            "edge_risk_level": edge_summary["edge_risk_level"],
            "edge_action": edge_summary["edge_action"],
            "edge_confidence": edge_summary["edge_confidence"],
            "gcm_fault_label": gcm_result.get("gcm_fault_label", "Unknown"),
            "gcm_risk_level": gcm_result.get("gcm_risk_level", "Unknown"),
            "gcm_action": gcm_result.get("gcm_action", "Unknown"),
            "gcm_confidence": gcm_result.get("gcm_confidence", 0.0),
            "gcm_reason": gcm_result.get("gcm_reason", ""),
            "consistent_with_edge": gcm_result.get("consistent_with_edge", False),
            "latency_ms": latency_ms,
            "mode": gcm_result.get("mode", "mock"),
            "used_model": gcm_result.get("used_model", "unknown"),
            "fallback_used": gcm_result.get("fallback_used", False),
            "error": gcm_result.get("error", "")
        }

        self._log_review(review_result)
        return review_result

    def _log_review(self, review_result: dict):
        df = pd.DataFrame([review_result])
        
        if os.path.exists(REVIEW_LOG_PATH):
            existing_df = pd.read_csv(REVIEW_LOG_PATH)
            df = pd.concat([existing_df, df], ignore_index=True)
        
        df.to_csv(REVIEW_LOG_PATH, index=False)

    def get_stats(self) -> dict:
        avg_latency = self.total_latency_ms / self.cloud_call_count if self.cloud_call_count > 0 else 0
        consistency_rate = self.consistent_count / self.cloud_call_count if self.cloud_call_count > 0 else 0

        return {
            "cloud_call_count": self.cloud_call_count,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": round(avg_latency, 2),
            "consistent_count": self.consistent_count,
            "edge_cloud_consistency": round(consistency_rate, 4)
        }


def main():
    reviewer = CloudReviewer()

    test_cases = [
        {
            "device_id": "device_001",
            "edge_fault_label": "Heat Dissipation Failure",
            "edge_risk_level": "high",
            "edge_action": "shutdown",
            "edge_confidence": 0.85,
            "device_features": {
                "Air temperature [K]": 305.2,
                "Process temperature [K]": 310.0,
                "Rotational speed [rpm]": 1450,
                "Torque [Nm]": 45.2,
                "Tool wear [min]": 150
            }
        },
        {
            "device_id": "device_002",
            "edge_fault_label": "Normal",
            "edge_risk_level": "low",
            "edge_action": "monitor",
            "edge_confidence": 0.45,
            "device_features": {
                "Air temperature [K]": 300.5,
                "Process temperature [K]": 305.1,
                "Rotational speed [rpm]": 1400,
                "Torque [Nm]": 38.5,
                "Tool wear [min]": 80
            }
        },
        {
            "device_id": "device_003",
            "edge_fault_label": "Power Failure",
            "edge_risk_level": "high",
            "edge_action": "replace",
            "edge_confidence": 0.72,
            "device_features": {
                "Air temperature [K]": 298.0,
                "Process temperature [K]": 302.0,
                "Rotational speed [rpm]": 0,
                "Torque [Nm]": 0.0,
                "Tool wear [min]": 200
            }
        }
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n=== 测试用例 {i+1} ===")
        print(f"输入: {json.dumps(test_case, indent=2, ensure_ascii=False)}")
        
        try:
            result = reviewer.review(test_case)
            print(f"输出: {json.dumps(result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"错误: {e}")

    print(f"\n=== 统计信息 ===")
    stats = reviewer.get_stats()
    print(json.dumps(stats, indent=2))

    print(f"\n复核日志已保存到: {REVIEW_LOG_PATH}")


if __name__ == "__main__":
    main()