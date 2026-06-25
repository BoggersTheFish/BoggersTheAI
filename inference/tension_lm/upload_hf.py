"""
upload_hf.py — upload a trained TensionLM checkpoint to HuggingFace Hub
========================================================================
Packages the checkpoint + tokenizer into a HuggingFace-compatible repo
and pushes it so anyone can pull and run inference with one line.

Prerequisites:
    pip install huggingface_hub
    huggingface-cli login   (or set HF_TOKEN env var)

Usage:
    python3 upload_hf.py \\
        --checkpoint checkpoints/tension/latest.pt \\
        --repo_id   BoggersTheFish/TensionLM-117M \\
        --private                           # optional: keep private until ready
"""

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

import torch


MODEL_CARD = """\
---
language: en
license: mit
tags:
  - language-model
  - tension
  - causal-lm
  - novel-architecture
---

# TensionLM

A language model trained on sigmoid *tension* instead of softmax attention.

## Architecture

Standard transformers use softmax attention — every position competes for a
fixed budget that sums to 1. TensionLM replaces this with independent sigmoid
scores: each token pair is judged on its own merits, not in competition with
others.

```
tau[t, w] = sigmoid( dot(q_t, k_{{t-w-1}}) / √d )
output[t] = Σ_w  tau[t, w] * v_{{t-w-1}}
```

## Usage

```python
import torch
from model import TensionConfig, TensionLM, generate
from tokenizers import Tokenizer

ckpt      = torch.load("pytorch_model.pt", map_location="cpu", weights_only=False)
model     = TensionLM(TensionConfig(**ckpt["cfg"]))
state     = {{k.replace("_orig_mod.", ""): v for k, v in ckpt["model"].items()}}
model.load_state_dict(state)
tokenizer = Tokenizer.from_file("tokenizer.json")

enc    = tokenizer.encode("The cat sat")
ids    = generate(model, enc.ids, max_new=100, temp=0.8, top_p=0.92)
result = tokenizer.decode(ids)
print(result)
```

Or use the CLI:
```bash
python3 generate.py --checkpoint pytorch_model.pt --prompt "The cat sat"
```

## Training

{training_info}

## Model card

| Property | Value |
|----------|-------|
| Parameters | {params} |
| Architecture | TensionLM (sigmoid tension, windowed) |
| Dataset | {dataset} |
| Val PPL | {val_ppl} |
| Context window | {window} tokens per layer × {num_layers} layers |

## Limitations

This is a research model. It does not follow instructions, has not been
fine-tuned, and may produce incoherent or incorrect text. It is intended
to demonstrate the tension mechanism, not as a production system.
"""


def get_args():
    p = argparse.ArgumentParser(
        description="Upload TensionLM checkpoint to HuggingFace Hub",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--repo_id",    required=True, help="e.g. username/TensionLM-117M")
    p.add_argument("--private",    action="store_true")
    p.add_argument("--commit_message", default="Upload TensionLM checkpoint")
    return p.parse_args()


def main():
    args = get_args()

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        raise SystemExit("pip install huggingface_hub")

    print(f"Loading {args.checkpoint} ...")
    ckpt = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    cfg_dict = ckpt["cfg"]
    val_ppl  = ckpt.get("val_ppl", "N/A")
    arch     = ckpt.get("arch", "tension")
    train_args = ckpt.get("args", {})

    from model import TensionConfig, TensionLM
    cfg   = TensionConfig(**cfg_dict)
    model = TensionLM(cfg)
    state = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model"].items()}
    model.load_state_dict(state)
    params = model.num_params

    dataset     = train_args.get("dataset", "unknown")
    training_info = (
        f"Trained for {ckpt.get('step', '?')} steps on {dataset}. "
        f"See [github.com/BoggersTheFish/bozo](https://github.com/BoggersTheFish/bozo) "
        f"for training code."
    )

    card = MODEL_CARD.format(
        training_info=training_info,
        params=f"{params:,}",
        dataset=dataset,
        val_ppl=f"{val_ppl:.2f}" if isinstance(val_ppl, float) else str(val_ppl),
        window=cfg.window,
        num_layers=cfg.num_layers,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save model checkpoint under HF-conventional name
        model_path = os.path.join(tmpdir, "pytorch_model.pt")
        torch.save(ckpt, model_path)

        # Copy tokenizer
        tok_src  = ckpt["tok_path"]
        tok_dest = os.path.join(tmpdir, "tokenizer.json")
        shutil.copy(tok_src, tok_dest)

        # Save config as JSON for discoverability
        config_path = os.path.join(tmpdir, "config.json")
        with open(config_path, "w") as f:
            json.dump({"arch": arch, **cfg_dict}, f, indent=2)

        # Write model card
        card_path = os.path.join(tmpdir, "README.md")
        Path(card_path).write_text(card)

        # Create repo if needed
        api = HfApi()
        create_repo(args.repo_id, private=args.private, exist_ok=True)
        print(f"Uploading to {args.repo_id} ...")

        api.upload_folder(
            folder_path=tmpdir,
            repo_id=args.repo_id,
            commit_message=args.commit_message,
        )

    print(f"\nDone!  https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
