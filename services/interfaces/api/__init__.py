"""API 路由聚合 — 统一注册所有 router"""

from fastapi import FastAPI

from interfaces.api.auth.router import router as auth_router
from interfaces.api.admin.user import router as admin_user_router
from interfaces.api.admin.content import router as admin_content_router
from interfaces.api.admin.learning import router as admin_learning_router
from interfaces.api.admin.tutor import router as admin_tutor_router
from interfaces.api.admin.model_config import router as admin_model_config_router
from interfaces.api.app.user import router as app_user_router
from interfaces.api.app.tutor import router as app_tutor_router
from interfaces.api.app.learning import router as app_learning_router
from interfaces.api.app.content import router as app_content_router


def register_routers(app: FastAPI) -> None:
    """将所有 router 注册到 FastAPI 实例"""
    # 公共
    app.include_router(auth_router)
    # 管理后台
    app.include_router(admin_user_router)
    app.include_router(admin_content_router)
    app.include_router(admin_learning_router)
    app.include_router(admin_tutor_router)
    app.include_router(admin_model_config_router)
    # 学生端 App
    app.include_router(app_user_router)
    app.include_router(app_tutor_router)
    app.include_router(app_learning_router)
    app.include_router(app_content_router)
