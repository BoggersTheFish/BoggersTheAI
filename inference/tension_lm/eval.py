"""
eval.py — evaluate a TensionLM or Transformer checkpoint on a standard benchmark
==================================================================================
Reports perplexity on WikiText-103 test set (or any custom text file).
This is the number needed for the release model card.

Usage:
    python3 eval.py --checkpoint checkpoints/tension/latest.pt
    python3 eval.py --checkpoint checkpoints/tension/latest.pt --dataset wikitext-103-raw-v1
    python3 eval.py --checkpoint checkpoints/tension/latest.pt --text_file my_test.txt
"""

import argparse
import math
import time

import torch
import torch.nn as nn


def get_args():
    p = argparse.ArgumentParser(
        description="Evaluate a TensionLM checkpoint",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--checkpoint",  required=True)
    p.add_argument("--dataset",     default="wikitext-2-raw-v1",
                   choices=["wikitext-2-raw-v1", "wikitext-103-raw-v1"])
    p.add_argument("--text_file",   default=None, help="Evaluate on a custom .txt file instead")
    p.add_argument("--split",       default="test", choices=["train", "validation", "test"])
    p.add_argument("--max_tokens",  default=None, type=int, help="Cap eval tokens (None = all)")
    p.add_argument("--batch_size",  default=16,   type=int)
    p.add_argument("--stride",      default=None, type=int,
                   help="Sliding window stride (default: seq_len = non-overlapping)")
    return p.parse_args()


def load_model(ckpt_path: str, device):
    print(f"Loading {ckpt_path} ...")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    arch = ckpt.get("arch", "tension")

    from model import TensionConfig
    cfg = TensionConfig(**ckpt["cfg"])

    if arch == "transformer":
        from baseline import TransformerLM
        model = TransformerLM(cfg)
    else:
        from model import TensionLM
        model = TensionLM(cfg)

    state = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model"].items()}
    model.load_state_dict(state)
    model.eval()
    model.to(device)

    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(ckpt["tok_path"])

    return model, tokenizer, cfg, arch, ckpt


@torch.no_grad()
def evaluate_ppl(model, token_ids: list, seq_len: int, batch_size: int,
                 stride: int, device, vocab_size: int) -> float:
    """Sliding-window perplexity — standard evaluation method."""
    import torch
    from torch.utils.data import DataLoader
    from train import TokenDataset

    ds     = TokenDataset(token_ids, seq_len, stride=stride)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, drop_last=False)

    criterion = nn.CrossEntropyLoss()
    total_loss, n = 0.0, 0

    for x, y in loader:
        x, y   = x.to(device), y.to(device)
        logits = model(x)
        loss   = criterion(logits.reshape(-1, vocab_size), y.reshape(-1))
        total_loss += loss.item()
        n          += 1

    return math.exp(min(total_loss / max(n, 1), 20))


def main():
    args   = get_args()
    device = torch.device("cpu")

    model, tokenizer, cfg, arch, ckpt = load_model(args.checkpoint, device)
    seq_len = cfg.max_seq_len
    stride  = args.stride or seq_len  # non-overlapping by default

    print(f"Architecture : {arch}")
    print(f"Parameters   : {model.num_params:,}")
    print(f"seq_len      : {seq_len}  |  stride: {stride}")
    print(f"Val PPL (train run): {ckpt.get('val_ppl', 'N/A')}")

    # ── Load text ──
    if args.text_file:
        import pathlib
        text = pathlib.Path(args.text_file).read_text(encoding="utf-8", errors="replace")
        print(f"\nEvaluating on {args.text_file} ({len(text):,} chars)")
    else:
        print(f"\nDownloading {args.dataset} [{args.split}]...")
        from datasets import load_dataset
        ds   = load_dataset("wikitext", args.dataset)
        text = "\n".join(t for t in ds[args.split]["text"] if t.strip())
        print(f"  {len(text):,} chars")

    print("Tokenising...")
    t0   = time.time()
    ids  = []
    for line in text.split("\n"):
        if line.strip():
            ids.extend(tokenizer.encode(line).ids)
        if args.max_tokens and len(ids) >= args.max_tokens:
            break
    if args.max_tokens:
        ids = ids[:args.max_tokens]
    print(f"  {len(ids):,} tokens  ({time.time()-t0:.1f}s)")

    print("\nEvaluating...")
    t0  = time.time()
    ppl = evaluate_ppl(model, ids, seq_len, args.batch_size, stride, device, cfg.vocab_size)
    print(f"\n{'─'*40}")
    print(f"  Model   : {arch}")
    print(f"  Dataset : {args.dataset if not args.text_file else args.text_file} [{args.split}]")
    print(f"  PPL     : {ppl:.2f}")
    print(f"  Time    : {time.time()-t0:.1f}s")
    print(f"{'─'*40}")


if __name__ == "__main__":
    main()
