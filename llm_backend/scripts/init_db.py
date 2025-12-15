import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 PYTHONPATH
# init_db.py位于: llm_backend/scripts/init_db.py
# 需要向上2级到达项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 导入所有模型以确保Base.metadata包含所有表定义
# 这些导入虽然看起来未使用，但它们是必需的，用于注册表定义到metadata
from holoassist.app.core.database import Base, engine  # noqa: E402
from holoassist.app.core.logger import get_logger  # noqa: E402
from holoassist.app.models import Conversation, Message, User  # noqa: E402, F401

logger = get_logger(service="init_db")


async def init_db():
    """初始化数据库

    删除所有现有表并重新创建所有表。
    使用engine.begin()确保事务性操作。
    """
    try:
        logger.info("Initializing database...")
        async with engine.begin() as conn:
            # 删除所有表（如果存在）
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Dropped all existing tables")
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Created all tables")
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise
    finally:
        # 显式关闭引擎，释放所有连接资源
        # 这可以避免在事件循环关闭后尝试清理连接时出现 RuntimeError
        await engine.dispose()


def main():
    """主函数

    使用asyncio.run()运行数据库初始化。
    """
    try:
        asyncio.run(init_db())
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
