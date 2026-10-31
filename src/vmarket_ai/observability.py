import json
import logging
from datetime import UTC, datetime

LOGGER = logging.getLogger("vmarket_ai")


def request_event(request_id: str, route: str, status: int, elapsed_ms: float) -> None:
    # Closed metadata projection: never use path/query/body/header values as log text.
    LOGGER.info(
        json.dumps(
            {
                "event": "http_request",
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "route": route,
                "status": status,
                "elapsed_ms": round(elapsed_ms, 3),
            }
        )
    )


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.handlers = [handler]
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    # Third-party HTTP debug output must not log raw provider requests.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
