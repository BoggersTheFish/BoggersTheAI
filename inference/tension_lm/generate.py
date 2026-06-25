"""
TensionLM generation CLI
=========================
Load a trained checkpoint and generate text.

Single prompt:
    python generate.py --checkpoint checkpoints/latest.pt --prompt "The cat"

Interactive mode (no --prompt):
    python generate.py --checkpoint checkpoints/latest.pt

Tune sampling:
    python generate.py --checkpoint checkpoints/latest.pt --temp 0.7 --top_p 0.85
"""

import argparse
import sys

import torch

from model import TensionConfig, TensionLM, generate as _generate, show_tensions


def get_args():
    p = argparse.ArgumentParser(
        description="TensionLM text generation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--checkpoint",  required=True, help="Path to .pt checkpoint")
    p.add_argument("--prompt",      default=None,  nargs="+", help="Input prompt (interactive if omitted)")
    p.add_argument("--max_new",     default=200,   type=int,   help="Max tokens to generate")
    p.add_argument("--temp",        default=0.80,  type=float, help="Sampling temperature (lower = more conservative)")
    p.add_argument("--top_p",       default=0.92,  type=float, help="Nucleus sampling probability")
    p.add_argument("--rep_penalty", default=1.30,  type=float, help="Repetition penalty (1.0 = off)")
    p.add_argument("--show_tension",action="store_true",       help="Show tension field for each prompt")
    p.add_argument("--layer",       default=0,     type=int,   help="Layer to visualise tensions for")
    return p.parse_args()


def load_model_and_tokenizer(ckpt_path: str):
    print(f"Loading {ckpt_path} ...")
    ckpt  = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    cfg   = TensionConfig(**ckpt["cfg"])
    arch  = ckpt.get("arch", "tension")

    if arch == "transformer":
        from baseline import TransformerLM
        model = TransformerLM(cfg)
    else:
        model = TensionLM(cfg)

    # Strip _orig_mod. prefix present when checkpoint was saved from a compiled model
    state = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model"].items()}
    model.load_state_dict(state)
    model.eval()

    tok_path = ckpt["tok_path"]
    try:
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_file(tok_path)
    except Exception as e:
        sys.exit(f"Could not load tokenizer from {tok_path}: {e}")

    return model, tokenizer, ckpt


def do_generate(model, tokenizer, prompt: str, args) -> str:
    enc     = tokenizer.encode(prompt)
    ids_out = _generate(
        model, enc.ids,
        max_new=args.max_new,
        temp=args.temp,
        top_p=args.top_p,
        rep_penalty=args.rep_penalty,
    )
    return tokenizer.decode(ids_out)


def print_model_info(model, ckpt):
    cfg = model.cfg
    np  = model.num_params
    ppl = ckpt.get("val_ppl", "?")
    ppl_str = f"{ppl:.2f}" if isinstance(ppl, float) else str(ppl)
    print(f"Model  : {np:,} params  |  val ppl {ppl_str}")
    print(f"Config : dim={cfg.dim}  layers={cfg.num_layers}  heads={cfg.num_heads}  "
          f"window={cfg.window}  vocab={cfg.vocab_size}")
    print(f"Step   : {ckpt.get('step', '?')}")
    print()


def main():
    args = get_args()
    model, tokenizer, ckpt = load_model_and_tokenizer(args.checkpoint)
    print_model_info(model, ckpt)

    if args.prompt:
        args.prompt = " ".join(args.prompt)
        result = do_generate(model, tokenizer, args.prompt, args)
        print(result)
        if args.show_tension:
            show_tensions(model, tokenizer, args.prompt, layer=args.layer)
        return

    # Interactive mode
    print("Interactive generation  (empty line to quit)")
    print(f"temp={args.temp}  top_p={args.top_p}  rep_penalty={args.rep_penalty}  max_new={args.max_new}")
    print("─" * 60)
    while True:
        try:
            prompt = input("\nPrompt> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not prompt:
            break
        result = do_generate(model, tokenizer, prompt, args)
        print(f"\n{result}")
        if args.show_tension:
            show_tensions(model, tokenizer, prompt, layer=args.layer)


if __name__ == "__main__":
    main()
