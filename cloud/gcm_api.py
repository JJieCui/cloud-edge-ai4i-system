import os
import json
import time
import random
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GCM_MODE = os.getenv("GCM_MODE", "mock")
GCM_35B_BASE_URL = os.getenv("GCM_35B_BASE_URL", "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1")
GCM_14B_BASE_URL = os.getenv("GCM_14B_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
GCM_MODEL = os.getenv("GCM_MODEL", "qwen3.5-35b-a3b")
GCM_BACKUP_MODEL = os.getenv("GCM_BACKUP_MODEL", "qwen3-14b")
GCM_API_KEY = os.getenv("GCM_API_KEY", "EMPTY")
GCM_TIMEOUT = int(os.getenv("GCM_TIMEOUT", 60))

_clients = {}


def _get_client(base_url: str):
    global _clients
    if base_url not in _clients:
        _clients[base_url] = OpenAI(
            api_key=GCM_API_KEY,
            base_url=base_url,
            timeout=GCM_TIMEOUT
        )
    return _clients[base_url]


def _is_35b_model(model_name: str) -> bool:
    return "35b" in model_name.lower() or "3.5" in model_name.lower()


def mock_gcm_response(edge_summary: dict) -> dict:
    edge_action = edge_summary.get("edge_action", "")
    edge_confidence = edge_summary.get("edge_confidence", 0.5)
    edge_risk_level = edge_summary.get("edge_risk_level", "medium")

    if edge_confidence > 0.8:
        agree_prob = 0.85
    elif edge_confidence > 0.5:
        agree_prob = 0.6
    else:
        agree_prob = 0.3

    if random.random() < agree_prob:
        gcm_fault_label = edge_summary.get("edge_fault_label", "Normal")
        gcm_risk_level = edge_risk_level
        gcm_action = edge_action
        gcm_confidence = min(edge_confidence + random.uniform(0.05, 0.15), 0.98)
    else:
        fault_options = ["Normal", "Heat Dissipation Failure", "Power Failure", "Sensor Failure", "Mechanical Wear"]
        gcm_fault_label = random.choice(fault_options)
        gcm_risk_level = random.choice(["low", "medium", "high"])
        action_options = ["maintain", "replace", "monitor", "shutdown"]
        gcm_action = random.choice(action_options)
        gcm_confidence = random.uniform(0.6, 0.95)

    return {
        "gcm_fault_label": gcm_fault_label,
        "gcm_risk_level": gcm_risk_level,
        "gcm_action": gcm_action,
        "gcm_confidence": round(gcm_confidence, 4),
        "gcm_reason": "Mock GCM review completed",
        "consistent_with_edge": gcm_action == edge_action,
        "latency_ms": random.randint(50, 200)
    }


def _build_prompt(edge_summary: dict) -> str:
    return f"""
你是一个工业设备故障诊断专家。请根据边缘节点上传的设备状态摘要进行复核。

边缘节点摘要：
- 设备ID: {edge_summary.get('device_id', 'unknown')}
- 边缘故障标签: {edge_summary.get('edge_fault_label', 'unknown')}
- 边缘风险等级: {edge_summary.get('edge_risk_level', 'unknown')}
- 边缘建议动作: {edge_summary.get('edge_action', 'unknown')}
- 边缘置信度: {edge_summary.get('edge_confidence', 0.0)}
- 设备状态特征: {json.dumps(edge_summary.get('device_features', {}), ensure_ascii=False)}

请输出JSON格式的复核结果，包含以下字段：
- gcm_fault_label: 故障标签（Normal/Heat Dissipation Failure/Power Failure/Sensor Failure/Mechanical Wear）
- gcm_risk_level: 风险等级（low/medium/high）
- gcm_action: 建议动作（maintain/replace/monitor/shutdown）
- gcm_confidence: 置信度（0-1之间）
- gcm_reason: 复核理由（简短说明）
- consistent_with_edge: 是否与边缘决策一致（true/false）

注意：只输出JSON字符串，不要包含其他内容。
"""


def _call_35b_api(model_name: str, prompt: str) -> dict:
    try:
        client = _get_client(GCM_35B_BASE_URL)
        
        response = client.responses.create(
            model=model_name,
            input=prompt,
            extra_body={"enable_thinking": True}
        )
        
        for item in response.output:
            if item.type == "message":
                content = item.content[0].text
                return {"success": True, "content": content}
        
        return {"success": False, "error": "未找到有效响应内容"}

    except Exception as e:
        error_msg = str(e)
        return _parse_error(error_msg)


def _call_14b_api(model_name: str, prompt: str) -> dict:
    try:
        client = _get_client(GCM_14B_BASE_URL)
        
        messages = [
            {"role": "system", "content": "你是一个专业的工业设备故障诊断专家，擅长分析设备状态并给出准确的维护建议。"},
            {"role": "user", "content": prompt}
        ]
        
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.3,
            max_tokens=500,
            extra_body={"enable_thinking": False}
        )
        
        content = completion.choices[0].message.content
        return {"success": True, "content": content}

    except Exception as e:
        error_msg = str(e)
        return _parse_error(error_msg)


def _parse_error(error_msg: str) -> dict:
    if "401" in error_msg or "Unauthorized" in error_msg:
        return {"success": False, "error": "认证失败(401)，请检查API Key"}
    elif "403" in error_msg or "Forbidden" in error_msg:
        return {"success": False, "error": "权限不足(403)，请检查账号权限或模型可用性"}
    elif "404" in error_msg or "Not Found" in error_msg:
        return {"success": False, "error": "模型不存在(404)，请检查模型ID"}
    elif "RateLimitError" in error_msg or "rate limit" in error_msg.lower():
        return {"success": False, "error": "请求频率超限，请稍后重试"}
    elif "ConnectionError" in error_msg or "Timeout" in error_msg:
        return {"success": False, "error": "网络连接超时，请检查网络"}
    else:
        return {"success": False, "error": f"请求失败: {error_msg}"}


def _call_openai_api(model_name: str, prompt: str) -> dict:
    if _is_35b_model(model_name):
        return _call_35b_api(model_name, prompt)
    else:
        return _call_14b_api(model_name, prompt)


def call_gcm_api(edge_summary: dict) -> dict:
    start_time = time.time()
    
    if GCM_MODE == "mock":
        result = mock_gcm_response(edge_summary)
        simulated_latency = result["latency_ms"]
        time.sleep(simulated_latency / 1000.0)
        result["mode"] = "mock"
        result["used_model"] = "mock"
        return result

    prompt = _build_prompt(edge_summary)
    models_to_try = [GCM_MODEL, GCM_BACKUP_MODEL] if GCM_BACKUP_MODEL else [GCM_MODEL]
    used_model = GCM_MODEL
    fallback_used = False

    for model_name in models_to_try:
        api_result = _call_openai_api(model_name, prompt)
        
        if api_result["success"]:
            used_model = model_name
            break
        elif model_name != models_to_try[-1]:
            fallback_used = True
            print(f"主模型 {model_name} 调用失败，尝试备用模型 {models_to_try[1]}")
        else:
            used_model = model_name

    if api_result["success"]:
        try:
            content = api_result["content"].strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            result = json.loads(content)
            result["gcm_reason"] = result.get("gcm_reason", "GCM复核完成")
        except json.JSONDecodeError:
            result = {
                "gcm_fault_label": edge_summary.get("edge_fault_label", "Normal"),
                "gcm_risk_level": edge_summary.get("edge_risk_level", "medium"),
                "gcm_action": edge_summary.get("edge_action", "monitor"),
                "gcm_confidence": 0.7,
                "gcm_reason": "JSON解析失败，使用边缘结果作为默认值",
                "consistent_with_edge": True
            }
    else:
        result = {
            "gcm_fault_label": edge_summary.get("edge_fault_label", "Normal"),
            "gcm_risk_level": edge_summary.get("edge_risk_level", "medium"),
            "gcm_action": edge_summary.get("edge_action", "monitor"),
            "gcm_confidence": 0.5,
            "gcm_reason": f"API调用失败: {api_result['error']}",
            "consistent_with_edge": True,
            "error": api_result["error"]
        }

    result["latency_ms"] = int((time.time() - start_time) * 1000)
    result["mode"] = "real"
    result["used_model"] = used_model
    result["fallback_used"] = fallback_used
    return result