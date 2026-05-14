"""项目全局配置模块。"""

from dotenv import load_dotenv

# 加载根目录下 .env，未创建时不会报错。
load_dotenv()

# 主调度模型，切换模型只需修改这一行。
ORCHESTRATOR_MODEL = "deepseek/deepseek-chat"
# 子 Agent 默认模型。
SUB_AGENT_MODEL = "deepseek/deepseek-chat"
# 向量化模型。
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# ChromaDB 本地存储路径。
CHROMA_DB_PATH = "./vector_store"
# 知识库文档目录。
KNOWLEDGE_BASE_PATH = "./knowledge_base"
# 最大子 Agent 并发数。
MAX_SUB_AGENTS = 3
# 模型调用最大重试次数。
MAX_RETRIES = 3
