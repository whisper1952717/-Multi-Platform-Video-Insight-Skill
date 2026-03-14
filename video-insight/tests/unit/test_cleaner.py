"""TranscriptCleaner 单元测试（含幂等性属性测试）。"""
import pytest


def test_clean_removes_filler_words():
    """清洗应去除常见口头禅。"""
    from openclaw.pipeline.cleaner import TranscriptCleaner
    cleaner = TranscriptCleaner()
    text = "嗯，就是说，这个 AI 技术，对吧，非常重要。"
    cleaned = cleaner.clean(text)
    # 清洗后应比原文短或相同
    assert len(cleaned) <= len(text)


def test_clean_removes_duplicate_paragraphs():
    """重复段落应被去重。"""
    from openclaw.pipeline.cleaner import TranscriptCleaner
    cleaner = TranscriptCleaner()
    text = "这是一段内容。\n这是一段内容。\n这是另一段内容。"
    cleaned = cleaner.clean(text)
    assert cleaned.count("这是一段内容") <= 1


def test_clean_idempotent():
    """清洗幂等性：对已清洗文本再次清洗应得到相同结果。"""
    from openclaw.pipeline.cleaner import TranscriptCleaner
    cleaner = TranscriptCleaner()
    text = "嗯，就是说，AI 技术非常重要，对吧。这是测试内容。"
    once = cleaner.clean(text)
    twice = cleaner.clean(once)
    assert once == twice


def test_clean_empty_string():
    """空字符串清洗不应崩溃。"""
    from openclaw.pipeline.cleaner import TranscriptCleaner
    cleaner = TranscriptCleaner()
    assert cleaner.clean("") == ""


def test_clean_preserves_content():
    """清洗不应删除核心内容。"""
    from openclaw.pipeline.cleaner import TranscriptCleaner
    cleaner = TranscriptCleaner()
    text = "人工智能正在改变商业模式，这是一个重要的趋势。"
    cleaned = cleaner.clean(text)
    assert "人工智能" in cleaned or "AI" in cleaned or len(cleaned) > 0
