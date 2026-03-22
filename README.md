# Guardrails++

**Policy-Driven AI Safety & Governance Gateway for LLM Applications**

Guardrails++ is a production-style prototype AI safety gateway that sits between client applications and Large Language Models (LLMs), enforcing security, safety, and governance policies on both inputs and outputs.

It is designed to mirror how enterprise AI safety systems operate in practice—combining policy-as-code, deterministic controls, machine-learning classifiers, and graduated response strategies (block, rewrite, safe_complete, log_only).

---

## Why Guardrails++ Exists

Most LLM safety examples rely on:

- a single classifier, or
- binary allow/deny logic.

Real-world systems require more nuance:

- Not all risky requests should be blocked
- Some requests should be deflected, not refused
- All decisions must be auditable
- Policies must be reviewable, change-controlled, and reversible

Guardrails++ addresses these requirements directly.

---

## Project Structure

```
src/
└── guardrails_pp/
    ├── api/
    │   ├── router.py              # FastAPI routes + HTTP response mapping
    │   └── schemas.py             # Pydantic request/response models
    ├── core/
    │   ├── config.py              # App configuration
    │   └── logging.py             # Structured JSON logging
    ├── externals/
    │   └── huggingface_client.py  # HuggingFace Inference API wrapper
    ├── integrations/
    │   └── safety_client.py       # Safety client interface
    ├── policy/
    │   └── engine.py              # Policy evaluation engine (core)
    ├── utils/
    │   └── correlation.py         # Correlation ID middleware
    ├── decision.py                # Decision dataclass
    ├── safe_completion.py         # Category-specific deflection responses
    └── main.py                    # App entrypoint
policies/
└── base_policies.yaml             # All safety rules (policy-as-code)
```

---

## High-Level Architecture

### Request Flow (Input → Output)

```
Client Request
      │
      ▼
CorrelationIDMiddleware  ←  assigns X-Correlation-ID UUID
      │
      ▼
POST /v1/chat/completions
      │
      ▼
evaluate_policies_for_request()  ←  INPUT pass
  ├── keyword_match policies       (synchronous, sequential)
  ├── regex_replace policies       (synchronous, sequential)
  └── external_safety_api          (async parallel via asyncio.gather)
      │
      ▼
Decision: allow / transform / block
      │
  ┌───┴───────────────────┐
  │                       │
block → 400         safe_complete → 200
rules_triggered[]   category deflection
      │
      ▼
evaluate_policies_for_request()  ←  OUTPUT pass
      │
      ▼
Final response with rule IDs + correlation ID
```

The gateway is LLM-agnostic at the policy and decision layer and does not assume a specific provider.

---

## Core Concepts

### 1. Policy-as-Code (YAML)

All safety logic is defined declaratively in YAML:

- No safety logic hard-coded in request handlers
- Policies are reviewable independently of code
- Rollback is achieved by reverting configuration
- Enables governance review and approval workflows

Each policy specifies:

- Scope (input / output)
- Detection method (keyword, regex, ML classifier)
- Severity
- Action (block, rewrite, safe_complete, log_only)
- Optional category (used for safe completion routing)

### 2. Multi-Layer Safety Detection

Guardrails++ intentionally combines deterministic rules with layered ML signals.

**Deterministic Controls**
- Keyword matching for high-confidence risks
- Regex-based redaction (e.g., emails, secrets)
- Explicit hard blocks for weapons, explosives, and security bypass attempts

**ML-Based Classifiers (Layered)**
- `unitary/unbiased-toxic-roberta`
- `s-nlp/roberta_toxicity_classifier`

Each classifier:
- Uses an independent threshold
- Is evaluated separately
- Cannot override deterministic hard blocks

This layered approach reduces both false negatives and over-reliance on any single model.

> **Note on classifier architecture:** These are RoBERTa-based single-sequence toxicity classifiers, not NLI (Natural Language Inference) models in the strict sense. True NLI models classify entailment/contradiction between premise and hypothesis. The models here score how likely a given text is harmful.

### 3. Graduated Response Model

Guardrails++ does not treat all violations equally.

| Action | Meaning |
|---|---|
| `block` | Reject request entirely (HTTP 400) |
| `rewrite` | Modify content (e.g., redact PII) |
| `safe_complete` | Replace response with a defensive, educational alternative |
| `log_only` | Allow request while emitting audit signal |
| `allow` | Pass through unchanged |

This enables risk-appropriate handling rather than blanket denial.

### 4. Safe Completion (Deflection, Not Censorship)

For high-risk but potentially legitimate domains (e.g., social engineering, data exfiltration, audit evasion):

- Requests are not answered operationally
- Users receive high-level, defensive explanations
- No procedural or actionable steps are provided

This mirrors safety behavior in enterprise AI governance platforms, Trust & Safety systems, and responsible AI deployments.

**Safe Completion Invariants**

Safe completion responses are designed to:
- Provide high-level explanations only
- Avoid step-by-step or procedural instructions
- Redirect toward prevention, ethics, or defensive understanding

Templates are reviewed manually to ensure they do not enable harm.

### 5. Structured Decision Object

Every policy evaluation produces a `Decision` object containing:

```python
Decision(
    decision:       "allow" | "transform" | "block",
    action:         "pass_through" | "rewrite" | "safe_completion" | "reject",
    rules_triggered: List[str],      # policy IDs that fired
    rewritten_text:  Optional[str],
    metadata:        Dict,           # ML scores, labels, debug context
    status_code:     int             # 200 or 400
)
```

This structure enables auditing, observability, debugging, and downstream analytics. The API router maps decisions directly to HTTP responses, ensuring consistency between policy intent and runtime enforcement.

---

## HTTP Behavior

| Scenario | HTTP Code | Reason |
|---|---|---|
| Hard safety violation | 400 | Request blocked |
| Safe completion | 200 | Content intentionally transformed |
| Rewrite / redaction | 200 | Content modified |
| Log-only | 200 | Risk recorded, no user impact |

This distinction is intentional and required for real deployments.

---

## Observability & Debugging

Guardrails++ includes:

- Rule IDs returned to clients on every response
- Correlation IDs (`X-Correlation-ID`) propagated through requests
- Debug endpoints:
  - `GET /v1/debug/policies` — list all loaded policies
  - `POST /v1/debug/policies/reload` — hot-reload YAML without server restart
  - `GET /v1/debug/eval?text=...&direction=input` — test evaluation against raw text

These features support incident investigation, governance review, and policy tuning.

---

## Policy Rationale & Governance Model

This section defines who controls policies, how changes are managed, and how risk is contained.

**Policy Ownership**
- AI Safety / Security Engineers define initial policies
- Deterministic rules capture known high-risk patterns
- ML thresholds are calibrated empirically

**Change Control**
- Policy updates are configuration changes
- Reviewed via code review or change-management process
- No application redeploy required for most updates

**Blast Radius Control**

Policies are scoped by direction (input vs output), action type, and category. A faulty rule affects only its matching scope.

**Rollback Strategy**
- Policies are version-controlled in Git
- Rollback = revert YAML + hot-reload
- No code changes required

**Governance Alignment**

This model aligns with:
- NIST AI Risk Management Framework
- EU AI Act expectations for high-risk systems
- Enterprise Trust & Safety practices

---

## Evaluation & Testing

Guardrails++ was evaluated using a curated prompt set designed to stress different policy categories.

**Test Set**
- ~40 prompts total
- Categories: social engineering, data exfiltration, violence/weapons, privilege escalation, benign technical questions

**Expected Outcomes**

| Category | Allow | Block | Safe Complete | Log Only |
|---|---|---|---|---|
| Social Engineering | 0 | 0 | 8 | 0 |
| Data Exfiltration | 0 | 0 | 6 | 0 |
| Weapons | 0 | 5 | 0 | 0 |
| Technical Malware | 6 | 0 | 0 | 4 |

**Observations**
- Deterministic rules provide high precision for known risks
- ML classifiers catch abusive language missed by keywords
- Some ambiguous prompts require threshold tuning

---

## Design Decisions & Tradeoffs

**Precedence**
Deterministic rules always win over ML signals; classifiers cannot override explicit hard blocks.

**Fail-Open on ML Errors**
If the HuggingFace API is unreachable, the safety client returns `risk_score=0.0`. The engine treats this as below threshold and allows the request through rather than causing a service outage. This is an explicit operational tradeoff — availability over maximum safety — appropriate for middleware that should degrade gracefully.

**Change Control**
Policies are versioned and hot-reloaded. Rollback requires reverting configuration, not code redeploy.

**Auditability**
Each decision returns rule IDs and metadata. Persistent audit storage is planned but not implemented in v0.5.

**Threat Model**
Known bypass vectors include paraphrasing, obfuscation, multilingual abuse, and role-play-based prompt injection.

**Abuse Handling**
Jailbreak resistance currently relies on layered signals; advanced jailbreak detection is planned.

---

## Project Status

**Version:** v0.5 → v1.0 in active development  
**State:** Production-style prototype — being hardened into standalone software

### ✅ Implemented (v0.5)
- Policy-as-code engine (YAML-driven, hot-reloadable)
- Layered deterministic + ML safety (keywords, regex, HuggingFace classifiers)
- Graduated response model (block, rewrite, safe_complete, log_only)
- Auditable Decision object with rule IDs, correlation IDs, ML metadata
- Bidirectional evaluation (input pass + output pass)
- Debug and observability endpoints

### 🔨 In Progress (v1.0 Roadmap)

Guardrails++ is actively being developed into a fully standalone, deployable safety gateway. The following are being built:

| Feature | Description | Status |
|---|---|---|
| **Real LLM proxying** | Live forwarding to OpenAI / Anthropic / Groq via pluggable provider adapter | 🔨 Building |
| **API key authentication** | Bearer token auth + per-key tenant resolution | 🔨 Building |
| **Rate limiting** | Redis-based token bucket per user + per tenant | 🔨 Building |
| **Persistent audit logs** | Structured log storage with queryable decision history | 🔨 Building |
| **Multi-tenant isolation** | Per-tenant policy overrides and scoped enforcement | 🔨 Building |
| **Policy hit metrics** | Aggregated violation counts, block rates, rule performance | 🔨 Building |
| **ML-assisted social engineering detection** | Intent classifier for fraud/BEC beyond keyword matching | 📋 Planned |
| **Advanced jailbreak detection** | Semantic similarity + role-play injection resistance | 📋 Planned |

---

## Production Readiness Scope

Guardrails++ v0.5 demonstrates AI safety architecture, governance controls, and decision semantics.

The following production concerns are **actively being implemented** toward v1.0:

- Authentication & authorization (API keys, RBAC)
- Persistent audit log storage
- Rate limiting & abuse throttling
- Multi-tenant isolation
- Real LLM provider proxying

---

## LLM Provider Abstraction

Safety evaluation and policy enforcement are provider-agnostic.

The current v0.5 API layer stubs the LLM call — the gateway architecture (policy evaluation, decision routing, response transformation) is fully functional. v1.0 will add a thin provider adapter supporting OpenAI-compatible endpoints, with Anthropic and Mistral adapters following.

> Supporting additional providers requires only a request/response adapter — no policy changes needed.

---

## Intended Use

Guardrails++ is being built as:

- A **standalone deployable safety gateway** for any LLM-backed application
- A **reference architecture** for policy-driven LLM controls
- A **portfolio demonstration** of AI safety and governance engineering principles
