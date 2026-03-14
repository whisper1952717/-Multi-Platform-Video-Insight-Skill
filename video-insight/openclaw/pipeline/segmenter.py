"""VideoSegmenter — 语义分段模块，不消耗 LLM token。"""
from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


class VideoSegmenter:
    """使用 semantic-text-splitter 进行语义分段。"""

    def __init__(self, max_chunk_size: int = 2000):
        self._max_chunk_size = max_chunk_size
        self._splitter = None  # 延迟加载

    def _get_splitter(self):
        if self._splitter is None:
            try:
                from semantic_text_splitter import TextSplitter
                self._splitter = TextSplitter(self._max_chunk_size)
            except ImportError:
                logger.warning("semantic-text-splitter 未安装，使用简单分段")
                self._splitter = _FallbackSplitter(self._max_chunk_size)
        return self._splitter

    def segment(self, cleaned_text: str) -> List[str]:
        """基于语义相似度分段，返回文本片段列表。"""
        if not cleaned_text.strip():
            return []
        splitter = self._get_splitter()
        chunks = splitter.chunks(cleaned_text)
        return [c for c in chunks if c.strip()]


class _FallbackSplitter:
    """当 semantic-text-splitter 不可用时的简单分段器。"""

    def __init__(self, max_size: int):
        self._max_size = max_size

    def chunks(self, text: str) -> List[str]:
        import re
        sentences = re.split(r"[。！？.!?\n]", text)
        chunks = []
        current = []
        current_len = 0
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if current_len + len(s) > self._max_size and current:
                chunks.append("。".join(current))
                current = [s]
                current_len = len(s)
            else:
                current.append(s)
                current_len += len(s)
        if current:
            chunks.append("。".join(current))
        return chunks
