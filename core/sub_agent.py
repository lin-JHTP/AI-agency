"""子 Agent 池：并行处理任务分片并进行结果汇总。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from litellm import completion

from config import settings


@dataclass
class SubAgent:
    """单个子 Agent，负责一次 LLM 调用。"""

    agent_id: int

    def run(self, task: str, context: str) -> str:
        """执行子任务并返回文本结果。"""
        prompt = (
            f"你是子智能体 #{self.agent_id}。\n"
            "请聚焦当前分片内容，提炼关键信息并给出可执行结论。\n"
            f"任务说明：{task}\n"
            f"分片内容：\n{context}"
        )
        try:
            response = completion(
                model=settings.SUB_AGENT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                num_retries=settings.MAX_RETRIES,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001 - 兜底异常，避免并行任务中断
            return f"子 Agent #{self.agent_id} 调用失败：{exc}"


class SubAgentPool:
    """管理多个子 Agent 实例并提供并行处理能力。"""

    def __init__(self, size: int = settings.MAX_SUB_AGENTS) -> None:
        # 至少保留一个子 Agent，防止非法配置。
        safe_size = max(1, size)
        self.size = safe_size
        self.agents = [SubAgent(agent_id=idx + 1) for idx in range(safe_size)]

    def parallel_process(self, chunks: list[str], task: str) -> list[str]:
        """并行处理文本块并按完成结果汇总。"""
        if not chunks:
            return []

        # 使用 None 作为初始值，避免空字符串掩盖异常任务。
        results: list[str | None] = [None] * len(chunks)
        max_workers = min(self.size, len(chunks))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 记录 future 到索引的映射，确保返回结果顺序稳定。
            future_to_index = {
                executor.submit(self.agents[idx % self.size].run, task, chunk): idx
                for idx, chunk in enumerate(chunks)
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as exc:  # noqa: BLE001 - 兜底异常
                    results[index] = f"子任务执行异常：{exc}"
        # 将未填充项替换为显式错误提示，确保调用方可感知异常。
        return [item if item is not None else "子任务未返回结果。" for item in results]

    def reduce(self, results: list[str], original_task: str) -> str:
        """将多个子结果汇总为最终输出。"""
        if not results:
            return "未获得可汇总的子任务结果。"

        merged_context = "\n\n".join(f"[子结果 {idx + 1}]\n{item}" for idx, item in enumerate(results))
        prompt = (
            "你是结果汇总智能体，请综合多个子结果，输出最终清晰结论。\n"
            f"原始任务：{original_task}\n"
            f"子结果汇总：\n{merged_context}"
        )
        try:
            response = completion(
                model=settings.ORCHESTRATOR_MODEL,
                messages=[{"role": "user", "content": prompt}],
                num_retries=settings.MAX_RETRIES,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001 - 兜底异常
            # 当汇总模型失败时，退化为拼接文本，保证主流程可继续。
            fallback = "\n".join(results)
            return f"汇总模型调用失败：{exc}\n\n回退结果：\n{fallback}"
