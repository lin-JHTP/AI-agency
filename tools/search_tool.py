"""搜索工具：优先调用 Serper API，无 Key 时使用模拟结果。"""

from __future__ import annotations

import os
from typing import Any

import requests

from tools.base_tool import BaseTool


class SearchTool(BaseTool):
    """调用网络搜索能力的工具。"""

    name = "search"
    description = "使用 Serper 搜索互联网信息"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
        },
        "required": ["query"],
    }

    def execute(self, **kwargs: Any) -> str:
        """执行搜索请求并返回摘要结果。"""
        query = kwargs.get("query", "").strip()
        if not query:
            return "搜索失败：query 不能为空。"

        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            # 无密钥时返回可读的模拟结果，保证系统可运行。
            return f"[模拟搜索结果] 关键词：{query}。请配置 SERPER_API_KEY 以获取真实结果。"

        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("organic", [])[:3]
            if not items:
                return f"未检索到与“{query}”相关的结果。"

            lines = [f"{idx + 1}. {item.get('title', '无标题')} - {item.get('link', '')}" for idx, item in enumerate(items)]
            return "\n".join(lines)
        except Exception as exc:  # noqa: BLE001 - 需要兜底异常避免主流程崩溃
            return f"搜索调用失败：{exc}"
