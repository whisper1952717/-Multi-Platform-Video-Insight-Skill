"""SQLite 数据存储后端。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiosqlite

from openclaw.models.types import VideoInfo, VideoStatus, TranscriptResult, VideoAnalysis
from openclaw.storage.datastore import BaseDataStore

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    creator TEXT NOT NULL,
    publish_date TEXT,
    view_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    skipped_reason TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    run_id TEXT
);

CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    raw_text TEXT,
    cleaned_text TEXT,
    segments TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    topic_classification TEXT,
    analysis_result TEXT,
    confidence_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    target TEXT NOT NULL,
    aggregated_result TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_logs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms INTEGER,
    error_message TEXT,
    token_usage TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checkpoints (
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saved_configs (
    name TEXT PRIMARY KEY,
    config TEXT NOT NULL,
    is_last_used INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class SQLiteDataStore(BaseDataStore):
    def __init__(self, db_path: str = "./data/openclaw.db"):
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            import os
            os.makedirs(os.path.dirname(self._db_path) if os.path.dirname(self._db_path) else ".", exist_ok=True)
            self._conn = await aiosqlite.connect(self._db_path)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def initialize(self) -> None:
        conn = await self._get_conn()
        for stmt in CREATE_TABLES_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(stmt)
        await conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def save_video(self, video: VideoInfo, run_id: str) -> str:
        video_id = str(uuid.uuid4())
        conn = await self._get_conn()
        await conn.execute(
            """INSERT OR IGNORE INTO videos (id, platform, url, title, creator, publish_date, view_count, run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (video_id, video.platform, video.url, video.title, video.creator,
             video.publish_date.isoformat(), video.view_count, run_id)
        )
        await conn.commit()
        # 若已存在，返回已有 id
        async with conn.execute("SELECT id FROM videos WHERE url = ?", (video.url,)) as cur:
            row = await cur.fetchone()
            return row["id"] if row else video_id

    async def get_video_status(self, url: str) -> Optional[VideoStatus]:
        conn = await self._get_conn()
        async with conn.execute("SELECT status FROM videos WHERE url = ?", (url,)) as cur:
            row = await cur.fetchone()
            return VideoStatus(row["status"]) if row else None

    async def update_video_status(self, url: str, status: VideoStatus, skipped_reason: Optional[str] = None) -> None:
        conn = await self._get_conn()
        await conn.execute(
            "UPDATE videos SET status = ?, skipped_reason = ? WHERE url = ?",
            (status.value, skipped_reason, url)
        )
        await conn.commit()

    async def save_transcript(self, video_id: str, transcript: TranscriptResult) -> None:
        conn = await self._get_conn()
        await conn.execute(
            """INSERT OR REPLACE INTO transcripts (id, video_id, raw_text, cleaned_text, segments)
               VALUES (?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), video_id, transcript.full_text, transcript.full_text,
             json.dumps([s.model_dump() for s in transcript.segments], ensure_ascii=False))
        )
        await conn.commit()

    async def save_analysis(self, video_id: str, analysis: VideoAnalysis) -> None:
        conn = await self._get_conn()
        await conn.execute(
            """INSERT OR REPLACE INTO analyses (id, video_id, analysis_result, confidence_score)
               VALUES (?, ?, ?, ?)""",
            (str(uuid.uuid4()), video_id,
             analysis.model_dump_json(),
             analysis.overall_quality)
        )
        await conn.commit()

    async def save_insights(self, run_id: str, mode: str, target: str, result: dict) -> None:
        conn = await self._get_conn()
        await conn.execute(
            """INSERT OR REPLACE INTO insights (id, run_id, mode, target, aggregated_result)
               VALUES (?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), run_id, mode, target, json.dumps(result, ensure_ascii=False))
        )
        await conn.commit()

    async def save_checkpoint(self, run_id: str, state: dict) -> None:
        conn = await self._get_conn()
        await conn.execute(
            """INSERT OR REPLACE INTO checkpoints (run_id, state, updated_at)
               VALUES (?, ?, ?)""",
            (run_id, json.dumps(state, ensure_ascii=False), datetime.now(timezone.utc).isoformat())
        )
        await conn.commit()

    async def load_checkpoint(self, run_id: str) -> Optional[dict]:
        conn = await self._get_conn()
        async with conn.execute("SELECT state FROM checkpoints WHERE run_id = ?", (run_id,)) as cur:
            row = await cur.fetchone()
            return json.loads(row["state"]) if row else None

    async def is_cached(self, url: str, cache_ttl_hours: int) -> bool:
        conn = await self._get_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=cache_ttl_hours)).isoformat()
        async with conn.execute(
            """SELECT v.id FROM videos v
               JOIN analyses a ON a.video_id = v.id
               WHERE v.url = ? AND v.status = 'analyzed' AND a.created_at > ?""",
            (url, cutoff)
        ) as cur:
            return await cur.fetchone() is not None

    async def has_content_changed(self, url: str, publish_date: str, view_count: int) -> bool:
        conn = await self._get_conn()
        async with conn.execute(
            "SELECT publish_date, view_count FROM videos WHERE url = ?", (url,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return True
            return row["publish_date"] != publish_date or row["view_count"] != view_count

    async def __aenter__(self) -> "SQLiteDataStore":
        await self.initialize()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
