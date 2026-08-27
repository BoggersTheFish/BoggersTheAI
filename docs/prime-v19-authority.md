# PRIME v19 authority seam

BoggersTheAI now has an explicit authority mode at the canonical `TSKernel`
commit boundary:

- `legacy_local` preserves the pre-PRIME transaction path during migration and
  is written into every TS receipt.
- `prime_required` is the production target. A `PrimeV19AuthorityAdapter` must
  be supplied, and no `commit_document()` call occurs when PRIME is absent,
  raises, rejects, abstains, returns a stale receipt, fails receipt validation,
  or no longer matches its live graph and ledger tip.

There is no silent fallback. Supplying a PRIME adapter while selecting
`legacy_local` is a configuration error.

## Bound transaction

Immediately before Boggers applies its local graph delta, the adapter creates a
PRIME `GraphPatchProposal`. Semantic commits contain one
`boggers_document_commit` node; representation transitions contain one
`boggers_representation_commit` node in the protected `representation`
authority class and always carry `representation_economics` evidence. The
mutation intent binds:

- the Boggers base graph hash and input hash;
- the complete TSIR document and document hash;
- the proposed commit or branch decision and claim statuses;
- the exact graph delta produced by a detached `commit_document()` preview,
  its Boggers hash, and the expected full post-state hash;
- every local verifier obligation and result;
- BOGVM artifacts; and
- request and receipt-chain provenance.

The proposal is also bound to the current PRIME lineage, graph root, authority
ledger tip, logical sequence, authenticated proposer identity, and proposer
key. Boggers accepts only a ledgered `AUTHORIZE`
receipt which passes PRIME receipt verification, matches the exact request and
intent, and still equals PRIME's live graph and ledger state. The mutation
intent schema is `boggers-document-commit-intent-v2`.

After admission, Boggers independently checks the projection binding, applies
the same deterministic commit, and compares both the returned delta and the
complete post-state hash with the authorized values. Any mismatch restores the
captured local base snapshot, emits an abstaining Boggers receipt with an empty
committed delta, and marks the nested admission wrapper invalid. The original
immutable PRIME receipt remains visible for reconciliation.

The adapter calls PRIME's contextual `verify_receipt()`, not the weaker
integrity-only check. A kernel restored through PRIME's authenticated checkpoint
API can be supplied to the same adapter and continues from its audited root,
ledger tip, sequence, and remaining budgets without a separate adapter path.

Boggers floating-point fields are represented as tagged Python decimal strings
inside the PRIME payload. This preserves their exact source representation
without weakening PRIME's no-float canonicalization rule. Dictionary keys must
already be strings; the adapter rejects coercion and key-collision ambiguity.
Proposer signing keys are validated at adapter construction with PRIME's minimum
length and byte-diversity requirements, so weak deployment configuration fails
at boot.

## Transaction isolation

The canonical transaction boundary is serialized by in-process graph identity,
not by `TSKernel` instance. Two kernels sharing one graph therefore cannot
authorize against the same base and publish in a different order. Re-entry on
the owning thread raises immediately instead of deadlocking. For
`UniversalLivingGraph`, the boundary also holds the graph's own re-entrant lock
from the base snapshot through receipt publication, preventing wave workers and
direct graph mutators from interleaving with projection, PRIME admission, or
local application.

The PRIME boot policy must explicitly classify `boggers_document_commit` as
`semantic` and `boggers_representation_commit` as `representation`, then
register every obligation named by the adapter. The reference integration uses
independent `safety`, `semantic`, and `representation_economics` validators.
Validators inspect and replay the bound intent; an evidence field such as
`accepted: true` is never authority.

## Current boundary

This is a development admission seam, not a sealed evidence release. The graph
coordinator and native graph lock are process-local; other processes and graph
implementations which bypass the same lock require external serialization or a
storage transaction. A custom graph lock must be re-entrant because
`commit_document()` calls graph methods while the boundary is held.

PRIME's commit and Boggers' local graph application are still two state stores
without a distributed two-phase commit. A local mismatch is rolled back, but
the already-ledgered PRIME `AUTHORIZE` remains and requires reconciliation. A
process failure after PRIME commits and before Boggers finishes has the same
requirement. Snapshot rollback is durable for the current in-memory mutation
path; custom backends which persist on every `add_node()`/`add_edge()` need a
backend transaction. Detached preview also assumes deterministic graph mutation
semantics and does not reproduce custom embedders or backend-only side effects.
The production evolution should make PRIME the single canonical graph store or
add an explicit prepare/finalize recovery protocol.
