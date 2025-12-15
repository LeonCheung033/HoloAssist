"""API路由模块

统一管理所有API路由。
"""
from fastapi import APIRouter

from holoassist.app.api.auth import router as auth_router

# 创建主API路由器
api_router = APIRouter()

# 注册认证路由
api_router.include_router(auth_router, tags=["authentication"])
