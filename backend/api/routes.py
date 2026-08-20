"""FastAPI 路由：谜题获取、解答验证、模板预生成。"""

from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sudoku_core.models import Difficulty, get_board_config
from sudoku_core.generator import KillerSudokuGenerator
from sudoku_core.validator import KillerSudokuValidator
from storage.repository import PuzzleRepository

router = APIRouter(prefix="/api", tags=["killer-sudoku"])

# 全局仓库实例（由 main.py 初始化后注入）
_repository: PuzzleRepository | None = None


def set_repository(repo: PuzzleRepository) -> None:
    """设置全局仓库实例。"""
    global _repository
    _repository = repo


def get_repository() -> PuzzleRepository:
    """获取全局仓库实例。"""
    if _repository is None:
        raise RuntimeError("仓库未初始化")
    return _repository


# 支持的尺寸
SUPPORTED_SIZES = [4, 6, 9]


class ValidateRequest(BaseModel):
    """验证解答请求。"""

    puzzle_id: str = Field(..., description="谜题 ID")
    solution: list[list[int]] = Field(..., description="用户提交的解答")


class GenerateRequest(BaseModel):
    """预生成请求。"""

    size: int = Field(..., description="棋盘尺寸")
    difficulty: str = Field(..., description="难度")
    count: int = Field(5, description="生成数量", ge=1, le=50)


def _validate_size(size: int) -> int:
    """校验棋盘尺寸。"""
    if size not in SUPPORTED_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的棋盘尺寸: {size}，支持: {SUPPORTED_SIZES}",
        )
    return size


def _parse_difficulty(difficulty: str) -> Difficulty:
    """解析难度参数。"""
    try:
        return Difficulty(difficulty)
    except ValueError:
        valid = [d.value for d in Difficulty]
        raise HTTPException(
            status_code=400,
            detail=f"无效难度: {difficulty}，支持: {valid}",
        )


@router.get("/puzzle")
async def get_puzzle(
    size: int = Query(9, description="棋盘尺寸 (4/6/9)"),
    difficulty: str = Query("medium", description="难度级别"),
) -> dict[str, Any]:
    """获取一个谜题（不含解答）。

    优先从模板库随机取，若库为空则实时生成。
    """
    size = _validate_size(size)
    diff = _parse_difficulty(difficulty)

    repo = get_repository()

    # 优先从模板库取
    public = repo.get_random_public(size, diff)
    if public is not None:
        return public

    # 模板库为空，实时生成
    rng = random.Random()
    generator = KillerSudokuGenerator.from_size(size, rng)
    try:
        puzzle = generator.generate(diff)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 存入模板库供后续使用
    repo.save(puzzle)
    return puzzle.to_public_dict()


@router.get("/puzzle/{puzzle_id}")
async def get_puzzle_by_id(puzzle_id: str) -> dict[str, Any]:
    """根据 ID 获取谜题（不含解答）。"""
    repo = get_repository()
    puzzle = repo.load_by_id(puzzle_id)
    if puzzle is None:
        raise HTTPException(status_code=404, detail=f"谜题不存在: {puzzle_id}")
    return puzzle.to_public_dict()


@router.post("/validate")
async def validate_solution(request: ValidateRequest) -> dict[str, Any]:
    """验证用户提交的解答。

    优先与预存解答对比，若找不到谜题则用验证器独立校验。
    """
    repo = get_repository()
    puzzle = repo.load_by_id(request.puzzle_id)

    if puzzle is None:
        raise HTTPException(
            status_code=404, detail=f"谜题不存在: {request.puzzle_id}"
        )

    # 与预存解答对比（快速验证）
    validator = KillerSudokuValidator.from_puzzle(puzzle)
    result = validator.validate_against_solution(request.solution, puzzle.solution)
    return result.to_dict()


@router.post("/admin/generate")
async def generate_templates(request: GenerateRequest) -> dict[str, Any]:
    """批量预生成谜题并存入模板库（管理接口）。"""
    size = _validate_size(request.size)
    diff = _parse_difficulty(request.difficulty)

    repo = get_repository()
    rng = random.Random()
    generator = KillerSudokuGenerator.from_size(size, rng)

    generated = 0
    errors: list[str] = []
    for i in range(request.count):
        try:
            puzzle = generator.generate(diff)
            repo.save(puzzle)
            generated += 1
        except RuntimeError as e:
            errors.append(f"第 {i + 1} 个生成失败: {e}")

    return {
        "size": size,
        "difficulty": diff.value,
        "requested": request.count,
        "generated": generated,
        "errors": errors,
        "total_in_stock": repo.count(size, diff),
    }


@router.get("/stock")
async def get_stock() -> dict[str, Any]:
    """查询模板库各尺寸+难度的库存数量。"""
    repo = get_repository()
    stock: dict[str, Any] = {}
    for size in SUPPORTED_SIZES:
        stock[f"{size}x{size}"] = {}
        for diff in Difficulty:
            stock[f"{size}x{size}"][diff.value] = repo.count(size, diff)
    return stock


@router.get("/difficulties")
async def get_difficulties() -> dict[str, Any]:
    """获取支持的难度级别和棋盘尺寸。"""
    return {
        "sizes": SUPPORTED_SIZES,
        "difficulties": [
            {"value": d.value, "label": _difficulty_label(d)}
            for d in Difficulty
        ],
    }


def _difficulty_label(diff: Difficulty) -> str:
    """难度中文标签。"""
    labels = {
        Difficulty.BEGINNER: "入门",
        Difficulty.EASY: "简单",
        Difficulty.MEDIUM: "中等",
        Difficulty.HARD: "困难",
        Difficulty.EXPERT: "专家",
    }
    return labels.get(diff, diff.value)
