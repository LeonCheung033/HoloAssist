from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

# 获取项目根目录
# config.py位于: src/holoassist/app/core/config.py
# 需要向上5级到达项目根目录
# __file__ -> core -> app -> holoassist -> src -> 项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class ServiceType(str, Enum):
    """服务类型枚举"""

    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    SILICONFLOW = "siliconflow"


class Settings(BaseSettings):
    "应用配置类，使用pydantic-settings管理所有配置"

    # DeepSeek settings
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str
    DEEPSEEK_MODEL: str
    DEEPSEEK_REASONER_MODEL: str = "deepseek-reasoner"  # 深度思考模型

    # Vision Model settings (独立配置)
    VISION_API_KEY: str
    VISION_BASE_URL: str
    VISION_MODEL: str

    # SiliconFlow settings (用于Embedding和视觉模型)
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"  # 默认embedding模型
    SILICONFLOW_VISION_MODEL: str = "Qwen/Qwen2.5-VL-32B-Instruct"  # 默认视觉模型
    SILICONFLOW_CHAT_MODEL: str = "deepseek-ai/DeepSeek-V3"

    # Ollama settings
    OLLAMA_BASE_URL: str
    OLLAMA_CHAT_MODEL: str
    OLLAMA_REASON_MODEL: str
    OLLAMA_EMBEDDING_MODEL: str
    OLLAMA_AGENT_MODEL: str

    # Service selection
    CHAT_SERVICE: ServiceType = ServiceType.DEEPSEEK
    REASON_SERVICE: ServiceType = ServiceType.OLLAMA
    AGENT_SERVICE: ServiceType = ServiceType.DEEPSEEK

    # Search settings
    TAVILY_API_KEY: str = Field(default="", alias="TAVILY_KEY")  # Tavily API密钥（优先使用，支持TAVILY_KEY别名）
    SERPAPI_KEY: str = ""  # SerpAPI密钥（向后兼容）
    SEARCH_RESULT_COUNT: int = 3

    # Database settings
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Neo4j settings
    NEO4J_URL: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"

    # JWT settings
    SECRET_KEY: str = "your-secret-key"  # 在生产环境中使用安全的密钥
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis settings
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_CACHE_EXPIRE: int = 3600
    REDIS_CACHE_THRESHOLD: float = 0.8

    # Embedding settings
    EMBEDDING_TYPE: str = "ollama"  # ollama、sentence_transformer 或 siliconflow
    EMBEDDING_MODEL: str = "bge-m3"  # embedding模型名称
    EMBEDDING_THRESHOLD: float = 0.90  # 语义相似度阈值

    # GraphRAG settings
    GRAPHRAG_PROJECT_DIR: str = "llm_backend/app/graphrag"  # GraphRAG项目目录
    GRAPHRAG_DATA_DIR: str = "data"  # 数据目录名称
    GRAPHRAG_QUERY_TYPE: str = "local"  # 查询类型
    GRAPHRAG_RESPONSE_TYPE: str = "text"  # 响应类型
    GRAPHRAG_COMMUNITY_LEVEL: int = 3  # 社区级别
    GRAPHRAG_DYNAMIC_COMMUNITY: bool = False  # 是否动态选择社区

    @property
    def DATABASE_URL(self) -> str:
        """构建MySQL数据库连接URL"""
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        """构建Redis URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def NEO4J_CONN_URL(self) -> str:
        """构建Neo4j连接URL"""
        return f"{self.NEO4J_URL}"

    class Config:
        env_file = str(ENV_FILE)  # 使用绝对路径
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局settings实例
# Settings会从环境变量读取配置，mypy无法静态分析
settings = Settings()  # type: ignore[call-arg]
