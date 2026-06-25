"""
TensionLM
=========
A language model built on CausalTensionGraphs instead of self-attention.

Core philosophy:
    Tokens don't "attend" to each other via softmax competition.
    Instead, each token exerts "tension" on its local neighborhood —
    a learned, sigmoid-gated pull that aggregates context like nodes
    in a dynamic graph where edge strength is content-aware.

    Tension score: sigmoid( dot(current, neighbor) / √head_dim )
    This differs from attention in a fundamental way:
      - Attention:  softmax across positions → values must compete,
                    the total weight always sums to 1.
      - Tension:    independent sigmoid per pair → a token can be
                    pulled hard by ALL neighbors or none. There is
                    no zero-sum competition.

    The model learns which pairs of tokens should "pull" on each other,
    regardless of who else is in the context.

Architecture:
    Embedding + LearnedPositional
    → N × TensionBlock:
        MultiHeadCausalTensionLayer  (local graph message passing)
        OscillatoryModulation        (learnable wave-based position signal)
        SwiGLU FFN                   (gated nonlinear mixing)
    → LayerNorm → LM head (weight-tied to embedding)

Training signal (all losses share one computation graph — no bugs):
    CrossEntropy            (next-token prediction)
    ManifoldClosureLoss     (first / last hidden state coherence)
    TensionDiversityLoss    (heads should spread tension, not collapse)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import math

# ── Corpus & Vocabulary ──────────────────────────────────────────────────────

CORPUS = """
the cat sat on the mat the dog ran away and then the cat chased the bird
the fox jumped over the fence the brown fox ate the fish the lazy dog drank milk
the quick cat played with the ball the happy bird flew high above the tree
the house was small but warm the slow fox watched the fast cat run past
the dog barked loud and the bird flew away into the sky above the hill
the cat slept by the fire while the dog watched the door all night long
a big fish swam under the bridge and the bird sat on the rail above
the fox and the cat played in the yard while the dog chased a ball
the tree grew tall and its branches reached over the old stone wall
rain fell soft on the roof and the cat watched from the window sill
the dog and the fox ran across the field as the sun went down low
a loud bird sang from the top of the tree while the cat listened below
the small house had a big yard with a tall fence all around it
the fish in the pond swam fast when the dog ran close to the edge
the cat and the bird sat on the mat while the fox slept under the tree
the fox crept low through the long grass toward the sleeping bird
the dog lifted its head and sniffed the cold air near the old gate
a small bird landed on the branch above the fox and sang once then flew
the cat watched the rain fall on the stone path outside the door
the old tree by the wall had one branch that hung over the pond
the dog slept near the fire while the cat sat high on the shelf above
the fox trotted past the house and into the field beyond the gate
the bird flew in a wide circle above the field before landing again
the fish swam slow near the bottom where the water was cold and dark
the cat jumped down from the shelf and walked past the sleeping dog
""".strip()


def build_vocab(text: str):
    words  = text.split()
    unique = sorted(set(words))
    w2i    = {w: i for i, w in enumerate(unique)}
    i2w    = {i: w for i, w in enumerate(unique)}
    return w2i, i2w, len(unique)


word_to_idx, idx_to_word, VOCAB_SIZE = build_vocab(CORPUS)
corpus_ids = [word_to_idx[w] for w in CORPUS.split()]


# ── Multi-Head Causal Tension Layer ──────────────────────────────────────────

class MultiHeadCausalTensionLayer(nn.Module):
    """
    For each token t, looks back at up to `window` previous tokens.

    Each head independently computes tension scores — how strongly the
    current token is drawn toward each past neighbor — then aggregates
    neighbor values weighted by those tensions.

    Tension = sigmoid( dot(q_t, k_{t-w}) / √head_dim )

    This is like scaled dot-product attention but with sigmoid instead
    of softmax. The distinction is load-bearing: sigmoid scores are
    independent — the total pull on token t can be 0, 4, or anything
    in between, depending on what's in the context. No competition.
    """
    def __init__(self, dim: int, window: int = 8, num_heads: int = 4):
        super().__init__()
        assert dim % num_heads == 0
        self.window    = window
        self.num_heads = num_heads
        self.head_dim  = dim // num_heads
        self.scale     = math.sqrt(self.head_dim)

        self.wq  = nn.Linear(dim, dim, bias=False)
        self.wkv = nn.Linear(dim, dim * 2, bias=False)  # k and v fused — one matmul
        self.wo  = nn.Linear(dim, dim, bias=False)
        self.norm = nn.LayerNorm(dim)

    def _gather_window(self, z: torch.Tensor, T: int) -> torch.Tensor:
        """
        Vectorised causal window gather.
        z: B T H C  →  B T H W C  (C = HD or 2×HD)
        result[:, t, :, w, :] = z[:, t-w-1, :, :] for w < t, else zeros.
        Uses pad + unfold — no Python loops over T or W.
        """
        W  = self.window
        zt = z.permute(0, 2, 3, 1)                              # B H C T
        zp = F.pad(zt, (W, 0), value=0.0)                       # B H C (T+W)
        nb = zp.unfold(-1, W, 1)[:, :, :, :T, :].flip(-1)      # B H C T W
        return nb.permute(0, 3, 1, 4, 2)                        # B T H W C

    def forward(self, x: torch.Tensor, return_tensions: bool = False):
        B, T, D = x.shape
        HD = self.head_dim

        q  = self.wq(x).view(B, T, self.num_heads, HD)
        kv = self.wkv(x).view(B, T, self.num_heads, HD * 2)

        # Single gather for k+v together — one unfold instead of two
        nb_kv        = self._gather_window(kv, T)   # B T H W 2*HD
        nb_k, nb_v   = nb_kv.split(HD, dim=-1)      # B T H W HD each
        k, v         = kv.split(HD, dim=-1)          # B T H HD each (unused k for clarity)

        # Tension: sigmoid scaled dot product — no softmax, no competition
        # q[:, t, h, :] · nb_k[:, t, h, w, :] → scalar per (t, h, w)
        tau = torch.sigmoid(
            (q.unsqueeze(3) * nb_k).sum(-1) / self.scale   # B T H W
        )


        # Aggregate neighbor values weighted by tension
        msg = (tau.unsqueeze(-1) * nb_v).sum(3)             # B T H HD
        out = self.norm(x + self.wo(msg.reshape(B, T, D)))

        if return_tensions:
            return out, tau   # tau: B T H W
        return out


# ── Oscillatory Positional Modulation ────────────────────────────────────────

class OscillatoryModulation(nn.Module):
    """
    Learned per-channel sinusoidal modulation indexed by token position.

    Each channel gets its own frequency and phase — free parameters the
    model can tune. Acts as a soft, wave-based positional signal layered
    on top of learned position embeddings, giving the model a second way
    to encode position that can vary in rhythm per channel.

    Unlike fixed sinusoidal encodings (Transformer), these waves are
    trained end-to-end and can specialize per layer.
    """
    def __init__(self, dim: int):
        super().__init__()
        self.freqs  = nn.Parameter(torch.randn(dim) * 0.02)
        self.phases = nn.Parameter(torch.zeros(dim))
        self.amp    = nn.Parameter(torch.full((1,), 0.1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        pos = torch.arange(T, device=x.device).float().unsqueeze(-1)  # T 1
        mod = torch.sin(pos * self.freqs + self.phases)                # T D
        return x * (1.0 + self.amp * mod.unsqueeze(0))


# ── SwiGLU Feed-Forward ───────────────────────────────────────────────────────

class TensionFFN(nn.Module):
    """Gated feed-forward with SwiGLU activation."""
    def __init__(self, dim: int, expansion: int = 3):
        super().__init__()
        hidden    = dim * expansion
        self.gate = nn.Linear(dim, hidden, bias=False)
        self.val  = nn.Linear(dim, hidden, bias=False)
        self.proj = nn.Linear(hidden, dim, bias=False)
        self.norm = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.norm(x + self.proj(F.silu(self.gate(x)) * self.val(x)))


# ── Tension Block ─────────────────────────────────────────────────────────────

class TensionBlock(nn.Module):
    def __init__(self, dim: int, window: int = 8, num_heads: int = 4):
        super().__init__()
        self.pre_norm  = nn.LayerNorm(dim)
        self.tension   = MultiHeadCausalTensionLayer(dim, window, num_heads)
        self.oscillate = OscillatoryModulation(dim)
        self.ffn       = TensionFFN(dim)

    def forward(self, x: torch.Tensor, return_tensions: bool = False):
        h = self.pre_norm(x)
        if return_tensions:
            h, tau = self.tension(h, return_tensions=True)
            return self.ffn(self.oscillate(h)), tau
        return self.ffn(self.oscillate(self.tension(h)))


# ── TensionLM ─────────────────────────────────────────────────────────────────

class TensionLM(nn.Module):
    def __init__(
        self,
        vocab_size:  int,
        dim:         int = 64,
        num_layers:  int = 4,
        window:      int = 8,
        num_heads:   int = 4,
        max_seq_len: int = 256,
    ):
        super().__init__()
        self.embedding     = nn.Embedding(vocab_size, dim)
        self.pos_embedding = nn.Embedding(max_seq_len, dim)
        self.blocks        = nn.ModuleList([
            TensionBlock(dim, window, num_heads) for _ in range(num_layers)
        ])
        self.final_norm = nn.LayerNorm(dim)
        self.lm_head    = nn.Linear(dim, vocab_size, bias=False)
        self.lm_head.weight = self.embedding.weight  # weight tying

        self._init_weights()

    def _init_weights(self):
        nn.init.normal_(self.embedding.weight, std=0.02)
        nn.init.normal_(self.pos_embedding.weight, std=0.02)
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)

    def forward(self, input_ids: torch.Tensor, return_all: bool = False):
        """
        return_all=True → (logits, hidden, all_tensions)
          hidden       : final normalised hidden states  [B, T, D]
          all_tensions : list of [B, T, H, W] per layer
        All three share one computation graph — aux losses backprop correctly.
        """
        B, T = input_ids.shape
        pos  = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x    = self.embedding(input_ids) + self.pos_embedding(pos)

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


# ── Auxiliary Losses ──────────────────────────────────────────────────────────

def manifold_closure_loss(hidden: torch.Tensor) -> torch.Tensor:
    """
    The sequence's final hidden state should be coherent with its first.
    Encourages the model to embed sequences onto a closed manifold:
    the 'story' should arrive somewhere related to where it started.
    Anchor (position 0) is detached — gradients flow only through position T.
    """
    return F.mse_loss(hidden[:, -1], hidden[:, 0].detach())


def tension_diversity_loss(all_tensions: list) -> torch.Tensor:
    """
    Penalise low-entropy tension distributions per head.
    Each head should spread its tension across the window rather than
    collapsing onto a single dominant position. Encourages specialisation.
    """
    device = all_tensions[0].device
    total  = torch.tensor(0.0, device=device)
    for tau in all_tensions:             # B T H W
        _, _, _, W = tau.shape
        p       = tau / (tau.sum(-1, keepdim=True) + 1e-8)
        entropy = -(p * torch.log(p + 1e-8)).sum(-1)   # B T H
        deficit = F.relu(math.log(W) - entropy.mean())
        total   = total + deficit
    return total / len(all_tensions)


# ── Dataset ───────────────────────────────────────────────────────────────────

SEQ_LEN    = 16
STRIDE     = 3
DIM        = 64
NUM_LAYERS = 4
WINDOW     = 8
NUM_HEADS  = 4
EPOCHS     = 50   # ~8s/epoch on CPU; increase to 150+ for better generation


def make_dataset(ids, seq_len=SEQ_LEN, stride=STRIDE):
    """Return (inputs, targets) tensors — all sequences stacked into one batch."""
    seqs = [
        ids[i : i + seq_len + 1]
        for i in range(0, len(ids) - seq_len, stride)
        if len(ids[i : i + seq_len + 1]) == seq_len + 1
    ]
    data   = torch.tensor(seqs, dtype=torch.long)   # N × (seq_len+1)
    inputs  = data[:, :-1]                          # N × seq_len
    targets = data[:, 1:]                           # N × seq_len
    return inputs, targets


# ── Training ──────────────────────────────────────────────────────────────────

model   = TensionLM(VOCAB_SIZE, DIM, NUM_LAYERS, WINDOW, NUM_HEADS, max_seq_len=64)
inputs, targets = make_dataset(corpus_ids)
n_seqs   = inputs.shape[0]
n_params = sum(p.numel() for p in model.parameters())

print(f"Vocab: {VOCAB_SIZE}  |  Corpus: {len(corpus_ids)} tokens")
print(f"Parameters: {n_params:,}  |  Training sequences: {n_seqs}")
print(f"Training {EPOCHS} epochs (full-batch, all {n_seqs} sequences per step)...")

optimizer = optim.AdamW(model.parameters(), lr=3e-3, weight_decay=0.01)
scheduler = optim.lr_scheduler.CosineAnnealingLR(
    optimizer, T_max=EPOCHS, eta_min=5e-5
)
criterion = nn.CrossEntropyLoss()

for epoch in range(1, EPOCHS + 1):
    model.train()
    optimizer.zero_grad()

    # Single forward pass over the entire dataset — all losses share the graph
    logits, hidden, all_tensions = model(inputs, return_all=True)

    loss_ce   = criterion(logits.reshape(-1, VOCAB_SIZE), targets.reshape(-1))
    loss_attr = manifold_closure_loss(hidden)
    loss_div  = tension_diversity_loss(all_tensions)

    loss = loss_ce + 0.05 * loss_attr + 0.02 * loss_div
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    scheduler.step()

    if epoch % 10 == 0:
        lr = scheduler.get_last_lr()[0]
        print(
            f"Epoch {epoch:3d}  "
            f"CE: {loss_ce.item():.4f}  "
            f"Closure: {loss_attr.item():.4f}  "
            f"Diversity: {loss_div.item():.4f}  "
            f"lr: {lr:.2e}"
        )


# ── Generation ────────────────────────────────────────────────────────────────

def top_p_sample(logits: torch.Tensor, p: float = 0.9, temp: float = 1.0) -> int:
    """Nucleus (top-p) sampling with temperature."""
    logits = logits / temp
    probs  = F.softmax(logits, dim=-1)
    sorted_probs, sorted_idx = torch.sort(probs, descending=True)
    cumprobs = torch.cumsum(sorted_probs, dim=-1)
    mask = (cumprobs - sorted_probs) < p
    sorted_probs[~mask] = 0.0
    sorted_probs /= sorted_probs.sum()
    return sorted_idx[torch.multinomial(sorted_probs, 1).item()].item()


def generate(
    model,
    prompt:  str,
    max_new: int   = 40,
    temp:    float = 0.85,
    top_p:   float = 0.92,
) -> str:
    model.eval()
    ids = [word_to_idx.get(w, 0) for w in prompt.split()]
    with torch.no_grad():
        for _ in range(max_new):
            ctx    = torch.tensor([ids[-32:]], dtype=torch.long)
            logits = model(ctx)[:, -1, :]
            for prev in set(ids[-5:]):   # light repetition penalty
                logits[0, prev] -= 1.8
            ids.append(top_p_sample(logits[0], p=top_p, temp=temp))
            if idx_to_word.get(ids[-1], "") in (".", "!"):
                break
    return " ".join(idx_to_word.get(i, "?") for i in ids)


# ── Tension Visualiser ────────────────────────────────────────────────────────

def show_tensions(model, prompt: str, layer: int = 0):
    """
    Print a readable map of what each token is being pulled toward
    in the specified layer (averaged over heads).
    Gives an intuitive view of what the model has learned to track.
    """
    model.eval()
    words = prompt.split()
    ids   = [word_to_idx.get(w, 0) for w in words]
    with torch.no_grad():
        _, _, all_tensions = model(
            torch.tensor([ids], dtype=torch.long), return_all=True
        )

    tau     = all_tensions[layer][0]    # T H W
    tau_avg = tau.mean(dim=1)           # T W  (averaged over heads)
    W       = model.blocks[0].tension.window

    print(f"\nTension field — layer {layer + 1} — '{prompt}'")
    print("─" * 60)
    for t, word in enumerate(words):
        if t == 0:
            print(f"  {word:<12}  (no causal history)")
            continue
        parts = []
        for w in range(min(W, t)):
            src = words[t - w - 1]
            val = tau_avg[t, w].item()
            bar = "▓" * max(1, round(val * 10))
            parts.append(f"{src}:{val:.2f}{bar}")
        print(f"  {word:<12} ← {' | '.join(parts)}")


# ── Run ───────────────────────────────────────────────────────────────────────

print("\n─── Generation ──────────────────────────────────────────")
for prompt in ["the cat", "the dog ran", "a big fish", "the fox and"]:
    print(f"  [{prompt}]  →  {generate(model, prompt)}")

print()
show_tensions(model, "the cat sat on the mat", layer=0)
show_tensions(model, "the fox jumped over the fence", layer=-1)
