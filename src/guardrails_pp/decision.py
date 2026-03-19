from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

DecisionType = Literal["allow", "transform", "block"]

@dataclass
class Decision:
    decision: DecisionType
    action: str  # "pass_through" | "safe_completion" | "reject" | "rewrite"
    rules_triggered: List[str] = field(default_factory=list)
    rewritten_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status_code: int = 200
