"""将所有谜题 JSON 打包为单个内联 JS 文件。

生成的 all-puzzles.js 会赋值到 window.ALL_PUZZLES，
使前端在 file:// 协议下（双击打开 index.html）也能正常加载谜题，
无需任何 fetch 请求。

用法：
    python backend/bundle_puzzles.py
"""

import json
from pathlib import Path


def bundle() -> None:
    """读取 frontend/puzzles/ 下所有谜题 JSON，打包为 all-puzzles.js。"""
    puzzles_dir = Path(__file__).resolve().parent.parent / "frontend" / "puzzles"
    output_file = puzzles_dir / "all-puzzles.js"

    if not puzzles_dir.exists():
        raise FileNotFoundError(f"谜题目录不存在: {puzzles_dir}")

    all_puzzles: dict[str, dict] = {}

    # 遍历 {size}x{size}/{difficulty}/{puzzle_id}.json
    for size_dir in sorted(puzzles_dir.iterdir()):
        if not size_dir.is_dir():
            continue
        size_key = size_dir.name  # e.g. "4x4"
        all_puzzles[size_key] = {}

        for diff_dir in sorted(size_dir.iterdir()):
            if not diff_dir.is_dir():
                continue
            difficulty = diff_dir.name  # e.g. "beginner"
            all_puzzles[size_key][difficulty] = {}

            for json_file in sorted(diff_dir.glob("*.json")):
                puzzle_id = json_file.stem  # e.g. "4x4_beginner_1787117846_97fa791c"
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                all_puzzles[size_key][difficulty][puzzle_id] = data

    # 统计
    total = 0
    for size_key, diffs in all_puzzles.items():
        for diff, puzzles in diffs.items():
            count = len(puzzles)
            total += count
            print(f"  {size_key}/{diff}: {count} 个谜题")
    print(f"  总计: {total} 个谜题")

    # 写入 JS 文件
    json_str = json.dumps(all_puzzles, ensure_ascii=False, separators=(",", ":"))
    js_content = (
        "/* 自动生成 - 请勿手动编辑\n"
        " * 包含所有预生成谜题数据，供 file:// 协议下离线使用。\n"
        " * 由 backend/bundle_puzzles.py 生成。\n"
        " */\n"
        f"window.ALL_PUZZLES = {json_str};\n"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(js_content)

    size_kb = len(js_content.encode("utf-8")) / 1024
    print(f"\n已生成: {output_file} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    bundle()
