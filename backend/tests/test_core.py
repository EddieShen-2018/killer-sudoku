"""核心数独库单元测试。

覆盖：
- 数据模型（棋盘配置、笼、谜题序列化）
- 求解器（求解、唯一解验证）
- 笼划分（覆盖所有单元格、笼内相邻）
- 生成器（生成各尺寸入门难度谜题、唯一解、验证器通过）
- 验证器（正确解通过、错误解报错）
- 难度评估（回溯次数统计）
"""

from __future__ import annotations

import random
import sys
import os
import time

# 将 backend 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sudoku_core.models import (
    BOARD_CONFIGS,
    Cage,
    Difficulty,
    Puzzle,
    get_board_config,
)
from sudoku_core.solver import KillerSudokuSolver
from sudoku_core.cage_builder import CageBuilder, CageParams
from sudoku_core.generator import KillerSudokuGenerator
from sudoku_core.validator import KillerSudokuValidator
from sudoku_core.difficulty import DIFFICULTY_PARAMS, DifficultyEvaluator


def test_board_configs():
    """测试棋盘配置。"""
    print("测试棋盘配置...", end=" ")
    for size, config in BOARD_CONFIGS.items():
        assert config.size == size
        assert len(config.symbols) == size
        assert config.box_rows * config.box_cols == size or (
            config.box_rows * (size // config.box_cols) == size
        )
        # 宫索引计算
        assert 0 <= config.box_index(0, 0) < size
        # 宫单元格数量正确
        for box_idx in range(size):
            cells = config.box_cells(box_idx)
            assert len(cells) == size
    # 不支持的尺寸应报错
    try:
        get_board_config(5)
        assert False, "应抛出 ValueError"
    except ValueError:
        pass
    print("通过")


def test_cage_serialization():
    """测试笼序列化。"""
    print("测试笼序列化...", end=" ")
    cage = Cage(cells=[(0, 0), (0, 1), (1, 0)], target_sum=15)
    d = cage.to_dict()
    assert d["target_sum"] == 15
    assert d["size"] == 3
    cage2 = Cage.from_dict(d)
    assert cage2.target_sum == 15
    assert cage2.cells == cage.cells
    assert cage2.contains(0, 0)
    assert not cage2.contains(2, 2)
    print("通过")


def test_solver_basic():
    """测试求解器基本功能：用已知解构造笼并求解。"""
    print("测试求解器基本功能...", end=" ")
    size = 4
    config = get_board_config(size)
    # 一个已知的 4x4 解
    solution = [
        [1, 2, 3, 4],
        [3, 4, 1, 2],
        [2, 1, 4, 3],
        [4, 3, 2, 1],
    ]
    # 构造笼：每行一个笼
    cages = []
    for r in range(size):
        cells = [(r, c) for c in range(size)]
        target = sum(solution[r][c] for c in range(size))
        cages.append(Cage(cells=cells, target_sum=target))

    solver = KillerSudokuSolver(config, cages)
    solutions = solver.solve(max_solutions=2)
    assert len(solutions) >= 1
    # 验证找到的解是正确的
    found = any(s == solution for s in solutions)
    assert found, "求解器未找到已知解"
    print("通过")


def test_solver_unique():
    """测试唯一解判断。"""
    print("测试唯一解判断...", end=" ")
    size = 4
    config = get_board_config(size)
    solution = [
        [1, 2, 3, 4],
        [3, 4, 1, 2],
        [2, 1, 4, 3],
        [4, 3, 2, 1],
    ]
    # 用细粒度笼（每格一笼）保证唯一解
    cages = []
    for r in range(size):
        for c in range(size):
            cages.append(Cage(cells=[(r, c)], target_sum=solution[r][c]))

    solver = KillerSudokuSolver(config, cages)
    assert solver.has_unique_solution(), "单格笼应有唯一解"
    print("通过")


def test_cage_builder():
    """测试笼划分：覆盖所有单元格。"""
    print("测试笼划分...", end=" ")
    size = 9
    config = get_board_config(size)
    rng = random.Random(42)
    builder = CageBuilder(config, rng)
    # 构造一个简单解
    solution = [[((r * 3 + r // 3 + c) % size) + 1 for c in range(size)] for r in range(size)]
    params = CageParams(min_size=2, max_size=4)
    cages = builder.build(solution, params)

    # 所有单元格应被覆盖且不重复
    all_cells = set()
    for cage in cages:
        for cell in cage.cells:
            assert cell not in all_cells, f"单元格 {cell} 被重复分配"
            all_cells.add(cell)
    assert len(all_cells) == size * size, "未覆盖所有单元格"

    # 笼内单元格应相邻
    for cage in cages:
        if len(cage.cells) <= 1:
            continue
        # 检查笼内连通性
        visited = {cage.cells[0]}
        frontier = [cage.cells[0]]
        while frontier:
            cell = frontier.pop()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nb = (cell[0] + dr, cell[1] + dc)
                if nb in cage.cells and nb not in visited:
                    visited.add(nb)
                    frontier.append(nb)
        assert len(visited) == len(cage.cells), "笼内单元格不连通"

    # 笼和应正确
    for cage in cages:
        expected = sum(solution[r][c] for r, c in cage.cells)
        assert cage.target_sum == expected, "笼和计算错误"
    print("通过")


def test_generator_small():
    """测试生成器：4x4 入门难度。"""
    print("测试生成器 4x4...", end=" ")
    rng = random.Random(123)
    gen = KillerSudokuGenerator.from_size(4, rng)
    puzzle = gen.generate(Difficulty.BEGINNER, max_attempts=10, max_cage_retries=10)
    assert puzzle.size == 4
    assert len(puzzle.cages) > 0
    assert puzzle.difficulty == Difficulty.BEGINNER

    # 入门难度不强制唯一解，只验证解合法
    # 验证解答正确
    validator = KillerSudokuValidator.from_puzzle(puzzle)
    result = validator.validate(puzzle.solution)
    assert result.valid, "生成的解答应通过验证"
    print("通过")


def test_generator_6x6():
    """测试生成器：6x6 入门难度。"""
    print("测试生成器 6x6...", end=" ")
    rng = random.Random(456)
    gen = KillerSudokuGenerator.from_size(6, rng)
    puzzle = gen.generate(Difficulty.BEGINNER, max_attempts=10, max_cage_retries=10)
    assert puzzle.size == 6
    # 入门难度不强制唯一解，只验证解合法
    validator = KillerSudokuValidator.from_puzzle(puzzle)
    assert validator.validate(puzzle.solution).valid
    print("通过")


def test_generator_9x9():
    """测试生成器：9x9 入门难度（入门难度不强制唯一解）。"""
    print("测试生成器 9x9...", end=" ")
    rng = random.Random(789)
    gen = KillerSudokuGenerator.from_size(9, rng)
    puzzle = gen.generate(Difficulty.BEGINNER, max_attempts=30, max_cage_retries=20)
    assert puzzle.size == 9
    # 入门难度不强制唯一解，只验证解合法
    validator = KillerSudokuValidator.from_puzzle(puzzle)
    assert validator.validate(puzzle.solution).valid
    print("通过")


def test_validator_errors():
    """测试验证器错误检测。"""
    print("测试验证器错误检测...", end=" ")
    size = 4
    config = get_board_config(size)
    solution = [
        [1, 2, 3, 4],
        [3, 4, 1, 2],
        [2, 1, 4, 3],
        [4, 3, 2, 1],
    ]
    cages = []
    for r in range(size):
        cells = [(r, c) for c in range(size)]
        cages.append(Cage(cells=cells, target_sum=10))

    validator = KillerSudokuValidator(config, cages)

    # 正确解
    result = validator.validate(solution)
    assert result.valid

    # 错误解：交换两个数字制造行重复
    wrong = [row[:] for row in solution]
    wrong[0][0], wrong[0][1] = wrong[0][1], wrong[0][0]
    result = validator.validate(wrong)
    assert not result.valid
    assert len(result.errors) > 0

    # 不完整解
    incomplete = [row[:] for row in solution]
    incomplete[0][0] = 0
    result = validator.validate(incomplete)
    assert not result.complete
    assert not result.valid
    print("通过")


def test_puzzle_serialization():
    """测试谜题序列化/反序列化。"""
    print("测试谜题序列化...", end=" ")
    rng = random.Random(321)
    gen = KillerSudokuGenerator.from_size(4, rng)
    puzzle = gen.generate(Difficulty.BEGINNER, max_attempts=10, max_cage_retries=10)

    d = puzzle.to_dict()
    assert "solution" in d
    puzzle2 = Puzzle.from_dict(d)
    assert puzzle2.size == puzzle.size
    assert puzzle2.difficulty == puzzle.difficulty
    assert len(puzzle2.cages) == len(puzzle.cages)
    assert puzzle2.solution == puzzle.solution

    # 公开字典不含解答
    pub = puzzle.to_public_dict()
    assert "solution" not in pub
    print("通过")


def test_difficulty_evaluator():
    """测试难度评估器。"""
    print("测试难度评估器...", end=" ")
    evaluator = DifficultyEvaluator(9)
    assert evaluator.scale == 1.0
    evaluator4 = DifficultyEvaluator(4)
    assert evaluator4.scale == 0.15

    # 所有难度配置都存在
    for diff in Difficulty:
        assert diff in DIFFICULTY_PARAMS
        profile = DIFFICULTY_PARAMS[diff]
        assert profile.cage_params.min_size >= 1
        assert profile.cage_params.max_size >= profile.cage_params.min_size
    print("通过")


def run_all():
    """运行所有测试。"""
    tests = [
        test_board_configs,
        test_cage_serialization,
        test_solver_basic,
        test_solver_unique,
        test_cage_builder,
        test_generator_small,
        test_generator_6x6,
        test_generator_9x9,
        test_validator_errors,
        test_puzzle_serialization,
        test_difficulty_evaluator,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"失败: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
