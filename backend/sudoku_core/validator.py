"""杀手数独验证器。

验证用户提交的解答是否正确，检查：
1. 每行包含所有数字且不重复。
2. 每列包含所有数字且不重复。
3. 每宫包含所有数字且不重复。
4. 每个笼的数字之和等于目标值。
5. 每个笼内数字不重复。

同时支持与预存解答对比的快速验证。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import BoardConfig, Cage, Puzzle, get_board_config


@dataclass
class ValidationResult:
    """验证结果。

    Attributes:
        valid: 解答是否完全正确。
        complete: 是否所有单元格都已填写。
        errors: 错误信息列表（每条描述一处违规）。
        error_cells: 出错的单元格坐标集合。
    """

    valid: bool
    complete: bool
    errors: list[str] = field(default_factory=list)
    error_cells: set[tuple[int, int]] = field(default_factory=set)

    def to_dict(self) -> dict:
        """序列化为字典。"""
        return {
            "valid": self.valid,
            "complete": self.complete,
            "errors": self.errors,
            "error_cells": [list(cell) for cell in sorted(self.error_cells)],
        }


class KillerSudokuValidator:
    """杀手数独验证器。"""

    def __init__(self, config: BoardConfig, cages: list[Cage]):
        """初始化验证器。

        Args:
            config: 棋盘配置。
            cages: 笼列表。
        """
        self.config = config
        self.size = config.size
        self.cages = cages

        # 构建单元格到笼的映射
        self.cell_to_cage: dict[tuple[int, int], Cage] = {}
        for cage in cages:
            for cell in cage.cells:
                self.cell_to_cage[cell] = cage

    @classmethod
    def from_puzzle(cls, puzzle: Puzzle) -> "KillerSudokuValidator":
        """便捷构造：从 Puzzle 创建验证器。"""
        return cls(puzzle.config, puzzle.cages)

    @classmethod
    def from_cages(cls, size: int, cages: list[Cage]) -> "KillerSudokuValidator":
        """便捷构造：根据尺寸和笼列表创建。"""
        return cls(get_board_config(size), cages)

    def validate(self, grid: list[list[int]]) -> ValidationResult:
        """验证完整解答。

        Args:
            grid: 用户提交的解答（二维列表）。

        Returns:
            ValidationResult 验证结果。
        """
        errors: list[str] = []
        error_cells: set[tuple[int, int]] = set()

        # 检查网格尺寸
        if len(grid) != self.size or any(len(row) != self.size for row in grid):
            errors.append(f"网格尺寸不正确，应为 {self.size}×{self.size}")
            return ValidationResult(valid=False, complete=False, errors=errors)

        # 检查是否完整填写
        complete = all(
            isinstance(grid[r][c], int) and grid[r][c] != 0
            for r in range(self.size)
            for c in range(self.size)
        )

        # 检查数字范围
        for r in range(self.size):
            for c in range(self.size):
                val = grid[r][c]
                if val != 0 and (val < 1 or val > self.size):
                    errors.append(f"单元格 ({r},{c}) 的数字 {val} 超出范围 1-{self.size}")
                    error_cells.add((r, c))

        # 检查行
        for r in range(self.size):
            seen: dict[int, int] = {}
            for c in range(self.size):
                val = grid[r][c]
                if val == 0:
                    continue
                if val in seen:
                    errors.append(
                        f"第 {r + 1} 行数字 {val} 重复（列 {seen[val] + 1} 和 {c + 1}）"
                    )
                    error_cells.add((r, c))
                    error_cells.add((r, seen[val]))
                else:
                    seen[val] = c

        # 检查列
        for c in range(self.size):
            seen = {}
            for r in range(self.size):
                val = grid[r][c]
                if val == 0:
                    continue
                if val in seen:
                    errors.append(
                        f"第 {c + 1} 列数字 {val} 重复（行 {seen[val] + 1} 和 {r + 1}）"
                    )
                    error_cells.add((r, c))
                    error_cells.add((seen[val], c))
                else:
                    seen[val] = r

        # 检查宫
        num_boxes = self.size  # 宫数等于 size
        for box_idx in range(num_boxes):
            box_cells = self.config.box_cells(box_idx)
            seen = {}
            for r, c in box_cells:
                val = grid[r][c]
                if val == 0:
                    continue
                if val in seen:
                    other = seen[val]
                    errors.append(
                        f"宫 {box_idx + 1} 数字 {val} 重复（{other} 和 ({r},{c})）"
                    )
                    error_cells.add((r, c))
                    error_cells.add(other)
                else:
                    seen[val] = (r, c)

        # 检查笼
        for idx, cage in enumerate(self.cages):
            cage_values = [grid[r][c] for r, c in cage.cells]
            # 笼内不重复
            seen = {}
            for (r, c), val in zip(cage.cells, cage_values):
                if val == 0:
                    continue
                if val in seen:
                    errors.append(f"笼 {idx + 1} 内数字 {val} 重复")
                    error_cells.add((r, c))
                    error_cells.add(seen[val])
                else:
                    seen[val] = (r, c)

            # 笼和检查（仅当笼内所有格子都已填写时）
            if all(v != 0 for v in cage_values):
                cage_sum = sum(cage_values)
                if cage_sum != cage.target_sum:
                    errors.append(
                        f"笼 {idx + 1} 的和为 {cage_sum}，应为 {cage.target_sum}"
                    )
                    for cell in cage.cells:
                        error_cells.add(cell)

        valid = len(errors) == 0 and complete
        return ValidationResult(
            valid=valid, complete=complete, errors=errors, error_cells=error_cells
        )

    def validate_against_solution(
        self, grid: list[list[int]], solution: list[list[int]]
    ) -> ValidationResult:
        """与预存解答对比验证（快速验证）。

        Args:
            grid: 用户提交的解答。
            solution: 预存正确解答。

        Returns:
            ValidationResult 验证结果。
        """
        errors: list[str] = []
        error_cells: set[tuple[int, int]] = set()

        complete = all(
            isinstance(grid[r][c], int) and grid[r][c] != 0
            for r in range(self.size)
            for c in range(self.size)
        )

        for r in range(self.size):
            for c in range(self.size):
                if grid[r][c] != 0 and grid[r][c] != solution[r][c]:
                    errors.append(f"单元格 ({r},{c}) 的数字 {grid[r][c]} 不正确")
                    error_cells.add((r, c))

        valid = len(errors) == 0 and complete
        return ValidationResult(
            valid=valid, complete=complete, errors=errors, error_cells=error_cells
        )
