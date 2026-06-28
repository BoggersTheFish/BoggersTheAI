from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("boggers.http_client")

_DEFAULT_TIMEOUT = 10
_DEFAULT_RETRIES = 3
_DEFAULT_BACKOFF = 1.0


def fetch_url(
    url: str,
    *,
    timeout: int = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    backoff: float = _DEFAULT_BACKOFF,
    headers: dict[str, str] | None = None,
) -> bytes:
    """Fetch URL with exponential backoff retries."""
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (URLError, OSError, TimeoutError) as exc:
            last_error = exc
            wait = backoff * (2**attempt)
            logger.warning(
                "HTTP %s attempt %d/%d failed: %s " "(retry in %.1fs)",
                url[:80],
                attempt + 1,
                retries,
                exc,
                wait,
            )
            if attempt < retries - 1:
                time.sleep(wait)
    raise last_error or URLError(f"Failed after {retries} attempts")


def fetch_json(url: str, **kwargs: Any) -> Any:
    """Fetch URL and parse as JSON."""
    data = fetch_url(url, **kwargs)
    return json.loads(data)
