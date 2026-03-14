"""TranscriptCleaner 属性测试（Property-Based Testing）。"""
import pytest
from hypothesis import given, settings, strategies as st
from openclaw.pipeline.cleaner import TranscriptCleaner


# ── 属性 7: 清洗幂等性 ────────────────────────────────────────────────────────

@given(text=st.text(min_size=0, max_size=500))
@settings(max_examples=100)
def test_clean_idempotent(text):
    """属性 7: 对已清洗文本再次清洗应得到相同结果。"""
    cleaner = TranscriptCleaner()
    once = cleaner.clean(text)
    twice = cleaner.clean(once)
    assert once == twice, f"清洗不幂等:\n  第一次: {once!r}\n  第二次: {twice!r}"


@given(text=st.text(min_size=1, max_size=200, alphabet=st.characters(
    whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
    whitelist_characters="。！？.!?，,、 \n"
)))
@settings(max_examples=50)
def test_clean_idempotent_chinese(text):
    """属性 7b: 中文文本清洗幂等性。"""
    cleaner = TranscriptCleaner()
    once = cleaner.clean(text)
    twice = cleaner.clean(once)
    assert once == twice


# ── 清洗不增加内容 ────────────────────────────────────────────────────────────

@given(text=st.text(min_size=0, max_size=500))
@settings(max_examples=100)
def test_clean_never_increases_length(text):
    """清洗后文本长度不应超过原始文本长度。"""
    cleaner = TranscriptCleaner()
    result = cleaner.clean(text)
    assert len(result) <= len(text), (
        f"清洗后文本变长: {len(text)} -> {len(result)}"
    )


# ── 广告去除 ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ad_text", [
    "关注一下支持我",
    "点赞支持本视频",
    "扫码下方二维码",
    "优惠码专属链接限时优惠",
    "广告合作推广",
    "私信加微信",
])
def test_ad_patterns_removed(ad_text):
    """广告关键词应被去除。"""
    cleaner = TranscriptCleaner()
    result = cleaner.clean(ad_text)
    # 广告内容应被清除（结果应比原文短或为空）
    assert len(result) < len(ad_text) or result.strip() == ""


# ── 口头禅去除 ────────────────────────────────────────────────────────────────

def test_filler_words_removed():
    """口头禅应被去除。"""
    cleaner = TranscriptCleaner()
    text = "嗯这个产品啊很好哦你知道吗"
    result = cleaner.clean(text)
    assert "嗯" not in result
    assert "啊" not in result
    assert "哦" not in result


def test_clean_preserves_meaningful_content():
    """清洗不应删除有意义的内容。"""
    cleaner = TranscriptCleaner()
    meaningful = "人工智能正在改变商业格局，创业公司需要找到差异化竞争策略。"
    result = cleaner.clean(meaningful)
    # 核心词汇应保留
    assert "人工智能" in result
    assert "商业" in result
    assert "创业" in result


# ── 去重 ──────────────────────────────────────────────────────────────────────

def test_dedup_removes_adjacent_repeats():
    """相邻重复句子应被去除。"""
    cleaner = TranscriptCleaner()
    text = "这是一句话。这是一句话。这是另一句话。"
    result = cleaner.clean(text)
    # 重复的句子应只出现一次
    assert result.count("这是一句话") == 1


def test_clean_empty_string():
    """空字符串清洗应返回空字符串。"""
    cleaner = TranscriptCleaner()
    assert cleaner.clean("") == ""
    assert cleaner.clean("   ") == ""
