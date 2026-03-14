FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（ffmpeg 为可选，网络不通时跳过）
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/* || echo "ffmpeg 安装跳过"

# 先复制依赖声明，利用 Docker 层缓存
COPY pyproject.toml ./

# 安装项目依赖（跳过 chromadb 和 faster-whisper 这类重型依赖，用轻量替代做测试）
RUN pip install --no-cache-dir \
    pydantic>=2.0 \
    pydantic-settings>=2.0 \
    structlog>=23.0 \
    rich>=13.0 \
    aiohttp>=3.9 \
    aiosqlite>=0.19 \
    pyyaml>=6.0 \
    cryptography>=41.0 \
    pytest>=7.0 \
    pytest-asyncio>=0.23 \
    hypothesis>=6.0 \
    pytest-cov>=4.0

# 可选重型依赖（网络允许时安装，失败不中断）
RUN pip install --no-cache-dir yt-dlp>=2024.0 || echo "yt-dlp 安装跳过"
RUN pip install --no-cache-dir faster-whisper>=1.0 || echo "faster-whisper 安装跳过"
RUN pip install --no-cache-dir semantic-text-splitter>=0.13 || echo "semantic-text-splitter 安装跳过"
RUN pip install --no-cache-dir asyncpg>=0.29 || echo "asyncpg 安装跳过"
RUN pip install --no-cache-dir chromadb>=0.4 || echo "chromadb 安装跳过"

# 复制项目代码
COPY . .

# 以可编辑模式安装（不触发依赖重装）
RUN pip install --no-cache-dir -e . --no-deps

# 创建运行时目录
RUN mkdir -p /app/data /app/logs /app/cookies

CMD ["pytest", "tests/", "-v", "--tb=short", "-x"]
