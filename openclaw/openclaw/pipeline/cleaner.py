"""TranscriptCleaner — 本地规则引擎清洗转录文本，不消耗 LLM token。"""
from __future__ import annotations

import re
from typing import List, Optional, Set

# 口头禅词库
FILLER_WORDS: Set[str] = {
    "嗯", "啊", "哦", "呢", "吧", "嘛", "哈", "呀", "哎", "唉",
    "那个", "这个", "就是", "然后", "对吧", "对不对", "你知道吗",
    "怎么说呢", "就是说", "其实吧",
}

# 广告关键词正则
AD_PATTERNS: List[re.Pattern] = [
    re.compile(r"(关注|点赞|收藏|转发|分享).{0,10}(一下|支持|我|本视频)", re.IGNORECASE),
    re.compile(r"(扫码|二维码|链接在).{0,20}(下方|简介|评论区)", re.IGNORECASE),
    re.compile(r"(优惠码|折扣码|专属链接|限时优惠).{0,30}", re.IGNORECASE),
    re.compile(r"(广告|赞助商|合作推广).{0,20}", re.IGNORECASE),
    re.compile(r"(私信|加微信|加群).{0,20}", re.IGNORECASE),
]


class TranscriptCleaner:
    """本地规则引擎清洗，不消耗 LLM token。"""

    def clean(self, transcript: str) -> str:
        """执行本地规则清洗：去广告、去口头禅、去重复段落。"""
        text = self._remove_ads(transcript)
        text = self._remove_fillers(text)
        text = self._deduplicate(text)
        return text.strip()

    def _remove_ads(self, text: str) -> str:
        """正则匹配去除广告段落。"""
        for pattern in AD_PATTERNS:
            text = pattern.sub("", text)
        return text

    def _remove_fillers(self, text: str) -> str:
        """去除口头禅。"""
        for word in FILLER_WORDS:
            text = text.replace(word, "")
        # 去除多余空格
        text = re.sub(r"\s{2,}", " ", text)
        return text

    def _deduplicate(self, text: str) -> str:
        """去除重复句子（相邻重复）。"""
        sentences = re.split(r"[。！？.!?]", text)
        seen: List[str] = []
        for s in sentences:
            s = s.strip()
            if s and s not in seen[-3:]:  # 检查最近 3 句
                seen.append(s)
        return "。".join(seen)

    async def clean_with_fallback(self, transcript: str, llm_client=None, model_config=None) -> str:
        """规则引擎处理后，如果文本仍然很脏且有 LLM 可用，降级使用轻量 LLM。"""
        cleaned = self.clean(transcript)
        # 简单启发式：如果清洗后文本长度减少超过 50%，认为规则引擎已足够
        if len(cleaned) > len(transcript) * 0.3:
            return cleaned
        # 降级到 LLM（如果提供）
        if llm_client and model_config:
            try:
                from openclaw.llm.prompts import TOPIC_CLASSIFIER_SYSTEM
                result = await llm_client.call(
                    model_config=model_config,
                    system_prompt="请清理以下转录文本，去除广告、口头禅和重复内容，保留核心信息，直接输出清理后的文本。",
                    user_prompt=transcript[:4000],
                )
                return result if isinstance(result, str) else cleaned
            except Exception:
                pass
        return cleaned
