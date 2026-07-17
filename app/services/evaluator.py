import time
from typing import List, Optional
from sqlmodel import Session, select
from app.models import EvaluationLog, EvaluationRequest, EvaluationResponse, Finding, Policy, AuditReview
from app.services.deterministic import run_pii_check, run_keyword_check
from app.services.llm_judge import evaluate_policy_with_judge, run_consensus_judge
from app.services.rewriter import rewrite_output

def evaluate_output(db: Session, request: EvaluationRequest) -> EvaluationResponse:
    start_time = time.time()
    
    # 1. Fetch active policies from DB
    stmt = select(Policy).where(Policy.is_active == True)
    policies = db.exec(stmt).all()
    
    # Filter policies if request specifies a list of features
    if request.features:
        policies = [p for p in policies if p.name in request.features]
        
    findings: List[Finding] = []
    
    # 2. Run Deterministic Checks First (Low latency, free)
    for policy in policies:
        if policy.detection_strategy == "deterministic":
            if policy.name == "pii_leakage":
                findings.extend(run_pii_check(request.output, policy))
            else:
                findings.extend(run_keyword_check(request.output, policy))
                
    # 3. If not blocked by deterministic checks, run LLM Judge Checks
    has_deterministic_block = any(f.decision == "block" for f in findings)
    
    if not has_deterministic_block:
        for policy in policies:
            if policy.detection_strategy == "llm_judge":
                # Double-judge consensus for high-severity safety policies
                if policy.severity == "high" and policy.action == "block":
                    finding = run_consensus_judge(request.prompt, request.output, policy)
                else:
                    finding = evaluate_policy_with_judge(request.prompt, request.output, policy)
                    
                if finding:
                    findings.append(finding)
                    
    # 4. Resolve Overall Decision
    # Precedence: block > review > rewrite > warn > approve
    decisions = [f.decision for f in findings]
    
    if "block" in decisions:
        overall_decision = "block"
        final_output = "The output has been blocked as it violates our safety and compliance policies."
    elif "review" in decisions:
        overall_decision = "review"
        final_output = request.output  # Sent as-is but flagged
    elif "rewrite" in decisions:
        overall_decision = "rewrite"
        rewrite_findings = [f for f in findings if f.decision == "rewrite"]
        final_output = rewrite_output(request.prompt, request.output, rewrite_findings)
    elif "warn" in decisions:
        overall_decision = "warn"
        final_output = request.output  # Return with findings warning
    else:
        overall_decision = "approve"
        final_output = request.output
        
    latency_ms = (time.time() - start_time) * 1000
    
    # 5. Log inside Database
    log_entry = EvaluationLog(
        prompt=request.prompt,
        original_output=request.output,
        final_output=final_output,
        decision=overall_decision,
        findings=[f.dict() for f in findings],
        latency_ms=latency_ms
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    # 6. Route to Audit queue if decision is review or block
    if overall_decision in ["review", "block"]:
        audit_entry = AuditReview(
            log_id=log_entry.id,
            status="pending"
        )
        db.add(audit_entry)
        db.commit()
        
    return EvaluationResponse(
        original_output=request.output,
        final_output=final_output,
        decision=overall_decision,
        findings=findings,
        latency_ms=latency_ms
    )
