"""
TensionLM — model definition
=============================
Sigmoid tension graph architecture.  No softmax competition between tokens.

    tau[t, h, w] = sigmoid( dot(q[t,h], k[t-w-1, h]) / sqrt(head_dim) )
    out[t]       = W_o ( concat_h  sum_w  tau[t,h,w] * v[t-w-1, h] )

Each token pair is scored independently — a token can be pulled hard by all
its neighbours or none.  No zero-sum weight budget.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint as _grad_checkpoint


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class TensionConfig:
    # vocab=2048 keeps the LM-head output tensor at 16 MB (vs 64 MB for 8192),
    # which is the dominant cost on memory-bandwidth-limited CPUs.
    # For better coverage (larger text) use vocab=4096 or 8192 if you have a GPU.
    vocab_size:          int   = 2048
    # Architecture — defaults tuned for Pentium-class CPUs (8 GB RAM).
    # Quality preset: --dim 256 --num_layers 6 --window 16 (much slower).
    dim:                 int   = 128
    num_layers:          int   = 4
    num_heads:           int   = 4
    window:              int   = 8     # causal look-back window per layer
    ffn_mult:            int   = 3     # SwiGLU hidden = dim * ffn_mult
    max_seq_len:         int   = 256
    dropout:             float = 0.10
    use_grad_checkpoint: bool  = False

    @property
    def head_dim(self) -> int:
        assert self.dim % self.num_heads == 0, "dim must be divisible by num_heads"
        return self.dim // self.num_heads


# ── Normalisation ─────────────────────────────────────────────────────────────

class RMSNorm(nn.Module):
    """Root Mean Square Normalisation — faster than LayerNorm, no mean shift."""
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps   = eps
        self.scale = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # F.rms_norm is a single fused kernel on PyTorch 2.4+; fallback otherwise.
        if hasattr(F, "rms_norm"):
            return F.rms_norm(x, x.shape[-1:], self.scale, self.eps)
        rms = x.pow(2).mean(-1, keepdim=True).add(self.eps).rsqrt()
        return x * rms * self.scale


# ── Core: Multi-Head Causal Tension Layer ─────────────────────────────────────

class MultiHeadCausalTensionLayer(nn.Module):
    """
    Vectorised causal tension with multiple heads.

    Tension replaces softmax with independent sigmoid scores, so the total
    pull on token t across all window positions and heads is unbounded —
    the model learns which relationships matter without forcing competition.
    """
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        self.window    = cfg.window
        self.num_heads = cfg.num_heads
        self.head_dim  = cfg.head_dim
        self.scale     = math.sqrt(self.head_dim)
        D              = cfg.dim

        self.wq      = nn.Linear(D, D, bias=False)
        self.wkv     = nn.Linear(D, D * 2, bias=False)  # k and v fused — one matmul
        self.wo      = nn.Linear(D, D, bias=False)
        self.norm    = RMSNorm(D)
        self.dropout = nn.Dropout(cfg.dropout)

    def _gather_window(self, z: torch.Tensor, T: int) -> torch.Tensor:
        """
        Vectorised causal window gather — no Python loops over T or W.
        z: B T H C  →  B T H W C
        result[b, t, h, w, :] = z[b, t-W+w, h, :]  (zero for out-of-bounds)
        w=0 is oldest token in window; w=W-1 is most recent.
        Avoids .flip() and .contiguous() — saves two large tensor copies (~800 MB
        at large config). torch.compile fuses the permute into downstream ops.
        """
        W  = self.window
        zt = z.permute(0, 2, 3, 1)                     # B H C T
        zp = F.pad(zt, (W, 0), value=0.0)              # B H C (T+W)
        nb = zp.unfold(-1, W, 1)[:, :, :, :T, :]       # B H C T W  (no flip)
        return nb.permute(0, 3, 1, 4, 2).contiguous() # B T H W C

    def forward(
        self,
        x: torch.Tensor,
        return_tensions: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        B, T, D = x.shape
        HD = self.head_dim

        q  = self.wq(x).view(B, T, self.num_heads, HD)
        kv = self.wkv(x).view(B, T, self.num_heads, HD * 2)

        nb_kv      = self._gather_window(kv, T)       # B T H W 2*HD
        nb_k, nb_v = nb_kv.split(HD, dim=-1)          # B T H W HD each

        # Independent sigmoid per pair — no softmax, no competition
        tau = torch.sigmoid(
            (q.unsqueeze(3) * nb_k).sum(-1) / self.scale  # B T H W
        )
        tau = self.dropout(tau)

        msg = (tau.unsqueeze(-1) * nb_v).sum(3)           # B T H HD
        out = self.norm(x + self.wo(msg.reshape(B, T, D)))

        if return_tensions:
            return out, tau
        return out


# ── Oscillatory Modulation ────────────────────────────────────────────────────

class OscillatoryModulation(nn.Module):
    """
    Learned per-channel sinusoidal positional modulation.
    Each of the D channels gets its own trainable frequency and phase,
    acting as a soft wave-based positional signal trained end-to-end.
    Amplitude starts near zero and grows only as needed.
    pos_buf is a non-persistent buffer — avoids torch.arange on every forward pass.
    """
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        self.freqs  = nn.Parameter(torch.randn(cfg.dim) * 0.02)
        self.phases = nn.Parameter(torch.zeros(cfg.dim))
        self.amp    = nn.Parameter(torch.full((1,), 0.1))
        pos = torch.arange(cfg.max_seq_len, dtype=torch.float).unsqueeze(-1)  # S 1
        self.register_buffer("pos_buf", pos, persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        pos = self.pos_buf[:T]                                  # T 1
        mod = torch.sin(pos * self.freqs + self.phases)         # T D
        return x * (1.0 + self.amp * mod.unsqueeze(0))


# ── SwiGLU Feed-Forward ───────────────────────────────────────────────────────

class TensionFFN(nn.Module):
    """Gated feed-forward with SwiGLU activation (as used in LLaMA/PaLM)."""
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        hidden    = cfg.dim * cfg.ffn_mult
        self.gate = nn.Linear(cfg.dim, hidden, bias=False)
        self.val  = nn.Linear(cfg.dim, hidden, bias=False)
        self.proj = nn.Linear(hidden, cfg.dim, bias=False)
        self.norm    = RMSNorm(cfg.dim)
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.silu(self.gate(x)) * self.val(x)
        return self.norm(x + self.dropout(self.proj(h)))


# ── Tension Block ─────────────────────────────────────────────────────────────

class TensionBlock(nn.Module):
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        self.pre_norm  = RMSNorm(cfg.dim)
        self.tension   = MultiHeadCausalTensionLayer(cfg)
        self.oscillate = OscillatoryModulation(cfg)
        self.ffn       = TensionFFN(cfg)
        self.use_ckpt  = cfg.use_grad_checkpoint

    def _impl_no_tensions(self, x: torch.Tensor) -> torch.Tensor:
        return self.ffn(self.oscillate(self.tension(self.pre_norm(x))))

    def _impl(
        self, x: torch.Tensor, return_tensions: bool = False
    ) -> torch.Tensor | tuple:
        h = self.pre_norm(x)
        if return_tensions:
            h, tau = self.tension(h, return_tensions=True)
            return self.ffn(self.oscillate(h)), tau
        return self.ffn(self.oscillate(self.tension(h)))

    def forward(
        self, x: torch.Tensor, return_tensions: bool = False
    ) -> torch.Tensor | tuple:
        # Gradient checkpointing trades compute for memory (~30% slower, ~40% less RAM).
        # Uses a tensions-free path when checkpointing to avoid tuple return issues.
        if self.use_ckpt and self.training:
            if return_tensions:
                # Checkpoint the block forward for memory savings, then recompute
                # tensions separately from the same input for the aux loss.
                out = _grad_checkpoint(self._impl_no_tensions, x, use_reentrant=False)
                _, tau = self.tension(self.pre_norm(x), return_tensions=True)
                return out, tau
            return _grad_checkpoint(self._impl_no_tensions, x, use_reentrant=False)
        return self._impl(x, return_tensions)


# ── TensionLM ─────────────────────────────────────────────────────────────────

class TensionLM(nn.Module):
    def __init__(self, cfg: TensionConfig):
        super().__init__()
        self.cfg = cfg
        self.embedding     = nn.Embedding(cfg.vocab_size, cfg.dim)
        self.pos_embedding = nn.Embedding(cfg.max_seq_len, cfg.dim)
        self.emb_drop      = nn.Dropout(cfg.dropout)
        self.blocks        = nn.ModuleList(
            [TensionBlock(cfg) for _ in range(cfg.num_layers)]
        )
        self.final_norm = RMSNorm(cfg.dim)
        self.lm_head    = nn.Linear(cfg.dim, cfg.vocab_size, bias=False)
        self.lm_head.weight = self.embedding.weight  # weight tying

        # Non-persistent buffer — avoids torch.arange on every forward pass.
        pos = torch.arange(cfg.max_seq_len).unsqueeze(0)  # 1 S
        self.register_buffer("pos_buf", pos, persistent=False)

        self._init_weights()

    def _init_weights(self):
        std   = 0.02
        depth = self.cfg.num_layers
        nn.init.normal_(self.embedding.weight,     std=std)
        nn.init.normal_(self.pos_embedding.weight, std=std)
        for name, m in self.named_modules():
            if isinstance(m, nn.Linear):
                # Scale output projections by depth (GPT-2 init, stabilises deep nets)
                if name.endswith(("wo", "proj")):
                    nn.init.normal_(m.weight, std=std / math.sqrt(2 * depth))
                else:
                    nn.init.xavier_uniform_(m.weight)

    def forward(
        self,
        input_ids:  torch.Tensor,
        return_all: bool = False,
    ):
        """
        input_ids : LongTensor [B, T]
        return_all: if True, returns (logits, hidden, all_tensions)
                    where all_tensions is a list of [B, T, H, W] per layer.
                    All three share one computation graph.
        """
        B, T = input_ids.shape
        assert T <= self.cfg.max_seq_len, \
            f"Sequence length {T} exceeds max_seq_len {self.cfg.max_seq_len}"

        x   = self.emb_drop(self.embedding(input_ids) + self.pos_embedding(self.pos_buf[:, :T]))

        all_tensions = []
        for block in self.blocks:
            if return_all:
                x, tau = block(x, return_tensions=True)
                all_tensions.append(tau)
            else:
                x = block(x)

        hidden = self.final_norm(x)
        logits = self.lm_head(hidden)

        if return_all:
            return logits, hidden, all_tensions
        return logits

    @property
    def num_params(self) -> int:
        return sum(p.numel() for p in self.parameters())


# ── Auxiliary Losses ──────────────────────────────────────────────────────────

def manifold_closure_loss(hidden: torch.Tensor) -> torch.Tensor:
    """
    The sequence's final hidden state should be geometrically coherent
    with its first.  Encourages the model to embed sequences onto a
    closed manifold.  Gradients flow only through the final position.
    """
    return F.mse_loss(hidden[:, -1], hidden[:, 0].detach())


def tension_diversity_loss(all_tensions: list[torch.Tensor]) -> torch.Tensor:
    """
    Penalise low-entropy tension distributions per head.
    Encourages each head to spread attention across the window rather
    than collapsing onto one dominant position.
    Returns 0 when called on a baseline model with no tension layers.
    """
    if not all_tensions:
        return torch.tensor(0.0)
    # Stack layers → single fused kernel instead of L sequential kernels
    tau  = torch.stack(all_tensions)              # L B T H W
    W    = tau.shape[-1]
    p    = tau / (tau.sum(-1, keepdim=True) + 1e-8)
    ent  = -(p * torch.log(p + 1e-8)).sum(-1)     # L B T H
    return F.relu(math.log(W) - ent.mean()).mean()


# ── Generation ────────────────────────────────────────────────────────────────

@torch.no_grad()
def generate(
    model:       TensionLM,
    input_ids:   list[int],
    max_new:     int   = 200,
    temp:        float = 0.8,
    top_p:       float = 0.92,
    rep_penalty: float = 1.3,
) -> list[int]:
    """Auto-regressive generation with top-p nucleus sampling."""
    model.eval()
    ids     = list(input_ids)
    max_ctx = model.cfg.max_seq_len

    for _ in range(max_new):
        ctx    = torch.tensor([ids[-max_ctx:]], dtype=torch.long)
        logits = model(ctx)[0, -1].float()

        # Repetition penalty over the last 32 tokens
        for tok in set(ids[-32:]):
            if logits[tok] > 0:
                logits[tok] /= rep_penalty
            else:
                logits[tok] *= rep_penalty

        logits = logits / max(temp, 1e-5)
        probs  = F.softmax(logits, dim=-1)
        sorted_p, sorted_i = torch.sort(probs, descending=True)
        cum_p  = torch.cumsum(sorted_p, dim=-1)
        mask   = (cum_p - sorted_p) < top_p
        sorted_p[~mask] = 0.0
        sorted_p /= sorted_p.sum()
        next_id = sorted_i[torch.multinomial(sorted_p, 1).item()].item()
        ids.append(next_id)

    return ids


# ── Tension Visualiser ────────────────────────────────────────────────────────

def show_tensions(model: TensionLM, tokenizer, text: str, layer: int = 0):
    """Print a human-readable map of what each token is pulled toward."""
    model.eval()
    enc  = tokenizer.encode(text)
    ids  = enc.ids
    toks = [tokenizer.id_to_token(i) or "?" for i in ids]

    with torch.no_grad():
        _, _, all_tensions = model(
            torch.tensor([ids], dtype=torch.long), return_all=True
        )

    tau     = all_tensions[layer][0]   # T H W
    tau_avg = tau.mean(dim=1)          # T W
    W       = model.cfg.window

    print(f"\nTension field — layer {layer + 1} — '{text}'")
    print("─" * 60)
    for t, tok in enumerate(toks):
        if t == 0:
            print(f"  {tok:<16}  (no causal history)")
            continue
        parts = []
        for w in range(min(W, t)):
            src = toks[t - w - 1]
            val = tau_avg[t, w].item()
            bar = "▓" * max(1, round(val * 10))
            parts.append(f"{src}:{val:.2f}{bar}")
        print(f"  {tok:<16} ← {' | '.join(parts)}")
