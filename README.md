# BoggersTheAI

Lightweight, modular TS-OS assistant architecture built around a graph + wave loop.

This project favors structure and constraint propagation over monolithic model size:
- Graph for externalized knowledge state
- Wave for propagation and tension handling
- Synthesis engine for context-grounded response generation
- Pluggable adapters/tools/multimodal modules

## Current Status

Implemented modules:
- Core: graph, wave, mode manager, query processor, query router
- Inference: synthesis engine + throttle-aware inference router
- Adapters: wikipedia, rss, hacker news, markdown, vault, x-api placeholder
- Tools: search, calc, code_run, file_read + registry/router/executor
- Multimodal: voice in, voice out, image caption path
- Entities: consolidation + insight generation
- Interface: runtime composition, API handler, CLI chat loop

## Repository Layout

```text
BoggersTheAI/
├── adapters/
├── core/
├── entities/
├── interface/
├── multimodal/
├── tools/
└── config.yaml
```

## Quick Start

### 1) Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Optional dependencies

Most modules use Python stdlib defaults. Install optional packages only if you want richer backends:

```powershell
pip install faster-whisper piper-tts feedparser beautifulsoup4
```

### 3) Run a simple query from Python

```python
from BoggersTheAI import BoggersRuntime

rt = BoggersRuntime()
response = rt.ask("Explain TS-OS graph wave architecture")
print(response.answer)
print(response.hypotheses)
```

### 4) Run CLI chat loop

```python
from BoggersTheAI.interface import run_chat
run_chat()
```

## Configuration

Main settings are in `config.yaml`:
- module enable/disable flags
- inference mode and throttle settings
- tool and adapter toggles
- deployment tier presets

Module-level configs are also available in:
- `adapters/config.yaml`
- `tools/config.yaml`
- `multimodal/config.yaml`

## Architecture Notes

- `core/router.py` orchestrates user flow and autonomous cycle flow.
- `core/query_processor.py` performs topic extraction, retrieval, sufficiency checks, optional ingestion/tooling, synthesis, consolidation, and insight generation.
- `entities/inference_router.py` enforces a minimum synthesis interval (throttle policy).
- Multimodal adapters convert non-text modalities into text before synthesis.

## GitHub Push Checklist

- Ensure `config.yaml` does not contain private secrets.
- Keep API keys in environment variables (see `.env.example`).
- Run compile check before pushing:

```powershell
python -m compileall BoggersTheAI
```

- Optional: add tests under `tests/` for stable CI before public release.

## License

Add your preferred license file before publishing (MIT/Apache-2.0 recommended).
