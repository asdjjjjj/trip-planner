"""Vercel 入口：暴露旅行助手 FastAPI 应用（ASGI）。"""

import os
import sys

# 将 backend 目录加入模块搜索路径（应用入口为 backend/app/main.py）
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.main import app  # noqa: E402

__all__ = ["app"]
