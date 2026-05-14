"""代码执行工具：在受限进程中执行 Python 代码。"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from typing import Any

from tools.base_tool import BaseTool


class CodeExecTool(BaseTool):
    """受限执行用户提供的 Python 代码片段。"""

    name = "code_exec"
    description = "在受限沙箱中执行 Python 代码并返回结果"
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "需要执行的 Python 代码"},
        },
        "required": ["code"],
    }

    _blocked_builtin_calls = {
        "__import__",
        "eval",
        "exec",
        "open",
        "compile",
        "input",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "breakpoint",
    }

    def _is_safe_code(self, code: str) -> tuple[bool, str]:
        """使用 AST 做基础安全校验，拒绝高风险语法。"""
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, f"语法错误：{exc}"

        for node in ast.walk(tree):
            # 禁止 import，避免访问系统与网络能力。
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False, "不允许使用 import 语句。"
            # 禁止全局声明与异常抛出，减少滥用风险。
            if isinstance(node, (ast.Global, ast.Nonlocal, ast.Raise)):
                return False, "不允许使用全局声明或主动抛出异常。"
            # 禁止 dunder 属性访问，降低逃逸可能。
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return False, "不允许访问双下划线属性。"
            # 检查函数调用是否包含高风险内建函数。
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in self._blocked_builtin_calls:
                    return False, f"不允许调用高风险函数：{node.func.id}"

        return True, ""

    def execute(self, **kwargs: Any) -> str:
        """执行代码并在 10 秒超时后中止。"""
        code = kwargs.get("code", "")
        if not code.strip():
            return "代码执行失败：code 不能为空。"

        is_safe, reason = self._is_safe_code(code)
        if not is_safe:
            return f"代码执行被拒绝：{reason}"

        try:
            # 使用临时目录 + 隔离模式运行，尽量减少对宿主环境影响。
            with tempfile.TemporaryDirectory(prefix="ai_agency_exec_") as tmp_dir:
                result = subprocess.run(
                    [sys.executable, "-I", "-S", "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    cwd=tmp_dir,
                    env={"PYTHONIOENCODING": "utf-8"},
                )
            output = (result.stdout or "").strip()
            error = (result.stderr or "").strip()
            if result.returncode == 0:
                return output or "代码执行成功（无输出）。"
            return f"代码执行失败（退出码 {result.returncode}）：{error or '未知错误'}"
        except subprocess.TimeoutExpired:
            return "代码执行超时：已超过 10 秒限制。"
        except Exception as exc:  # noqa: BLE001 - 需要兜底异常避免主流程崩溃
            return f"代码执行异常：{exc}"
