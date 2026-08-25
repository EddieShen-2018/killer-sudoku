"""杀手数独求解器。

采用回溯 + 约束传播算法：
1. 维护每个单元格的候选数字集合（基于行/列/宫唯一性约束）。
2. 维护每个笼的剩余和与可用数字约束。
3. 使用 MRV（最小剩余值）启发式选择候选最少的单元格优先填充。
4. 回溯搜索，支持限制解的数量（用于唯一性验证）。
"""

from __future__ import annotations

from typing import Optional

from .models import BoardConfig, Cage, get_board_config


class KillerSudokuSolver:
    """杀手数独求解器。

    给定棋盘配置和笼信息，求解满足所有约束的完整解。
    可用于：
    - 验证谜题是否有唯一解
    - 评估谜题难度（通过搜索深度/回溯次数）
    - 求解给定谜题
    """

    def __init__(self, config: BoardConfig, cages: list[Cage]):
        """初始化求解器。

        Args:
            config: 棋盘配置。
            cages: 笼列表。
        """
        self.config = config
        self.size = config.size
        self.symbols = set(config.symbols)

        # 构建单元格到笼的映射
        self.cell_to_cage: dict[tuple[int, int], Cage] = {}
        for cage in cages:
            for cell in cage.cells:
                self.cell_to_cage[cell] = cage

        # 统计：回溯次数（用于难度评估）
        self.backtrack_count: int = 0
        # 搜索是否因回溯限制而中断（未完成）
        self.search_truncated: bool = False

    @classmethod
    def from_cages(cls, size: int, cages: list[Cage]) -> "KillerSudokuSolver":
        """便捷构造：根据棋盘尺寸和笼列表创建求解器。"""
        return cls(get_board_config(size), cages)

    def solve(
        self,
        max_solutions: int = 1,
        max_backtracks: int = 100000,
    ) -> list[list[list[int]]]:
        """求解所有满足约束的解。

        Args:
            max_solutions: 最多返回的解的数量（找到即停止）。
            max_backtracks: 最大回溯次数限制（防止超时）。

        Returns:
            解的列表，每个解是二维列表 solution[row][col]。
        """
        self.backtrack_count = 0
        self.search_truncated = False
        solutions: list[list[list[int]]] = []

        # 初始化空棋盘
        grid: list[list[int]] = [[0] * self.size for _ in range(self.size)]

        # 初始化候选集合：每个单元格初始可填所有数字
        candidates: dict[tuple[int, int], set[int]] = {
            (r, c): set(self.symbols)
            for r in range(self.size)
            for c in range(self.size)
        }

        # 笼状态：已填数字、剩余和、剩余格数（按对象 id 分组，去重）
        cage_state: dict[int, dict] = {}
        seen_cages: set[int] = set()
        for cage in self.cell_to_cage.values():
            if id(cage) not in seen_cages:
                seen_cages.add(id(cage))
                cage_state[id(cage)] = {
                    "cage": cage,
                    "filled": [],
                    "remaining_sum": cage.target_sum,
                    "remaining_cells": set(cage.cells),
                }

        self._search(grid, candidates, cage_state, solutions, max_solutions, max_backtracks)
        return solutions

    def _search(
        self,
        grid: list[list[int]],
        candidates: dict[tuple[int, int], set[int]],
        cage_state: dict[int, dict],
        solutions: list[list[list[int]]],
        max_solutions: int,
        max_backtracks: int,
    ) -> bool:
        """回溯搜索核心。

        Returns:
            True 表示已找到足够数量的解，应停止搜索。
        """
        if len(solutions) >= max_solutions:
            return True
        if self.backtrack_count > max_backtracks:
            self.search_truncated = True
            return True

        # 选择候选最少的单元格（MRV 启发式）
        cell = self._select_mrv_cell(grid, candidates)
        if cell is None:
            # 所有单元格已填满，找到一个解
            solution = [row[:] for row in grid]
            solutions.append(solution)
            return len(solutions) >= max_solutions

        row, col = cell
        cage = self.cell_to_cage.get(cell)
        state = cage_state[id(cage)] if cage else None

        for value in sorted(candidates[cell]):
            # 检查笼约束
            if state is not None:
                new_sum = sum(state["filled"]) + value
                remaining_after = state["remaining_sum"] - new_sum
                remaining_cells_after = len(state["remaining_cells"]) - 1

                # 和不能超过目标
                if new_sum > state["cage"].target_sum:
                    continue
                # 如果这是笼的最后一个格子，和必须正好等于目标
                if remaining_cells_after == 0 and new_sum != state["cage"].target_sum:
                    continue
                # 剩余格子的最小可能和不能超过剩余和
                if remaining_cells_after > 0:
                    min_possible = self._min_remaining_sum(remaining_cells_after, value)
                    if new_sum + min_possible > state["cage"].target_sum:
                        continue
                    max_possible = self._max_remaining_sum(remaining_cells_after, value)
                    if new_sum + max_possible < state["cage"].target_sum:
                        continue

            # 尝试填入 value
            removed = self._place(grid, candidates, cage_state, row, col, value)

            if self._search(grid, candidates, cage_state, solutions, max_solutions, max_backtracks):
                self._undo(grid, candidates, cage_state, row, col, value, removed)
                return True

            self._undo(grid, candidates, cage_state, row, col, value, removed)

        self.backtrack_count += 1
        return False

    def _select_mrv_cell(
        self, grid: list[list[int]], candidates: dict[tuple[int, int], set[int]]
    ) -> Optional[tuple[int, int]]:
        """选择候选数最少的未填单元格（MRV 启发式）。

        若存在候选为 0 的单元格，直接返回它（触发回溯）。
        """
        best_cell: Optional[tuple[int, int]] = None
        best_count = self.size + 1
        for r in range(self.size):
            for c in range(self.size):
                if grid[r][c] == 0:
                    count = len(candidates[(r, c)])
                    if count == 0:
                        return (r, c)
                    if count < best_count:
                        best_count = count
                        best_cell = (r, c)
                        if count == 1:
                            return best_cell
        return best_cell

    def _place(
        self,
        grid: list[list[int]],
        candidates: dict[tuple[int, int], set[int]],
        cage_state: dict[int, dict],
        row: int,
        col: int,
        value: int,
    ) -> dict[tuple[int, int], int]:
        """在 (row, col) 填入 value，更新约束状态。

        Returns:
            removed: 记录被移除候选的单元格及对应值，用于撤销。
        """
        grid[row][col] = value
        removed: dict[tuple[int, int], int] = {}

        # 从同行、同列、同宫的候选中移除 value
        for nr, nc in self.config.neighbors(row, col):
            if grid[nr][nc] == 0 and value in candidates[(nr, nc)]:
                candidates[(nr, nc)].discard(value)
                removed[(nr, nc)] = value

        # 更新笼状态
        cage = self.cell_to_cage.get((row, col))
        if cage is not None:
            state = cage_state[id(cage)]
            state["filled"].append(value)
            state["remaining_sum"] -= value
            state["remaining_cells"].discard((row, col))

            # 从同笼其它未填单元格的候选中移除 value（笼内不重复）
            for cell in state["remaining_cells"]:
                if value in candidates[cell]:
                    candidates[cell].discard(value)
                    removed[cell] = value

        return removed

    def _undo(
        self,
        grid: list[list[int]],
        candidates: dict[tuple[int, int], set[int]],
        cage_state: dict[int, dict],
        row: int,
        col: int,
        value: int,
        removed: dict[tuple[int, int], int],
    ) -> None:
        """撤销 _place 的操作。"""
        grid[row][col] = 0

        # 恢复候选
        for cell, val in removed.items():
            candidates[cell].add(val)

        # 恢复笼状态
        cage = self.cell_to_cage.get((row, col))
        if cage is not None:
            state = cage_state[id(cage)]
            state["filled"].remove(value)
            state["remaining_sum"] += value
            state["remaining_cells"].add((row, col))

    def _min_remaining_sum(self, num_cells: int, exclude: int) -> int:
        """计算 num_cells 个不同数字（排除 exclude）的最小和。"""
        available = sorted(s for s in self.symbols if s != exclude)
        return sum(available[:num_cells])

    def _max_remaining_sum(self, num_cells: int, exclude: int) -> int:
        """计算 num_cells 个不同数字（排除 exclude）的最大和。"""
        available = sorted((s for s in self.symbols if s != exclude), reverse=True)
        return sum(available[:num_cells])

    def has_unique_solution(self, max_backtracks: int = 100000) -> bool:
        """判断谜题是否有唯一解。

        找到 2 个解即判定为非唯一。
        若搜索因回溯限制而中断（未完成），返回 False（不确定）。
        """
        solutions = self.solve(max_solutions=2, max_backtracks=max_backtracks)
        if self.search_truncated:
            return False
        return len(solutions) == 1

    def count_solutions(self, max_solutions: int = 2, max_backtracks: int = 100000) -> int:
        """统计解的数量（最多统计到 max_solutions 个）。"""
        return len(self.solve(max_solutions=max_solutions, max_backtracks=max_backtracks))
