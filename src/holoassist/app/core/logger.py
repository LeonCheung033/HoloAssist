import sys
from pathlib import Path

from loguru import logger

# 创建日志目录
# logs目录会在当前工作目录下创建
# 注意：如果从不同目录运行脚本，logs目录位置会相应变化
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)


# 移除默认的控制台输出
logger.remove()

# 添加控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

# 添加文件输出 - 普通日志
logger.add(
    "logs/app.log",  # 普通日志文件
    rotation="500 MB",  # 日志文件大小超过500MB时轮转
    retention="10 days",  # 保留10天的日志
    compression="zip",  # 压缩旧的日志文件
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    encoding="utf-8",
)

# 错误日志单独存储
logger.add(
    "logs/error.log",  # 错误日志文件
    rotation="100 MB",  # 日志文件大小超过100MB时轮转
    retention="30 days",  # 保留30天的日志
    compression="zip",  # 压缩旧的日志文件
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    encoding="utf-8",
)


def get_logger(service: str):
    """获取带有服务名称的 logger

    Args:
        service: 服务名称，用于标识日志来源

    Returns:
        绑定服务名称的logger实例
    """
    return logger.bind(service=service)


def log_structured(event_type: str, data: dict):
    """结构化日志记录

    Args:
        event_type: 事件类型
        data: 事件数据字典
    """
    logger.info({"event_type": event_type, "data": data})
