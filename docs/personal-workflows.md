# Personal Workflows

This document describes optional local workflows used by the maintainer. These
are not autonomous runtime capabilities and are not part of the verifier
authority boundary.

## Manual Grok Hand-Off

Some local meta-critique traces include prompt fields intended for manual
copy/paste into a third-party chat interface. That hand-off is a personal
review workflow:

- `traces/` is gitignored.
- `traces/meta_critique/.gitkeep` exists only so the local path is present.
- Runtime files such as `waves.jsonl` and `NEXT_GROK_PROMPT.txt` remain local.
- `next_grok_prompt` records are skipped when folding wave traces into graph
  nodes.
- Copying `embedded_full_cursor_prompt` into Grok is manual. It is not an
  automated TS runtime feature, not a verifier, and not proof authority.

The only accepted TS authority path remains a verifier-backed committed kernel
receipt.
