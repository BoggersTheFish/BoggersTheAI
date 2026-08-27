"""Deterministic online GRU baseline for PRIME M26."""

from __future__ import annotations

import torch
from torch import nn


class GRUOnlinePredictor:
    def __init__(
        self,
        *,
        seed: int,
        hidden_size: int = 32,
        learning_rate: float = 0.01,
        chunk_length: int = 32,
    ) -> None:
        torch.set_num_threads(1)

        torch.manual_seed(seed)

        try:
            torch.use_deterministic_algorithms(
                True
            )
        except Exception:
            pass

        self.hidden_size = hidden_size

        self.cell = nn.GRUCell(
            input_size=1,
            hidden_size=hidden_size,
        )

        self.output = nn.Linear(
            hidden_size,
            1,
        )

        self.parameters = (
            list(
                self.cell.parameters()
            )
            + list(
                self.output.parameters()
            )
        )

        self.optimizer = torch.optim.Adam(
            self.parameters,
            lr=learning_rate,
        )

        self.loss_function = (
            nn.BCEWithLogitsLoss()
        )

        self.hidden = torch.zeros(
            1,
            hidden_size,
        )

        self.chunk_length = (
            chunk_length
        )

        self.chunk_h0 = None
        self.chunk_x = []
        self.chunk_y = []

        self.last_loss = None

    @property
    def parameter_count(
        self,
    ) -> int:
        return sum(
            parameter.numel()
            for parameter
            in self.parameters
        )

    def predict(
        self,
        observation: int,
    ) -> int:
        if not self.chunk_x:
            self.chunk_h0 = (
                self.hidden
                .detach()
                .clone()
            )

        x = torch.tensor(
            [[
                float(
                    observation
                )
            ]],
            dtype=torch.float32,
        )

        with torch.no_grad():
            self.hidden = (
                self.cell(
                    x,
                    self.hidden,
                )
            )

            logit = (
                self.output(
                    self.hidden
                )
            )

        self.chunk_x.append(
            float(
                observation
            )
        )

        return int(
            logit.item()
            >= 0.0
        )

    def learn(
        self,
        target: int,
    ) -> None:
        self.chunk_y.append(
            float(
                target
            )
        )

        if (
            len(
                self.chunk_y
            )
            >= self.chunk_length
        ):
            self._train_chunk()

    def _train_chunk(
        self,
    ) -> None:
        if not self.chunk_y:
            return

        if self.chunk_h0 is None:
            raise RuntimeError(
                "missing GRU chunk initial state"
            )

        self.optimizer.zero_grad(
            set_to_none=True
        )

        hidden = (
            self.chunk_h0
        )

        logits = []

        for observation in self.chunk_x:
            x = torch.tensor(
                [[observation]],
                dtype=torch.float32,
            )

            hidden = self.cell(
                x,
                hidden,
            )

            logits.append(
                self.output(
                    hidden
                )
            )

        logit_tensor = (
            torch.cat(
                logits,
                dim=0,
            )
            .reshape(-1)
        )

        target_tensor = torch.tensor(
            self.chunk_y,
            dtype=torch.float32,
        )

        loss = (
            self.loss_function(
                logit_tensor,
                target_tensor,
            )
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            self.parameters,
            max_norm=1.0,
        )

        self.optimizer.step()

        self.last_loss = float(
            loss.detach().item()
        )

        self.chunk_x = []
        self.chunk_y = []
        self.chunk_h0 = None
