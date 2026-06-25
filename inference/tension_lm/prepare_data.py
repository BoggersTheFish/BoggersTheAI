"""
prepare_data.py — tokenise a large dataset into binary shards for streaming training.

Streams documents from HuggingFace (never loads the full dataset into RAM),
tokenises with BPE, and writes compact uint16 binary shards suitable for
memory-mapped training on arbitrarily large datasets.

Usage:
    # FineWeb 10B — reuse an existing tokenizer
    python3 prepare_data.py \\
        --dataset fineweb-10B \\
        --out_dir data/fineweb-10B \\
        --tokenizer checkpoints/tension_117m/tokenizer.json

    # WikiText-103 — train a fresh tokenizer from scratch
    python3 prepare_data.py \\
        --dataset wikitext-103-raw-v1 \\
        --out_dir data/wikitext103 \\
        --vocab_size 32768

    # Then train:
    python3 train.py --data_dir data/fineweb-10B --train_tokens 10_000_000_000 ...
    torchrun --nproc_per_node=2 train.py --data_dir data/fineweb-10B --train_tokens 10_000_000_000 ...

Output layout:
    data/fineweb-10B/
        train_0000.bin      # packed uint16 token IDs, ~100M tokens each (~200 MB)
        train_0001.bin
        ...
        val_0000.bin
        tokenizer.json
        metadata.json       # shard paths, token counts, split labels
"""

import argparse
import json
import os
import shutil
import time
from pathlib import Path

import numpy as np


SHARD_SIZE_DEFAULT = 100_000_000  # 100M tokens ≈ 200 MB as uint16


def get_args():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--dataset", required=True,
                   choices=["fineweb-10B", "fineweb-100B",
                            "wikitext-2-raw-v1", "wikitext-103-raw-v1"],
                   help="Dataset to tokenise")
    p.add_argument("--out_dir",         required=True,
                   help="Output directory for shards and metadata")
    p.add_argument("--tokenizer",       default=None,
                   help="Reuse an existing tokenizer.json (skips training)")
    p.add_argument("--vocab_size",      default=32768, type=int,
                   help="Vocab size when training a new BPE tokenizer")
    p.add_argument("--shard_size",      default=SHARD_SIZE_DEFAULT, type=int,
                   help="Tokens per shard file")
    p.add_argument("--tokenizer_docs",  default=500_000, type=int,
                   help="Documents sampled for tokenizer training (FineWeb only)")
    p.add_argument("--val_shards",      default=1, type=int,
                   help="Number of shards to hold out for validation (FineWeb only — "
                        "wikitext uses its own validation split)")
    return p.parse_args()


# ── Streaming document iterators ──────────────────────────────────────────────

def stream_docs(dataset: str):
    """Yield (text, split) pairs, one document at a time, streaming from HF."""
    from datasets import load_dataset

    if dataset == "fineweb-10B":
        ds = load_dataset("HuggingFaceFW/fineweb", name="sample-10BT",
                          streaming=True, split="train", trust_remote_code=True)
        for doc in ds:
            yield doc["text"], "train"

    elif dataset == "fineweb-100B":
        ds = load_dataset("HuggingFaceFW/fineweb", name="sample-100BT",
                          streaming=True, split="train", trust_remote_code=True)
        for doc in ds:
            yield doc["text"], "train"

    elif dataset in ("wikitext-2-raw-v1", "wikitext-103-raw-v1"):
        ds = load_dataset("wikitext", dataset)
        for hf_split, out_split in [("train", "train"), ("validation", "val")]:
            for row in ds[hf_split]:
                if row["text"].strip():
                    yield row["text"], out_split


# ── Tokenizer ─────────────────────────────────────────────────────────────────

def build_tokenizer(docs_iter, vocab_size: int, save_path: str):
    from tokenizers import Tokenizer
    from tokenizers.models import BPE
    from tokenizers.trainers import BpeTrainer
    from tokenizers.pre_tokenizers import ByteLevel
    from tokenizers.decoders import ByteLevel as ByteLevelDecoder

    tok = Tokenizer(BPE(unk_token="<unk>"))
    tok.pre_tokenizer = ByteLevel()
    tok.decoder       = ByteLevelDecoder()
    trainer = BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=["<pad>", "<bos>", "<eos>", "<unk>"],
        min_frequency=2,
        show_progress=True,
    )
    tok.train_from_iterator(docs_iter, trainer=trainer)
    tok.save(save_path)
    print(f"Tokenizer saved → {save_path}  (vocab={tok.get_vocab_size()})")
    return tok


# ── Shard writer ──────────────────────────────────────────────────────────────

def flush_shard(tokens: list, out_dir: Path, idx: int, split: str) -> dict:
    path = out_dir / f"{split}_{idx:04d}.bin"
    np.array(tokens, dtype=np.uint16).tofile(str(path))
    return {"split": split, "path": str(path), "tokens": len(tokens)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args    = get_args()
    out     = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tok_dst = str(out / "tokenizer.json")

    # ── Tokenizer ──
    if args.tokenizer:
        from tokenizers import Tokenizer
        if os.path.abspath(args.tokenizer) != os.path.abspath(tok_dst):
            shutil.copy(args.tokenizer, tok_dst)
        tokenizer = Tokenizer.from_file(tok_dst)
        print(f"Tokenizer loaded from {args.tokenizer}  "
              f"(vocab={tokenizer.get_vocab_size()})")
    else:
        print(f"Sampling {args.tokenizer_docs:,} docs for tokenizer training...")
        sample = []
        for text, _ in stream_docs(args.dataset):
            sample.append(text)
            if len(sample) >= args.tokenizer_docs:
                break
        tokenizer = build_tokenizer(iter(sample), args.vocab_size, tok_dst)
        del sample

    # ── Shard ──
    print(f"\nSharding '{args.dataset}' → {out}")
    print(f"  shard size: {args.shard_size/1e6:.0f}M tokens  "
          f"≈ {args.shard_size * 2 / 1e6:.0f} MB each\n")

    shards: list[dict] = []
    bufs   = {"train": [], "val": []}
    idxs   = {"train": 0,  "val": 0}
    total_tokens = 0
    t0 = time.time()

    for doc_i, (text, split) in enumerate(stream_docs(args.dataset)):
        bufs[split].extend(tokenizer.encode(text).ids)

        for sp in ("train", "val"):
            while len(bufs[sp]) >= args.shard_size:
                meta = flush_shard(bufs[sp][:args.shard_size], out, idxs[sp], sp)
                bufs[sp] = bufs[sp][args.shard_size:]
                shards.append(meta)
                total_tokens += meta["tokens"]
                idxs[sp] += 1
                elapsed = time.time() - t0
                print(f"  {meta['path'].split('/')[-1]}  "
                      f"total {total_tokens/1e9:.2f}B tokens  ({elapsed:.0f}s)")

    # Flush remaining tokens
    for sp in ("train", "val"):
        if bufs[sp]:
            meta = flush_shard(bufs[sp], out, idxs[sp], sp)
            shards.append(meta)
            total_tokens += meta["tokens"]
            idxs[sp] += 1

    # FineWeb has no built-in val split — promote last N train shards to val
    if args.dataset.startswith("fineweb"):
        train_shards = [s for s in shards if s["split"] == "train"]
        for meta in train_shards[-args.val_shards:]:
            old = Path(meta["path"])
            new = old.parent / old.name.replace("train_", "val_")
            old.rename(new)
            meta["path"]  = str(new)
            meta["split"] = "val"

    # ── Metadata ──
    train_tokens = sum(s["tokens"] for s in shards if s["split"] == "train")
    val_tokens   = sum(s["tokens"] for s in shards if s["split"] == "val")
    metadata = {
        "dataset":      args.dataset,
        "vocab_size":   tokenizer.get_vocab_size(),
        "tokenizer":    tok_dst,
        "total_tokens": total_tokens,
        "train_tokens": train_tokens,
        "val_tokens":   val_tokens,
        "shards":       shards,
    }
    meta_path = out / "metadata.json"
    json.dump(metadata, open(meta_path, "w"), indent=2)

    elapsed = time.time() - t0
    n_train = len([s for s in shards if s["split"] == "train"])
    n_val   = len([s for s in shards if s["split"] == "val"])
    print(f"\nDone in {elapsed/60:.1f} min")
    print(f"  {n_train} train shards  ({train_tokens/1e9:.2f}B tokens)")
    print(f"  {n_val} val shards    ({val_tokens/1e9:.2f}B tokens)")
    print(f"  Metadata → {meta_path}")
    print(f"\nTo train:")
    print(f"  python3 train.py --data_dir {out} --train_tokens {train_tokens} ...")
    print(f"  torchrun --nproc_per_node=2 train.py "
          f"--data_dir {out} --train_tokens {train_tokens} ...")


if __name__ == "__main__":
    main()
