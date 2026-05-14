"""代码执行工具：在受限进程中执行 Python 代码。"""

from __future__ import annotations

import subprocess
import sys
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

    def execute(self, **kwargs: Any) -> str:
        """执行代码并在 10 秒超时后中止。"""
        code = kwargs.get("code", "")
        if not code.strip():
            return "代码执行失败：code 不能为空。"

        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
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
