"""文档 Agent：负责知识库管理、向量检索与任务摘要落盘。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings


class DocAgent:
    """提供文档入库、语义检索、上下文召回能力。"""

    def __init__(self) -> None:
        self.knowledge_base_path = Path(settings.KNOWLEDGE_BASE_PATH)
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)

        # 本地内存兜底，避免外部依赖不可用时整个系统不可用。
        self._fallback_docs: list[dict[str, Any]] = []
        self._vector_store = None
        self._init_vector_store()

    def _init_vector_store(self) -> None:
        """初始化 ChromaDB 向量库，失败时自动降级为内存模式。"""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import Chroma

            embedding = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
            self._vector_store = Chroma(
                collection_name="ai_agency_knowledge",
                embedding_function=embedding,
                persist_directory=settings.CHROMA_DB_PATH,
            )
        except Exception:
            self._vector_store = None

    def add_document(self, content: str, metadata: dict[str, Any]) -> None:
        """将文档向量化后存储到 ChromaDB（或内存兜底）。"""
        if not content.strip():
            return

        if self._vector_store is not None:
            try:
                self._vector_store.add_texts(texts=[content], metadatas=[metadata])
                return
            except Exception:
                # 向量库失败时降级内存，保证业务可继续。
                pass

        self._fallback_docs.append({"content": content, "metadata": metadata})

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """语义检索相关文档并返回统一结构结果。"""
        if not query.strip():
            return []

        if self._vector_store is not None:
            try:
                docs = self._vector_store.similarity_search(query=query, k=top_k)
                return [
                    {"content": doc.page_content, "metadata": doc.metadata or {}}
                    for doc in docs
                ]
            except Exception:
                pass

        # 兜底逻辑：简单关键词匹配最近文档。
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self._fallback_docs:
            score = 1 if query.lower() in item["content"].lower() else 0
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored[:top_k] if score >= 0]

    def auto_summarize_and_save(self, task: str, result: str) -> Path:
        """自动生成任务摘要并落盘到 knowledge_base 目录。"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        file_path = self.knowledge_base_path / f"{today}_task_summary.md"

        # 采用文件追加写入，避免每次读全量文件造成性能损耗。
        section = (
            f"## {now.strftime('%H:%M:%S')}\n\n"
            f"### 任务\n{task}\n\n"
            f"### 结果摘要\n{result}\n\n"
            "---\n\n"
        )
        if not file_path.exists():
            file_path.write_text(f"# 每日任务摘要（{today}）\n\n", encoding="utf-8")
        with file_path.open("a", encoding="utf-8") as file:
            file.write(section)
        return file_path

    def get_relevant_context(self, query: str) -> str:
        """检索并拼接与任务相关的上下文文本。"""
        docs = self.search(query=query, top_k=5)
        if not docs:
            return ""
        return "\n\n".join(item.get("content", "") for item in docs if item.get("content"))
