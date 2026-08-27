"""Mega PRIME Native Cortex.

Ternary projections + matrix-valued delta recurrent memory +
sparse expert routing.

The cortex has no canonical epistemic authority.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
import torch.nn.functional as F

from .telemetry import (
    LayerObservation,
)


class RMSNorm(
    nn.Module
):
    def __init__(
        self,
        dimension: int,
        eps: float = 1e-6,
    ) -> None:
        super().__init__()

        self.weight = nn.Parameter(
            torch.ones(
                dimension
            )
        )

        self.eps = eps

    def forward(
        self,
        x,
    ):
        scale = (
            x.pow(2)
            .mean(
                dim=-1,
                keepdim=True,
            )
            .add(
                self.eps
            )
            .rsqrt()
        )

        return (
            x
            * scale
            * self.weight
        )


class TernaryLinear(
    nn.Module
):
    """Trainable FP weights; ternary effective forward weights.

    Straight-through estimator:

        {-scale, 0, +scale}

    This establishes the low-bit architecture without requiring
    specialized inference kernels yet.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        *,
        bias: bool = True,
    ) -> None:
        super().__init__()

        self.weight = nn.Parameter(
            torch.empty(
                out_features,
                in_features,
            )
        )

        if bias:
            self.bias = nn.Parameter(
                torch.zeros(
                    out_features
                )
            )
        else:
            self.register_parameter(
                "bias",
                None,
            )

        nn.init.normal_(
            self.weight,
            mean=0.0,
            std=(
                in_features
                ** -0.5
            ),
        )

    def effective_weight(
        self,
    ):
        scale = (
            self.weight
            .detach()
            .abs()
            .mean(
                dim=-1,
                keepdim=True,
            )
            .clamp_min(
                1e-6
            )
        )

        quantized = (
            torch.round(
                self.weight
                / scale
            )
            .clamp(
                -1,
                1,
            )
            * scale
        )

        # Straight-through estimator.
        return (
            self.weight
            + (
                quantized
                - self.weight
            ).detach()
        )

    def forward(
        self,
        x,
    ):
        return F.linear(
            x,
            self.effective_weight(),
            self.bias,
        )


@dataclass(frozen=True)
class CortexConfig:
    vocab_size: int = 259

    d_model: int = 96

    layers: int = 3

    memory_heads: int = 4

    experts: int = 4

    expert_hidden: int = 192

    verifier_classes: int = 5

    dropout: float = 0.0


@dataclass
class CortexOutput:
    logits: torch.Tensor

    verifier_logits: torch.Tensor

    states: list[
        torch.Tensor
    ]

    auxiliary_loss: torch.Tensor

    telemetry: list | None = None


class DeltaMemory(
    nn.Module
):
    def __init__(
        self,
        config: CortexConfig,
    ) -> None:
        super().__init__()

        if (
            config.d_model
            % config.memory_heads
            != 0
        ):
            raise ValueError(
                "d_model must divide memory_heads"
            )

        self.d_model = (
            config.d_model
        )

        self.heads = (
            config.memory_heads
        )

        self.head_dim = (
            config.d_model
            // config.memory_heads
        )

        self.q_proj = (
            TernaryLinear(
                config.d_model,
                config.d_model,
                bias=False,
            )
        )

        self.k_proj = (
            TernaryLinear(
                config.d_model,
                config.d_model,
                bias=False,
            )
        )

        self.v_proj = (
            TernaryLinear(
                config.d_model,
                config.d_model,
                bias=False,
            )
        )

        self.out_proj = (
            TernaryLinear(
                config.d_model,
                config.d_model,
                bias=False,
            )
        )

        self.gates = nn.Linear(
            config.d_model,
            2
            * config.memory_heads,
        )

        with torch.no_grad():
            self.gates.bias[
                :config.memory_heads
            ].fill_(
                -2.0
            )

            self.gates.bias[
                config.memory_heads:
            ].fill_(
                -1.0
            )

    def initial_state(
        self,
        batch_size: int,
        *,
        device,
        dtype,
    ):
        return torch.zeros(
            batch_size,
            self.heads,
            self.head_dim,
            self.head_dim,
            device=device,
            dtype=dtype,
        )

    def step(
        self,
        x,
        state,
    ):
        batch = x.shape[0]

        q = (
            self.q_proj(
                x
            )
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        k = (
            self.k_proj(
                x
            )
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        v = (
            self.v_proj(
                x
            )
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        q = F.normalize(
            q,
            dim=-1,
            eps=1e-6,
        )

        k = F.normalize(
            k,
            dim=-1,
            eps=1e-6,
        )

        read = torch.einsum(
            "bhkv,bhk->bhv",
            state,
            q,
        )

        predicted = torch.einsum(
            "bhkv,bhk->bhv",
            state,
            k,
        )

        gate_values = (
            torch.sigmoid(
                self.gates(
                    x
                )
            )
            .reshape(
                batch,
                self.heads,
                2,
            )
        )

        erase = (
            0.10
            * gate_values[
                :,
                :,
                0,
            ]
        )

        write = (
            0.50
            * gate_values[
                :,
                :,
                1,
            ]
        )

        residual = (
            v
            - predicted
        )

        delta = (
            k.unsqueeze(
                -1
            )
            * residual.unsqueeze(
                -2
            )
        )

        new_state = (
            (
                1.0
                - erase.unsqueeze(
                    -1
                ).unsqueeze(
                    -1
                )
            )
            * state
            + write.unsqueeze(
                -1
            ).unsqueeze(
                -1
            )
            * delta
        )

        output = (
            self.out_proj(
                read.reshape(
                    batch,
                    self.d_model,
                )
            )
        )

        stats = {
            "state_norm": (
                new_state
                .detach()
                .float()
                .norm(
                    dim=(-2, -1)
                )
                .mean()
                .item()
            ),
            "read_norm": (
                read
                .detach()
                .float()
                .norm(
                    dim=-1
                )
                .mean()
                .item()
            ),
            "erase_mean": (
                erase
                .detach()
                .float()
                .mean()
                .item()
            ),
            "write_mean": (
                write
                .detach()
                .float()
                .mean()
                .item()
            ),
        }

        return (
            output,
            new_state,
            stats,
        )


class SparseExpert(
    nn.Module
):
    def __init__(
        self,
        config: CortexConfig,
    ) -> None:
        super().__init__()

        self.up = TernaryLinear(
            config.d_model,
            config.expert_hidden,
        )

        self.down = TernaryLinear(
            config.expert_hidden,
            config.d_model,
        )

    def forward(
        self,
        x,
    ):
        return self.down(
            F.silu(
                self.up(
                    x
                )
            )
        )


class SparseMoE(
    nn.Module
):
    def __init__(
        self,
        config: CortexConfig,
    ) -> None:
        super().__init__()

        self.expert_count = (
            config.experts
        )

        self.router = nn.Linear(
            config.d_model,
            config.experts,
        )

        self.experts = nn.ModuleList(
            [
                SparseExpert(
                    config
                )
                for _ in range(
                    config.experts
                )
            ]
        )

    def forward(
        self,
        x,
    ):
        probabilities = (
            torch.softmax(
                self.router(
                    x
                ),
                dim=-1,
            )
        )

        top_probability, top_index = (
            probabilities.max(
                dim=-1
            )
        )

        output = torch.zeros_like(
            x
        )

        for expert_index, expert in (
            enumerate(
                self.experts
            )
        ):
            mask = (
                top_index
                == expert_index
            )

            if not torch.any(
                mask
            ):
                continue

            expert_output = expert(
                x[
                    mask
                ]
            )

            output[
                mask
            ] = (
                expert_output
                * top_probability[
                    mask
                ].unsqueeze(
                    -1
                )
            )

        importance = (
            probabilities.mean(
                dim=0
            )
        )

        load = (
            F.one_hot(
                top_index,
                num_classes=(
                    self.expert_count
                ),
            )
            .float()
            .mean(
                dim=0
            )
        )

        auxiliary_loss = (
            self.expert_count
            * (
                importance
                * load
            ).sum()
        )

        return (
            output,
            auxiliary_loss,
            top_index,
            top_probability,
        )


class CortexBlock(
    nn.Module
):
    def __init__(
        self,
        config: CortexConfig,
    ) -> None:
        super().__init__()

        self.norm_memory = (
            RMSNorm(
                config.d_model
            )
        )

        self.memory = (
            DeltaMemory(
                config
            )
        )

        self.norm_expert = (
            RMSNorm(
                config.d_model
            )
        )

        self.moe = (
            SparseMoE(
                config
            )
        )

        self.dropout = nn.Dropout(
            config.dropout
        )

    def initial_state(
        self,
        batch_size,
        *,
        device,
        dtype,
    ):
        return (
            self.memory.initial_state(
                batch_size,
                device=device,
                dtype=dtype,
            )
        )

    def step(
        self,
        x,
        state,
    ):
        memory_output, state, stats = (
            self.memory.step(
                self.norm_memory(
                    x
                ),
                state,
            )
        )

        x = (
            x
            + self.dropout(
                memory_output
            )
        )

        expert_output, aux, index, probability = (
            self.moe(
                self.norm_expert(
                    x
                )
            )
        )

        x = (
            x
            + self.dropout(
                expert_output
            )
        )

        stats.update(
            {
                "expert_index": (
                    index
                ),
                "expert_probability": (
                    probability
                ),
            }
        )

        return (
            x,
            state,
            aux,
            stats,
        )


class NativeCortex(
    nn.Module
):
    VERIFIER_LABELS = (
        "UNKNOWN",
        "ACCEPT",
        "REJECT",
        "REPAIR",
        "ABSTAIN",
    )

    def __init__(
        self,
        config: CortexConfig,
    ) -> None:
        super().__init__()

        self.config = config

        self.embedding = nn.Embedding(
            config.vocab_size,
            config.d_model,
        )

        self.blocks = nn.ModuleList(
            [
                CortexBlock(
                    config
                )
                for _ in range(
                    config.layers
                )
            ]
        )

        self.final_norm = (
            RMSNorm(
                config.d_model
            )
        )

        self.verifier_head = (
            TernaryLinear(
                config.d_model,
                config.verifier_classes,
            )
        )

    def parameter_count(
        self,
    ) -> int:
        return sum(
            parameter.numel()
            for parameter
            in self.parameters()
        )

    def initial_states(
        self,
        batch_size,
        *,
        device,
        dtype=None,
    ):
        if dtype is None:
            dtype = (
                self.embedding
                .weight
                .dtype
            )

        return [
            block.initial_state(
                batch_size,
                device=device,
                dtype=dtype,
            )
            for block
            in self.blocks
        ]

    def step(
        self,
        tokens,
        states=None,
        *,
        telemetry=False,
    ):
        if tokens.ndim != 1:
            raise ValueError(
                "step tokens must have shape [batch]"
            )

        x = self.embedding(
            tokens
        )

        if states is None:
            states = (
                self.initial_states(
                    tokens.shape[0],
                    device=(
                        tokens.device
                    ),
                    dtype=x.dtype,
                )
            )

        new_states = []

        layer_stats = []

        auxiliary = (
            x.new_zeros(
                ()
            )
        )

        for layer_index, (
            block,
            state,
        ) in enumerate(
            zip(
                self.blocks,
                states,
            )
        ):
            x, new_state, aux, stats = (
                block.step(
                    x,
                    state,
                )
            )

            new_states.append(
                new_state
            )

            auxiliary = (
                auxiliary
                + aux
            )

            if telemetry:
                layer_stats.append(
                    LayerObservation(
                        layer=(
                            layer_index
                        ),
                        recurrent_state_norm=(
                            stats[
                                "state_norm"
                            ]
                        ),
                        read_norm=(
                            stats[
                                "read_norm"
                            ]
                        ),
                        erase_mean=(
                            stats[
                                "erase_mean"
                            ]
                        ),
                        write_mean=(
                            stats[
                                "write_mean"
                            ]
                        ),
                        selected_expert=int(
                            stats[
                                "expert_index"
                            ][0].item()
                        ),
                        expert_probability=float(
                            stats[
                                "expert_probability"
                            ][0].item()
                        ),
                    )
                )

        x = self.final_norm(
            x
        )

        # Weight-tied output head.
        logits = F.linear(
            x,
            self.embedding.weight,
        )

        verifier_logits = (
            self.verifier_head(
                x
            )
        )

        return (
            logits,
            verifier_logits,
            new_states,
            auxiliary
            / len(
                self.blocks
            ),
            (
                layer_stats
                if telemetry
                else None
            ),
        )

    def forward(
        self,
        tokens,
        states=None,
        *,
        telemetry=False,
    ) -> CortexOutput:
        if tokens.ndim != 2:
            raise ValueError(
                "tokens must have shape [batch, sequence]"
            )

        logits = []

        verifier_logits = []

        telemetry_rows = (
            []
            if telemetry
            else None
        )

        auxiliary = (
            self.embedding
            .weight
            .new_zeros(
                ()
            )
        )

        for position in range(
            tokens.shape[1]
        ):
            (
                token_logits,
                token_verifier,
                states,
                token_aux,
                token_telemetry,
            ) = self.step(
                tokens[
                    :,
                    position,
                ],
                states,
                telemetry=(
                    telemetry
                ),
            )

            logits.append(
                token_logits
            )

            verifier_logits.append(
                token_verifier
            )

            auxiliary = (
                auxiliary
                + token_aux
            )

            if telemetry:
                telemetry_rows.append(
                    token_telemetry
                )

        return CortexOutput(
            logits=torch.stack(
                logits,
                dim=1,
            ),
            verifier_logits=(
                torch.stack(
                    verifier_logits,
                    dim=1,
                )
            ),
            states=states,
            auxiliary_loss=(
                auxiliary
                / tokens.shape[1]
            ),
            telemetry=(
                telemetry_rows
            ),
        )
