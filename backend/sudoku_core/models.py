"""数独核心数据模型。

定义棋盘配置、笼、谜题等核心数据结构，支持 4×4、6×6、9×9 三种尺寸。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Difficulty(str, Enum):
    """难度级别枚举。"""

    BEGINNER = "beginner"  # 入门
    EASY = "easy"  # 简单
    MEDIUM = "medium"  # 中等
    HARD = "hard"  # 困难
    EXPERT = "expert"  # 专家


@dataclass(frozen=True)
class BoardConfig:
    """棋盘配置：描述一种尺寸的数独棋盘结构。

    Attributes:
        size: 棋盘边长（如 9 表示 9×9）。
        box_rows: 每个宫的行数。
        box_cols: 每个宫的列数。
        symbols: 可用数字集合（1..size）。
    """

    size: int
    box_rows: int
    box_cols: int
    symbols: tuple[int, ...]

    @property
    def num_cells(self) -> int:
        """总单元格数。"""
        return self.size * self.size

    @property
    def max_symbol(self) -> int:
        """最大数字。"""
        return self.size

    def box_index(self, row: int, col: int) -> int:
        """计算单元格所属的宫索引。"""
        boxes_per_row = self.size // self.box_cols
        return (row // self.box_rows) * boxes_per_row + (col // self.box_cols)

    def box_cells(self, box_idx: int) -> list[tuple[int, int]]:
        """返回指定宫内的所有单元格坐标。"""
        boxes_per_row = self.size // self.box_cols
        start_row = (box_idx // boxes_per_row) * self.box_rows
        start_col = (box_idx % boxes_per_row) * self.box_cols
        cells: list[tuple[int, int]] = []
        for r in range(start_row, start_row + self.box_rows):
            for c in range(start_col, start_col + self.box_cols):
                cells.append((r, c))
        return cells

    def neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """返回与某单元格同行、同列、同宫的所有其它单元格（用于约束检查）。"""
        seen: set[tuple[int, int]] = set()
        result: list[tuple[int, int]] = []
        # 同行
        for c in range(self.size):
            if c != col:
                cell = (row, c)
                if cell not in seen:
                    seen.add(cell)
                    result.append(cell)
        # 同列
        for r in range(self.size):
            if r != row:
                cell = (r, col)
                if cell not in seen:
                    seen.add(cell)
                    result.append(cell)
        # 同宫
        for r, c in self.box_cells(self.box_index(row, col)):
            if (r, c) != (row, col) and (r, c) not in seen:
                seen.add((r, c))
                result.append((r, c))
        return result


# 各尺寸棋盘配置表
BOARD_CONFIGS: dict[int, BoardConfig] = {
    4: BoardConfig(size=4, box_rows=2, box_cols=2, symbols=(1, 2, 3, 4)),
    6: BoardConfig(size=6, box_rows=2, box_cols=3, symbols=(1, 2, 3, 4, 5, 6)),
    9: BoardConfig(size=9, box_rows=3, box_cols=3, symbols=(1, 2, 3, 4, 5, 6, 7, 8, 9)),
}


def get_board_config(size: int) -> BoardConfig:
    """根据尺寸获取棋盘配置。

    Args:
        size: 棋盘边长（4/6/9）。

    Returns:
        对应的 BoardConfig。

    Raises:
        ValueError: 不支持的尺寸。
    """
    if size not in BOARD_CONFIGS:
        raise ValueError(
            f"不支持的棋盘尺寸: {size}，支持的尺寸: {list(BOARD_CONFIGS.keys())}"
        )
    return BOARD_CONFIGS[size]


@dataclass
class Cage:
    """笼：一组相邻单元格及其目标和。

    Attributes:
        cells: 单元格坐标列表 [(row, col), ...]。
        target_sum: 笼内所有数字之和的目标值。
    """

    cells: list[tuple[int, int]]
    target_sum: int

    @property
    def size(self) -> int:
        """笼内单元格数量。"""
        return len(self.cells)

    def contains(self, row: int, col: int) -> bool:
        """判断某单元格是否在此笼内。"""
        return (row, col) in self.cells

    def to_dict(self) -> dict:
        """序列化为字典（用于 JSON 存储/传输）。"""
        return {
            "cells": [list(cell) for cell in self.cells],
            "target_sum": self.target_sum,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cage":
        """从字典反序列化。"""
        cells = [tuple(cell) for cell in data["cells"]]
        return cls(cells=cells, target_sum=data["target_sum"])


@dataclass
class Puzzle:
    """完整谜题：笼信息 + 解答 + 元数据。

    Attributes:
        size: 棋盘尺寸。
        cages: 所有笼。
        solution: 完整解（二维列表，solution[row][col]）。
        difficulty: 难度级别。
        puzzle_id: 唯一标识。
    """

    size: int
    cages: list[Cage]
    solution: list[list[int]]
    difficulty: Difficulty = Difficulty.MEDIUM
    puzzle_id: str = ""

    @property
    def config(self) -> BoardConfig:
        """对应的棋盘配置。"""
        return get_board_config(self.size)

    def cage_of(self, row: int, col: int) -> Optional[Cage]:
        """返回包含某单元格的笼。"""
        for cage in self.cages:
            if cage.contains(row, col):
                return cage
        return None

    def to_dict(self) -> dict:
        """序列化为字典（用于 JSON 存储/传输）。

        注意：solution 默认包含在内，供后端验证使用；
        传给前端时应通过 to_public_dict 隐藏解答。
        """
        return {
            "puzzle_id": self.puzzle_id,
            "size": self.size,
            "difficulty": self.difficulty.value,
            "cages": [cage.to_dict() for cage in self.cages],
            "solution": self.solution,
        }

    def to_public_dict(self) -> dict:
        """序列化为公开字典（不含解答，供前端使用）。"""
        return {
            "puzzle_id": self.puzzle_id,
            "size": self.size,
            "difficulty": self.difficulty.value,
            "cages": [cage.to_dict() for cage in self.cages],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Puzzle":
        """从字典反序列化。"""
        return cls(
            size=data["size"],
            cages=[Cage.from_dict(c) for c in data["cages"]],
            solution=data["solution"],
            difficulty=Difficulty(data.get("difficulty", "medium")),
            puzzle_id=data.get("puzzle_id", ""),
        )
