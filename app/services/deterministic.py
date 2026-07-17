import re
import json
from typing import List, Optional
from app.models import Finding, Policy

# Default PII Patterns
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
CREDIT_CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
API_KEY_REGEX = re.compile(r'(?i)(api[-_]?key|secret|token|password)[\s]*[:=][\s]*["'']?[a-zA-Z0-9_\-]{16,}["'']?')

def validate_json_schema(output: str, schema: Optional[dict] = None) -> Optional[Finding]:
    """
    Checks if output is valid JSON and optionally fits the provided JSON schema.
    """
    try:
        data = json.loads(output)
        if schema:
            # Simple type & key checks if schema is provided
            for key, val_type in schema.items():
                if key not in data:
                    return Finding(
                        policy_name="schema_mismatch",
                        decision="block",
                        severity="high",
                        reason=f"Missing required key: {key}",
                        evidence=output
                    )
        return None
    except json.JSONDecodeError as e:
        return Finding(
            policy_name="schema_mismatch",
            decision="block",
            severity="high",
            reason=f"Output is not a valid JSON: {str(e)}",
            evidence=output
        )

def run_pii_check(output: str, policy: Policy) -> List[Finding]:
    """
    Scans the output text for PII patterns using configured regexes.
    """
    findings = []
    
    # Check default/custom regex rules defined in the policy
    rules = policy.rules or []
    if not rules:
        # Fallback to defaults
        rules = [
            {"name": "email", "pattern": EMAIL_REGEX.pattern},
            {"name": "phone_number", "pattern": PHONE_REGEX.pattern},
            {"name": "credit_card", "pattern": CREDIT_CARD_REGEX.pattern},
            {"name": "api_key", "pattern": API_KEY_REGEX.pattern}
        ]

    for rule in rules:
        pattern_str = rule.get("pattern")
        rule_name = rule.get("name", "pii")
        if not pattern_str:
            continue
        
        try:
            pattern = re.compile(pattern_str)
            matches = list(pattern.finditer(output))
            for match in matches:
                findings.append(Finding(
                    policy_name=policy.name,
                    decision=policy.action,
                    severity=policy.severity,
                    evidence=match.group(),
                    reason=f"Detected PII type: {rule_name}"
                ))
        except Exception as e:
            # Avoid crashing on invalid regex
            pass
            
    return findings

def run_keyword_check(output: str, policy: Policy) -> List[Finding]:
    """
    Checks for exact matches or simple keywords/regex from rules.
    """
    findings = []
    rules = policy.rules or []
    for rule in rules:
        rule_name = rule.get("name", "keyword")
        pattern_str = rule.get("pattern")
        
        if not pattern_str:
            continue
            
        if rule.get("type") == "regex":
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                matches = list(pattern.finditer(output))
                for match in matches:
                    findings.append(Finding(
                        policy_name=policy.name,
                        decision=policy.action,
                        severity=policy.severity,
                        evidence=match.group(),
                        reason=f"Keyword policy violation: {rule_name}"
                    ))
            except Exception:
                pass
        else:
            if pattern_str.lower() in output.lower():
                findings.append(Finding(
                    policy_name=policy.name,
                    decision=policy.action,
                    severity=policy.severity,
                    evidence=pattern_str,
                    reason=f"Detected forbidden term: '{pattern_str}'"
                ))
                
    return findings
