from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.router import api_router
from .core.logging import setup_logging
from .core.config import Settings
from .utils.correlation import CorrelationIDMiddleware

settings = Settings()
setup_logging()

app = FastAPI(
    title="Guardrails++",
    version="0.1.0",
    description="AI Safety Gateway middleware for LLMs",
)

app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")
