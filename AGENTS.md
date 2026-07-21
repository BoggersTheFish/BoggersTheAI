# Thinking System Agent & Contributor Directives

This repository is governed by strict verifier-first architectural rules. All AI coding assistants and human contributors must comply with these guidelines.

---

## Operating Directives

1. **Verifier Authority Rule:**
   Do not introduce state modification logic that bypasses `TSKernel` verifier obligations. Generated LLM text is never proof authority.

2. **No Test Weakening:**
   Do not weaken or remove assertions to make tests pass. Fix the underlying contract or implementation.

3. **No Secret or Weight Commits:**
   Never commit `.env` secrets, model weights (`.safetensors`, `.bin`), local databases (`*.db`), or private log traces.

4. **Dependency Direction Enforcement:**
   Run `make check-architecture` before committing. Core packages must not import application or UI modules.
