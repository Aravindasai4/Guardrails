import os
from typing import Literal
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from .schemas import ChatCompletionRequest, ChatCompletionResponse
from ..policy.engine import (
    evaluate_policies_for_request,
    debug_list_policies,
    debug_evaluate_raw,
    reload_policies,
)
from ..utils.correlation import log_decision

api_router = APIRouter()


@api_router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
):
    tenant = {"id": "demo-tenant"}
    correlation_id = getattr(request.state, "correlation_id", None)

    decision = await evaluate_policies_for_request(
        text=body.input,
        direction="input",
        tenant=tenant,
        metadata={
            "endpoint": "chat.completions",
            "correlation_id": correlation_id,
        },
    )

    log_decision(request, decision)

    if decision.decision == "block":
        return JSONResponse(
            status_code=400,
            content={
                "error": "Request blocked by Guardrails++",
                "rules_triggered": decision.rules_triggered,
                "correlation_id": correlation_id,
            },
            headers={"X-Correlation-ID": correlation_id or ""},
        )

    if decision.action == "safe_completion":
        return ChatCompletionResponse(
            output=decision.rewritten_text or "I can't help with that request.",
            model=body.model,
            rules_triggered=decision.rules_triggered,
        )

    rewritten_input = decision.rewritten_text or body.input

    llm_response_text = rewritten_input

    output_decision = await evaluate_policies_for_request(
        text=llm_response_text,
        direction="output",
        tenant=tenant,
        metadata={
            "endpoint": "chat.completions",
            "correlation_id": correlation_id,
        },
    )

    log_decision(request, output_decision)

    if output_decision.decision == "block":
        safe_output = "[Guardrails++] Output blocked by safety policies."
    elif output_decision.action == "safe_completion":
        safe_output = output_decision.rewritten_text or llm_response_text
    else:
        safe_output = output_decision.rewritten_text or llm_response_text

    rules = decision.rules_triggered + output_decision.rules_triggered

    return ChatCompletionResponse(
        output=safe_output,
        model=body.model,
        rules_triggered=rules,
    )


@api_router.get("/debug/policies")
async def debug_policies():
    return {"policies": debug_list_policies()}


@api_router.post("/debug/policies/reload")
async def reload_policies_endpoint():
    count = reload_policies()
    return {"message": "Policies reloaded", "policy_count": count}


@api_router.get("/debug/eval")
async def debug_eval(
    text: str = Query(..., description="Text to evaluate with policies"),
    direction: Literal["input", "output"] = Query("input"),
):
    raw = await debug_evaluate_raw(text=text, direction=direction)
    return raw
