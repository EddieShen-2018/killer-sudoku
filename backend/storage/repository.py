"""模板库存储：按尺寸+难度分类的谜题 JSON 存储。

目录结构：
    templates_db/
    ├── 4x4/
    │   ├── beginner/
    │   │   ├── 001.json
    │   │   └── ...
    │   ├── easy/
    │   └── ...
    ├── 6x6/
    └── 9x9/

每个 JSON 文件存储一个 Puzzle 的完整序列化数据。
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

from sudoku_core.models import Difficulty, Puzzle


class PuzzleRepository:
    """谜题模板库仓库：管理谜题的存储与读取。"""

    def __init__(self, base_dir: str | Path):
        """初始化仓库。

        Args:
            base_dir: 模板库根目录路径。
        """
        self.base_dir = Path(base_dir)

    def _difficulty_dir(self, size: int, difficulty: Difficulty) -> Path:
        """获取指定尺寸+难度的目录路径。"""
        return self.base_dir / f"{size}x{size}" / difficulty.value

    def _puzzle_path(self, size: int, difficulty: Difficulty, puzzle_id: str) -> Path:
        """获取谜题文件路径。"""
        return self._difficulty_dir(size, difficulty) / f"{puzzle_id}.json"

    def save(self, puzzle: Puzzle) -> Path:
        """保存谜题到模板库。

        Args:
            puzzle: 谜题对象。

        Returns:
            保存的文件路径。
        """
        dir_path = self._difficulty_dir(puzzle.size, puzzle.difficulty)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{puzzle.puzzle_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(puzzle.to_dict(), f, ensure_ascii=False, indent=2)
        return file_path

    def load(self, size: int, difficulty: Difficulty, puzzle_id: str) -> Puzzle | None:
        """加载指定谜题。

        Args:
            size: 棋盘尺寸。
            difficulty: 难度。
            puzzle_id: 谜题 ID。

        Returns:
            Puzzle 对象，若不存在返回 None。
        """
        file_path = self._puzzle_path(size, difficulty, puzzle_id)
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Puzzle.from_dict(data)

    def load_by_id(self, puzzle_id: str) -> Puzzle | None:
        """根据 puzzle_id 在所有目录中查找谜题。

        Args:
            puzzle_id: 谜题 ID（格式: {size}x{size}_{difficulty}_{...}）。

        Returns:
            Puzzle 对象，若不存在返回 None。
        """
        # 从 ID 解析尺寸和难度
        parts = puzzle_id.split("_")
        if len(parts) < 2:
            return None
        try:
            size = int(parts[0].split("x")[0])
            difficulty = Difficulty(parts[1])
        except (ValueError, IndexError):
            return None
        return self.load(size, difficulty, puzzle_id)

    def list_puzzles(self, size: int, difficulty: Difficulty) -> list[str]:
        """列出指定尺寸+难度下的所有谜题 ID。

        Returns:
            谜题 ID 列表。
        """
        dir_path = self._difficulty_dir(size, difficulty)
        if not dir_path.exists():
            return []
        return sorted(p.stem for p in dir_path.glob("*.json"))

    def count(self, size: int, difficulty: Difficulty) -> int:
        """统计指定尺寸+难度下的谜题数量。"""
        return len(self.list_puzzles(size, difficulty))

    def get_random(self, size: int, difficulty: Difficulty) -> Puzzle | None:
        """随机获取一个谜题。

        Args:
            size: 棋盘尺寸。
            difficulty: 难度。

        Returns:
            随机 Puzzle 对象，若库为空返回 None。
        """
        ids = self.list_puzzles(size, difficulty)
        if not ids:
            return None
        chosen_id = random.choice(ids)
        return self.load(size, difficulty, chosen_id)

    def get_random_public(self, size: int, difficulty: Difficulty) -> dict | None:
        """随机获取一个谜题的公开字典（不含解答）。

        Returns:
            公开字典，若库为空返回 None。
        """
        puzzle = self.get_random(size, difficulty)
        if puzzle is None:
            return None
        return puzzle.to_public_dict()

    def ensure_stock(
        self,
        size: int,
        difficulty: Difficulty,
        target_count: int,
        generator,
    ) -> int:
        """确保模板库中指定尺寸+难度有足够谜题，不足则生成补充。

        Args:
            size: 棋盘尺寸。
            difficulty: 难度。
            target_count: 目标数量。
            generator: KillerSudokuGenerator 实例。

        Returns:
            新生成的谜题数量。
        """
        current = self.count(size, difficulty)
        needed = target_count - current
        if needed <= 0:
            return 0

        generated = 0
        for _ in range(needed):
            try:
                puzzle = generator.generate(difficulty)
                self.save(puzzle)
                generated += 1
            except RuntimeError:
                # 生成失败则跳过
                continue
        return generated
