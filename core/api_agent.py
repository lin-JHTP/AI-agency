"""API Agent：负责工具注册、发现与统一调用。"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class APIAgent:
    """统一管理工具生命周期与调用过程。"""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._auto_register_tools()

    def _auto_register_tools(self) -> None:
        """自动加载 tools 目录下所有 BaseTool 子类。"""
        tools_dir = Path(__file__).resolve().parent.parent / "tools"
        for module_info in pkgutil.iter_modules([str(tools_dir)]):
            module_name = module_info.name
            if module_name in {"__init__", "base_tool"}:
                continue

            full_module_name = f"tools.{module_name}"
            try:
                module = importlib.import_module(full_module_name)
            except Exception as exc:  # noqa: BLE001 - 跳过异常模块，不影响主流程
                logger.warning("加载工具模块失败 %s: %s", full_module_name, exc)
                continue

            for _, cls in inspect.getmembers(module, inspect.isclass):
                if cls is BaseTool or not issubclass(cls, BaseTool):
                    continue
                try:
                    instance = cls()
                    self.register_tool(instance)
                except Exception as exc:  # noqa: BLE001 - 跳过异常工具，不影响主流程
                    logger.warning("注册工具失败 %s: %s", cls.__name__, exc)

    def register_tool(self, tool: BaseTool) -> None:
        """注册单个工具实例。"""
        self._tools[tool.name] = tool

    def call_tool(self, tool_name: str, **kwargs: Any) -> str:
        """调用指定工具并记录日志。"""
        tool = self._tools.get(tool_name)
        if tool is None:
            return f"工具不存在：{tool_name}"

        try:
            result = tool.execute(**kwargs)
            logger.info("工具调用成功 tool=%s kwargs=%s", tool_name, kwargs)
            return result
        except Exception as exc:  # noqa: BLE001 - 保证工具异常不会击穿主流程
            logger.exception("工具调用失败 tool=%s", tool_name)
            return f"工具调用失败：{exc}"

    def list_tools(self) -> list[str]:
        """返回已注册工具名称列表。"""
        return sorted(self._tools.keys())
