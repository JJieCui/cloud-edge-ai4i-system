# 统一边缘决策输出格式

def build_decision(fault_label, risk_level, action, confidence, reason):
    return {
        "fault_label": fault_label,
        "risk_level": risk_level,
        "action": action,
        "confidence": confidence,
        "reason": reason,
    }
