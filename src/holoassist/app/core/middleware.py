import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from holoassist.app.core.logger import get_logger

logger = get_logger(service="http")


class LoggingMiddleware(BaseHTTPMiddleware):
    """HTTP请求日志记录中间件

    记录每个HTTP请求的详细信息，包括：
    - 客户端IP和端口
    - HTTP方法和路径
    - HTTP版本
    - 响应状态码
    - 请求处理时间
    """

    async def dispatch(self, request: Request, call_next):
        """处理HTTP请求并记录日志

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: HTTP响应对象
        """
        start_time = time.time()

        # 调用下一个中间件或路由处理函数
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time

        # 记录请求日志
        logger.info(
            f"{request.client.host}:{request.client.port} - "
            f'"{request.method} {request.url.path} HTTP/{request.scope.get("http_version", "1.1")}" '
            f"{response.status_code} - {process_time:.2f}s"
        )

        return response
