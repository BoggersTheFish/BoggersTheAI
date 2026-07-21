# Authority Boundary Specification

The Thinking System authority boundary establishes non-negotiable rules governing state modification and claim acceptance:

---

## Authority Boundary Rules

1. **Generated Language is NOT Proof Authority:**
   Outputs produced by language models or dialogue components are treated strictly as unverified proposal candidates.

2. **Model Confidence is NOT Proof Authority:**
   Soft probabilities or logit confidence scores cannot satisfy verifier obligations.

3. **Execution Completion is NOT Proof Authority:**
   Successful completion of a code block or script execution does not automatically imply semantic correctness without explicit verifier checks.

4. **Verifier Gate Requirement:**
   State transitions, graph node commits, and claim assertions MUST be verifier-gated and backed by content-addressable receipts.

5. **Fail-Closed Default:**
   If a verifier obligation fails or is unsupported, the transaction MUST fail closed (decision: `quarantine`, `branch`, or `abstain`).
