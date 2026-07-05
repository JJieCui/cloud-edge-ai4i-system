import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from .cloud_review import CloudReviewer
from .global_decision import GlobalDecisionMaker

app = FastAPI(title="Cloud GCM Review Service", version="1.0.0")

reviewer = CloudReviewer()
decision_maker = GlobalDecisionMaker()


class EdgeSummary(BaseModel):
    device_id: str = Field(..., description="设备ID")
    edge_fault_label: str = Field(..., description="边缘故障标签")
    edge_risk_level: str = Field(..., description="边缘风险等级")
    edge_action: str = Field(..., description="边缘建议动作")
    edge_confidence: float = Field(..., description="边缘置信度", ge=0.0, le=1.0)
    device_features: Optional[Dict[str, Any]] = Field(None, description="设备状态特征")


class CloudReviewResponse(BaseModel):
    review_id: str
    timestamp: str
    device_id: str
    edge_fault_label: str
    edge_risk_level: str
    edge_action: str
    edge_confidence: float
    gcm_fault_label: str
    gcm_risk_level: str
    gcm_action: str
    gcm_confidence: float
    gcm_reason: str
    consistent_with_edge: bool
    latency_ms: int
    mode: str
    used_model: str
    fallback_used: bool
    error: str


class GlobalDecisionRequest(BaseModel):
    edge_result: Dict[str, Any]
    cloud_result: Optional[Dict[str, Any]] = None


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "cloud_gcm_review"}


@app.post("/cloud_review", response_model=CloudReviewResponse)
def cloud_review(edge_summary: EdgeSummary):
    try:
        result = reviewer.review(edge_summary.dict())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"云端复核失败: {str(e)}")


@app.post("/global_decision")
def global_decision(request: GlobalDecisionRequest):
    try:
        result = decision_maker.make_decision(request.edge_result, request.cloud_result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全局决策失败: {str(e)}")


@app.get("/stats")
def get_stats():
    review_stats = reviewer.get_stats()
    decision_stats = decision_maker.get_stats()
    return {
        "cloud_review": review_stats,
        "global_decision": decision_stats
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)