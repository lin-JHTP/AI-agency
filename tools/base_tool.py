"""工具抽象基类，定义统一工具协议。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """所有工具都应继承该基类。"""

    # 工具名称，用于路由调用。
    name: str = "base_tool"
    # 工具说明，帮助 Agent 理解用途。
    description: str = "基础工具"
    # 参数定义，兼容 OpenAI Function Calling。
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """执行工具逻辑，返回字符串结果。"""

    def to_openai_function(self) -> dict[str, Any]:
        """将工具信息转换为 OpenAI Function Calling 结构。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
