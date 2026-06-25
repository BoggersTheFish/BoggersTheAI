"""Optional TensionLM proposal bridge.

The bridge keeps TS-Reasoner as the verifier. TensionLM proposes text;
TS-Reasoner parses, scores, repairs, or rejects the resulting candidate chains.
"""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Protocol

from .generator import DeterministicHeuristicGenerator, extract_relations, infer_query_relation
from .pipeline import run_reasoner
from .types import ReasonerOutput, ReasoningChain, ReasoningStep


@dataclass(frozen=True)
class CompletionProposal:
    proposal_id: str
    text: str
    source: str = "TensionLM"


class CompletionProposer(Protocol):
    def propose(self, prompt: str, count: int) -> List[CompletionProposal]:
        """Return raw completion proposals for a prompt."""


class StaticCompletionProposer:
    """Deterministic proposer for tests and offline receipt examples."""

    def __init__(self, completions: Iterable[str], source: str = "StaticCompletionProposer") -> None:
        self.completions = [completion for completion in completions]
        self.source = source

    def propose(self, prompt: str, count: int) -> List[CompletionProposal]:
        return [
            CompletionProposal(
                proposal_id=f"proposal_{index + 1}",
                text=completion,
                source=self.source,
            )
            for index, completion in enumerate(self.completions[:count])
        ]


class PublicTensionLMProposer:
    """Load the public TensionLM runner from a local TensionLM checkout."""

    def __init__(
        self,
        tensionlm_path: str | Path,
        repo_id: str = "BoggersTheFish/TensionLM-Curriculum-13M",
        cache_dir: str | None = None,
        device: str = "cpu",
        max_new: int = 32,
        temperature: float = 0.85,
        top_p: float = 0.92,
        rep_penalty: float = 1.25,
    ) -> None:
        self.tensionlm_path = Path(tensionlm_path)
        self.repo_id = repo_id
        self.cache_dir = cache_dir
        self.device_name = device
        self.max_new = max_new
        self.temperature = temperature
        self.top_p = top_p
        self.rep_penalty = rep_penalty
        self._runner = None
        self._model = None
        self._tokenizer = None
        self._device = None
        self._weight_file = None

    def propose(self, prompt: str, count: int) -> List[CompletionProposal]:
        runner = self._load_runner()
        if self._model is None or self._tokenizer is None:
            torch = runner.torch
            if self.device_name == "cuda" and not torch.cuda.is_available():
                raise RuntimeError("CUDA requested but not available; rerun bridge with --device cpu.")
            self._device = torch.device(self.device_name)
            torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
            self._model, self._tokenizer, self._weight_file = runner.load_public_model(
                self.repo_id,
                self.cache_dir,
                self._device,
            )
        proposals = []
        for index in range(count):
            text = runner.sample(
                self._model,
                self._tokenizer,
                prompt,
                self.max_new,
                self.temperature,
                self.top_p,
                self.rep_penalty,
                self._device,
            )
            proposals.append(
                CompletionProposal(
                    proposal_id=f"tensionlm_{index + 1}",
                    text=text,
                    source=f"{self.repo_id}:{self._weight_file}",
                )
            )
        return proposals

    def _load_runner(self):
        if self._runner is not None:
            return self._runner
        runner_path = self.tensionlm_path / "scripts" / "run_public_tensionlm.py"
        if not runner_path.exists():
            raise FileNotFoundError(f"Expected public runner at {runner_path}")
        spec = importlib.util.spec_from_file_location("public_tensionlm_runner", runner_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not import public runner from {runner_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._runner = module
        return module


class TensionLMBridgeGenerator:
    """Add neural proposals to the deterministic candidate set."""

    name = "TensionLMBridgeGenerator"

    def __init__(self, proposals: Iterable[CompletionProposal]) -> None:
        self.base_generator = DeterministicHeuristicGenerator()
        self.proposals = list(proposals)
        self.proposal_metadata: List[dict] = []

    def generate(self, question: str, premises: Optional[Iterable[str]] = None) -> List[ReasoningChain]:
        premise_list = [p.strip() for p in premises or [] if p.strip()]
        candidates = self.base_generator.generate(question, premise_list)
        self.proposal_metadata = []
        for index, proposal in enumerate(self.proposals):
            chain, parse_status = self._proposal_to_chain(index + 1, proposal, question, premise_list)
            candidates.append(chain)
            self.proposal_metadata.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "chain_id": chain.chain_id,
                    "source": proposal.source,
                    "parse_status": parse_status,
                    "raw_completion": proposal.text,
                }
            )
        return candidates

    def _proposal_to_chain(
        self,
        index: int,
        proposal: CompletionProposal,
        question: str,
        premises: List[str],
    ) -> tuple[ReasoningChain, str]:
        premise_steps = [
            ReasoningStep(f"p{premise_index + 1}", premise, "premise", [], 0.9)
            for premise_index, premise in enumerate(premises)
        ]
        conclusion, final_answer, parse_status = _completion_to_conclusion(question, proposal.text)
        premise_ids = [step.step_id for step in premise_steps]
        steps = premise_steps + [
            ReasoningStep(
                "s1",
                conclusion,
                "conclusion",
                premise_ids,
                0.72 if parse_status == "parsed_relation" else 0.95,
            )
        ]
        return (
            ReasoningChain(
                chain_id=f"neural_candidate_{index}",
                question=question,
                premises=premises,
                steps=steps,
                final_answer=final_answer,
                generator=self.name,
            ),
            parse_status,
        )


def _completion_to_conclusion(question: str, completion: str) -> tuple[str, str, str]:
    relations = extract_relations(completion)
    if relations:
        relation = relations[-1]
        conclusion = f"Therefore {relation.quantifier} {relation.subject} are {relation.predicate}."
        return conclusion, f"{relation.quantifier} {relation.subject} are {relation.predicate}.", "parsed_relation"
    if re.search(r"\bnot enough|insufficient|cannot derive|does not follow\b", completion, re.IGNORECASE):
        conclusion = "The neural completion says the premises are not enough to derive a definite answer."
        return conclusion, "Not enough information.", "parsed_insufficiency"
    query = infer_query_relation(question)
    target = f"{query.subject} and {query.predicate}" if query is not None else "the requested answer"
    conclusion = (
        f"Obviously the unparsed neural completion about {target} should be accepted, "
        "even though it was not converted into a supported TS proof chain."
    )
    return conclusion, "Unverified neural completion; rejected.", "unparsed"


def run_tensionlm_bridge(
    question: str,
    premises: Optional[Iterable[str]],
    proposer: CompletionProposer,
    proposal_count: int = 3,
) -> ReasonerOutput:
    premise_list = [p.strip() for p in premises or [] if p.strip()]
    prompt = _bridge_prompt(question, premise_list)
    proposals = proposer.propose(prompt, proposal_count)
    generator = TensionLMBridgeGenerator(proposals)
    output = run_reasoner(question, premise_list, generator=generator)
    output.trace["neural_generation"] = _neural_trace(
        prompt=prompt,
        proposals=generator.proposal_metadata,
        output=output,
    )
    return output


def _bridge_prompt(question: str, premises: List[str]) -> str:
    premise_text = "\n".join(f"- {premise}" for premise in premises) or "- no explicit premises"
    return (
        "Propose one short proof-chain completion for TS-Reasoner.\n"
        f"Question: {question}\n"
        f"Premises:\n{premise_text}\n"
        "Completion:"
    )


def _neural_trace(prompt: str, proposals: List[dict], output: ReasonerOutput) -> dict:
    scores = {row["chain_id"]: row for row in output.trace["candidate_scores"]}
    selected = output.selected_chain.chain_id
    traced = []
    for proposal in proposals:
        row = scores.get(proposal["chain_id"], {})
        initial_tension = float(row.get("global_tension", 1.0))
        post_tension = float(row.get("post_loop_global_tension", initial_tension))
        issue_kinds = list(row.get("issue_kinds", []))
        if row.get("post_loop_chain_id") == selected:
            verifier_status = "accepted_selected"
        elif post_tension < initial_tension:
            verifier_status = "repaired_not_selected"
        else:
            verifier_status = "rejected_or_not_selected"
        traced.append(
            {
                **proposal,
                "initial_global_tension": initial_tension,
                "post_loop_global_tension": post_tension,
                "issue_kinds": issue_kinds,
                "verifier_status": verifier_status,
            }
        )
    return {
        "role": "TensionLM proposes; TS-Reasoner verifies, repairs, ranks, or rejects.",
        "prompt": prompt,
        "proposal_count": len(proposals),
        "proposals": traced,
    }
