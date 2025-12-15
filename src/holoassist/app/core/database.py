import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from holoassist.app.core.config import settings

# 设置 SQLAlchemy 日志级别为 WARNING，这样就不会显示 INFO 级别的 SQL 查询日志
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 设置为 False 也可以关闭 SQL 日志
    pool_pre_ping=True,  # 自动检测断开的连接
    pool_size=5,  # 连接池大小，保持 5 个连接处于可用状态。在高并发情况下，最多可以同时处理 5 个数据库请求，而不需要每次都去创建新的连接。
    max_overflow=10,  # 最大溢出连接数，如果连接池中的连接都被占用，最多可以再创建 10 个额外的连接。因此，最多可以同时处理 15 个请求（5 个常规连接 + 10 个溢出连接）。超出这个数量的请求将会被阻塞，直到有连接可用。
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# 创建基类
Base = declarative_base()


# 获取数据库会话的依赖函数
async def get_db():
    """获取数据库会话的依赖注入函数

    Yields:
        AsyncSession: 数据库会话对象

    使用示例:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # 使用 db 进行数据库操作
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
