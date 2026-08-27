"""Transparent byte tokenizer for Mega PRIME Native Cortex."""

from __future__ import annotations


class ByteTokenizer:
    PAD = 256
    BOS = 257
    EOS = 258

    vocab_size = 259

    def encode(
        self,
        text: str,
        *,
        add_bos: bool = True,
        add_eos: bool = True,
    ) -> list[int]:
        tokens = list(
            text.encode(
                "utf-8"
            )
        )

        if add_bos:
            tokens.insert(
                0,
                self.BOS,
            )

        if add_eos:
            tokens.append(
                self.EOS
            )

        return tokens

    def decode(
        self,
        tokens,
    ) -> str:
        raw = bytes(
            token
            for token in tokens
            if (
                0 <= token < 256
            )
        )

        return raw.decode(
            "utf-8",
            errors="replace",
        )

    def token_label(
        self,
        token: int,
    ) -> str:
        if token == self.PAD:
            return "<PAD>"

        if token == self.BOS:
            return "<BOS>"

        if token == self.EOS:
            return "<EOS>"

        if not (
            0 <= token < 256
        ):
            return "<INVALID>"

        value = bytes(
            [token]
        )

        try:
            decoded = value.decode(
                "utf-8"
            )
        except UnicodeDecodeError:
            return (
                f"<BYTE:{token:02x}>"
            )

        if decoded.isprintable():
            return repr(
                decoded
            )

        return (
            f"<BYTE:{token:02x}>"
        )
