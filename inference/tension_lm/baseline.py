"""
Baseline Transformer — fair comparison for TensionLM
======================================================
Standard causal multi-head softmax attention with the same:
  - TensionConfig  (identical hyperparameters)
  - RMSNorm, SwiGLU FFN, weight-tied LM head
  - Auxiliary loss support (same manifold/diversity API — diversity is a no-op)
  - generate() and show_tensions() compatible interfaces

The one intentional difference: full O(T²) softmax attention vs TensionLM's
windowed sigmoid tension.  Everything else is held constant so the loss curves
are a direct measure of the mechanism difference.
"""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from model import TensionConfig, RMSNorm, TensionFFN


# ── Standard Causal Self-Attention ────────────────────────────────────────────

class MultiHeadCausalAttention(nn.Module):
    """
    Standard scaled dot-product attention with a causal mask.
    Full O(T²) softmax — the direct counterpart to TensionLM's windowed sigmoid.
    Parameter count is identical: wq + wk + wv + wo = 4 × dim².
    """
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        self.num_heads = cfg.num_heads
        self.head_dim  = cfg.head_dim
        self.scale     = math.sqrt(self.head_dim)
        D              = cfg.dim

        self.wq      = nn.Linear(D, D, bias=False)
        self.wk      = nn.Linear(D, D, bias=False)
        self.wv      = nn.Linear(D, D, bias=False)
        self.wo      = nn.Linear(D, D, bias=False)
        self.norm    = RMSNorm(D)
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        H, HD   = self.num_heads, self.head_dim

        q = self.wq(x).view(B, T, H, HD).transpose(1, 2)  # B H T HD
        k = self.wk(x).view(B, T, H, HD).transpose(1, 2)
        v = self.wv(x).view(B, T, H, HD).transpose(1, 2)

        # Causal mask — upper triangle is -inf
        scores = (q @ k.transpose(-2, -1)) / self.scale          # B H T T
        mask   = torch.triu(torch.ones(T, T, device=x.device), diagonal=1).bool()
        scores = scores.masked_fill(mask.unsqueeze(0).unsqueeze(0), float("-inf"))

        attn = self.dropout(F.softmax(scores, dim=-1))
        out  = (attn @ v).transpose(1, 2).contiguous().view(B, T, D)
        return self.norm(x + self.wo(out))


# ── Transformer Block ─────────────────────────────────────────────────────────

class TransformerBlock(nn.Module):
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        self.pre_norm = RMSNorm(cfg.dim)
        self.attn     = MultiHeadCausalAttention(cfg)
        self.ffn      = TensionFFN(cfg)
        self.use_ckpt = cfg.use_grad_checkpoint

    def _impl(self, x: torch.Tensor) -> torch.Tensor:
        return self.ffn(self.attn(self.pre_norm(x)))

    def forward(self, x: torch.Tensor, return_tensions: bool = False):
        if self.use_ckpt and self.training and not return_tensions:
            from torch.utils.checkpoint import checkpoint
            out = checkpoint(self._impl, x, use_reentrant=False)
        else:
            out = self._impl(x)
        # return_tensions=True is a no-op here; kept for API compatibility
        if return_tensions:
            return out, None
        return out


# ── TransformerLM ─────────────────────────────────────────────────────────────

class TransformerLM(nn.Module):
    """
    Drop-in replacement for TensionLM.
    Same __init__ signature, forward signature, num_params property,
    and generate() / show_tensions() compatibility.
    """
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        self.cfg = cfg
        self.embedding     = nn.Embedding(cfg.vocab_size, cfg.dim)
        self.pos_embedding = nn.Embedding(cfg.max_seq_len, cfg.dim)
        self.emb_drop      = nn.Dropout(cfg.dropout)
        self.blocks        = nn.ModuleList(
            [TransformerBlock(cfg) for _ in range(cfg.num_layers)]
        )
        self.final_norm = RMSNorm(cfg.dim)
        self.lm_head    = nn.Linear(cfg.dim, cfg.vocab_size, bias=False)
        self.lm_head.weight = self.embedding.weight  # weight tying

        self._init_weights()

    def _init_weights(self):
        std   = 0.02
        depth = self.cfg.num_layers
        nn.init.normal_(self.embedding.weight,     std=std)
        nn.init.normal_(self.pos_embedding.weight, std=std)
        for name, m in self.named_modules():
            if isinstance(m, nn.Linear):
                if name.endswith(("wo", "proj")):
                    nn.init.normal_(m.weight, std=std / math.sqrt(2 * depth))
                else:
                    nn.init.xavier_uniform_(m.weight)

    def forward(self, input_ids: torch.Tensor, return_all: bool = False):
        B, T = input_ids.shape
        assert T <= self.cfg.max_seq_len, \
            f"Sequence length {T} exceeds max_seq_len {self.cfg.max_seq_len}"

        pos = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x   = self.emb_drop(self.embedding(input_ids) + self.pos_embedding(pos))

        for block in self.blocks:
            x = block(x)

        hidden = self.final_norm(x)
        logits = self.lm_head(hidden)

        if return_all:
            # Tensions are None for transformer — aux losses are skipped in train.py
            return logits, hidden, []
        return logits

    @property
    def num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())
