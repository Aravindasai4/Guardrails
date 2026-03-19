# Guardrails PP - FastAPI Application

## Overview
A FastAPI-based middleware safety gateway for LLMs with policy-driven content moderation, YAML DSL configuration, correlation ID tracing, and integration with external ML safety classifiers (HuggingFace toxicity detection models).

## Project Structure
```
src/
  guardrails_pp/
    __init__.py
    main.py              # FastAPI app entrypoint
    decision.py          # Decision dataclass (ALLOW/TRANSFORM/BLOCK)
    safe_completion.py   # Safe completion templates by category
    api/
      __init__.py
      router.py          # API routes with policy enforcement
      schemas.py         # Pydantic models
    core/
      __init__.py
      config.py          # Settings
      logging.py         # Logging setup
    policy/
      __init__.py
      engine.py          # Policy evaluation engine with reload support
    integrations/
      __init__.py
      safety_client.py   # HuggingFace toxicity API client
    utils/
      __init__.py
      correlation.py     # CorrelationIDMiddleware + structured logging
  policies/
    base_policies.yaml   # Policy definitions
```

## Running the Application
```bash
cd src && uvicorn guardrails_pp.main:app --host 0.0.0.0 --port 5000
```

## API Endpoints
- `POST /v1/chat/completions` - Main chat endpoint with policy evaluation
- `GET /v1/debug/policies` - View loaded policies
- `POST /v1/debug/policies/reload` - Reload policies from YAML
- `GET /v1/debug/eval?text=...&direction=input|output` - Test policy evaluation

## Decision System (ALLOW/TRANSFORM/BLOCK)
The policy engine returns Decision objects with:
- **decision**: "allow" | "transform" | "block"
- **action**: "pass_through" | "safe_completion" | "rewrite" | "reject"
- **status_code**: 200 (allow/transform) or 400 (block)
- **rewritten_text**: Safe completion or modified text

## Policy Actions
- `block` - Hard reject (400)
- `safe_complete` - Return helpful alternatives (200) - requires `category` field
- `rewrite` - Modify text
- `log_only` - Log and allow

## Safe Completion Categories
- `social_engineering` - Fraud/impersonation deflection
- `physical_harm` - Violence prevention
- `data_exfiltration` - Data theft deflection
- `weapons_explosives` - Violence prevention
- `toxicity` - Harmful language deflection

## External ML Classifiers
- `unitary/unbiased-toxic-roberta` - Primary toxicity detection
- `s-nlp/roberta_toxicity_classifier` - Secondary toxicity detection
- HuggingFace API: `https://router.huggingface.co/hf-inference/models/`

## Middleware
- **CorrelationIDMiddleware**: X-Correlation-ID header propagation + structured JSON logging
- **CORSMiddleware**: Allows all origins

## Structured Logging
Each request logs JSON with correlation_id:
```json
{"ts": 1765668417.027972, "correlation_id": "68b15f86-...", "method": "GET", "path": "/v1/debug/eval", "status_code": 200, "duration_ms": 3790.2}
```

## Recent Changes
- 2024-12-13: Added CorrelationIDMiddleware with structured JSON logging
- 2024-12-13: Added /debug/policies/reload endpoint for hot-reloading
- 2024-12-13: Expanded social engineering triggers (CEO fraud, BEC, wire, gift cards)
- 2024-12-13: Expanded physical harm triggers (shrapnel, pressure vessel, improvised device)
- 2024-12: Refactored to ALLOW/TRANSFORM/BLOCK decision system
- 2024-12: Added safe completion templates with categories
