# AI-agency

一个从零构建的多智能体 AI 助理框架，支持任务调度、工具调用、知识库沉淀、RAG 检索与自我升级。

## 1. 项目介绍与架构图

该项目通过 **Orchestrator + SubAgent Pool** 将复杂任务拆分并并行处理，同时通过工具体系连接外部 API，通过 ChromaDB 管理知识库并支持 RAG 检索。

```text
┌─────────────────────────────────────────────────────────┐
│                  OrchestratorAgent                      │
│   analyze → route → [sub_agents / api_agent] → reduce │
│              → doc_update → respond                     │
└───────────────┬───────────────────────────────┬────────┘
                │                               │
        ┌───────▼────────┐              ┌──────▼─────────┐
        │  SubAgentPool   │              │   APIAgent     │
        │  并行 Map 处理    │              │ 工具注册与调用  │
        └───────┬────────┘              └──────┬─────────┘
                │                               │
        ┌───────▼───────────────────────────────▼────────┐
        │                    DocAgent                     │
        │  文档整理 + 向量检索 + 上下文召回（ChromaDB）     │
        └──────────────────────────┬──────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │ SelfUpgradeAgent │
                          │ 失败分析与 Prompt │
                          │ 自动优化          │
                          └──────────────────┘
```

## 2. 功能特性

- 多智能体调度：LangGraph 有向图编排任务
- 子 Agent 并行处理：Map-Reduce 处理长文本/复杂任务
- API 工具集成：插件式工具自动注册与统一调用
- 知识库与 RAG：任务结果自动入库并可语义检索
- 自我升级：失败案例记录 + Prompt 优化
- 安全配置：`.env` 本地化管理，避免密钥泄露

## 3. 快速开始

### 3.1 克隆项目

```bash
git clone https://github.com/lin-JHTP/AI-agency.git
cd AI-agency
```

### 3.2 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows 使用 venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 配置环境变量

```bash
cp .env.example .env
# 然后编辑 .env，填入你的 API Key
```

### 3.4 运行程序

```bash
python main.py
```

## 4. 各模块说明

- `core/orchestrator.py`：总调度 Agent，负责图工作流与路由
- `core/sub_agent.py`：子 Agent 池，提供并行处理与汇总
- `core/api_agent.py`：工具自动发现、注册、调用、日志记录
- `core/doc_agent.py`：文档入库、检索、上下文召回、摘要落盘
- `core/self_upgrade.py`：失败案例记录与 Prompt 自动优化
- `tools/*.py`：可插拔工具实现（搜索/天气/代码执行）

## 5. 如何切换模型

只需修改 `config/settings.py` 一行，例如：

```python
ORCHESTRATOR_MODEL = "deepseek/deepseek-chat"
```

同理可修改 `SUB_AGENT_MODEL`。

## 6. 如何添加自定义工具

1. 在 `tools/` 下新建文件（例如 `my_tool.py`）
2. 继承 `BaseTool` 并实现 `execute(**kwargs) -> str`
3. 填写 `name`、`description`、`parameters`
4. 启动后 `APIAgent` 会自动扫描并注册该工具

示例：

```python
from tools.base_tool import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "我的自定义工具"
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs):
        return "hello"
```

## 7. 费用说明（推荐 DeepSeek）

- 推荐使用 DeepSeek 作为默认模型，调用成本更低
- 初期开发可小额充值（如 20~50 元）满足大量测试
- 若需切换 OpenAI/Anthropic，只需替换模型名并配置对应 Key

## 8. 注意事项（API Key 安全）

- **不要**提交 `.env` 到公开仓库
- `.gitignore` 已默认忽略 `.env`
- 仅提交 `.env.example` 作为配置模板
- 若误泄露密钥，请立刻在平台后台吊销并重建
