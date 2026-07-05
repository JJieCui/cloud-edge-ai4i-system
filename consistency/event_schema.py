# 本科生5：统一事件对象

def build_event(node_id, timestamp, device_id, risk_level, action, confidence, source):
    return {
        "node_id": node_id,
        "timestamp": timestamp,
        "device_id": device_id,
        "risk_level": risk_level,
        "action": action,
        "confidence": confidence,
        "source": source,
    }
