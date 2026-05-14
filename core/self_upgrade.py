"""自我升级 Agent：记录失败案例并生成可追溯的 Prompt 优化结果。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from litellm import completion

from config import settings


class SelfUpgradeAgent:
    """负责失败样本沉淀、Prompt 优化与版本化存储。"""

    def __init__(self) -> None:
        self.knowledge_base_path = Path(settings.KNOWLEDGE_BASE_PATH)
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)
        self.failures_file = self.knowledge_base_path / "failures.json"
        self.optimized_prompts_file = self.knowledge_base_path / "optimized_prompts.json"

    def _read_json(self, file_path: Path, default: Any) -> Any:
        """读取 JSON 文件，失败时返回默认值。"""
        if not file_path.exists():
            return default
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _write_json(self, file_path: Path, data: Any) -> None:
        """写入 JSON 文件。"""
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_failure(self, task: str, error: str, agent_output: str) -> None:
        """记录失败案例到 knowledge_base/failures.json。"""
        failures = self._read_json(self.failures_file, [])
        failures.append({"task": task, "error": error, "agent_output": agent_output})
        self._write_json(self.failures_file, failures)

    def optimize_prompt(self, original_prompt: str, failure_cases: list[dict[str, Any]]) -> str:
        """基于失败样本调用 LLM 生成更稳健的优化 Prompt。"""
        if not failure_cases:
            return original_prompt

        prompt = (
            "你是 Prompt 优化专家，请根据失败案例改写系统提示词。\n"
            f"原始 Prompt：{original_prompt}\n"
            f"失败案例：{json.dumps(failure_cases, ensure_ascii=False)}\n"
            "请仅输出优化后的 Prompt 正文。"
        )
        try:
            response = completion(
                model=settings.ORCHESTRATOR_MODEL,
                messages=[{"role": "user", "content": prompt}],
                num_retries=settings.MAX_RETRIES,
            )
            content = response.choices[0].message.content or ""
            return content.strip() or original_prompt
        except Exception:
            return original_prompt

    def analyze_and_upgrade(self) -> dict[str, str]:
        """分析失败样本并更新 optimized_prompts.json。"""
        failures = self._read_json(self.failures_file, [])
        grouped: dict[str, list[dict[str, Any]]] = {}

        # 使用简单规则将失败样本映射到目标 Agent。
        for item in failures:
            task_text = str(item.get("task", "")).lower()
            if "api" in task_text or "天气" in task_text or "搜索" in task_text:
                agent_name = "api_agent"
                base_prompt = "你是 API Agent，优先调用工具并返回可验证结果。"
            elif "代码" in task_text or "code" in task_text:
                agent_name = "sub_agent"
                base_prompt = "你是代码子智能体，输出可执行、可验证的步骤。"
            else:
                agent_name = "orchestrator"
                base_prompt = "你是总调度智能体，先分解任务再协调执行。"

            grouped.setdefault(agent_name, [])
            grouped[agent_name].append({**item, "base_prompt": base_prompt})

        optimized = self._read_json(self.optimized_prompts_file, {})
        for agent_name, cases in grouped.items():
            original_prompt = cases[0].get("base_prompt", "你是 AI 智能体。")
            optimized_prompt = self.optimize_prompt(original_prompt, cases)
            optimized[agent_name] = optimized_prompt

        self._write_json(self.optimized_prompts_file, optimized)
        return optimized

    def get_optimized_prompt(self, agent_name: str) -> str:
        """获取指定 Agent 的最新优化 Prompt。"""
        optimized = self._read_json(self.optimized_prompts_file, {})
        return str(optimized.get(agent_name, ""))
