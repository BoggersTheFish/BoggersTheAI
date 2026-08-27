"""Transaction request, workspace and result types."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
import threading
from typing import Any
import weakref

from ..types import Edge, Node
from .ir import TSIRDocument, VerifierObligation, stable_hash


class ReentrantGraphTransactionError(RuntimeError):
    """Raised instead of deadlocking on a nested transaction for one graph."""


@dataclass(slots=True)
class _GraphTransactionGuard:
    transaction_lock: threading.Lock = field(default_factory=threading.Lock)
    owner_lock: threading.Lock = field(default_factory=threading.Lock)
    owner_thread_id: int | None = None


_GRAPH_GUARDS_LOCK = threading.Lock()
_GRAPH_GUARDS: dict[
    int,
    tuple[weakref.ReferenceType[Any] | Any, _GraphTransactionGuard],
] = {}


def _drop_graph_guard(
    graph_id: int,
    graph_reference: weakref.ReferenceType[Any],
) -> None:
    with _GRAPH_GUARDS_LOCK:
        entry = _GRAPH_GUARDS.get(graph_id)
        if entry is not None and entry[0] is graph_reference:
            _GRAPH_GUARDS.pop(graph_id, None)


def _graph_transaction_guard(graph: Any) -> _GraphTransactionGuard:
    graph_id = id(graph)
    with _GRAPH_GUARDS_LOCK:
        existing = _GRAPH_GUARDS.get(graph_id)
        if existing is not None:
            reference, guard = existing
            referenced_graph = (
                reference()
                if isinstance(reference, weakref.ReferenceType)
                else reference
            )
            if referenced_graph is graph:
                return guard
            _GRAPH_GUARDS.pop(graph_id, None)

        guard = _GraphTransactionGuard()
        try:
            reference = weakref.ref(
                graph,
                lambda item, key=graph_id: _drop_graph_guard(key, item),
            )
        except TypeError:
            # A non-weak-referenceable graph is retained so object-id reuse can
            # never alias two guards. Such custom graph objects are uncommon.
            reference = graph
        _GRAPH_GUARDS[graph_id] = (reference, guard)
        return guard


@contextmanager
def _held_graph_lock(graph: Any):
    """Hold a graph-native lock for callers which mutate through graph methods.

    ``UniversalLivingGraph`` exposes a re-entrant context-manager lock. The
    acquire/release fallback supports equivalent graph implementations without
    requiring them to implement the context-manager protocol.
    """

    graph_lock = getattr(graph, "_lock", None)
    if graph_lock is None:
        yield
        return
    if hasattr(graph_lock, "__enter__") and hasattr(graph_lock, "__exit__"):
        with graph_lock:
            yield
        return
    acquire = getattr(graph_lock, "acquire", None)
    release = getattr(graph_lock, "release", None)
    if not callable(acquire) or not callable(release):
        yield
        return
    acquire()
    try:
        yield
    finally:
        release()


@contextmanager
def serialized_graph_transaction(graph: Any):
    """Serialize the complete TSKernel transaction for one graph object.

    The guard is shared by every TSKernel instance using the same in-process
    graph. A nested call from the owning thread fails immediately instead of
    blocking forever on the non-reentrant transaction lock.
    """

    guard = _graph_transaction_guard(graph)
    thread_id = threading.get_ident()
    with guard.owner_lock:
        if guard.owner_thread_id == thread_id:
            raise ReentrantGraphTransactionError(
                "a graph transaction cannot re-enter itself"
            )

    with _held_graph_lock(graph):
        guard.transaction_lock.acquire()
        try:
            with guard.owner_lock:
                guard.owner_thread_id = thread_id
            yield
        finally:
            with guard.owner_lock:
                guard.owner_thread_id = None
            guard.transaction_lock.release()


class CommitDecision(str, Enum):
    COMMIT = "commit"
    REJECT = "reject"
    QUARANTINE = "quarantine"
    REPAIR = "repair"
    BRANCH = "branch"
    ABSTAIN = "abstain"


@dataclass(frozen=True, slots=True)
class TransactionRequest:
    raw_input: str
    provenance: str = "user"
    render_language: bool = True
    use_bogvm: bool = True


@dataclass(slots=True)
class TransactionWorkspace:
    base_graph_hash: str
    document: TSIRDocument
    base_nodes: dict[str, Node]
    base_edges: list[Edge]
    obligations: list[VerifierObligation] = field(default_factory=list)
    proof_objects: list[Any] = field(default_factory=list)
    verification_results: list[Any] = field(default_factory=list)
    bogvm_artifacts: list[dict[str, Any]] = field(default_factory=list)
    derived_claims: list[Any] = field(default_factory=list)
    rejected_claims: list[str] = field(default_factory=list)
    committed_graph_delta: dict[str, Any] = field(
        default_factory=lambda: {"nodes": [], "edges": []}
    )

    def is_required_obligation(self, obligation_id: str) -> bool:
        for obligation in self.obligations:
            if obligation.id == obligation_id:
                return obligation.required
        return False

    def add_obligation(self, obligation: VerifierObligation) -> None:
        if any(existing.id == obligation.id for existing in self.obligations):
            return
        self.obligations.append(obligation)


@dataclass(frozen=True, slots=True)
class TransactionResult:
    decision: CommitDecision
    receipt: Any
    rendered: str


def graph_snapshot(graph: Any) -> tuple[dict[str, Node], list[Edge]]:
    if hasattr(graph, "snapshot_read"):
        return graph.snapshot_read()
    return (
        {node_id: copy.deepcopy(node) for node_id, node in graph.nodes.items()},
        [copy.deepcopy(edge) for edge in graph.edges],
    )


def graph_state_hash_from_parts(nodes: dict[str, Node], edges: list[Edge]) -> str:
    payload = {
        "nodes": sorted(
            (asdict(node) for node in nodes.values()), key=lambda x: x["id"]
        ),
        "edges": sorted(
            (asdict(edge) for edge in edges),
            key=lambda x: (x["src"], x["dst"], x["relation"], x["weight"]),
        ),
    }
    return stable_hash(payload)


def graph_state_hash(graph: Any) -> str:
    nodes, edges = graph_snapshot(graph)
    return graph_state_hash_from_parts(nodes, edges)
