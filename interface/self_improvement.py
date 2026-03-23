from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from ..core.local_llm import LocalLLM

logger = logging.getLogger("boggers.runtime")


class SelfImprovementMixin:
    """Mixin providing self-improvement, fine-tuning, and quality-gate logic.

    Expects the consuming class to supply:
        self.graph, self.config, self.raw_config, self.trace_processor,
        self.fine_tuner, self.local_llm, self._llm_lock, self._fine_cfg,
        self._trace_count_cache, self._trace_count_cache_time,
        self.query_processor, self.min_traces_for_tune,
        self._last_fine_tune_time, self._last_tuned_trace_count
    """

    def build_training_dataset(self) -> dict:
        return self.trace_processor.build_dataset()

    def trigger_self_improvement(self) -> dict:
        return self._auto_fine_tune_check(force=True)

    def fine_tune_and_hotswap(self, epochs: int = 1) -> dict:
        stats = self.fine_tuner.fine_tune(epochs=epochs)
        if stats.get("track") == "cpu_distillora":
            stats["hotswapped"] = False
            return stats
        if not bool(stats.get("success", False)):
            stats["hotswapped"] = False
            return stats

        fine_cfg = self._fine_cfg
        auto_hotswap = (
            bool(fine_cfg.get("auto_hotswap", True))
            if isinstance(fine_cfg, dict)
            else True
        )
        validation_enabled = (
            bool(fine_cfg.get("validation_enabled", True))
            if isinstance(fine_cfg, dict)
            else True
        )
        state = self._get_self_improvement_state()
        previous_best_loss = state.get("best_val_loss")
        new_val_loss = stats.get("val_loss")
        if (
            validation_enabled
            and new_val_loss is not None
            and previous_best_loss is not None
        ):
            if float(new_val_loss) >= float(previous_best_loss):
                stats["hotswapped"] = False
                stats["skipped"] = True
                stats["reason"] = "validation_not_improved"
                stats["previous_best_val_loss"] = float(previous_best_loss)
                return stats

        adapter_path = str(stats.get("adapter_path", ""))

        if validation_enabled and adapter_path:
            test_result = self._run_quality_gate(adapter_path, fine_cfg)
            if not test_result.get("passed", False):
                stats["hotswapped"] = False
                stats["quality_gate"] = test_result
                return stats

        backup_path = None
        if (
            self.local_llm is not None
            and getattr(self.local_llm, "adapter_path", None)
            and Path(str(self.local_llm.adapter_path)).exists()
        ):
            backup_root = Path("models/backups")
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_path = (
                backup_root
                / f"adapter_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            )
            try:
                shutil.copytree(
                    str(self.local_llm.adapter_path),
                    str(backup_path),
                    dirs_exist_ok=True,
                )
            except Exception as exc:
                logger.warning("Backup copy failed: %s", exc)
                backup_path = None

        if auto_hotswap and adapter_path:
            try:
                if self.local_llm is None:
                    ollama_cfg = (
                        self.config.get("inference", {}).get("ollama", {})
                        if isinstance(self.config.get("inference", {}), dict)
                        else {}
                    )
                    self.local_llm = LocalLLM(
                        model=str(ollama_cfg.get("model", "llama3.2")),
                        temperature=float(ollama_cfg.get("temperature", 0.3)),
                        max_tokens=int(ollama_cfg.get("max_tokens", 512)),
                        adapter_path=adapter_path,
                        base_model=(
                            str(
                                fine_cfg.get(
                                    "base_model", "unsloth/llama-3.2-1b-instruct"
                                )
                            )
                            if isinstance(fine_cfg, dict)
                            else "unsloth/llama-3.2-1b-instruct"
                        ),
                        base_url=str(
                            ollama_cfg.get("base_url", "http://localhost:11434")
                        ),
                    )
                else:
                    self.local_llm.load_adapter(
                        adapter_path,
                        base_model=(
                            str(
                                fine_cfg.get(
                                    "base_model", "unsloth/llama-3.2-1b-instruct"
                                )
                            )
                            if isinstance(fine_cfg, dict)
                            else "unsloth/llama-3.2-1b-instruct"
                        ),
                    )
                self.query_processor.local_llm = self.local_llm
                stats["hotswapped"] = True
                lineage_id = (
                    f"finetune:{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
                )
                finetune_content = (
                    f"Fine-tuned adapter from {stats.get('epochs', 1)} epochs, "
                    f"loss={stats.get('loss', 0):.4f}"
                )
                self.graph.add_node(
                    node_id=lineage_id,
                    content=finetune_content,
                    topics=["finetune", "self_improvement", "lineage"],
                    activation=0.1,
                    stability=0.9,
                    base_strength=0.8,
                    attributes={
                        "type": "finetune_lineage",
                        "adapter_path": adapter_path,
                        "epochs": stats.get("epochs", 1),
                        "loss": stats.get("loss", 0.0),
                        "val_loss": stats.get("val_loss"),
                        "wave_cycle": self.graph.get_wave_status().get(
                            "cycle_count", 0
                        ),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as exc:
                rolled_back = False
                if self.local_llm is not None:
                    rolled_back = self.local_llm.load_previous_adapter()
                if not rolled_back and backup_path and self.local_llm is not None:
                    self.local_llm.load_adapter(
                        str(backup_path),
                        base_model=(
                            str(
                                fine_cfg.get(
                                    "base_model", "unsloth/llama-3.2-1b-instruct"
                                )
                            )
                            if isinstance(fine_cfg, dict)
                            else "unsloth/llama-3.2-1b-instruct"
                        ),
                    )
                    rolled_back = True
                stats["hotswapped"] = False
                stats["rollback_applied"] = rolled_back
                stats["error"] = str(exc)
                return stats
        else:
            stats["hotswapped"] = False

        current_trace_count = self._count_traces()
        self._last_fine_tune_time = time.time()
        self._last_tuned_trace_count = current_trace_count
        state_update = {
            "last_fine_tune_time": self._last_fine_tune_time,
            "last_tuned_trace_count": self._last_tuned_trace_count,
        }
        if validation_enabled and new_val_loss is not None:
            if previous_best_loss is None or float(new_val_loss) < float(
                previous_best_loss
            ):
                state_update["best_val_loss"] = float(new_val_loss)
        self._update_self_improvement_state(state_update)
        stats["previous_best_val_loss"] = (
            float(previous_best_loss) if previous_best_loss is not None else None
        )
        stats["best_val_loss"] = self._get_self_improvement_state().get("best_val_loss")
        return stats

    def _auto_fine_tune_check(self, force: bool = False) -> dict:
        inference_cfg = self.config.get("inference", {})
        (
            inference_cfg.get("self_improvement", {})
            if isinstance(inference_cfg, dict)
            else {}
        )
        fine_cfg = self._fine_cfg
        if not isinstance(fine_cfg, dict) or not bool(fine_cfg.get("enabled", False)):
            return {"triggered": False, "reason": "fine_tuning_disabled"}
        if not force and not bool(fine_cfg.get("auto_schedule", True)):
            return {"triggered": False, "reason": "auto_schedule_disabled"}

        current_trace_count = self._count_traces()
        new_traces = max(0, current_trace_count - int(self._last_tuned_trace_count))
        nightly_hour = int(self.config.get("os_loop", {}).get("nightly_hour_utc", 3))
        should_run_nightly = datetime.now(timezone.utc).hour == nightly_hour
        should_run_threshold = new_traces >= int(self.min_traces_for_tune)

        if not force and not (should_run_nightly or should_run_threshold):
            return {
                "triggered": False,
                "reason": "conditions_not_met",
                "new_traces": new_traces,
            }

        epochs = int(fine_cfg.get("epochs", 1))
        stats = self.fine_tune_and_hotswap(epochs=epochs)
        stats["triggered"] = True
        stats["new_traces"] = new_traces
        return stats

    def _count_traces(self) -> int:
        now = time.time()
        if now - self._trace_count_cache_time < 60.0:
            return self._trace_count_cache
        inference_cfg = self.config.get("inference", {})
        self_improvement_cfg = (
            inference_cfg.get("self_improvement", {})
            if isinstance(inference_cfg, dict)
            else {}
        )
        traces_dir = (
            str(self_improvement_cfg.get("traces_dir", "traces"))
            if isinstance(self_improvement_cfg, dict)
            else "traces"
        )
        traces_path = Path(traces_dir)
        if not traces_path.exists():
            return 0
        total = 0
        for file_path in traces_path.glob("*.jsonl"):
            try:
                total += len(file_path.read_text(encoding="utf-8").splitlines())
            except Exception:
                continue
        self._trace_count_cache = total
        self._trace_count_cache_time = now
        return total

    def _get_self_improvement_state(self) -> dict:
        node = self.graph.get_node("runtime:self_improvement")
        if node is None:
            return {}
        attrs = getattr(node, "attributes", {})
        return attrs if isinstance(attrs, dict) else {}

    def _update_self_improvement_state(self, updates: dict) -> None:
        node = self.graph.get_node("runtime:self_improvement")
        if node is None:
            self._ensure_self_improvement_node()
            node = self.graph.get_node("runtime:self_improvement")
        if node is None:
            return
        attributes = getattr(node, "attributes", {})
        if not isinstance(attributes, dict):
            attributes = {}
        attributes.update(updates)
        node.attributes = attributes
        self.graph.save()

    def _run_quality_gate(self, adapter_path: str, fine_cfg: dict) -> dict:
        try:
            if self.local_llm is None:
                return {"passed": True, "reason": "no_llm_to_test"}
            with self._llm_lock:
                result = self.local_llm.summarize_and_hypothesize(
                    "Test context about TS-OS graph wave architecture.",
                    "What is the core TS-OS loop?",
                )
            confidence = float(result.get("confidence", 0.0))
            has_answer = bool(str(result.get("answer", "")).strip())
            passed = has_answer and confidence > 0.3
            return {
                "passed": passed,
                "confidence": confidence,
                "has_answer": has_answer,
            }
        except Exception as exc:
            logger.warning("Quality gate failed: %s", exc)
            return {"passed": False, "error": str(exc)}

    def _warn_self_improvement(self) -> None:
        inference_cfg = self.config.get("inference", {})
        if not isinstance(inference_cfg, dict):
            return
        si_cfg = inference_cfg.get("self_improvement", {})
        if not isinstance(si_cfg, dict):
            return
        ft_cfg = si_cfg.get("fine_tuning", {})
        if isinstance(ft_cfg, dict) and bool(ft_cfg.get("enabled", False)):
            logger.warning(
                "Self-improvement (fine-tuning) is EXPERIMENTAL and can "
                "degrade model quality. Ensure validation_enabled=true and "
                "safety_dry_run=true for safe testing."
            )

    def _resolve_fine_cfg(self) -> dict:
        inference_cfg = self.config.get("inference", {})
        si_cfg = (
            inference_cfg.get("self_improvement", {})
            if isinstance(inference_cfg, dict)
            else {}
        )
        return si_cfg.get("fine_tuning", {}) if isinstance(si_cfg, dict) else {}
