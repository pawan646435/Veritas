from fastapi import FastAPI

from app.api.routes import router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Veritas",
    description="An autonomous agent that audits other AI agents for hallucination, "
    "tool misuse, and task failure.",
    version="0.1.0",
)
app.include_router(router)
