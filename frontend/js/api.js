/* 谜题数据访问层
 *
 * 数据来源优先级：
 *   1. window.ALL_PUZZLES（内联 JS，file:// 协议下可用，无需 fetch）
 *   2. fetch ./puzzles/ 静态 JSON（HTTP 服务器 / GitHub Pages 场景）
 *
 * 这样双击打开 index.html（file://）和部署到 GitHub Pages（http://）均可正常工作。
 */

const API = {
    // 内联数据是否可用
    _hasInline() {
        return typeof window !== "undefined" && window.ALL_PUZZLES;
    },

    /**
     * 获取指定尺寸+难度的所有谜题 ID 列表
     * @returns {Promise<string[]>}
     */
    async _getPuzzleIds(size, difficulty) {
        const sizeKey = `${size}x${size}`;

        // 优先使用内联数据
        if (this._hasInline()) {
            const bucket = window.ALL_PUZZLES[sizeKey] && window.ALL_PUZZLES[sizeKey][difficulty];
            return bucket ? Object.keys(bucket) : [];
        }

        // 回退：从 index.json 加载
        if (!this._index) {
            try {
                const resp = await fetch("./puzzles/index.json");
                if (!resp.ok) throw new Error("Failed to load puzzle index");
                this._index = await resp.json();
            } catch (e) {
                console.error("Failed to load index:", e);
                this._index = {};
            }
        }
        const puzzles = this._index[sizeKey] && this._index[sizeKey][difficulty];
        return puzzles || [];
    },

    /**
     * 根据 ID 获取谜题原始数据
     * @returns {Promise<object>}
     */
    async _getPuzzleData(puzzleId) {
        // 优先使用内联数据
        if (this._hasInline()) {
            const parts = puzzleId.split("_");
            const sizeKey = parts[0];
            const difficulty = parts[1];
            const data = window.ALL_PUZZLES[sizeKey] &&
                         window.ALL_PUZZLES[sizeKey][difficulty] &&
                         window.ALL_PUZZLES[sizeKey][difficulty][puzzleId];
            if (data) return data;
            throw new Error(`Puzzle not found in inline data: ${puzzleId}`);
        }

        // 回退：fetch 静态 JSON
        const parts = puzzleId.split("_");
        if (parts.length < 2) throw new Error("Invalid puzzle ID");
        const sizeKey = parts[0];
        const difficulty = parts[1];
        const url = `./puzzles/${sizeKey}/${difficulty}/${puzzleId}.json`;
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`Puzzle not found (${resp.status})`);
        return await resp.json();
    },

    /**
     * 获取谜题（随机取一个）
     * @param {number} size - 棋盘尺寸 (4/6/9)
     * @param {string} difficulty - 难度 (beginner/easy/medium/hard/expert)
     * @returns {Promise<object>} 谜题公开数据（含 _solution 用于本地验证）
     */
    async getPuzzle(size, difficulty) {
        const ids = await this._getPuzzleIds(size, difficulty);
        if (ids.length === 0) {
            throw new Error(`No ${size}x${size} ${difficulty} puzzles available`);
        }

        // 随机选一个
        const puzzleId = ids[Math.floor(Math.random() * ids.length)];
        const data = await this._getPuzzleData(puzzleId);

        return {
            puzzle_id: data.puzzle_id,
            size: data.size,
            difficulty: data.difficulty,
            cages: data.cages,
            _solution: data.solution, // 保留解答用于本地验证
        };
    },

    /**
     * 根据 ID 获取谜题
     * @param {string} puzzleId - 谜题 ID
     * @returns {Promise<object>} 谜题公开数据（含 _solution）
     */
    async getPuzzleById(puzzleId) {
        const data = await this._getPuzzleData(puzzleId);
        return {
            puzzle_id: data.puzzle_id,
            size: data.size,
            difficulty: data.difficulty,
            cages: data.cages,
            _solution: data.solution,
        };
    },

    /**
     * 本地验证解答（不依赖后端）
     * @param {string} puzzleId - 谜题 ID
     * @param {number[][]} solution - 用户解答
     * @param {number[][]} correctSolution - 已加载的正确解答（可选，避免重复请求）
     * @returns {Promise<object>} 验证结果
     */
    async validateSolution(puzzleId, solution, correctSolution = null) {
        // 优先使用已加载的解答，避免重复请求
        if (!correctSolution) {
            const puzzle = await this.getPuzzleById(puzzleId);
            correctSolution = puzzle._solution;
        }
        const size = correctSolution.length;

        const errors = [];
        const errorCells = [];
        let complete = true;

        // 检查完整性
        for (let r = 0; r < size; r++) {
            for (let c = 0; c < size; c++) {
                if (!solution[r][c] || solution[r][c] === 0) {
                    complete = false;
                }
            }
        }

        // 与正确解答对比
        for (let r = 0; r < size; r++) {
            for (let c = 0; c < size; c++) {
                if (solution[r][c] && solution[r][c] !== 0 && solution[r][c] !== correctSolution[r][c]) {
                    errors.push(`Cell (${r + 1},${c + 1}) value ${solution[r][c]} is incorrect`);
                    errorCells.push([r, c]);
                }
            }
        }

        return {
            valid: errors.length === 0 && complete,
            complete: complete,
            errors: errors,
            error_cells: errorCells,
        };
    },

    /**
     * 获取支持的尺寸和难度
     * @returns {Promise<object>}
     */
    async getDifficulties() {
        return {
            sizes: [4, 6, 9],
            difficulties: [
                { value: "beginner", label: "Beginner" },
                { value: "easy", label: "Easy" },
                { value: "medium", label: "Medium" },
                { value: "hard", label: "Hard" },
                { value: "expert", label: "Expert" },
            ],
        };
    },
};
