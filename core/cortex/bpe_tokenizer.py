"""BPE tokenizer adapter for Mega PRIME Native Cortex."""

from __future__ import annotations

from tokenizers import Tokenizer


class BPETokenizer:
    def __init__(
        self,
        path: str,
    ) -> None:
        self.tokenizer = (
            Tokenizer.from_file(path)
        )

        vocab = (
            self.tokenizer.get_vocab()
        )

        self.PAD = vocab["<PAD>"]
        self.BOS = vocab["<BOS>"]
        self.EOS = vocab["<EOS>"]
        self.UNK = vocab["<UNK>"]

        self.vocab_size = (
            self.tokenizer
            .get_vocab_size()
        )

    def encode(
        self,
        text: str,
        *,
        add_bos: bool = True,
        add_eos: bool = True,
    ) -> list[int]:
        ids = list(
            self.tokenizer
            .encode(text)
            .ids
        )

        if add_bos:
            ids.insert(
                0,
                self.BOS,
            )

        if add_eos:
            ids.append(
                self.EOS
            )

        return ids

    def decode(
        self,
        tokens,
    ) -> str:
        ids = [
            int(token)
            for token in tokens
            if int(token) not in (
                self.PAD,
                self.BOS,
                self.EOS,
            )
        ]

        return self.tokenizer.decode(
            ids
        )

    def token_label(
        self,
        token: int,
    ) -> str:
        value = (
            self.tokenizer
            .id_to_token(
                int(token)
            )
        )

        return (
            value
            if value is not None
            else "<INVALID>"
        )
