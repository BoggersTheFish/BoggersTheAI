from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("boggers.finetune")


@dataclass(slots=True)
class FineTuningConfig:
    """``track`` selects GPU QLoRA vs CPU graph-first DistilLoRA-style path."""

    enabled: bool = True
    track: str = "gpu_qlora"  # gpu_qlora | cpu_distillora
    base_model: str = "unsloth/llama-3.2-1b-instruct"
    max_seq_length: int = 2048
    learning_rate: float = 2e-4
    epochs: int = 1
    adapter_save_path: str = "models/fine_tuned_adapter"
    auto_hotswap: bool = True
    validation_enabled: bool = True
    max_memory_gb: int = 12
    safety_dry_run: bool = True
    lora_r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    target_modules: str = "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    train_path: str = "dataset/train.jsonl"
    val_path: str = "dataset/val.jsonl"


class UnslothFineTuner:
    def __init__(
        self,
        config: object | None = None,
        graph: object | None = None,
    ) -> None:
        self.config = self._resolve_config(config)
        self.adapter_save_path = Path(self.config.adapter_save_path)
        self.graph = graph

    def fine_tune(self, epochs: int = 1) -> dict:
        if not self.config.enabled:
            return {
                "success": False,
                "skipped": True,
                "reason": "fine_tuning_disabled",
                "adapter_path": str(self.adapter_save_path),
            }

        if self.config.track == "cpu_distillora":
            return self._cpu_distillora_run(epochs=epochs)

        train_path = Path(self.config.train_path)
        val_path = Path(self.config.val_path)
        if not train_path.exists():
            return {
                "success": False,
                "skipped": True,
                "reason": "dataset_missing",
                "adapter_path": str(self.adapter_save_path),
            }
        if self.config.safety_dry_run:
            return {
                "success": False,
                "skipped": True,
                "reason": "safety_dry_run_enabled",
                "adapter_path": str(self.adapter_save_path),
                "epochs": max(1, int(epochs or self.config.epochs)),
                "validation_enabled": bool(self.config.validation_enabled),
            }

        try:
            import torch

            if self.config.track == "gpu_qlora" and not torch.cuda.is_available():
                return {
                    "success": False,
                    "skipped": True,
                    "reason": "gpu_qlora_requires_cuda",
                    "adapter_path": str(self.adapter_save_path),
                    "message": (
                        "Set inference.self_improvement.fine_tuning.track to "
                        "cpu_distillora on CPU-only hosts."
                    ),
                }
        except Exception:
            pass

        start = time.time()
        requested_epochs = max(1, int(epochs or self.config.epochs))

        try:
            import torch

            if torch.cuda.is_available():
                gpu_mem_gb = torch.cuda.get_device_properties(0).total_mem / (1024**3)
                if gpu_mem_gb < float(self.config.max_memory_gb) * 0.5:
                    logger.warning(
                        "GPU memory %.1fGB may be insufficient (config max: %dGB)",
                        gpu_mem_gb,
                        self.config.max_memory_gb,
                    )
        except Exception:
            pass

        try:
            from datasets import load_dataset
            from transformers import TrainingArguments
            from trl import SFTTrainer
            from unsloth import FastLanguageModel

            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.config.base_model,
                max_seq_length=int(self.config.max_seq_length),
                dtype=None,
                load_in_4bit=True,
            )
            model = FastLanguageModel.get_peft_model(
                model,
                r=self.config.lora_r,
                target_modules=self.config.target_modules.split(","),
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                bias="none",
                use_gradient_checkpointing=True,
            )

            data_files: Dict[str, str] = {"train": str(train_path)}
            if val_path.exists():
                data_files["validation"] = str(val_path)
            dataset = load_dataset("json", data_files=data_files)

            def _to_text(example: Dict[str, Any]) -> Dict[str, str]:
                instruction = str(example.get("instruction", "")).strip()
                input_text = str(example.get("input", "")).strip()
                output_text = str(example.get("output", "")).strip()
                joined = (
                    "### Instruction:\n"
                    f"{instruction}\n\n"
                    "### Input:\n"
                    f"{input_text}\n\n"
                    "### Response:\n"
                    f"{output_text}"
                )
                return {"text": joined}

            train_dataset = dataset["train"].map(_to_text)
            eval_dataset = dataset.get("validation")
            if eval_dataset is not None:
                eval_dataset = eval_dataset.map(_to_text)

            args = TrainingArguments(
                output_dir=str(self.adapter_save_path / "checkpoints"),
                per_device_train_batch_size=self.config.batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                learning_rate=float(self.config.learning_rate),
                num_train_epochs=requested_epochs,
                logging_steps=5,
                save_strategy="no",
                evaluation_strategy="no",
                report_to=[],
            )

            trainer = SFTTrainer(
                model=model,
                tokenizer=tokenizer,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                dataset_text_field="text",
                max_seq_length=int(self.config.max_seq_length),
                args=args,
            )
            train_output = trainer.train()
            logger.info(
                "Training complete: epochs=%d loss=%.4f duration=%.1fs adapter=%s",
                requested_epochs,
                float(getattr(train_output, "training_loss", 0.0)),
                time.time() - start,
                str(self.adapter_save_path),
            )
            val_loss = None
            if bool(self.config.validation_enabled) and eval_dataset is not None:
                eval_result = trainer.evaluate()
                if isinstance(eval_result, dict) and "eval_loss" in eval_result:
                    val_loss = float(eval_result["eval_loss"])

            self.adapter_save_path.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(str(self.adapter_save_path))
            tokenizer.save_pretrained(str(self.adapter_save_path))

            duration = time.time() - start
            return {
                "success": True,
                "adapter_path": str(self.adapter_save_path),
                "epochs": requested_epochs,
                "loss": float(getattr(train_output, "training_loss", 0.0)),
                "val_loss": val_loss,
                "duration_seconds": round(duration, 2),
            }
        except Exception as exc:
            duration = time.time() - start
            return {
                "success": False,
                "adapter_path": str(self.adapter_save_path),
                "epochs": requested_epochs,
                "error": str(exc),
                "duration_seconds": round(duration, 2),
            }

    def _cpu_distillora_run(self, epochs: int = 1) -> dict:
        """
        CPU-only DistilLoRA-style path: graph consolidation + trace stats.
        """
        start = time.time()
        self.adapter_save_path.mkdir(parents=True, exist_ok=True)
        stats_path = self.adapter_save_path / "cpu_distillora_stats.json"
        train_path = Path(self.config.train_path)
        n_samples = 0
        if train_path.exists():
            with train_path.open(encoding="utf-8") as fh:
                n_samples = sum(1 for _ in fh)

        graph_info: Dict[str, Any] = {}
        if self.graph is not None:
            pruned = 0
            try:
                pr_fn = getattr(self.graph, "prune", None)
                if callable(pr_fn):
                    pruned = int(pr_fn(threshold=0.15))
                sv = getattr(self.graph, "save", None)
                if callable(sv):
                    sv()
            except Exception as exc:
                logger.warning("cpu_distillora graph pass: %s", exc)
                pruned = 0
            graph_info = {
                "graph_pruned": pruned,
                "graph_nodes": len(getattr(self.graph, "nodes", {}) or {}),
            }

        payload = {
            "track": "cpu_distillora",
            "epochs": max(1, int(epochs)),
            "train_samples_seen": n_samples,
            "sample_run": {
                "mode": "cpu_distillora",
                "note": "Graph consolidation + dataset scan (no GPU torch session).",
                "simulated_training_loss": 0.0,
            },
            **graph_info,
        }
        stats_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        duration = time.time() - start
        return {
            "success": True,
            "skipped": False,
            "reason": "cpu_distillora_completed",
            "adapter_path": str(self.adapter_save_path),
            "track": "cpu_distillora",
            "message": (
                "CPU DistilLoRA: graph consolidation + dataset stats; "
                "no GPU session."
            ),
            "duration_seconds": round(duration, 3),
            "stats_path": str(stats_path),
            "train_samples_seen": n_samples,
            "epochs": max(1, int(epochs)),
            **graph_info,
        }

    def _resolve_config(self, config: object | None) -> FineTuningConfig:
        if config is None:
            return FineTuningConfig()

        inference_cfg: Dict[str, Any] = {}
        if isinstance(config, dict):
            inference_cfg = (
                config.get("inference", {})
                if isinstance(config.get("inference", {}), dict)
                else {}
            )
        else:
            maybe = getattr(config, "inference", {})
            inference_cfg = maybe if isinstance(maybe, dict) else {}

        self_improvement_cfg = (
            inference_cfg.get("self_improvement", {})
            if isinstance(inference_cfg.get("self_improvement", {}), dict)
            else {}
        )
        fine_cfg = (
            self_improvement_cfg.get("fine_tuning", {})
            if isinstance(self_improvement_cfg.get("fine_tuning", {}), dict)
            else {}
        )
        dataset_cfg = (
            self_improvement_cfg.get("dataset_build", {})
            if isinstance(self_improvement_cfg.get("dataset_build", {}), dict)
            else {}
        )

        return FineTuningConfig(
            enabled=bool(fine_cfg.get("enabled", True)),
            track=str(fine_cfg.get("track", "gpu_qlora")),
            base_model=str(fine_cfg.get("base_model", "unsloth/llama-3.2-1b-instruct")),
            max_seq_length=int(fine_cfg.get("max_seq_length", 2048)),
            learning_rate=float(fine_cfg.get("learning_rate", 2e-4)),
            epochs=int(fine_cfg.get("epochs", 1)),
            adapter_save_path=str(
                fine_cfg.get("adapter_save_path", "models/fine_tuned_adapter")
            ),
            auto_hotswap=bool(fine_cfg.get("auto_hotswap", True)),
            validation_enabled=bool(fine_cfg.get("validation_enabled", True)),
            max_memory_gb=int(fine_cfg.get("max_memory_gb", 12)),
            safety_dry_run=bool(fine_cfg.get("safety_dry_run", True)),
            lora_r=int(fine_cfg.get("lora_r", 16)),
            lora_alpha=int(fine_cfg.get("lora_alpha", 16)),
            lora_dropout=float(fine_cfg.get("lora_dropout", 0.0)),
            target_modules=str(
                fine_cfg.get(
                    "target_modules",
                    "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj",
                )
            ),
            batch_size=int(fine_cfg.get("batch_size", 2)),
            gradient_accumulation_steps=int(
                fine_cfg.get("gradient_accumulation_steps", 4)
            ),
            train_path=str(
                Path(dataset_cfg.get("output_dir", "dataset")) / "train.jsonl"
            ),
            val_path=str(Path(dataset_cfg.get("output_dir", "dataset")) / "val.jsonl"),
        )
