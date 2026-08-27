"""Mega PRIME Native Cortex V1.

Architecture:

    BPE
    multi-timescale delta recurrence
    bounded local attention
    top-2 train / top-1 inference sparse experts
    ternary-effective projections
    factorized output decoder

The cortex has zero epistemic authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import torch
from torch import nn
import torch.nn.functional as F

from .model import (
    RMSNorm,
    SparseExpert,
    TernaryLinear,
)


@dataclass(frozen=True)
class CortexV1Config:
    vocab_size: int = 4096

    d_model: int = 192

    layers: int = 4

    memory_heads: int = 6

    attention_heads: int = 6

    attention_every: int = 2

    attention_window: int = 64

    experts: int = 6

    expert_hidden: int = 384

    output_rank: int = 64

    verifier_classes: int = 5

    dropout: float = 0.0


@dataclass
class BlockState:
    memory: torch.Tensor

    attention_keys: torch.Tensor | None = None

    attention_values: torch.Tensor | None = None


@dataclass
class CortexV1Output:
    logits: torch.Tensor

    verifier_logits: torch.Tensor

    hidden: torch.Tensor

    states: list[BlockState]

    router_balance_loss: torch.Tensor

    router_z_loss: torch.Tensor

    router_entropy_normalized: torch.Tensor

    diagnostics: list[dict] | None = None


class MultiTimescaleDeltaMemory(
    nn.Module
):
    def __init__(
        self,
        config: CortexV1Config,
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

        self.q_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

        self.k_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

        self.v_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

        self.out_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

        self.gates = nn.Linear(
            config.d_model,
            2 * self.heads,
        )

        half_lives = torch.logspace(
            math.log10(4.0),
            math.log10(768.0),
            steps=self.heads,
        )

        retention = torch.pow(
            torch.tensor(0.5),
            1.0 / half_lives,
        )

        self.register_buffer(
            "base_retention",
            retention,
            persistent=True,
        )

        with torch.no_grad():
            self.gates.bias[
                :self.heads
            ].fill_(
                -2.0
            )

            self.gates.bias[
                self.heads:
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
            self.q_proj(x)
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        k = (
            self.k_proj(x)
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        v = (
            self.v_proj(x)
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

        prediction = torch.einsum(
            "bhkv,bhk->bhv",
            state,
            k,
        )

        gates = (
            torch.sigmoid(
                self.gates(x)
            )
            .reshape(
                batch,
                self.heads,
                2,
            )
        )

        erase = gates[
            :,
            :,
            0,
        ]

        write = (
            0.35
            * gates[
                :,
                :,
                1,
            ]
        )

        base = (
            self.base_retention
            .to(
                dtype=state.dtype,
                device=state.device,
            )
            .view(
                1,
                self.heads,
            )
        )

        retention = (
            base
            * (
                1.0
                - 0.25
                * erase
            )
        ).clamp(
            0.0,
            0.99995,
        )

        residual = (
            v
            - prediction
        )

        delta = (
            k.unsqueeze(-1)
            * residual.unsqueeze(-2)
        )

        new_state = (
            retention[
                :,
                :,
                None,
                None,
            ]
            * state
            + write[
                :,
                :,
                None,
                None,
            ]
            * delta
        )

        output = self.out_proj(
            read.reshape(
                batch,
                self.d_model,
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
            ),
            "read_norm": (
                read
                .detach()
                .float()
                .norm(
                    dim=-1
                )
                .mean()
            ),
            "erase_mean": (
                erase
                .detach()
                .float()
                .mean()
            ),
            "write_mean": (
                write
                .detach()
                .float()
                .mean()
            ),
            "retention_mean": (
                retention
                .detach()
                .float()
                .mean()
            ),
        }

        return (
            output,
            new_state,
            stats,
        )


class LocalAttention(
    nn.Module
):
    def __init__(
        self,
        config: CortexV1Config,
    ) -> None:
        super().__init__()

        if (
            config.d_model
            % config.attention_heads
            != 0
        ):
            raise ValueError(
                "d_model must divide attention_heads"
            )

        self.heads = (
            config.attention_heads
        )

        self.head_dim = (
            config.d_model
            // self.heads
        )

        self.window = (
            config.attention_window
        )

        self.q_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

        self.k_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

        self.v_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

        self.out_proj = TernaryLinear(
            config.d_model,
            config.d_model,
            bias=False,
        )

    def step(
        self,
        x,
        key_cache,
        value_cache,
        *,
        disabled: bool = False,
    ):
        if disabled:
            return (
                torch.zeros_like(x),
                key_cache,
                value_cache,
                {
                    "attention_entropy": (
                        x.new_zeros(())
                    ),
                    "attention_context": 0,
                },
            )

        batch = x.shape[0]

        q = (
            self.q_proj(x)
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        k = (
            self.k_proj(x)
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        v = (
            self.v_proj(x)
            .reshape(
                batch,
                self.heads,
                self.head_dim,
            )
        )

        k = k.unsqueeze(2)
        v = v.unsqueeze(2)

        if key_cache is None:
            keys = k
            values = v

        else:
            keys = torch.cat(
                (
                    key_cache,
                    k,
                ),
                dim=2,
            )

            values = torch.cat(
                (
                    value_cache,
                    v,
                ),
                dim=2,
            )

        if (
            keys.shape[2]
            > self.window
        ):
            keys = keys[
                :,
                :,
                -self.window:,
                :
            ]

            values = values[
                :,
                :,
                -self.window:,
                :
            ]

        scale = (
            self.head_dim
            ** -0.5
        )

        scores = (
            torch.einsum(
                "bhd,bhtd->bht",
                q,
                keys,
            )
            * scale
        )

        probabilities = (
            torch.softmax(
                scores,
                dim=-1,
            )
        )

        context = torch.einsum(
            "bht,bhtd->bhd",
            probabilities,
            values,
        )

        output = self.out_proj(
            context.reshape(
                batch,
                -1,
            )
        )

        length = (
            probabilities.shape[-1]
        )

        if length > 1:
            entropy = -(
                probabilities
                * torch.log(
                    probabilities
                    + 1e-12
                )
            ).sum(
                dim=-1
            ).mean()

            entropy = (
                entropy
                / math.log(length)
            )

        else:
            entropy = (
                probabilities
                .new_zeros(())
            )

        return (
            output,
            keys,
            values,
            {
                "attention_entropy": (
                    entropy
                    .detach()
                    .float()
                ),
                "attention_context": (
                    length
                ),
            },
        )


class TopKMoE(
    nn.Module
):
    def __init__(
        self,
        config: CortexV1Config,
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
        router_logits = (
            self.router(x)
        )

        probabilities = (
            torch.softmax(
                router_logits,
                dim=-1,
            )
        )

        top_k = (
            min(
                2,
                self.expert_count,
            )
            if self.training
            else 1
        )

        top_values, top_indices = (
            torch.topk(
                probabilities,
                top_k,
                dim=-1,
            )
        )

        top_weights = (
            top_values
            / top_values.sum(
                dim=-1,
                keepdim=True,
            ).clamp_min(
                1e-9
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
            for slot in range(
                top_k
            ):
                mask = (
                    top_indices[
                        :,
                        slot,
                    ]
                    == expert_index
                )

                if not torch.any(mask):
                    continue

                expert_output = (
                    expert(
                        x[mask]
                    )
                )

                output[mask] += (
                    expert_output
                    * top_weights[
                        mask,
                        slot,
                    ].unsqueeze(
                        -1
                    )
                )

        importance = (
            probabilities.mean(
                dim=0
            )
        )

        assignments = (
            F.one_hot(
                top_indices,
                num_classes=(
                    self.expert_count
                ),
            )
            .float()
            .sum(
                dim=1
            )
            / top_k
        )

        load = (
            assignments.mean(
                dim=0
            )
        )

        balance_loss = (
            self.expert_count
            * (
                importance
                * load
            ).sum()
        )

        z_loss = (
            torch.logsumexp(
                router_logits,
                dim=-1,
            )
            .pow(2)
            .mean()
        )

        entropy = -(
            probabilities
            * torch.log(
                probabilities
                + 1e-12
            )
        ).sum(
            dim=-1
        ).mean()

        entropy_normalized = (
            entropy
            / math.log(
                self.expert_count
            )
        )

        stats = {
            "top_expert": (
                top_indices[
                    :,
                    0,
                ]
                .detach()
            ),
            "top_probability": (
                top_values[
                    :,
                    0,
                ]
                .detach()
            ),
            "entropy_normalized": (
                entropy_normalized
                .detach()
            ),
        }

        return (
            output,
            balance_loss,
            z_loss,
            entropy_normalized,
            stats,
        )


class CortexV1Block(
    nn.Module
):
    def __init__(
        self,
        config: CortexV1Config,
        *,
        use_attention: bool,
    ) -> None:
        super().__init__()

        self.use_attention = (
            use_attention
        )

        self.memory_norm = RMSNorm(
            config.d_model
        )

        self.memory = (
            MultiTimescaleDeltaMemory(
                config
            )
        )

        if use_attention:
            self.attention_norm = (
                RMSNorm(
                    config.d_model
                )
            )

            self.attention = (
                LocalAttention(
                    config
                )
            )

        else:
            self.attention_norm = None
            self.attention = None

        self.expert_norm = RMSNorm(
            config.d_model
        )

        self.moe = TopKMoE(
            config
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
        return BlockState(
            memory=(
                self.memory
                .initial_state(
                    batch_size,
                    device=device,
                    dtype=dtype,
                )
            ),
        )

    def step(
        self,
        x,
        state: BlockState,
        *,
        disable_attention: bool = False,
    ):
        (
            memory_output,
            memory_state,
            memory_stats,
        ) = self.memory.step(
            self.memory_norm(x),
            state.memory,
        )

        x = (
            x
            + self.dropout(
                memory_output
            )
        )

        attention_stats = {
            "attention_entropy": (
                x.new_zeros(())
            ),
            "attention_context": 0,
        }

        attention_keys = (
            state.attention_keys
        )

        attention_values = (
            state.attention_values
        )

        if self.use_attention:
            (
                attention_output,
                attention_keys,
                attention_values,
                attention_stats,
            ) = self.attention.step(
                self.attention_norm(x),
                attention_keys,
                attention_values,
                disabled=(
                    disable_attention
                ),
            )

            x = (
                x
                + self.dropout(
                    attention_output
                )
            )

        (
            expert_output,
            balance_loss,
            z_loss,
            entropy,
            expert_stats,
        ) = self.moe(
            self.expert_norm(x)
        )

        x = (
            x
            + self.dropout(
                expert_output
            )
        )

        stats = {
            **memory_stats,
            **attention_stats,
            **expert_stats,
        }

        return (
            x,
            BlockState(
                memory=memory_state,
                attention_keys=(
                    attention_keys
                ),
                attention_values=(
                    attention_values
                ),
            ),
            balance_loss,
            z_loss,
            entropy,
            stats,
        )


class NativeCortexV1(
    nn.Module
):
    """Observable low-compute recurrent language cortex."""

    def __init__(
        self,
        config: CortexV1Config,
    ) -> None:
        super().__init__()

        self.config = config

        self.embedding = nn.Embedding(
            config.vocab_size,
            config.d_model,
        )

        self.blocks = nn.ModuleList(
            [
                CortexV1Block(
                    config,
                    use_attention=(
                        (
                            layer_index
                            + 1
                        )
                        % config.attention_every
                        == 0
                    ),
                )
                for layer_index
                in range(
                    config.layers
                )
            ]
        )

        self.final_norm = RMSNorm(
            config.d_model
        )

        self.lm_bottleneck = (
            TernaryLinear(
                config.d_model,
                config.output_rank,
                bias=False,
            )
        )

        self.lm_output = (
            TernaryLinear(
                config.output_rank,
                config.vocab_size,
                bias=False,
            )
        )

        self.verifier_head = (
            TernaryLinear(
                config.d_model,
                config.verifier_classes,
            )
        )

        self.future_predictor = (
            TernaryLinear(
                config.d_model,
                config.d_model,
                bias=False,
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
        dtype,
    ):
        return [
            block.initial_state(
                batch_size,
                device=device,
                dtype=dtype,
            )
            for block
            in self.blocks
        ]

    def decode_logits(
        self,
        hidden,
    ):
        bottleneck = (
            self.lm_bottleneck(
                hidden
            )
        )

        return self.lm_output(
            bottleneck
        )

    def step(
        self,
        tokens,
        states=None,
        *,
        reset_recurrence: bool = False,
        disable_attention: bool = False,
        collect_diagnostics: bool = False,
    ):
        if tokens.ndim != 1:
            raise ValueError(
                "step tokens must be [batch]"
            )

        x = self.embedding(
            tokens
        )

        if states is None:
            states = (
                self.initial_states(
                    tokens.shape[0],
                    device=tokens.device,
                    dtype=x.dtype,
                )
            )

        if reset_recurrence:
            states = [
                BlockState(
                    memory=(
                        torch.zeros_like(
                            state.memory
                        )
                    ),
                    attention_keys=(
                        state.attention_keys
                    ),
                    attention_values=(
                        state.attention_values
                    ),
                )
                for state
                in states
            ]

        new_states = []

        balance_total = (
            x.new_zeros(())
        )

        z_total = (
            x.new_zeros(())
        )

        entropy_total = (
            x.new_zeros(())
        )

        diagnostics = (
            []
            if collect_diagnostics
            else None
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
            (
                x,
                new_state,
                balance,
                z_loss,
                entropy,
                stats,
            ) = block.step(
                x,
                state,
                disable_attention=(
                    disable_attention
                ),
            )

            new_states.append(
                new_state
            )

            balance_total = (
                balance_total
                + balance
            )

            z_total = (
                z_total
                + z_loss
            )

            entropy_total = (
                entropy_total
                + entropy
            )

            if collect_diagnostics:
                diagnostics.append(
                    {
                        "layer": (
                            layer_index
                        ),
                        **stats,
                    }
                )

        hidden = self.final_norm(
            x
        )

        logits = self.decode_logits(
            hidden
        )

        verifier_logits = (
            self.verifier_head(
                hidden
            )
        )

        denominator = len(
            self.blocks
        )

        return (
            logits,
            verifier_logits,
            hidden,
            new_states,
            balance_total
            / denominator,
            z_total
            / denominator,
            entropy_total
            / denominator,
            diagnostics,
        )

    def forward(
        self,
        tokens,
        states=None,
        *,
        reset_recurrence: bool = False,
        disable_attention: bool = False,
        collect_diagnostics: bool = False,
    ) -> CortexV1Output:
        if tokens.ndim != 2:
            raise ValueError(
                "tokens must be [batch, sequence]"
            )

        logits = []
        verifier_logits = []
        hidden_rows = []

        balance_total = (
            self.embedding
            .weight
            .new_zeros(())
        )

        z_total = (
            self.embedding
            .weight
            .new_zeros(())
        )

        entropy_total = (
            self.embedding
            .weight
            .new_zeros(())
        )

        diagnostic_totals = None

        if collect_diagnostics:
            diagnostic_totals = [
                {
                    "expert_counts": (
                        torch.zeros(
                            self.config.experts,
                            dtype=torch.long,
                        )
                    ),
                    "router_confidence_sum": 0.0,
                    "router_entropy_sum": 0.0,
                    "state_norm_sum": 0.0,
                    "read_norm_sum": 0.0,
                    "erase_sum": 0.0,
                    "write_sum": 0.0,
                    "retention_sum": 0.0,
                    "attention_entropy_sum": 0.0,
                    "attention_steps": 0,
                    "steps": 0,
                }
                for _ in range(
                    self.config.layers
                )
            ]

        for position in range(
            tokens.shape[1]
        ):
            (
                token_logits,
                token_verifier,
                token_hidden,
                states,
                balance,
                z_loss,
                entropy,
                diagnostics,
            ) = self.step(
                tokens[
                    :,
                    position,
                ],
                states,
                reset_recurrence=(
                    reset_recurrence
                ),
                disable_attention=(
                    disable_attention
                ),
                collect_diagnostics=(
                    collect_diagnostics
                ),
            )

            logits.append(
                token_logits
            )

            verifier_logits.append(
                token_verifier
            )

            hidden_rows.append(
                token_hidden
            )

            balance_total = (
                balance_total
                + balance
            )

            z_total = (
                z_total
                + z_loss
            )

            entropy_total = (
                entropy_total
                + entropy
            )

            if collect_diagnostics:
                for row in diagnostics:
                    layer = row[
                        "layer"
                    ]

                    target = (
                        diagnostic_totals[
                            layer
                        ]
                    )

                    expert = (
                        row[
                            "top_expert"
                        ]
                        .detach()
                        .cpu()
                    )

                    target[
                        "expert_counts"
                    ] += torch.bincount(
                        expert,
                        minlength=(
                            self.config.experts
                        ),
                    )

                    target[
                        "router_confidence_sum"
                    ] += float(
                        row[
                            "top_probability"
                        ]
                        .float()
                        .mean()
                        .item()
                    )

                    target[
                        "router_entropy_sum"
                    ] += float(
                        row[
                            "entropy_normalized"
                        ]
                        .item()
                    )

                    target[
                        "state_norm_sum"
                    ] += float(
                        row[
                            "state_norm"
                        ].item()
                    )

                    target[
                        "read_norm_sum"
                    ] += float(
                        row[
                            "read_norm"
                        ].item()
                    )

                    target[
                        "erase_sum"
                    ] += float(
                        row[
                            "erase_mean"
                        ].item()
                    )

                    target[
                        "write_sum"
                    ] += float(
                        row[
                            "write_mean"
                        ].item()
                    )

                    target[
                        "retention_sum"
                    ] += float(
                        row[
                            "retention_mean"
                        ].item()
                    )

                    if (
                        row[
                            "attention_context"
                        ]
                        > 0
                    ):
                        target[
                            "attention_entropy_sum"
                        ] += float(
                            row[
                                "attention_entropy"
                            ].item()
                        )

                        target[
                            "attention_steps"
                        ] += 1

                    target[
                        "steps"
                    ] += 1

        sequence = (
            tokens.shape[1]
        )

        return CortexV1Output(
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
            hidden=torch.stack(
                hidden_rows,
                dim=1,
            ),
            states=states,
            router_balance_loss=(
                balance_total
                / sequence
            ),
            router_z_loss=(
                z_total
                / sequence
            ),
            router_entropy_normalized=(
                entropy_total
                / sequence
            ),
            diagnostics=(
                diagnostic_totals
            ),
        )
