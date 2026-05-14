"""命令行入口：启动多智能体 AI 助理。"""

from __future__ import annotations

import logging

from rich.console import Console
from rich.panel import Panel

from core.orchestrator import OrchestratorAgent
from core.self_upgrade import SelfUpgradeAgent


def setup_logging() -> None:
    """初始化日志配置。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def main() -> None:
    """程序主入口，提供交互式命令行会话。"""
    setup_logging()
    console = Console()
    orchestrator = OrchestratorAgent()
    self_upgrade = SelfUpgradeAgent()

    console.print(
        Panel(
            "欢迎使用多智能体 AI 助理！\n"
            "输入任务开始对话；输入 [bold]tools[/bold] 查看工具；\n"
            "输入 [bold]upgrade[/bold] 执行自我升级分析；输入 [bold]exit[/bold] 退出。",
            title="AI-Agency",
        )
    )
    console.print(f"可用工具：{', '.join(orchestrator.api_agent.list_tools()) or '无'}")

    while True:
        try:
            user_input = console.input("\n[bold cyan]你[/bold cyan] > ").strip()
            if not user_input:
                continue

            if user_input.lower() == "exit":
                console.print("已退出，欢迎下次使用。")
                break

            if user_input.lower() == "tools":
                tools = orchestrator.api_agent.list_tools()
                console.print(f"当前工具：{', '.join(tools) if tools else '暂无可用工具'}")
                continue

            if user_input.lower() == "upgrade":
                upgraded = self_upgrade.analyze_and_upgrade()
                console.print(f"自我升级完成，已更新 {len(upgraded)} 个 Agent Prompt。")
                continue

            result = orchestrator.run(user_input)
            console.print(f"[bold green]助手[/bold green] > {result}")
        except KeyboardInterrupt:
            console.print("\n检测到中断，输入 exit 可安全退出。")
        except Exception as exc:  # noqa: BLE001 - 全局兜底，避免程序崩溃
            console.print(f"发生异常：{exc}")
            try:
                self_upgrade.record_failure(task=user_input, error=str(exc), agent_output="")
            except Exception:
                # 失败记录失败时仅静默处理，防止二次异常中断会话。
                pass


if __name__ == "__main__":
    main()
