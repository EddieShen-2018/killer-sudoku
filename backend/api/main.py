"""FastAPI 应用主入口。

启动方式：
    cd backend
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

提供：
- /api/* REST API（谜题获取、验证、预生成）
- / 前端静态文件服务（frontend 目录）
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router, set_repository
from storage.repository import PuzzleRepository

# 模板库根目录（backend/templates_db）
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates_db"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# 创建 FastAPI 应用
app = FastAPI(
    title="杀手数独 API",
    description="支持多种尺寸和难度的杀手数独生成、验证服务",
    version="1.0.0",
)

# CORS 配置（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化模板库仓库
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
repository = PuzzleRepository(TEMPLATES_DIR)
set_repository(repository)

# 注册 API 路由
app.include_router(router)


@app.on_event("startup")
async def startup_event() -> None:
    """应用启动时执行：确保模板库目录存在。"""
    for size in [4, 6, 9]:
        for diff in ["beginner", "easy", "medium", "hard", "expert"]:
            (TEMPLATES_DIR / f"{size}x{size}" / diff).mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "ok", "service": "killer-sudoku-api"}


# 前端静态文件服务
if FRONTEND_DIR.exists():
    # 挂载静态资源目录（css/js/assets/puzzles）
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    css_dir = FRONTEND_DIR / "css"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    js_dir = FRONTEND_DIR / "js"
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    puzzles_dir = FRONTEND_DIR / "puzzles"
    if puzzles_dir.exists():
        app.mount("/puzzles", StaticFiles(directory=str(puzzles_dir)), name="puzzles")

    @app.get("/")
    async def serve_index():
        """提供前端首页。"""
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """提供前端路由（回退到 index.html）。"""
        # 如果是 API 路径，不处理（交给路由）
        if path.startswith("api"):
            return {"detail": "Not Found"}
        # 尝试返回对应文件
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # 回退到 index.html
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"detail": "Not Found"}
