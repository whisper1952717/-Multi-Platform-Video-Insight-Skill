"""InsightMemory — 洞察记忆模块（可选），支持向量检索历史洞察。"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class InsightMemory:
    """洞察记忆模块，使用 ChromaDB 或 FAISS 存储历史洞察。"""

    def __init__(self, persist_dir: str = "./data/memory", backend: str = "chromadb"):
        self._persist_dir = persist_dir
        self._backend = backend
        self._collection = None
        self._initialized = False

    def _init_backend(self) -> bool:
        """延迟初始化向量存储后端。"""
        if self._initialized:
            return True
        try:
            if self._backend == "chromadb":
                import chromadb
                client = chromadb.PersistentClient(path=self._persist_dir)
                self._collection = client.get_or_create_collection("insights")
                self._initialized = True
                return True
        except ImportError:
            logger.warning("chromadb 未安装，InsightMemory 不可用")
        except Exception as e:
            logger.error(f"[memory] 初始化失败: {e}")
        return False

    def store(self, run_id: str, insights: dict, metadata: Optional[dict] = None) -> bool:
        """存储一次运行的聚合洞察。"""
        if not self._init_backend():
            return False
        try:
            doc = json.dumps(insights, ensure_ascii=False)
            self._collection.add(
                documents=[doc],
                ids=[run_id],
                metadatas=[metadata or {}],
            )
            return True
        except Exception as e:
            logger.error(f"[memory] 存储失败: {e}")
            return False

    def query(self, query_text: str, n_results: int = 5) -> List[dict]:
        """基于向量检索历史洞察。"""
        if not self._init_backend():
            return []
        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results,
            )
            docs = results.get("documents", [[]])[0]
            return [json.loads(d) for d in docs]
        except Exception as e:
            logger.error(f"[memory] 查询失败: {e}")
            return []
