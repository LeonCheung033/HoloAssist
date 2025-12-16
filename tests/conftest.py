"""
Pytest配置文件
"""

import os
from pathlib import Path

# 加载 .env 文件（如果存在），确保集成测试可以使用真实的API密钥
# 注意：必须在设置默认值之前加载，这样 .env 文件中的值会被优先使用
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)  # override=False 确保已存在的环境变量不会被覆盖

# 设置测试环境变量，避免导入config模块时验证失败
# 注意：只有在环境变量不存在时才设置默认值
os.environ.setdefault("DEEPSEEK_API_KEY", "test-api-key")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
os.environ.setdefault("DEEPSEEK_MODEL", "test-model")
os.environ.setdefault("VISION_API_KEY", "test-vision-key")
os.environ.setdefault("VISION_BASE_URL", "https://api.test.com/v1")
os.environ.setdefault("VISION_MODEL", "test-vision-model")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_CHAT_MODEL", "test-chat-model")
os.environ.setdefault("OLLAMA_REASON_MODEL", "test-reason-model")
os.environ.setdefault("OLLAMA_EMBEDDING_MODEL", "test-embedding-model")
os.environ.setdefault("OLLAMA_AGENT_MODEL", "test-agent-model")
os.environ.setdefault("SERPAPI_KEY", "test-serpapi-key")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "zl020722")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

# 导入模型以确保表定义被注册
import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from holoassist.app.core.database import Base  # noqa: E402
from holoassist.app.models import Conversation, Message, User  # noqa: F401, E402


@pytest_asyncio.fixture
async def db_session():
    """创建测试数据库会话"""
    # 使用测试数据库
    test_db_url = (
        f"mysql+aiomysql://{os.environ.get('DB_USER', 'root')}:"
        f"{os.environ.get('DB_PASSWORD', 'zl020722')}@"
        f"{os.environ.get('DB_HOST', 'localhost')}:"
        f"{os.environ.get('DB_PORT', '3306')}/"
        f"{os.environ.get('DB_NAME', 'test_db')}"
    )

    engine = create_async_engine(test_db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    # 清理：删除表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
