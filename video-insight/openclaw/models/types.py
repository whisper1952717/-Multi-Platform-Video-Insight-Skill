from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


# ── 视频信息 ──
class VideoInfo(BaseModel):
    url: str
    title: str
    creator: str
    platform: str
    publish_date: datetime
    view_count: int


class VideoStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    TRANSCRIBED = "transcribed"
    ANALYZED = "analyzed"
    SKIPPED = "skipped"


# ── 下载结果 ──
class DownloadResult(BaseModel):
    video_id: str
    method: str  # "subtitle" | "audio" | "skipped"
    file_path: Optional[str] = None
    subtitle_text: Optional[str] = None
    skipped_reason: Optional[str] = None


# ── 转录结果 ──
class TimestampedSegment(BaseModel):
    start: float  # 秒
    end: float
    text: str


class TranscriptResult(BaseModel):
    video_id: str
    segments: List[TimestampedSegment]
    full_text: str


# ── 主题分类 ──
class ContentType(str, Enum):
    OPINION = "观点输出"
    TUTORIAL = "教程讲解"
    CASE_STUDY = "案例分析"
    INDUSTRY = "行业分析"
    PRODUCT = "产品推荐"
    OTHER = "其他"


class TopicClassification(BaseModel):
    primary_topic: str
    secondary_topics: List[str] = []
    content_type: ContentType
    business_relevance: float = Field(ge=0.0, le=1.0)
    skip_reason: Optional[str] = None


# ── 视频分析结果 ──
class CoreSignal(BaseModel):
    signal: str
    evidence: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class CognitionFramework(BaseModel):
    framework: str
    reasoning_chain: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class MethodologyFragment(BaseModel):
    method: str
    applicable_scenario: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class HighValueQuote(BaseModel):
    quote: str
    context: str


class VideoAnalysis(BaseModel):
    video_id: str
    core_signals: List[CoreSignal]
    cognition_framework: List[CognitionFramework]
    methodology_fragments: List[MethodologyFragment]
    high_value_quotes: List[HighValueQuote]
    overall_quality: float = Field(ge=0.0, le=1.0)


# ── 聚合洞察 ──
class BusinessOpportunity(BaseModel):
    direction_judgment: List[dict]  # {"judgment": str, "confidence_score": float}
    verifiable_hypotheses: List[dict]  # {"hypothesis": str, "confidence_score": float}


class QualitySummary(BaseModel):
    overall_confidence: float = Field(ge=0.0, le=1.0)
    low_quality_signals_count: int
    notes: str


class Mode1Insights(BaseModel):
    metadata: dict
    core_signals: List[dict]
    cognition_framework: List[dict]
    methodology_fragments: List[dict]
    business_opportunities: BusinessOpportunity
    high_value_quotes: List[dict]
    insights_for_me: List[str]
    quality_summary: QualitySummary


class ConsensusAndDivergence(BaseModel):
    consensus: List[dict]
    divergence: List[dict]


class Mode2Insights(BaseModel):
    metadata: dict
    trend_signals: List[dict]
    consensus_and_divergence: ConsensusAndDivergence
    common_methodology: List[dict]
    business_opportunities: BusinessOpportunity
    high_value_quotes: List[dict]
    insights_for_me: List[str]
    quality_summary: QualitySummary
