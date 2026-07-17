from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField, SQLModel, JSON

# --- API Schemas (Pydantic) ---

class EvaluationRequest(BaseModel):
    prompt: Optional[str] = None
    output: str
    features: Optional[List[str]] = None  # Specific policy names to evaluate (runs all if None)

class Finding(BaseModel):
    policy_name: str
    decision: str  # approve, warn, rewrite, block, review
    severity: str  # info, low, medium, high
    evidence: Optional[str] = None
    reason: str

class EvaluationResponse(BaseModel):
    original_output: str
    final_output: str
    decision: str
    findings: List[Finding]
    latency_ms: float

# --- Database Models (SQLModel) ---

class Policy(SQLModel, table=True):
    __tablename__ = "policies"
    
    id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(unique=True, index=True)
    category: str
    description: str
    severity: str
    action: str
    detection_strategy: str
    rules: Optional[List[Dict[str, Any]]] = SQLField(default=None, sa_type=JSON)
    examples: Optional[List[str]] = SQLField(default=None, sa_type=JSON)
    is_active: bool = SQLField(default=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    updated_at: datetime = SQLField(default_factory=datetime.utcnow)

class EvaluationLog(SQLModel, table=True):
    __tablename__ = "evaluation_logs"
    
    id: Optional[int] = SQLField(default=None, primary_key=True)
    prompt: Optional[str] = None
    original_output: str
    final_output: str
    decision: str
    findings: List[Dict[str, Any]] = SQLField(default=[], sa_type=JSON)
    latency_ms: float
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)

class AuditReview(SQLModel, table=True):
    __tablename__ = "audit_reviews"
    
    id: Optional[int] = SQLField(default=None, primary_key=True)
    log_id: int = SQLField(foreign_key="evaluation_logs.id")
    reviewer_notes: Optional[str] = None
    status: str = SQLField(default="pending")  # pending, approved, overridden
    override_decision: Optional[str] = None
    overridden_output: Optional[str] = None
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
