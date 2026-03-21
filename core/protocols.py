from __future__ import annotations

from typing import Iterable, List, Protocol


class VoiceInProtocol(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


class VoiceOutProtocol(Protocol):
    def synthesize(self, text: str) -> bytes: ...


class ImageInProtocol(Protocol):
    def caption(self, image: bytes) -> str: ...


class GraphProtocol(Protocol):
    def add_node(
        self,
        node_id: str,
        content: str,
        topics: Iterable[str] | None = None,
        activation: float = 0.0,
        stability: float = 1.0,
        last_wave: int = 0,
    ) -> object: ...

    def add_edge(self, src: str, dst: str, weight: float = 1.0) -> object: ...
    def get_nodes_by_topic(self, topic: str) -> List[object]: ...
    def get_activated_subgraph(
        self, query_topic: str, top_k: int = 5
    ) -> list[dict]: ...
