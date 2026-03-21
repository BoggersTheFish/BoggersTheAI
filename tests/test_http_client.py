from __future__ import annotations

import io
import json
from unittest.mock import patch
from urllib.error import URLError

import pytest
from BoggersTheAI.adapters.http_client import (
    fetch_json,
    fetch_url,
)


class _FakeResponse(io.BytesIO):
    """Minimal urlopen response stand-in."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


_URL = "https://example.com/data"


@patch("BoggersTheAI.adapters.http_client.urlopen")
def test_fetch_url_success(mock_urlopen):
    mock_urlopen.return_value = _FakeResponse(b"hello")
    result = fetch_url(_URL)
    assert result == b"hello"
    mock_urlopen.assert_called_once()


@patch("BoggersTheAI.adapters.http_client.urlopen")
def test_fetch_url_retries_on_failure(
    mock_urlopen,
):
    mock_urlopen.side_effect = [
        URLError("err1"),
        _FakeResponse(b"ok"),
    ]
    result = fetch_url(_URL, retries=2, backoff=0.0)
    assert result == b"ok"
    assert mock_urlopen.call_count == 2


@patch("BoggersTheAI.adapters.http_client.urlopen")
def test_fetch_url_raises_after_exhausted_retries(
    mock_urlopen,
):
    mock_urlopen.side_effect = URLError("boom")
    with pytest.raises(URLError):
        fetch_url(_URL, retries=2, backoff=0.0)
    assert mock_urlopen.call_count == 2


@patch("BoggersTheAI.adapters.http_client.time.sleep")
@patch("BoggersTheAI.adapters.http_client.urlopen")
def test_fetch_url_backoff_timing(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [
        URLError("e1"),
        URLError("e2"),
        _FakeResponse(b"ok"),
    ]
    result = fetch_url(_URL, retries=3, backoff=1.0)
    assert result == b"ok"
    assert mock_sleep.call_count == 2
    delays = [c.args[0] for c in mock_sleep.call_args_list]
    assert delays[0] == pytest.approx(1.0)
    assert delays[1] == pytest.approx(2.0)


@patch("BoggersTheAI.adapters.http_client.urlopen")
def test_fetch_url_custom_headers(mock_urlopen):
    mock_urlopen.return_value = _FakeResponse(b"body")
    fetch_url(_URL, headers={"X-Test": "value"})
    req = mock_urlopen.call_args[0][0]
    assert req.get_header("X-test") == "value"


@patch("BoggersTheAI.adapters.http_client.urlopen")
def test_fetch_json_parses(mock_urlopen):
    payload = {"key": [1, 2, 3]}
    mock_urlopen.return_value = _FakeResponse(json.dumps(payload).encode())
    result = fetch_json(_URL)
    assert result == payload
