"""
Pytest配置文件
"""

import os

# 设置测试环境变量，避免导入config模块时验证失败
os.environ.setdefault("DEEPSEEK_API_KEY", "test-api-key")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.test.com/v1")
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
from holoassist.app.models import Conversation, Message, User  # noqa: F401, E402
