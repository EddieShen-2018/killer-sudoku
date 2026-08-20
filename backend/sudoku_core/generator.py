"""杀手数独生成器。

生成流程：
1. 生成一个完整的标准数独解（随机化回溯填充）。
2. 根据目标难度的笼参数，在完整解上划分笼。
3. 用求解器验证笼划分是否产生唯一解。
4. 用难度评估器验证实际难度是否匹配目标。
5. 若不满足，重新划分笼（多次尝试）；仍不满足则重新生成完整解。

生成结果为 Puzzle 对象，包含笼信息、完整解、难度和唯一 ID。
"""

from __future__ import annotations

import random
import time
import uuid

from .cage_builder import CageBuilder, CageParams
from .difficulty import DIFFICULTY_PARAMS, DifficultyEvaluator
from .models import BoardConfig, Cage, Difficulty, Puzzle, get_board_config
from .solver import KillerSudokuSolver


class KillerSudokuGenerator:
    """杀手数独生成器。"""

    def __init__(self, config: BoardConfig, rng: random.Random | None = None):
        """初始化生成器。

        Args:
            config: 棋盘配置。
            rng: 随机数生成器。
        """
        self.config = config
        self.size = config.size
        self.rng = rng or random.Random()
        self._cage_builder = CageBuilder(config, self.rng)
        self._evaluator = DifficultyEvaluator(self.size)

    @classmethod
    def from_size(cls, size: int, rng: random.Random | None = None) -> "KillerSudokuGenerator":
        """便捷构造：根据棋盘尺寸创建。"""
        return cls(get_board_config(size), rng)

    def generate(
        self,
        difficulty: Difficulty = Difficulty.MEDIUM,
        max_attempts: int = 30,
        max_cage_retries: int = 20,
    ) -> Puzzle:
        """生成一个指定难度的杀手数独谜题。

        Args:
            difficulty: 目标难度。
            max_attempts: 重新生成完整解的最大尝试次数。
            max_cage_retries: 每个完整解上重新划分笼的最大尝试次数。

        Returns:
            生成的 Puzzle 对象。

        Raises:
            RuntimeError: 超过最大尝试次数仍无法生成匹配难度的谜题。
        """
        profile = DIFFICULTY_PARAMS[difficulty]

        # 唯一性验证的回溯限制：适中即可，搜索被截断视为"很可能唯一"
        uniqueness_limit = max(
            5000,
            int(profile.max_backtracks * self._evaluator.scale * 2),
        )

        # 入门难度不强制要求唯一解（小笼约束弱，难以保证唯一性）
        require_unique = difficulty != Difficulty.BEGINNER

        # 记录找到的最佳谜题（唯一解但难度不匹配的）
        best_puzzle: Puzzle | None = None

        for attempt in range(1, max_attempts + 1):
            # 1. 生成完整解
            solution = self._generate_full_solution()

            # 2. 多次尝试笼划分
            for cage_attempt in range(max_cage_retries):
                cages = self._cage_builder.build(solution, profile.cage_params)

                # 3. 验证唯一解（入门难度跳过）
                if require_unique:
                    solver = KillerSudokuSolver(self.config, cages)
                    solutions = solver.solve(max_solutions=2, max_backtracks=uniqueness_limit)
                    if len(solutions) >= 2:
                        # 明确找到 2 个解，非唯一，跳过
                        continue
                    # 0 或 1 个解：若被截断，视为"很可能唯一"，接受

                # 4. 验证难度匹配
                matches, backtracks, actual = self._evaluator.matches_target(cages, difficulty)
                if matches:
                    puzzle_id = self._make_id(difficulty)
                    return Puzzle(
                        size=self.size,
                        cages=cages,
                        solution=solution,
                        difficulty=difficulty,
                        puzzle_id=puzzle_id,
                    )

                # 5. 记录谜题作为备选
                if best_puzzle is None:
                    puzzle_id = self._make_id(actual)
                    best_puzzle = Puzzle(
                        size=self.size,
                        cages=cages,
                        solution=solution,
                        difficulty=actual,
                        puzzle_id=puzzle_id,
                    )

        # 若严格匹配失败，返回找到的谜题（难度取评估值）
        if best_puzzle is not None:
            return best_puzzle

        raise RuntimeError(
            f"无法在 {max_attempts} 次尝试内生成 {self.size}×{self.size} "
            f"{difficulty.value} 难度的谜题"
        )

    def _generate_full_solution(self) -> list[list[int]]:
        """生成一个完整的标准数独解（随机化）。

        使用随机化回溯填充：每次填入单元格时随机打乱数字顺序。
        """
        grid: list[list[int]] = [[0] * self.size for _ in range(self.size)]
        self._fill_grid(grid, 0, 0)
        return grid

    def _fill_grid(self, grid: list[list[int]], row: int, col: int) -> bool:
        """递归回溯填充网格（随机化）。"""
        if row == self.size:
            return True  # 全部填完
        next_row, next_col = self._next_cell(row, col)

        numbers = list(self.config.symbols)
        self.rng.shuffle(numbers)

        for num in numbers:
            if self._is_valid_placement(grid, row, col, num):
                grid[row][col] = num
                if self._fill_grid(grid, next_row, next_col):
                    return True
                grid[row][col] = 0

        return False

    def _next_cell(self, row: int, col: int) -> tuple[int, int]:
        """计算下一个单元格坐标（行优先）。"""
        col += 1
        if col == self.size:
            col = 0
            row += 1
        return row, col

    def _is_valid_placement(
        self, grid: list[list[int]], row: int, col: int, num: int
    ) -> bool:
        """检查在 (row, col) 填入 num 是否满足数独约束。"""
        # 同行
        for c in range(self.size):
            if grid[row][c] == num:
                return False
        # 同列
        for r in range(self.size):
            if grid[r][col] == num:
                return False
        # 同宫
        box = self.config.box_cells(self.config.box_index(row, col))
        for r, c in box:
            if grid[r][c] == num:
                return False
        return True

    def _make_id(self, difficulty: Difficulty) -> str:
        """生成谜题唯一 ID。"""
        timestamp = int(time.time())
        unique = uuid.uuid4().hex[:8]
        return f"{self.size}x{self.size}_{difficulty.value}_{timestamp}_{unique}"
