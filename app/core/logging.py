import logging

from rich.logging import RichHandler

from app.core.config import settings


def setup_logging() -> None:
    """Configure root logging once, at application startup."""
    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger — call this at the top of every module, not print()."""
    return logging.getLogger(name)
