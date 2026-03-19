from dataclasses import dataclass, field
from typing import List, Optional, Literal, Any
from pathlib import Path
import re
import asyncio

import yaml

from ..integrations.safety_client import get_safety_client
from ..decision import Decision
from ..safe_completion import get_safe_completion

ActionType = Literal["allow", "block", "rewrite", "log_only", "safe_complete"]
Direction = Literal["input", "output"]


@dataclass
class Policy:
    id: str
    applies_to: List[str]
    type: str
    action: ActionType
    severity: str = "medium"
    category: Optional[str] = None

    keywords: List[str] = field(default_factory=list)

    regex: Optional[re.Pattern] = None
    replacement: Optional[str] = None

    provider: Optional[str] = None
    threshold: Optional[float] = None
    model_name: Optional[str] = None
    invert_score: bool = False


BASE_POLICIES_PATH = Path("policies/base_policies.yaml")

_policies_cache: List[Policy] | None = None


def _load_policies() -> List[Policy]:
    global _policies_cache
    if _policies_cache is not None:
        return _policies_cache

    if not BASE_POLICIES_PATH.exists():
        _policies_cache = []
        return _policies_cache

    with BASE_POLICIES_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    policies: List[Policy] = []
    for p in raw.get("policies", []):
        p_type = p.get("type")
        applies_to = p.get("applies_to", ["input", "output"])
        action: ActionType = p.get("action", "block")
        severity = p.get("severity", "medium")
        category = p.get("category")

        if p_type == "keyword_match":
            keywords = [k.lower() for k in p.get("match", [])]
            policies.append(
                Policy(
                    id=p["id"],
                    applies_to=applies_to,
                    type=p_type,
                    action=action,
                    severity=severity,
                    category=category,
                    keywords=keywords,
                )
            )

        elif p_type == "regex_replace":
            pattern = p.get("pattern")
            if not pattern:
                continue
            compiled = re.compile(pattern)
            replacement = p.get("replacement", "[REDACTED]")
            policies.append(
                Policy(
                    id=p["id"],
                    applies_to=applies_to,
                    type=p_type,
                    action=action,
                    severity=severity,
                    category=category,
                    regex=compiled,
                    replacement=replacement,
                )
            )

        elif p_type == "external_safety_api":
            provider = p.get("provider", "demo_safety")
            threshold = float(p.get("threshold", 0.5))
            model_name = p.get("model_name")
            invert_score = bool(p.get("invert_score", False))
            policies.append(
                Policy(
                    id=p["id"],
                    applies_to=applies_to,
                    type=p_type,
                    action=action,
                    severity=severity,
                    category=category,
                    provider=provider,
                    threshold=threshold,
                    model_name=model_name,
                    invert_score=invert_score,
                )
            )

        else:
            continue

    _policies_cache = policies
    return _policies_cache


def _make_safe_completion(rule_id: str, category: str) -> Decision:
    return Decision(
        decision="transform",
        action="safe_completion",
        rules_triggered=[rule_id],
        rewritten_text=get_safe_completion(category or "default"),
        metadata={"category": category},
        status_code=200,
    )


async def evaluate_policies_for_request(
    text: str,
    direction: Direction,
    tenant: dict,
    metadata: dict | None = None,
) -> Decision:
    policies = _load_policies()
    triggered: List[str] = []

    original_text = text
    current_text = text
    final_decision = "allow"
    final_action = "pass_through"
    engine_metadata: dict[str, Any] = metadata.copy() if metadata else {}
    safe_completion_policy: Optional[Policy] = None

    external_policies: List[Policy] = []

    for policy in policies:
        if direction not in policy.applies_to:
            continue

        if policy.type == "external_safety_api":
            external_policies.append(policy)
            continue

        working_text = current_text
        lowered = working_text.lower()

        if policy.type == "keyword_match":
            if not policy.keywords:
                continue

            if any(kw in lowered for kw in policy.keywords):
                triggered.append(policy.id)

                if policy.action == "block":
                    final_decision = "block"
                    final_action = "reject"
                elif policy.action == "safe_complete":
                    if final_decision not in ("block",):
                        final_decision = "transform"
                        final_action = "safe_completion"
                        safe_completion_policy = policy
                elif policy.action == "rewrite" and final_decision not in ("block", "transform"):
                    for kw in policy.keywords:
                        working_text = working_text.replace(kw, "[REDACTED]")
                    current_text = working_text
                    final_decision = "transform"
                    final_action = "rewrite"
                elif policy.action == "log_only":
                    pass

        elif policy.type == "regex_replace" and policy.regex is not None:
            if policy.regex.search(working_text):
                triggered.append(policy.id)

                if policy.action == "block":
                    final_decision = "block"
                    final_action = "reject"
                elif policy.action == "safe_complete":
                    if final_decision not in ("block",):
                        final_decision = "transform"
                        final_action = "safe_completion"
                        safe_completion_policy = policy
                elif policy.action == "rewrite" and final_decision not in ("block", "transform"):
                    working_text = policy.regex.sub(
                        policy.replacement or "[REDACTED]",
                        working_text,
                    )
                    current_text = working_text
                    final_decision = "transform"
                    final_action = "rewrite"

    if external_policies and final_decision != "block":
        tasks = []
        for policy in external_policies:
            client = get_safety_client(
                policy.provider or "demo_safety",
                model_name=policy.model_name,
            )
            tasks.append(
                client.score_text(
                    current_text,
                    direction=direction,
                    tenant=tenant,
                    metadata={"policy_id": policy.id, **(metadata or {})},
                )
            )

        results = await asyncio.gather(*tasks)

        for policy, safety_result in zip(external_policies, results):
            engine_metadata.setdefault("external_safety", {})[policy.id] = {
                "risk_score": safety_result.risk_score,
                "label": safety_result.label,
                "invert_score": policy.invert_score,
            }

            should_trigger = False
            if policy.threshold is not None:
                if policy.invert_score:
                    should_trigger = safety_result.risk_score < policy.threshold
                else:
                    should_trigger = safety_result.risk_score >= policy.threshold

            if should_trigger:
                triggered.append(policy.id)

                if policy.action == "block":
                    final_decision = "block"
                    final_action = "reject"
                elif policy.action == "safe_complete":
                    if final_decision not in ("block",):
                        final_decision = "transform"
                        final_action = "safe_completion"
                        safe_completion_policy = policy
                elif policy.action == "rewrite" and final_decision not in ("block", "transform"):
                    current_text = (
                        "[Guardrails++] Safety warning: content was flagged "
                        f"({safety_result.label}).\n\n{current_text}"
                    )
                    final_decision = "transform"
                    final_action = "rewrite"

    rewritten_text: Optional[str] = None
    status_code = 200

    if final_decision == "block":
        status_code = 400
        rewritten_text = None
    elif final_action == "safe_completion" and safe_completion_policy:
        rewritten_text = get_safe_completion(safe_completion_policy.category or "default")
    elif final_decision == "transform" and current_text != original_text:
        rewritten_text = current_text

    return Decision(
        decision=final_decision,
        action=final_action,
        rules_triggered=triggered,
        rewritten_text=rewritten_text,
        metadata=engine_metadata,
        status_code=status_code,
    )


def reload_policies() -> int:
    global _policies_cache
    _policies_cache = None
    policies = _load_policies()
    return len(policies)


def debug_list_policies() -> list[dict[str, Any]]:
    policies = _load_policies()
    result: list[dict[str, Any]] = []
    for p in policies:
        result.append(
            {
                "id": p.id,
                "type": p.type,
                "applies_to": p.applies_to,
                "action": p.action,
                "severity": p.severity,
                "category": p.category,
                "keywords": getattr(p, "keywords", []),
                "provider": getattr(p, "provider", None),
                "threshold": getattr(p, "threshold", None),
                "model_name": getattr(p, "model_name", None),
            }
        )
    return result


async def debug_evaluate_raw(
    text: str,
    direction: Direction = "input",
) -> dict[str, Any]:
    tenant = {"id": "debug-tenant"}
    decision = await evaluate_policies_for_request(
        text=text,
        direction=direction,
        tenant=tenant,
        metadata={"debug": True},
    )

    return {
        "decision": decision.decision,
        "action": decision.action,
        "rules_triggered": decision.rules_triggered,
        "rewritten_text": decision.rewritten_text,
        "metadata": decision.metadata,
        "status_code": decision.status_code,
    }
