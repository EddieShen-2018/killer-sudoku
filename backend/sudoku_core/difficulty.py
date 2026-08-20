"""难度评估与控制系统。

定义五级难度（入门/简单/中等/困难/专家）的笼参数和评估标准。

难度通过以下维度综合控制：
1. 笼大小范围：笼越大，线索越集中，越简单。
2. 单格笼比例：单格笼直接给出数字，越简单。
3. 求解器回溯次数：回溯越多，需要越复杂的推理。

难度评估流程：
- 生成谜题后，用求解器求解并统计回溯次数。
- 结合笼参数，判断实际难度是否落在目标区间。
"""

from __future__ import annotations

from dataclasses import dataclass

from .cage_builder import CageParams
from .models import Difficulty
from .solver import KillerSudokuSolver


@dataclass(frozen=True)
class DifficultyProfile:
    """难度档位配置。

    Attributes:
        difficulty: 难度枚举。
        cage_params: 笼划分参数。
        max_backtracks: 求解器评估时的最大回溯次数上限。
        min_backtracks: 该难度期望的最小回溯次数（低于则太简单）。
        target_backtracks: 该难度期望的最大回溯次数（高于则太难）。
    """

    difficulty: Difficulty
    cage_params: CageParams
    max_backtracks: int
    min_backtracks: int
    target_backtracks: int


# 五级难度配置
# 注意：回溯次数阈值会随棋盘尺寸变化，这里给出 9×9 的基准值，
# 评估器会根据尺寸做缩放。
DIFFICULTY_PARAMS: dict[Difficulty, DifficultyProfile] = {
    # 入门：中等笼为主，约束较强，易解易保证唯一解（无单格笼）
    Difficulty.BEGINNER: DifficultyProfile(
        difficulty=Difficulty.BEGINNER,
        cage_params=CageParams(min_size=2, max_size=4, single_cell_ratio=0.0),
        max_backtracks=500,
        min_backtracks=0,
        target_backtracks=150,
    ),
    # 简单：中等笼为主（无单格笼）
    Difficulty.EASY: DifficultyProfile(
        difficulty=Difficulty.EASY,
        cage_params=CageParams(min_size=2, max_size=4, single_cell_ratio=0.0),
        max_backtracks=2000,
        min_backtracks=50,
        target_backtracks=600,
    ),
    # 中等：中等笼（无单格笼）
    Difficulty.MEDIUM: DifficultyProfile(
        difficulty=Difficulty.MEDIUM,
        cage_params=CageParams(min_size=2, max_size=5, single_cell_ratio=0.0),
        max_backtracks=6000,
        min_backtracks=300,
        target_backtracks=2500,
    ),
    # 困难：中大笼（无单格笼）
    Difficulty.HARD: DifficultyProfile(
        difficulty=Difficulty.HARD,
        cage_params=CageParams(min_size=2, max_size=5, single_cell_ratio=0.0),
        max_backtracks=30000,
        min_backtracks=1500,
        target_backtracks=12000,
    ),
    # 专家：大笼为主，约束最弱（无单格笼）
    Difficulty.EXPERT: DifficultyProfile(
        difficulty=Difficulty.EXPERT,
        cage_params=CageParams(min_size=2, max_size=6, single_cell_ratio=0.0),
        max_backtracks=100000,
        min_backtracks=3000,
        target_backtracks=50000,
    ),
}


# 棋盘尺寸对应的回溯次数缩放因子（尺寸越大，单元格越多，回溯基准越高）
_SIZE_SCALE: dict[int, float] = {
    4: 0.15,
    6: 0.4,
    9: 1.0,
}


class DifficultyEvaluator:
    """难度评估器：评估生成谜题的实际难度是否匹配目标难度。"""

    def __init__(self, size: int):
        """初始化评估器。

        Args:
            size: 棋盘尺寸。
        """
        self.size = size
        self.scale = _SIZE_SCALE.get(size, 1.0)

    def evaluate(
        self, cages, max_backtracks: int | None = None
    ) -> tuple[int, Difficulty]:
        """评估谜题难度。

        用求解器求解并统计回溯次数，结合尺寸缩放后映射到难度级别。

        Args:
            cages: 笼列表。
            max_backtracks: 求解器最大回溯次数（默认取专家级配置）。

        Returns:
            (backtracks, difficulty): 实际回溯次数与评估出的难度级别。
        """
        if max_backtracks is None:
            max_backtracks = int(DIFFICULTY_PARAMS[Difficulty.EXPERT].max_backtracks * self.scale)

        solver = KillerSudokuSolver.from_cages(self.size, cages)
        solver.solve(max_solutions=1, max_backtracks=max_backtracks)
        raw_backtracks = solver.backtrack_count

        # 尺寸缩放后的回溯次数
        scaled = raw_backtracks / self.scale

        difficulty = self._classify(scaled)
        return raw_backtracks, difficulty

    def matches_target(
        self, cages, target: Difficulty
    ) -> tuple[bool, int, Difficulty]:
        """判断谜题难度是否匹配目标难度。

        Args:
            cages: 笼列表。
            target: 目标难度。

        Returns:
            (matches, backtracks, actual_difficulty):
            - matches: 是否匹配目标难度
            - backtracks: 实际回溯次数
            - actual_difficulty: 评估出的实际难度
        """
        profile = DIFFICULTY_PARAMS[target]
        max_bt = int(profile.max_backtracks * self.scale)
        backtracks, actual = self.evaluate(cages, max_backtracks=max_bt)
        matches = actual == target
        return matches, backtracks, actual

    def _classify(self, scaled_backtracks: float) -> Difficulty:
        """根据缩放后的回溯次数映射到难度级别。"""
        for diff in [
            Difficulty.BEGINNER,
            Difficulty.EASY,
            Difficulty.MEDIUM,
            Difficulty.HARD,
            Difficulty.EXPERT,
        ]:
            profile = DIFFICULTY_PARAMS[diff]
            if scaled_backtracks <= profile.target_backtracks:
                return diff
        return Difficulty.EXPERT
