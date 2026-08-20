# 杀手数独 Web 应用

支持多种棋盘尺寸（4×4、6×6、9×9）和五种难度（入门、简单、中等、困难、专家）的杀手数独（Killer Sudoku）Web 应用。采用黑白灰风格，适配手机端，可部署到 GitHub Pages。

## 功能特性

- **多种尺寸**：4×4、6×6、9×9
- **五种难度**：入门、简单、中等、困难、专家
- **杀手数独**：带笼（cages）和求和线索
- **填数交互**：点击单元格 + 点击数字条填入
- **检索功能**：数字填完后，数字条上该数字变灰
- **强调高亮**：选中数字时，棋盘上同数字高亮
- **撤销功能**：最多回退 3 步
- **标记功能**：标记模式下可在单元格内记录候选小字
- **通关标记**：完成游戏后自动标记已通关
- **键盘支持**：数字键填数、方向键移动、N 切换标记、Ctrl+Z 撤销

## 项目结构

```
sudoku/
├── backend/                  # Python 后端
│   ├── sudoku_core/          # 核心数独库
│   │   ├── models.py         # 数据模型
│   │   ├── solver.py         # 求解器
│   │   ├── cage_builder.py   # 笼划分算法
│   │   ├── generator.py      # 生成器
│   │   ├── validator.py      # 验证器
│   │   └── difficulty.py     # 难度评估
│   ├── api/                  # FastAPI 服务（开发用）
│   ├── storage/              # 模板库存储
│   ├── tests/                # 单元测试
│   ├── generate_puzzles.py   # 谜题预生成脚本
│   ├── bundle_puzzles.py     # 打包内联数据脚本（file:// 离线用）
│   └── requirements.txt
├── frontend/                 # 前端（可独立部署 GitHub Pages）
│   ├── index.html
│   ├── css/                  # 黑白灰样式
│   ├── js/                   # 交互逻辑
│   └── puzzles/              # 预生成的谜题数据
│       ├── index.json        # 谜题索引（HTTP 服务器用）
│       ├── all-puzzles.js    # 内联全部谜题（file:// 离线用）
│       └── {size}x{size}/    # 各尺寸谜题 JSON 文件
└── README.md
```

## 部署方式

### 方式一：GitHub Pages（推荐，纯静态）

前端直接加载预生成的谜题数据，无需后端运行。

1. **预生成谜题**（需要 Python 环境）：
   ```bash
   cd backend
   pip install -r requirements.txt
   python generate_puzzles.py --count 5 --sizes 4,6,9
   ```

2. **打包内联数据**（支持 file:// 双击打开）：
   ```bash
   python bundle_puzzles.py
   ```
   此步骤将所有谜题 JSON 打包为 `frontend/puzzles/all-puzzles.js`，
   使前端在 `file://` 协议下（双击 index.html）也能正常加载谜题。

3. **部署前端**：
   - 将 `frontend/` 目录内容推送到 GitHub 仓库
   - 在仓库 Settings → Pages 中启用 GitHub Pages
   - 选择 `main` 分支根目录

### 方式二：本地直接打开（file:// 协议）

双击 `frontend/index.html` 即可直接游玩，无需任何服务器。
前提是已运行 `bundle_puzzles.py` 生成 `all-puzzles.js` 内联数据文件。

### 方式三：本地开发服务器（前后端联调）

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000

## 预生成谜题

```bash
cd backend

# 生成所有尺寸所有难度，每种 5 个
python generate_puzzles.py --count 5

# 仅生成 9×9 中等难度，10 个
python generate_puzzles.py --count 10 --sizes 9 --difficulties medium

# 指定随机种子（可复现）
python generate_puzzles.py --count 5 --seed 42
```

生成的谜题存放在 `frontend/puzzles/{尺寸}x{尺寸}/{难度}/` 目录，并自动生成 `index.json` 索引。

运行 `python bundle_puzzles.py` 可将所有谜题打包为 `all-puzzles.js` 内联文件，
供 `file://` 协议离线使用。前端会优先使用内联数据，HTTP 服务器场景下回退到 fetch JSON。

## 运行测试

```bash
cd backend
python tests/test_core.py
```

## 技术栈

- **后端**：Python 3.10+、FastAPI
- **前端**：原生 HTML/CSS/JavaScript（无构建步骤）
- **存储**：JSON 文件（静态部署）/ FastAPI（开发模式）
