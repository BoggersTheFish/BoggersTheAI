from __future__ import annotations

from BoggersTheAI.core.local_llm import LocalLLM


def test_parse_json_valid():
    llm = LocalLLM.__new__(LocalLLM)
    llm.model = "test"
    result = llm._parse_json('{"answer": "hello"}')
    assert result["answer"] == "hello"


def test_parse_json_invalid():
    llm = LocalLLM.__new__(LocalLLM)
    llm.model = "test"
    result = llm._parse_json("not json at all")
    assert result == {}


def test_parse_json_embedded():
    llm = LocalLLM.__new__(LocalLLM)
    llm.model = "test"
    result = llm._parse_json('Some text {"key": "value"} more text')
    assert result["key"] == "value"
