#!/usr/bin/env python3
"""Compare byte and BPE sequence cost on DEVELOPMENT prose."""

from __future__ import annotations

import json

from core.cortex import (
    BPETokenizer,
    ByteTokenizer,
)


DEVELOPMENT_PATH = (
    "data/native_cortex/splits/"
    "development.jsonl"
)

TOKENIZER_PATH = (
    "data/native_cortex/tokenizer/"
    "tokenizer.json"
)


byte_tokenizer = (
    ByteTokenizer()
)

bpe_tokenizer = (
    BPETokenizer(
        TOKENIZER_PATH
    )
)

documents = 0

utf8_bytes = 0

byte_tokens = 0

bpe_tokens = 0

roundtrip_failures = 0


with open(
    DEVELOPMENT_PATH,
    "r",
    encoding="utf-8",
) as handle:
    for line in handle:
        row = json.loads(line)

        text = row["text"]

        encoded_byte = (
            byte_tokenizer.encode(
                text
            )
        )

        encoded_bpe = (
            bpe_tokenizer.encode(
                text
            )
        )

        decoded_bpe = (
            bpe_tokenizer.decode(
                encoded_bpe
            )
        )

        if decoded_bpe != text:
            roundtrip_failures += 1

        documents += 1

        utf8_bytes += len(
            text.encode(
                "utf-8"
            )
        )

        byte_tokens += len(
            encoded_byte
        )

        bpe_tokens += len(
            encoded_bpe
        )


print("=" * 78)

print(
    "MEGA PRIME — TOKENIZER EFFICIENCY"
)

print("=" * 78)

print(
    "development documents:",
    documents,
)

print(
    "UTF-8 bytes:",
    utf8_bytes,
)

print(
    "byte tokens:",
    byte_tokens,
)

print(
    "BPE tokens:",
    bpe_tokens,
)

print(
    "byte tokens / UTF-8 byte:",
    byte_tokens / utf8_bytes,
)

print(
    "BPE tokens / UTF-8 byte:",
    bpe_tokens / utf8_bytes,
)

print(
    "sequence reduction:",
    byte_tokens / bpe_tokens,
    "x",
)

print(
    "effective context multiplier:",
    byte_tokens / bpe_tokens,
    "x",
)

print(
    "BPE roundtrip failures:",
    roundtrip_failures,
)

print("=" * 78)
