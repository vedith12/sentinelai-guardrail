import re
from typing import List, Optional
from app.models import Finding
from app.services.llm_judge import call_llm

def deterministic_rewrite(output: str, findings: List[Finding]) -> str:
    """
    Deterministically replaces exact evidence matches with safe placeholders.
    Highly effective for simple PII leaks.
    """
    rewritten = output
    for finding in findings:
        if finding.policy_name == "pii_leakage" and finding.evidence:
            evidence_escaped = re.escape(finding.evidence)
            # Find the type of PII from reason if possible
            placeholder = "[PII_REDACTED]"
            if "email" in finding.reason.lower():
                placeholder = "[EMAIL_REDACTED]"
            elif "phone" in finding.reason.lower():
                placeholder = "[PHONE_REDACTED]"
            elif "key" in finding.reason.lower() or "secret" in finding.reason.lower():
                placeholder = "[API_KEY_REDACTED]"
                
            rewritten = re.sub(evidence_escaped, placeholder, rewritten)
            
    return rewritten

def llm_rewrite(prompt_context: Optional[str], output: str, findings: List[Finding]) -> str:
    """
    Uses the LLM to rewrite output, correcting tone, brand voice, or warning issues
    while keeping the helpfulness of the original message intact.
    """
    system_prompt = (
        "You are an AI compliance and editing assistant. Your job is to rewrite the candidate output to fix specific policy violations.\n"
        "Keep the core response structure, format, and helpful information intact, but completely remove or alter any violating parts.\n"
        "Do not explain your changes or add comments. Return ONLY the rewritten text."
    )

    findings_summary = "\n".join([
        f"- Policy: {f.policy_name}, Issue: {f.reason}, Evidence: {f.evidence}"
        for f in findings
    ])

    user_prompt = (
        f"CONTEXT (User Prompt that generated output):\n"
        f"\"{prompt_context or 'No context.'}\"\n\n"
        f"ORIGINAL OUTPUT:\n"
        f"\"{output}\"\n\n"
        f"VIOLATIONS DETECTED:\n"
        f"{findings_summary}\n\n"
        f"Please rewrite the ORIGINAL OUTPUT to resolve these violations. Return ONLY the rewritten text:"
    )

    try:
        rewritten = call_llm(user_prompt, system_prompt).strip()
        return rewritten
    except Exception:
        # If rewriting fails, fallback to original output (or blocking flow will handle it)
        return output

def rewrite_output(prompt_context: Optional[str], output: str, findings: List[Finding]) -> str:
    """
    Applies deterministic edits first (for PII), then LLM-based corrections for tone/policy warnings.
    """
    # 1. Mask PII
    rewritten = deterministic_rewrite(output, findings)
    
    # 2. Check if we need LLM rewrite (for brand voice, advice, toxic warnings etc.)
    non_pii_findings = [f for f in findings if f.policy_name != "pii_leakage" and f.decision == "rewrite"]
    if non_pii_findings:
        rewritten = llm_rewrite(prompt_context, rewritten, non_pii_findings)
        
    return rewritten
