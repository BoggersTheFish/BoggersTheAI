import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import math

# Toy vocabulary (expanded)
vocab = [
    "the", "cat", "sat", "on", "mat", "dog", "ran", "away", "and", "then",
    "happy", "sad", "big", "small", "house", "tree", "quick", "slow", "jump",
    "sleep", "fox", "brown", "lazy", "over", "fence", "ate", "fish", "drank",
    "milk", "played", "ball", "chased", "bird", "flew", "high", "low", "fast",
    "slowly", "loud", "quiet", ".", "!"
]
word_to_idx = {word: i for i, word in enumerate(vocab)}
idx_to_word = {i: word for i, word in enumerate(vocab)}
vocab_size = len(vocab)

# CausalTensionGraphLayer (exact schizo_bet primitive)
class CausalTensionGraphLayer(nn.Module):
    def __init__(self, dim: int, window: int = 4):
        super().__init__()
        self.window = window
        self.dim = dim
        self.tension_net = nn.Sequential(
            nn.Linear(dim * 2, dim // 2),
            nn.SiLU(),
            nn.Linear(dim // 2, 1)
        )
        self.wv = nn.Linear(dim, dim)
        self.merge = nn.Linear(dim * 2, dim)
        self.norm = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor, return_tensions: bool = False):
        B, T, D = x.shape
        nb = torch.zeros(B, T, self.window, D, device=x.device)
        for t in range(T):
            for w in range(min(self.window, t)):
                nb[:, t, w] = x[:, t - w - 1]
        h_t = x.unsqueeze(2).expand(-1, -1, self.window, -1)
        pair = torch.cat([h_t, nb], dim=-1)
        tau_logits = self.tension_net(pair).squeeze(-1)
        tau = torch.sigmoid(tau_logits)
        v = self.wv(nb)
        msg = (tau.unsqueeze(-1) * v).sum(dim=2)
        y = self.merge(torch.cat([x, msg], dim=-1))
        y = self.norm(y)
        if return_tensions:
            return y, tau.mean(dim=0)
        return y

# Oscillatory modulation (wave propagation)
def apply_oscillatory(x: torch.Tensor, timestep: int):
    B, T, D = x.shape
    omega = 2 * math.pi / 12.0
    phase = timestep * omega
    scale = 1.0 + 0.15 * torch.sin(torch.arange(T, device=x.device).float() * omega + phase)
    return x * scale.unsqueeze(0).unsqueeze(-1)

# Full toy model
class ToySchizoBet(nn.Module):
    def __init__(self, dim: int = 32, window: int = 4):
        super().__init__()
        self.dim = dim
        self.embedding = nn.Embedding(vocab_size, dim)
        self.layer = CausalTensionGraphLayer(dim, window)
        self.lm_head = nn.Linear(dim, vocab_size)

    def forward(self, input_ids: torch.Tensor):
        x = self.embedding(input_ids)
        x = self.layer(x)
        x = apply_oscillatory(x, input_ids.shape[1])
        logits = self.lm_head(x)
        return logits

# Auxiliary losses (from schizo_bet)
def attractor_manifold_loss(hidden_states):
    return F.mse_loss(hidden_states[:, -1], hidden_states[:, 0].detach())

def tension_entropy_deficit(tau_avg, window=4):
    p = tau_avg / (tau_avg.sum() + 1e-8)
    entropy = - (p * torch.log(p + 1e-8)).sum()
    max_entropy = math.log(window)
    return max(0, max_entropy - entropy)

# Corpus (~200 tokens)
corpus = (
    "the cat sat on the mat the dog ran away the cat chased the bird the fox "
    "jumped over the fence the brown fox ate the fish the lazy dog drank milk "
    "the quick cat played with the ball the happy bird flew high the tree was big "
    "the house was small the slow fox chased the fast cat ."
)
tokens = corpus.split()
token_ids = [word_to_idx.get(w, 0) for w in tokens]

# Train
model = ToySchizoBet(dim=32)
optimizer = optim.Adam(model.parameters(), lr=3e-3)
criterion = nn.CrossEntropyLoss()

for epoch in range(80):
    for i in range(0, len(token_ids) - 10, 6):
        seq = token_ids[i:i+10]
        if len(seq) < 10: continue
        input_ids = torch.tensor([seq[:-1]], dtype=torch.long)
        targets = torch.tensor([seq[1:]], dtype=torch.long)
        
        optimizer.zero_grad()
        logits = model(input_ids)
        loss_ce = criterion(logits.view(-1, vocab_size), targets.view(-1))
        
        with torch.no_grad():
            emb = model.embedding(input_ids)
            hidden, tau = model.layer(emb, return_tensions=True)
        
        loss_attr = attractor_manifold_loss(hidden)
        loss_tent = tension_entropy_deficit(tau)
        
        loss = loss_ce + 0.1 * loss_attr + 0.05 * loss_tent
        loss.backward()
        optimizer.step()

# Generation
def generate(model, prompt_words, max_new=30, temp=0.85):
    prompt_ids = [word_to_idx.get(w, 0) for w in prompt_words.split()]
    generated = prompt_ids[:]
    model.eval()
    with torch.no_grad():
        for _ in range(max_new):
            input_ids = torch.tensor([generated[-8:]], dtype=torch.long)
            logits = model(input_ids)[:, -1, :]
            logits = logits / temp
            for prev in set(generated[-3:]):
                logits[0, prev] -= 2.0
            probs = F.softmax(logits, dim=-1)
            next_idx = torch.multinomial(probs, 1).item()
            generated.append(next_idx)
            if next_idx == word_to_idx.get(".", 0):
                break
    return " ".join([idx_to_word[i] for i in generated])

result = generate(model, "the cat")
print(result)
