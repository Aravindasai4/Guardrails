import uuid
import json
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..decision import Decision

HEADER_NAME = "X-Correlation-ID"


def get_or_create_correlation_id(request: Request) -> str:
    for header_name in request.headers.keys():
        if header_name.lower() == "x-correlation-id":
            cid = request.headers.get(header_name)
            if cid:
                return cid
    return str(uuid.uuid4())


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = get_or_create_correlation_id(request)
        request.state.correlation_id = correlation_id

        start_time = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start_time

        response.headers[HEADER_NAME] = correlation_id

        log_entry = {
            "ts": time.time(),
            "correlation_id": correlation_id,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }
        print(json.dumps(log_entry))

        return response


def log_decision(request: Request, decision: Decision) -> None:
    correlation_id = getattr(request.state, "correlation_id", None)
    payload = {
        "ts": time.time(),
        "type": "guardrails_decision",
        "correlation_id": correlation_id,
        "path": str(request.url.path),
        "decision": decision.decision,
        "action": decision.action,
        "rules_triggered": decision.rules_triggered,
        "status_code": decision.status_code,
        "meta": decision.metadata or {},
    }
    print(json.dumps(payload))
