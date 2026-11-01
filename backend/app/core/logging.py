"""Application logging for the Phase 3 API."""

from __future__ import annotations

import logging
from typing import Any


def setup_logging(level: str = "INFO") -> None:
    """Configure a compact log format. Do not log secrets or full prompts."""

    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    """Log a short event with selected fields. Values must already be redacted."""

    extras = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("%s %s", message, extras)
