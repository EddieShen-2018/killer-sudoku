"""批量预生成谜题脚本。

为三种尺寸 × 五种难度预生成谜题 JSON 文件，供前端静态加载。
生成的文件存放在 frontend/puzzles/ 目录，按尺寸/难度分类。

用法：
    cd backend
    python generate_puzzles.py [--count N] [--sizes 4,6,9] [--difficulties beginner,easy,medium,hard,expert]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

# 将 backend 目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sudoku_core.models import Difficulty
from sudoku_core.generator import KillerSudokuGenerator

# 输出目录：frontend/puzzles/{size}x{size}/{difficulty}/
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "frontend" / "puzzles"

SUPPORTED_SIZES = [4, 6, 9]
ALL_DIFFICULTIES = [
    Difficulty.BEGINNER,
    Difficulty.EASY,
    Difficulty.MEDIUM,
    Difficulty.HARD,
    Difficulty.EXPERT,
]


def generate_for_combo(size: int, difficulty: Difficulty, count: int, rng: random.Random) -> tuple[int, int]:
    """为指定尺寸+难度生成谜题。

    Returns:
        (成功数, 失败数)
    """
    output_dir = OUTPUT_DIR / f"{size}x{size}" / difficulty.value
    output_dir.mkdir(parents=True, exist_ok=True)

    # 清理该目录下的旧文件（避免难度不匹配的残留）
    for old_file in output_dir.glob("*.json"):
        old_file.unlink()

    generator = KillerSudokuGenerator.from_size(size, rng)
    success = 0
    failed = 0

    # 根据尺寸调整生成参数（大尺寸更耗时）
    max_attempts = 30 if size <= 9 else 15
    max_cage_retries = 20 if size <= 9 else 10

    for i in range(count):
        try:
            puzzle = generator.generate(difficulty, max_attempts=max_attempts, max_cage_retries=max_cage_retries)
            # 只存储难度匹配的谜题（生成器兜底可能返回不同难度）
            if puzzle.difficulty != difficulty:
                # 重新生成 ID 以匹配目标难度
                puzzle.difficulty = difficulty
                puzzle.puzzle_id = generator._make_id(difficulty)
            file_path = output_dir / f"{puzzle.puzzle_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(puzzle.to_dict(), f, ensure_ascii=False, indent=2)
            success += 1
            print(f"  [{success}/{count}] {puzzle.puzzle_id}")
        except RuntimeError as e:
            failed += 1
            print(f"  [失败 {failed}] {e}")

    return success, failed


def generate_index() -> None:
    """生成谜题索引文件，列出所有可用谜题。"""
    index: dict = {}
    for size in SUPPORTED_SIZES:
        size_key = f"{size}x{size}"
        index[size_key] = {}
        for diff in ALL_DIFFICULTIES:
            diff_dir = OUTPUT_DIR / size_key / diff.value
            if diff_dir.exists():
                files = sorted(p.stem for p in diff_dir.glob("*.json"))
                index[size_key][diff.value] = files
            else:
                index[size_key][diff.value] = []

    index_path = OUTPUT_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n索引文件已生成: {index_path}")


def main():
    parser = argparse.ArgumentParser(description="批量预生成杀手数独谜题")
    parser.add_argument("--count", type=int, default=5, help="每种尺寸+难度生成的谜题数量（默认5）")
    parser.add_argument("--sizes", type=str, default="4,6,9", help="尺寸列表（逗号分隔）")
    parser.add_argument("--difficulties", type=str, default="beginner,easy,medium,hard,expert", help="难度列表")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（用于复现）")
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    diff_names = args.difficulties.split(",")
    difficulties = [Difficulty(d.strip()) for d in diff_names]

    rng = random.Random(args.seed)

    print(f"输出目录: {OUTPUT_DIR}")
    print(f"尺寸: {sizes}")
    print(f"难度: {[d.value for d in difficulties]}")
    print(f"每种组合数量: {args.count}")
    print("=" * 50)

    total_success = 0
    total_failed = 0
    start_time = time.time()

    for size in sizes:
        for diff in difficulties:
            print(f"\n生成 {size}×{size} {diff.value}...")
            combo_start = time.time()
            success, failed = generate_for_combo(size, diff, args.count, rng)
            combo_time = time.time() - combo_start
            total_success += success
            total_failed += failed
            print(f"  完成: {success} 成功, {failed} 失败, 耗时 {combo_time:.1f}s")

    # 生成索引
    generate_index()

    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"全部完成: {total_success} 成功, {total_failed} 失败, 总耗时 {elapsed:.1f}s")


if __name__ == "__main__":
    main()
