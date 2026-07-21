# Dependency Direction Rules

To prevent architectural degradation and maintain authority boundaries, the codebase enforces strict dependency direction rules:

---

## Dependency Rules

1. **Foundational packages (`ts-core`, `ts-ir`, `ts-artifacts`, `ts-verifiers`, `ts-kernel`) MUST NOT import application modules (`apps/`, `dashboard`, `interface/chat`).**
2. **Verification authority MUST NOT depend on language generation or LLM libraries (`ollama`, `transformers`, `torch`).**
3. **Rendering and UI components MUST NOT possess proof authority.**
4. **Imports MUST NOT form cycles between core packages.**

---

## Automated Enforcement

Dependency direction rules are automatically verified in CI via:
```bash
make check-architecture
# or: python3 tools/check_architecture.py
```
