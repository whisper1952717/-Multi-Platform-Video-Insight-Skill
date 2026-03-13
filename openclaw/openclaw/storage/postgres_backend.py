"""PostgreSQL 数据存储后端（使用 asyncpg）。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore

from openclaw.models.types import VideoInfo, VideoStatus, TranscriptResult, VideoAnalysis
from openclaw.storage.datastore import BaseDataStore

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    creator TEXT NOT NULL,
    publish_date TIMESTAMPTZ,
    view_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    skipped_reason TEXT,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    run_id TEXT
);
CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    raw_text TEXT,
    cleaned_text TEXT,
    segments JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    topic_classification JSONB,
    analysis_result JSONB,
    confidence_score REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    target TEXT NOT NULL,
    aggregated_result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id TEXT PRIMARY KEY,
    state JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS saved_configs (
    name TEXT PRIMARY KEY,
    config JSONB NOT NULL,
    is_last_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""


class PostgresDataStore(BaseDataStore):
    def __init__(self, dsn: str):
        if asyncpg is None:
            raise ImportError("asyncpg 未安装，请运行 pip install asyncpg")
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            for stmt in CREATE_TABLES_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(stmt)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def save_video(self, video: VideoInfo, run_id: str) -> str:
        video_id = str(uuid.uuid4())
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO videos (id, platform, url, title, creator, publish_date, view_count, run_id)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (url) DO NOTHING""",
                video_id, video.platform, video.url, video.title, video.creator,
                video.publish_date, video.view_count, run_id
            )
            row = await conn.fetchrow("SELECT id FROM videos WHERE url = $1", video.url)
            return row["id"]

    async def get_video_status(self, url: str) -> Optional[VideoStatus]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM videos WHERE url = $1", url)
            return VideoStatus(row["status"]) if row else None

    async def update_video_status(self, url: str, status: VideoStatus, skipped_reason: Optional[str] = None) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE videos SET status=$1, skipped_reason=$2 WHERE url=$3",
                status.value, skipped_reason, url
            )

    async def save_transcript(self, video_id: str, transcript: TranscriptResult) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO transcripts (id, video_id, raw_text, segments)
                   VALUES ($1,$2,$3,$4) ON CONFLICT (id) DO NOTHING""",
                str(uuid.uuid4()), video_id, transcript.full_text,
                json.dumps([s.model_dump() for s in transcript.segments])
            )

    async def save_analysis(self, video_id: str, analysis: VideoAnalysis) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO analyses (id, video_id, analysis_result, confidence_score)
                   VALUES ($1,$2,$3,$4) ON CONFLICT (id) DO NOTHING""",
                str(uuid.uuid4()), video_id,
                analysis.model_dump_json(), analysis.overall_quality
            )

    async def save_insights(self, run_id: str, mode: str, target: str, result: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO insights (id, run_id, mode, target, aggregated_result)
                   VALUES ($1,$2,$3,$4,$5) ON CONFLICT (id) DO NOTHING""",
                str(uuid.uuid4()), run_id, mode, target, json.dumps(result)
            )

    async def save_checkpoint(self, run_id: str, state: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO checkpoints (run_id, state, updated_at) VALUES ($1,$2,$3)
                   ON CONFLICT (run_id) DO UPDATE SET state=$2, updated_at=$3""",
                run_id, json.dumps(state), datetime.now(timezone.utc)
            )

    async def load_checkpoint(self, run_id: str) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT state FROM checkpoints WHERE run_id=$1", run_id)
            return json.loads(row["state"]) if row else None

    async def is_cached(self, url: str, cache_ttl_hours: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=cache_ttl_hours)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT v.id FROM videos v JOIN analyses a ON a.video_id=v.id
                   WHERE v.url=$1 AND v.status='analyzed' AND a.created_at > $2""",
                url, cutoff
            )
            return row is not None

    async def has_content_changed(self, url: str, publish_date: str, view_count: int) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT publish_date, view_count FROM videos WHERE url=$1", url
            )
            if not row:
                return True
            return str(row["publish_date"]) != publish_date or row["view_count"] != view_count

    async def __aenter__(self) -> "PostgresDataStore":
        await self.initialize()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
