"""
Intuition layer: TensionLM as the generative 'LLM' front-end for the TS system.

In the TS paradigm, this is the 'System 1' proposer that generates candidate text from graph context.
The TS stack (graph, waves, verifiers, BOGVM) then verifies and integrates it.

This makes the whole thing a full LLM: deterministic reasoning + verified generation.
"""

# Add bozo to path for real TensionLM
import os
import sys
from pathlib import Path

import torch

bozo_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "bozo")
)
sys.path.insert(0, bozo_path)

try:
    from bozo.model import TensionConfig, TensionLM
    from bozo.model import generate as tension_generate
    from tokenizers import Tokenizer
except Exception as e:
    TensionLM = None
    tension_generate = None
    Tokenizer = None
    print(f"Warning: Could not import bozo TensionLM: {e}")


class TensionGenerator:
    def __init__(self, checkpoint_path: str = None):
        self.device = torch.device("cpu")  # on-device
        if TensionLM is None:
            self.model = None
            self.tokenizer = None
            return
        if checkpoint_path is None:
            # bozo is at /home/boggersthefish/bozo relative to workspace
            checkpoint_path = "/home/boggersthefish/bozo/bozo/checkpoints/tension_117m_v2/pytorch_model.pt"
        ckpt = torch.load(checkpoint_path, map_location=self.device)
        cfg_dict = ckpt["cfg"]
        self.cfg = TensionConfig(**cfg_dict)
        self.model = TensionLM(self.cfg)
        # Strip _orig_mod. prefix from compiled model
        state_dict = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model"].items()}
        self.model.load_state_dict(state_dict, strict=False)
        self.model.to(self.device)
        self.model.eval()
        tok_path = str(Path(checkpoint_path).parent / "tokenizer.json")
        self.tokenizer = Tokenizer.from_file(tok_path)
        print("TensionGenerator loaded 117M model for TS intuition/generation")

    def generate_from_context(
        self, context_text: str, max_new: int = 50, temp: float = 0.7
    ) -> str:
        """Generate continuation from graph-derived context."""
        ids = self.tokenizer.encode(context_text).ids
        new_ids = tension_generate(self.model, ids, max_new=max_new, temp=temp)
        text = self.tokenizer.decode(new_ids)
        return text

    def propose_from_graph(
        self, graph_state: dict, query: str = "", max_new: int = 40
    ) -> str:
        """Propose text from TS graph state (e.g., stable nodes as context).
        For full LLM behavior: the TS stack verifies the context, this generates the text.
        """
        if self.model is None:
            contents = [
                n.get("content", "") for n in graph_state.get("high_activation", [])
            ]
            base = "Based on verified graph state: " + " ".join(contents[:3]) + "."
            if query:
                base = query.strip() + " " + base
            return base
        contents = [
            n.get("content", "") for n in graph_state.get("high_activation", [])
        ]
        context = (
            " ".join(contents) if contents else "Reasoning from verified TS state."
        )
        if query:
            context = f"Query: {query}. Verified facts: {context}"
        else:
            context = "Using verified knowledge: " + context
        return self.generate_from_context(context, max_new=max_new)
