# Guardrails++

A middleware safety gateway for LLMs with policy-driven blocking, explainable rule IDs, and correlation-ID tracing.

## Features

- **Policy-driven blocking logic** - Configurable rules to block, allow, or rewrite LLM requests/responses
- **Explainable rule IDs** - Every triggered policy returns identifiable rule names for debugging
- **Correlation-ID tracing** - X-Correlation-ID header propagation for request tracking
- **YAML DSL configuration** - Policies defined in YAML, not hard-coded logic
- **Clean separation of concerns** - Transport, policy logic, and detectors are modular

## Project Structure

```
src/
  guardrails_pp/
    main.py              # FastAPI app entrypoint
    api/
      router.py          # API routes (/v1/chat/completions)
      schemas.py         # Pydantic request/response models
    core/
      config.py          # Application settings
      logging.py         # Logging configuration
    policy/
      engine.py          # Policy evaluation engine
    utils/
      correlation.py     # Correlation ID helper
```

## Running the Application

```bash
bash run.sh
```

Or manually:

```bash
cd src && uvicorn guardrails_pp.main:app --host 0.0.0.0 --port 5000
```

## API Endpoints

- `POST /v1/chat/completions` - Chat completion endpoint with policy evaluation

## Example Request

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, world!", "model": "gpt-4"}'
```

## Policy Rationale (Governance + Change Control)

### Who Defines the Rules
Policies are defined in `policies/base_policies.yaml` using a declarative YAML DSL. Security, compliance, or product teams author rules specifying keywords, regex patterns, or external safety classifiers. No code changes required—just edit the YAML and reload.

### Who Approves Changes
- **Recommended**: Require pull-request review for `base_policies.yaml` changes before merging to main
- **Current**: Hot-reload via `POST /v1/debug/policies/reload` allows immediate testing in dev; production should gate behind CI/CD approval

### Blast Radius Controls
- Policies specify `applies_to: ["input", "output"]` to limit scope
- Actions range from `log_only` (observe) → `safe_complete` (transform) → `block` (reject)
- External classifiers have configurable `threshold` to tune sensitivity
- **Recommended**: Tenant-scoped policies (not yet implemented) to isolate rule sets per customer

### Rollback Strategy
- YAML files are version-controlled—`git revert` restores previous policy state
- `reload_policies()` clears cache and reloads from disk instantly
- **Recommended**: Kill-switch endpoint (not yet implemented) to disable all blocking and fall back to allow-all mode during incidents

### Auditability
- Every decision returns `rules_triggered[]` identifying which policies matched
- `X-Correlation-ID` header propagates through request lifecycle for log correlation
- Structured JSON logs include correlation ID, decision, duration, and status code
- External safety scores from HuggingFace models are recorded in decision metadata

## License

MIT
