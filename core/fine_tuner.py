from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(slots=True)
class FineTuningConfig:
    enabled: bool = True
    base_model: str = "unsloth/llama-3.2-1b-instruct"
    max_seq_length: int = 2048
    learning_rate: float = 2e-4
    epochs: int = 1
    adapter_save_path: str = "models/fine_tuned_adapter"
    auto_hotswap: bool = True
    validation_enabled: bool = True
    max_memory_gb: int = 12
    safety_dry_run: bool = True
    train_path: str = "dataset/train.jsonl"
    val_path: str = "dataset/val.jsonl"


class UnslothFineTuner:
    def __init__(self, config: object | None = None) -> None:
        self.config = self._resolve_config(config)
        self.adapter_save_path = Path(self.config.adapter_save_path)

    def fine_tune(self, epochs: int = 1) -> dict:
        if not self.config.enabled:
            return {
                "success": False,
                "skipped": True,
                "reason": "fine_tuning_disabled",
                "adapter_path": str(self.adapter_save_path),
            }

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

        start = time.time()
        requested_epochs = max(1, int(epochs or self.config.epochs))
        try:
            from datasets import load_dataset
            from trl import SFTTrainer
            from transformers import TrainingArguments
            from unsloth import FastLanguageModel

            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.config.base_model,
                max_seq_length=int(self.config.max_seq_length),
                dtype=None,
                load_in_4bit=True,
            )
            model = FastLanguageModel.get_peft_model(
                model,
                r=16,
                target_modules=[
                    "q_proj",
                    "k_proj",
                    "v_proj",
                    "o_proj",
                    "gate_proj",
                    "up_proj",
                    "down_proj",
                ],
                lora_alpha=16,
                lora_dropout=0,
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
                per_device_train_batch_size=2,
                gradient_accumulation_steps=4,
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

    def _resolve_config(self, config: object | None) -> FineTuningConfig:
        if config is None:
            return FineTuningConfig()

        inference_cfg: Dict[str, Any] = {}
        if isinstance(config, dict):
            inference_cfg = config.get("inference", {}) if isinstance(config.get("inference", {}), dict) else {}
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
            base_model=str(fine_cfg.get("base_model", "unsloth/llama-3.2-1b-instruct")),
            max_seq_length=int(fine_cfg.get("max_seq_length", 2048)),
            learning_rate=float(fine_cfg.get("learning_rate", 2e-4)),
            epochs=int(fine_cfg.get("epochs", 1)),
            adapter_save_path=str(fine_cfg.get("adapter_save_path", "models/fine_tuned_adapter")),
            auto_hotswap=bool(fine_cfg.get("auto_hotswap", True)),
            validation_enabled=bool(fine_cfg.get("validation_enabled", True)),
            max_memory_gb=int(fine_cfg.get("max_memory_gb", 12)),
            safety_dry_run=bool(fine_cfg.get("safety_dry_run", True)),
            train_path=str(Path(dataset_cfg.get("output_dir", "dataset")) / "train.jsonl"),
            val_path=str(Path(dataset_cfg.get("output_dir", "dataset")) / "val.jsonl"),
        )
