"""总调度 Agent：使用 LangGraph 编排多智能体工作流。"""

from __future__ import annotations

from enum import Enum
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from core.api_agent import APIAgent
from core.doc_agent import DocAgent
from core.sub_agent import SubAgentPool


class TaskType(str, Enum):
    """任务类型枚举。"""

    SIMPLE_QA = "SIMPLE_QA"
    LONG_DOCUMENT = "LONG_DOCUMENT"
    API_REQUIRED = "API_REQUIRED"
    CODE_TASK = "CODE_TASK"


class OrchestratorState(TypedDict, total=False):
    """LangGraph 在节点间传递的状态结构。"""

    user_input: str
    task_type: str
    chunks: list[str]
    partial_results: list[str]
    reduced_result: str
    final_response: str
    context: str


class OrchestratorAgent:
    """总调度 Agent，负责任务分析、分发、汇总与知识沉淀。"""

    def __init__(self) -> None:
        self.sub_agent_pool = SubAgentPool()
        self.api_agent = APIAgent()
        self.doc_agent = DocAgent()
        self.graph = self._build_graph()

    def analyze_task(self, user_input: str) -> TaskType:
        """分析任务类型并决定处理路径。"""
        text = user_input.lower()
        if any(keyword in text for keyword in ["天气", "weather", "搜索", "search", "api"]):
            return TaskType.API_REQUIRED
        if any(keyword in text for keyword in ["代码", "python", "bug", "debug", "函数"]):
            return TaskType.CODE_TASK
        if len(user_input) > 1200 or user_input.count("\n") > 15:
            return TaskType.LONG_DOCUMENT
        return TaskType.SIMPLE_QA

    def _split_text(self, text: str, chunk_size: int = 800) -> list[str]:
        """将长文本切分为多个分片，用于 Map 阶段并行处理。"""
        if len(text) <= chunk_size:
            return [text]
        return [text[idx : idx + chunk_size] for idx in range(0, len(text), chunk_size)]

    def _build_graph(self):
        """构建 LangGraph：analyze → route → worker → reduce → doc_update → respond。"""
        workflow = StateGraph(OrchestratorState)
        workflow.add_node("analyze", self._node_analyze)
        workflow.add_node("route", self._node_route)
        workflow.add_node("sub_agents", self._node_sub_agents)
        workflow.add_node("api_agent", self._node_api_agent)
        workflow.add_node("reduce", self._node_reduce)
        workflow.add_node("doc_update", self._node_doc_update)
        workflow.add_node("respond", self._node_respond)

        workflow.add_edge(START, "analyze")
        workflow.add_edge("analyze", "route")
        workflow.add_conditional_edges(
            "route",
            self._route_after_analysis,
            {
                "sub_agents": "sub_agents",
                "api_agent": "api_agent",
            },
        )
        workflow.add_edge("sub_agents", "reduce")
        workflow.add_edge("api_agent", "reduce")
        workflow.add_edge("reduce", "doc_update")
        workflow.add_edge("doc_update", "respond")
        workflow.add_edge("respond", END)

        return workflow.compile()

    def _node_analyze(self, state: OrchestratorState) -> OrchestratorState:
        """分析输入任务并准备基础上下文。"""
        user_input = state.get("user_input", "")
        task_type = self.analyze_task(user_input)
        context = self.doc_agent.get_relevant_context(user_input)
        return {**state, "task_type": task_type.value, "context": context}

    def _node_route(self, state: OrchestratorState) -> OrchestratorState:
        """路由节点：保留状态，路由逻辑由条件边控制。"""
        return state

    def _route_after_analysis(self, state: OrchestratorState) -> str:
        """根据任务类型决定后续执行节点。"""
        task_type = state.get("task_type", TaskType.SIMPLE_QA.value)
        return "api_agent" if task_type == TaskType.API_REQUIRED.value else "sub_agents"

    def _node_sub_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Map 阶段：切分输入并分发给子 Agent 池并行处理。"""
        user_input = state.get("user_input", "")
        context = state.get("context", "")
        task_type = state.get("task_type", TaskType.SIMPLE_QA.value)

        task_instruction = {
            TaskType.SIMPLE_QA.value: "请回答问题并给出关键依据。",
            TaskType.LONG_DOCUMENT.value: "请总结分片核心观点与结论。",
            TaskType.CODE_TASK.value: "请分析代码任务并给出可执行步骤。",
        }.get(task_type, "请处理任务并输出结果。")

        combined_input = f"{user_input}\n\n相关上下文：\n{context}" if context else user_input
        chunks = self._split_text(combined_input)
        results = self.sub_agent_pool.parallel_process(chunks=chunks, task=task_instruction)
        return {**state, "chunks": chunks, "partial_results": results}

    def _node_api_agent(self, state: OrchestratorState) -> OrchestratorState:
        """API 阶段：根据输入语义选择合适工具执行。"""
        user_input = state.get("user_input", "")
        text = user_input.lower()

        if any(keyword in text for keyword in ["天气", "weather"]):
            # 提取城市名的简化规则：取最后一个词作为城市。
            city = user_input.strip().split()[-1] if user_input.strip().split() else "Beijing"
            tool_result = self.api_agent.call_tool("weather", city=city)
        elif any(keyword in text for keyword in ["搜索", "search", "查一下"]):
            tool_result = self.api_agent.call_tool("search", query=user_input)
        elif any(keyword in text for keyword in ["执行代码", "run code", "python"]):
            tool_result = self.api_agent.call_tool("code_exec", code=user_input)
        else:
            tool_result = "未匹配到明确工具，建议使用 tools 命令查看可用工具。"

        return {**state, "partial_results": [tool_result]}

    def _node_reduce(self, state: OrchestratorState) -> OrchestratorState:
        """Reduce 阶段：汇总子结果形成统一输出。"""
        partial_results = state.get("partial_results", [])
        user_input = state.get("user_input", "")

        if len(partial_results) <= 1:
            reduced = partial_results[0] if partial_results else "未生成有效结果。"
        else:
            reduced = self.sub_agent_pool.reduce(results=partial_results, original_task=user_input)

        return {**state, "reduced_result": reduced}

    def _node_doc_update(self, state: OrchestratorState) -> OrchestratorState:
        """任务完成后更新知识库与摘要文件。"""
        user_input = state.get("user_input", "")
        reduced_result = state.get("reduced_result", "")

        try:
            self.doc_agent.auto_summarize_and_save(task=user_input, result=reduced_result)
            self.doc_agent.add_document(
                content=f"任务：{user_input}\n结果：{reduced_result}",
                metadata={"source": "orchestrator_run"},
            )
        except Exception:
            # 文档更新失败不应阻断主流程。
            pass

        return state

    def _node_respond(self, state: OrchestratorState) -> OrchestratorState:
        """最终响应节点。"""
        return {**state, "final_response": state.get("reduced_result", "未生成回复。")}

    def run(self, user_input: str) -> str:
        """主入口：执行图工作流并返回最终结果。"""
        result = self.graph.invoke({"user_input": user_input})
        return result.get("final_response", "系统未返回结果。")
