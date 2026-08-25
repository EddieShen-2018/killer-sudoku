"""笼划分算法。

在已生成的完整数独解上，将所有单元格划分为若干"笼"（cages）。
每个笼是一组相邻单元格，并记录其目标和（即笼内数字之和）。

算法采用随机 flood-fill 扩展：
1. 随机选择未分配单元格作为新笼起点。
2. 向相邻未分配单元格扩展，笼大小受难度参数控制。
3. 重复直到所有单元格被分配。
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .models import BoardConfig, Cage, get_board_config


@dataclass
class CageParams:
    """笼划分参数（由难度决定）。

    Attributes:
        min_size: 笼最小单元格数。
        max_size: 笼最大单元格数。
        single_cell_ratio: 允许单格笼的概率（专家难度较高）。
    """

    min_size: int
    max_size: int
    single_cell_ratio: float = 0.0


class CageBuilder:
    """笼划分器：在完整解上生成笼结构。"""

    def __init__(self, config: BoardConfig, rng: random.Random | None = None):
        """初始化笼划分器。

        Args:
            config: 棋盘配置。
            rng: 随机数生成器（可传入以复现结果）。
        """
        self.config = config
        self.size = config.size
        self.rng = rng or random.Random()

    @classmethod
    def from_size(cls, size: int, rng: random.Random | None = None) -> "CageBuilder":
        """便捷构造：根据棋盘尺寸创建。"""
        return cls(get_board_config(size), rng)

    def build(self, solution: list[list[int]], params: CageParams) -> list[Cage]:
        """在完整解上划分笼。

        多次尝试划分，确保没有小于 min_size 的笼。

        Args:
            solution: 完整数独解（二维列表）。
            params: 笼划分参数。

        Returns:
            笼列表。
        """
        max_retries = 50
        for _ in range(max_retries):
            cages = self._build_once(solution, params)
            if params.min_size <= 1 or not self._has_small_cages(cages, params.min_size):
                return cages
        # 最后一次尝试仍失败，返回最好的结果（可能有少量小笼）
        return cages

    def _build_once(self, solution: list[list[int]], params: CageParams) -> list[Cage]:
        """单次划分笼（不保证无小笼）。"""
        # 已分配单元格集合
        assigned: set[tuple[int, int]] = set()
        cages: list[Cage] = []

        all_cells = [
            (r, c) for r in range(self.size) for c in range(self.size)
        ]
        self.rng.shuffle(all_cells)

        for start in all_cells:
            if start in assigned:
                continue
            cage_cells = self._grow_cage(start, assigned, params, solution)
            for cell in cage_cells:
                assigned.add(cell)
            target_sum = sum(solution[r][c] for r, c in cage_cells)
            cages.append(Cage(cells=cage_cells, target_sum=target_sum))

        # 后处理：合并小于 min_size 的笼到相邻笼中
        if params.min_size > 1:
            cages = self._merge_small_cages(cages, solution, params)

        return cages

    def _has_small_cages(self, cages: list[Cage], min_size: int) -> bool:
        """检查是否存在小于 min_size 的笼。"""
        return any(len(cage.cells) < min_size for cage in cages)

    def _merge_small_cages(
        self,
        cages: list[Cage],
        solution: list[list[int]],
        params: CageParams,
    ) -> list[Cage]:
        """将小于 min_size 的笼合并到相邻的笼中。

        对于每个过小的笼，找到与其单元格相邻的其他笼，
        将其合并到其中最大的相邻笼中（避免连锁产生新的小笼）。
        """
        # 构建单元格到笼索引的映射
        cell_to_cage: dict[tuple[int, int], int] = {}
        for idx, cage in enumerate(cages):
            for cell in cage.cells:
                cell_to_cage[cell] = idx

        changed = True
        while changed:
            changed = False
            # 重新构建映射
            cell_to_cage = {}
            for idx, cage in enumerate(cages):
                for cell in cage.cells:
                    cell_to_cage[cell] = idx

            for i, cage in enumerate(cages):
                if len(cage.cells) >= params.min_size:
                    continue

                # 找到所有相邻的笼
                neighbor_cages: dict[int, list[tuple[int, int]]] = {}
                for cell in cage.cells:
                    for nb in self._adjacent(cell):
                        nb_idx = cell_to_cage.get(nb)
                        if nb_idx is not None and nb_idx != i:
                            neighbor_cages.setdefault(nb_idx, []).append(nb)

                if not neighbor_cages:
                    continue

                # 选择最大的相邻笼合并（减少产生新小笼的概率），且不产生重复值
                small_values = {solution[r][c] for r, c in cage.cells}
                best_idx = None
                best_size = 0
                for nb_idx in neighbor_cages:
                    target_cage = cages[nb_idx]
                    target_values = {solution[r][c] for r, c in target_cage.cells}
                    if target_values & small_values:
                        continue  # 合并会产生重复值，跳过
                    if len(target_cage.cells) > best_size:
                        best_size = len(target_cage.cells)
                        best_idx = nb_idx

                if best_idx is None:
                    continue  # 无法无重复合并，跳过

                # 合并：将当前笼的单元格加入目标笼
                target_cage = cages[best_idx]
                merged_cells = list(target_cage.cells) + list(cage.cells)
                merged_sum = sum(solution[r][c] for r, c in merged_cells)
                cages[best_idx] = Cage(
                    cells=merged_cells, target_sum=merged_sum
                )
                # 标记当前笼为空（稍后过滤）
                cages[i] = Cage(cells=[], target_sum=0)
                changed = True
                break  # 重新开始循环，因为索引已变化

        # 过滤掉空笼
        return [c for c in cages if len(c.cells) > 0]

    def _grow_cage(
        self,
        start: tuple[int, int],
        assigned: set[tuple[int, int]],
        params: CageParams,
        solution: list[list[int]],
    ) -> list[tuple[int, int]]:
        """从起点单元格开始扩展一个笼。

        Args:
            start: 起点单元格。
            assigned: 已分配单元格集合（本方法会读取但不修改，由调用方更新）。
            params: 笼参数。
            solution: 完整数独解（用于确保笼内数字不重复）。

        Returns:
            笼内所有单元格坐标列表。
        """
        cage_cells: list[tuple[int, int]] = [start]
        cage_values: set[int] = {solution[start[0]][start[1]]}
        # 决定本笼目标大小
        target_size = self._decide_cage_size(params)

        while len(cage_cells) < target_size:
            # 收集所有相邻的未分配单元格（且值不在笼内）
            frontier: list[tuple[int, int]] = []
            for cell in cage_cells:
                for nb in self._adjacent(cell):
                    if nb not in assigned and nb not in cage_cells and nb not in frontier:
                        nb_val = solution[nb[0]][nb[1]]
                        if nb_val not in cage_values:
                            frontier.append(nb)

            if not frontier:
                break

            # 随机选择一个相邻单元格加入
            chosen = self.rng.choice(frontier)
            cage_cells.append(chosen)
            cage_values.add(solution[chosen[0]][chosen[1]])

        return cage_cells

    def _decide_cage_size(self, params: CageParams) -> int:
        """决定本笼的目标大小。"""
        # 单格笼概率
        if params.min_size <= 1 and self.rng.random() < params.single_cell_ratio:
            return 1
        return self.rng.randint(params.min_size, params.max_size)

    def _adjacent(self, cell: tuple[int, int]) -> list[tuple[int, int]]:
        """返回单元格的上下左右相邻单元格（不越界）。"""
        r, c = cell
        neighbors: list[tuple[int, int]] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                neighbors.append((nr, nc))
        return neighbors
