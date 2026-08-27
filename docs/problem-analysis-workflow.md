# PRIME-governed TS problem analysis (M19.1)

M19.1 adds one bounded path from a structured `ProblemSpec` to the canonical
PRIME v19 graph. It does not make arbitrary prose true and it does not govern
the older direct graph-writing surfaces elsewhere in BoggersTheAI.

## Authority path

The workflow follows this fixed wave:

`READY -> BOUND -> FIELD_READY -> FOCUSED -> PROPOSED -> ROUTED -> REQUEST_READY -> SUBMITTED -> COMMITTED | REJECTED | ABSTAINED | FAIL_CLOSED`

1. `ProblemSpec` bounds the question, context, constraints, desired outcomes,
   failure modes, testable predictions, scope, and source provenance.
2. The existing `constraint_fields` library projects that structure into a
   deterministic field. Native finite floats are converted to exact tagged
   `float.hex()` values; non-finite floats, non-string keys, and source-authored
   numeric tags are rejected.
3. The active frontier records primitives, tension markers, and the
   `Propagate -> Relax -> Break -> Evolve` trajectory without model scores.
4. A mounted sealed-v18 proposer may provide rank-only advice through the tiny
   `AdviceProtocol`. Its exact archive, manifest, sealed-release, scientific
   freeze, parent field, field model, NumPy archive, tensor, worker request, and
   result bindings are checked. Invalid or unavailable advice is ablated. Raw
   advice remains receipt evidence only; it is never promoted into or hashed
   into the canonical semantic node.
5. Three independent, fingerprinted validators recompute the workflow boundary,
   field integrity, and provenance binding from untrusted evidence.
   A signed shared-evidence bundle hash commits every common field across all
   three obligation envelopes, preventing split-view verifier attacks.
6. Only a caller-supplied PRIME `AuthorityKernel` can publish the change.

The only permitted canonical change is one add-only node of kind
`ts.problem_analysis`. Edges, deletion, overwrite, executable payloads,
representation transitions, unknown kinds, missing evidence, and stale parents
fail closed. The node means “deterministically validated constraint-field
analysis”; it is explicitly not a world-truth claim.

The node id is the full normalized `ProblemSpec` SHA-256. Its payload is a pure
function of that spec, the deterministic field/focus projection, and stable
workflow semantics. Advice, mount/runtime details, parent roots, authority tips,
and sequence numbers remain signed proposal/evidence/receipt bindings only.
Consequently advice availability and problem commit order cannot change the
canonical node content, and equivalent final problem sets converge to the same
graph root.

The v1 identity contract freezes the workflow/projection semantics carried by
`boggers-ts-problem-spec-v1`. Any future projection or canonical-semantics
change must introduce a new ProblemSpec schema and node identity namespace;
reusing the v1 schema with different canonical semantics is forbidden.

## Boot boundary

`build_problem_workflow_kernel` requires the caller to supply independent
authority, proposer, workflow-verifier, field-verifier, provenance-verifier,
and economics-verifier identities and keys. The proposer is semantic-only.
Policy maps only `ts.problem_analysis`; representation economics is still
registered and every representation path is denied. This package contains no
production or default key material.

The specialized builder always starts from an empty genesis. Existing state
can enter only through an authenticated, replay-verified checkpoint whose graph
lineage matches the requested lineage. Restore additionally audits the entire
receipt ledger from a fresh empty kernel and requires the reconstructed graph,
tip, sequence, and budgets to equal the checkpoint state; an authenticated
checkpoint containing unvalidated genesis state is rejected. Supplying a separately constructed
`AuthorityKernel` to `ProblemAnalysisWorkflow` is an explicit caller-trusted
policy, registry, and genesis boundary; the workflow cannot retroactively
validate that kernel's boot state.

## Honest limits

- The workflow does not call the Universal Living Graph or `commit_document`.
  PRIME is the sole canonical writer for this path, but other legacy Boggers
  paths still require migration before repo-wide authority can be claimed.
- Sealed-v18 executes through PRIME's proposal-only subprocess mount. A
  subprocess is not a full operating-system security boundary; production use
  still needs a separate user, container, or service boundary.
- `AdviceProtocol` strictly validates the exact claimed v18 receipt and result
  fields, but an arbitrary caller-supplied object can imitate that structural
  shape. Real sealed-parent provenance requires passing the object returned by
  `mount_v18_proposer`; this remains canonically inert evidence, not independent
  third-party attestation.
- PRIME's present same-process HMAC design is tamper evidence, not independent
  third-party attestation. Rollback/fork detection requires an external anchor.
- The structured projection validates integrity and deterministic mechanics,
  not the empirical truth of user-supplied premises or predictions.
