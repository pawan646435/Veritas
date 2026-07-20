from fastapi import FastAPI
from fastapi.responses import RedirectResponse

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


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """The bare root path is what a shared link (LinkedIn, a resume, etc.)
    actually points to — redirect it to the interactive API docs instead
    of returning a bare 404, since that's genuinely useful to a visitor
    with no other context.
    """
    return RedirectResponse(url="/docs")
