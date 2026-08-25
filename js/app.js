/* 主应用：状态管理与功能整合 */

const App = {
    // 游戏状态
    puzzle: null, // 谜题数据
    size: 9,
    difficulty: "medium",
    userGrid: [], // 用户填入的数字
    notes: {}, // 标记: "r,c" -> Set<number>
    history: [], // 撤销历史栈（最多3步）
    noteMode: false, // 标记模式
    completed: false,
    // 迷你计算器状态
    calc: { display: "0", pending: null, op: null, fresh: true },
    calcActive: false, // 计算器联动开关：true 时数字条同时输入计算器

    /**
     * 初始化应用
     */
    init() {
        this._bindEvents();
        // 从 URL 参数读取初始设置
        const params = new URLSearchParams(window.location.search);
        const size = parseInt(params.get("size"));
        const diff = params.get("difficulty");
        if (size) this._setSize(size);
        if (diff) document.getElementById("difficulty-select").value = diff;

        // 默认显示空白 9×9 棋盘
        this.difficulty = document.getElementById("difficulty-select").value;
        this._renderEmptyBoard();

        // 检测是否有已保存的进度，启用读取按钮
        this._updateLoadButton();

    },

    /**
     * 渲染空白棋盘（无笼信息，仅显示网格）
     */
    _renderEmptyBoard() {
        this.puzzle = null;
        this.userGrid = Array.from({ length: this.size }, () =>
            Array(this.size).fill(0)
        );
        this.notes = {};
        this.history = [];
        this.noteMode = false;
        this.completed = false;
        document.getElementById("note-btn").classList.remove("active");

        // 用空笼列表初始化棋盘
        Board.init({ size: this.size, cages: [] });
        Board.onCellSelect = (r, c) => this._onCellSelect(r, c);

        // 渲染数字条
        this._renderNumberPad();

        // 更新通关标记
        this._updateCompletedBadge();
        this._updateBoardCompletedBorder();

        // 更新撤销按钮状态
        this._updateUndoButton();

        this._setStatus(`Click "New" to start ${this.size}×${this.size} ${this._difficultyLabel(this.difficulty)}`);
    },

    /**
     * 绑定事件
     */
    _bindEvents() {
        // 尺寸选择
        document.querySelectorAll("#size-group .btn-toggle").forEach((btn) => {
            btn.addEventListener("click", () => {
                this._setSize(parseInt(btn.dataset.size));
            });
        });

        // 难度选择：更新当前难度并刷新读取按钮状态
        document.getElementById("difficulty-select").addEventListener("change", (e) => {
            this.difficulty = e.target.value;
            this._updateLoadButton();
        });

        // 新游戏
        document.getElementById("new-game-btn").addEventListener("click", () => {
            this.startNewGame();
        });

        // 保存进度
        document.getElementById("save-btn").addEventListener("click", () => {
            this.saveProgress();
        });

        // 读取进度
        document.getElementById("load-btn").addEventListener("click", () => {
            this.loadProgress();
        });

        // 撤销
        document.getElementById("undo-btn").addEventListener("click", () => {
            this.undo();
        });

        // 标记模式
        document.getElementById("note-btn").addEventListener("click", () => {
            this.toggleNoteMode();
        });

        // 清除
        document.getElementById("erase-btn").addEventListener("click", () => {
            this.eraseSelected();
        });

        // 验证
        document.getElementById("check-btn").addEventListener("click", () => {
            this.checkSolution();
        });

        // 迷你计算器
        this._initCalculator();
// 键盘支持
document.addEventListener("keydown", (e) => {
    this._handleKeydown(e);
});
},


    /**
     * 设置棋盘尺寸
     */
    _setSize(size) {
        this.size = size;
        document.querySelectorAll("#size-group .btn-toggle").forEach((btn) => {
            btn.classList.toggle("active", parseInt(btn.dataset.size) === size);
        });
        // 如果当前没有加载谜题，重新渲染空白棋盘
        if (!this.puzzle) {
            this._renderEmptyBoard();
        }
        // 尺寸变化后刷新读取按钮状态（按当前尺寸+难度判断是否有存档）
        this._updateLoadButton();
    },

    /**
     * 开始新游戏
     */
    async startNewGame() {
        this.difficulty = document.getElementById("difficulty-select").value;
        this._setLoading(true);
        this._setStatus("Generating...");

        try {
            const puzzle = await API.getPuzzle(this.size, this.difficulty);
            this._loadPuzzle(puzzle);
            this._setStatus(`Loaded ${this.size}×${this.size} ${this._difficultyLabel(this.difficulty)}`);
        } catch (e) {
            this._setStatus(`Error: ${e.message}`);
            console.error(e);
        } finally {
            this._setLoading(false);
        }
    },

    /**
     * 加载谜题
     */
    _loadPuzzle(puzzle) {
        this.puzzle = puzzle;
        this.size = puzzle.size;
        this.completed = Storage.isCompleted(puzzle.puzzle_id);
        this.userGrid = Array.from({ length: this.size }, () =>
            Array(this.size).fill(0)
        );
        this.notes = {};
        this.history = [];
        this.noteMode = false;
        document.getElementById("note-btn").classList.remove("active");

        // 初始化棋盘
        Board.init(puzzle);
        Board.onCellSelect = (r, c) => this._onCellSelect(r, c);

        // 根据通关状态显示/隐藏金色边框
        this._updateBoardCompletedBorder();

        // 渲染数字条
        this._renderNumberPad();

        // 更新通关标记
        this._updateCompletedBadge();

        // 更新撤销按钮状态
        this._updateUndoButton();

        // 隐藏提示面板（新棋盘无选中格）
        this._updateHint(null);
    },

    /**
     * 渲染数字条
     */
    _renderNumberPad() {
        const pad = document.getElementById("number-pad");
        pad.innerHTML = "";
        // 根据尺寸调整列数（+1 为 0 按钮）
        const cols = (this.size <= 9 ? this.size : 8) + 1;
        pad.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

        for (let n = 1; n <= this.size; n++) {
            const btn = document.createElement("button");
            btn.className = "number-btn";
            btn.dataset.number = n;
            btn.textContent = n;
            btn.style.position = "relative";

            // 数量计数
            const countEl = document.createElement("span");
            countEl.className = "count";
            countEl.id = `count-${n}`;
            btn.appendChild(countEl);

            btn.addEventListener("click", () => {
                if (this.calcActive) {
                    this._calcInputDigit(n);
                } else {
                    this._inputNumber(n);
                }
            });
            pad.appendChild(btn);
        }

        // 0 按钮：仅用于计算器，不能填入棋盘
        const zeroBtn = document.createElement("button");
        zeroBtn.className = "number-btn number-btn-zero";
        zeroBtn.dataset.number = 0;
        zeroBtn.textContent = "0";
        zeroBtn.title = "Calculator only";
        zeroBtn.addEventListener("click", () => {
            if (this.calcActive) this._calcInputDigit(0);
        });
        pad.appendChild(zeroBtn);

        this._updateNumberPad();
    },

    /**
     * 单元格选中回调
     */
    _onCellSelect(r, c) {
        Board._updateHighlights(this.userGrid);
        this._updateNumberPad();
        this._updateHint(r, c);
    },

    /**
     * 更新提示面板：显示选中格所在宫/笼的数字之和
     * 1. 所在宫已填数字之和
     * 2. 所在笼已填数字之和
     * 3. 所在宫中有交集的笼的未填数字之和（笼目标值之和）
     * 4. 与所在笼有相同宫的笼的未填数字之和（笼目标值之和）
     */
    _updateHint(r, c) {
        const panel = document.getElementById("hint-panel");
        if (r === null || r === undefined || !this.puzzle) {
            panel.style.display = "none";
            return;
        }
        panel.style.display = "flex";

        const size = this.size;
        const boxRows = Board._getBoxRows();
        const boxCols = Board._getBoxCols();
        const cages = Board.cages;
        const cellToCage = Board.cellToCage;

        // 选中格所在宫的行列范围
        const boxR0 = Math.floor(r / boxRows) * boxRows;
        const boxC0 = Math.floor(c / boxCols) * boxCols;
        const boxCells = [];
        for (let rr = boxR0; rr < boxR0 + boxRows; rr++) {
            for (let cc = boxC0; cc < boxC0 + boxCols; cc++) {
                boxCells.push([rr, cc]);
            }
        }

        // 1. 所在宫已填数字
        const boxFilledNums = [];
        for (const [rr, cc] of boxCells) {
            if (this.userGrid[rr][cc]) boxFilledNums.push(this.userGrid[rr][cc]);
        }

        // 2. 所在笼已填数字
        const cageIdx = cellToCage[`${r},${c}`];
        const cage = cages[cageIdx];
        const cageFilledNums = [];
        for (const [rr, cc] of cage.cells) {
            if (this.userGrid[rr][cc]) cageFilledNums.push(this.userGrid[rr][cc]);
        }

        // 辅助：判断某格是否未填
        const isEmpty = (rr, cc) => !this.userGrid[rr][cc];

        // 辅助：判断某笼是否与给定宫有交集
        const cageIntersectsBox = (cg, bR0, bC0) => {
            for (const [rr, cc] of cg.cells) {
                if (rr >= bR0 && rr < bR0 + boxRows && cc >= bC0 && cc < bC0 + boxCols) {
                    return true;
                }
            }
            return false;
        };

        // 3. 所在宫中有交集且含未填格的笼的目标值
        const boxCagesTargets = [];
        for (const cg of cages) {
            if (!cageIntersectsBox(cg, boxR0, boxC0)) continue;
            let emptyInBox = 0;
            for (const [rr, cc] of cg.cells) {
                if (rr >= boxR0 && rr < boxR0 + boxRows &&
                    cc >= boxC0 && cc < boxC0 + boxCols) {
                    if (isEmpty(rr, cc)) emptyInBox++;
                }
            }
            if (emptyInBox > 0) {
                boxCagesTargets.push(cg.target_sum);
            }
        }

        // 4. 与所在笼有相同宫且含未填格的笼的目标值（含自身）
        const cageBoxSet = new Set();
        for (const [rr, cc] of cage.cells) {
            const bR = Math.floor(rr / boxRows) * boxRows;
            const bC = Math.floor(cc / boxCols) * boxCols;
            cageBoxSet.add(`${bR},${bC}`);
        }
        const cageBoxesTargets = [];
        for (const cg of cages) {
            let hasOverlap = false;
            for (const [rr, cc] of cg.cells) {
                const bR = Math.floor(rr / boxRows) * boxRows;
                const bC = Math.floor(cc / boxCols) * boxCols;
                if (cageBoxSet.has(`${bR},${bC}`)) {
                    hasOverlap = true;
                    break;
                }
            }
            if (!hasOverlap) continue;
            let hasEmpty = false;
            for (const [rr, cc] of cg.cells) {
                if (isEmpty(rr, cc)) { hasEmpty = true; break; }
            }
            if (hasEmpty) {
                cageBoxesTargets.push(cg.target_sum);
            }
        }

        // 格式化为等式：左边列出求和项，右边为求和后的值
        const fmt = (nums) => {
            if (nums.length === 0) return "0=0";
            const total = nums.reduce((a, b) => a + b, 0);
            return `${nums.join("+")}=${total}`;
        };
        document.getElementById("hint-box").textContent = fmt(boxFilledNums);
        document.getElementById("hint-cage").textContent = fmt(cageFilledNums);
        document.getElementById("hint-box-cages").textContent = fmt(boxCagesTargets);
        document.getElementById("hint-cage-boxes").textContent = fmt(cageBoxesTargets);
    },

    /**
     * 输入数字
     */
    _inputNumber(num) {
        if (!this.puzzle || !Board.selectedCell) return;
        const { row, col } = Board.selectedCell;

        if (this.noteMode) {
            // 标记模式：切换候选数字
            this._toggleNote(row, col, num);
        } else {
            // 填数模式
            this._placeNumber(row, col, num);
        }
    },

    /**
     * 填入数字
     */
    _placeNumber(row, col, num) {
        const oldValue = this.userGrid[row][col];
        if (oldValue === num) return; // 相同数字不操作

        // 记录历史（最多3步）
        this._pushHistory({
            type: "place",
            row,
            col,
            oldValue,
            newValue: num,
        });

        this.userGrid[row][col] = num;
        Board.setCellValue(row, col, num);
        Board.clearErrors();
        Board._updateHighlights(this.userGrid);
        this._updateNumberPad();
        this._updateHint(row, col);
    },

    /**
     * 切换标记（候选数字）
     */
    _toggleNote(row, col, num) {
        const key = `${row},${col}`;
        if (!this.notes[key]) {
            this.notes[key] = new Set();
        }
        const notes = this.notes[key];

        // 记录历史
        const hadNote = notes.has(num);
        this._pushHistory({
            type: "note",
            row,
            col,
            num,
            hadNote,
        });

        if (hadNote) {
            notes.delete(num);
        } else {
            notes.add(num);
        }

        Board.setCellNotes(row, col, notes);
    },

    /**
     * 清除选中单元格
     */
    eraseSelected() {
        if (!this.puzzle || !Board.selectedCell) return;
        const { row, col } = Board.selectedCell;
        const oldValue = this.userGrid[row][col];
        const key = `${row},${col}`;
        const oldNotes = this.notes[key] ? new Set(this.notes[key]) : null;

        if (oldValue === 0 && !oldNotes) return;

        this._pushHistory({
            type: "erase",
            row,
            col,
            oldValue,
            oldNotes,
        });

        this.userGrid[row][col] = 0;
        delete this.notes[key];
        Board.setCellValue(row, col, 0);
        Board.setCellNotes(row, col, new Set());
        Board._updateHighlights(this.userGrid);
        this._updateNumberPad();
        this._updateHint(row, col);
    },

    /**
     * 撤销（最多回退3步）
     */
    undo() {
        if (this.history.length === 0) return;
        const action = this.history.pop();

        if (action.type === "place") {
            this.userGrid[action.row][action.col] = action.oldValue;
            Board.setCellValue(action.row, action.col, action.oldValue);
        } else if (action.type === "note") {
            const key = `${action.row},${action.col}`;
            if (!this.notes[key]) this.notes[key] = new Set();
            if (action.hadNote) {
                this.notes[key].add(action.num);
            } else {
                this.notes[key].delete(action.num);
            }
            Board.setCellNotes(action.row, action.col, this.notes[key]);
        } else if (action.type === "erase") {
            this.userGrid[action.row][action.col] = action.oldValue;
            Board.setCellValue(action.row, action.col, action.oldValue);
            if (action.oldNotes) {
                const key = `${action.row},${action.col}`;
                this.notes[key] = new Set(action.oldNotes);
                Board.setCellNotes(action.row, action.col, this.notes[key]);
            }
        }

        Board._updateHighlights(this.userGrid);
        this._updateNumberPad();
        this._updateUndoButton();
        if (Board.selectedCell) {
            this._updateHint(Board.selectedCell.row, Board.selectedCell.col);
        }
    },

    /**
     * 推入历史栈（最多保留3步）
     */
    _pushHistory(action) {
        this.history.push(action);
        if (this.history.length > 3) {
            this.history.shift();
        }
        this._updateUndoButton();
    },

    /**
     * 更新撤销按钮状态
     */
    _updateUndoButton() {
        const btn = document.getElementById("undo-btn");
        btn.disabled = this.history.length === 0;
    },

    /**
     * 切换标记模式
     */
    toggleNoteMode() {
        this.noteMode = !this.noteMode;
        document.getElementById("note-btn").classList.toggle("active", this.noteMode);
    },

    /**
     * 更新数字条状态（检索功能：变灰）
     */
    _updateNumberPad() {
        if (!this.puzzle) return;
        // 统计每个数字已填入的数量
        const counts = {};
        for (let n = 1; n <= this.size; n++) counts[n] = 0;
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.userGrid[r][c] > 0) {
                    counts[this.userGrid[r][c]]++;
                }
            }
        }

        for (let n = 1; n <= this.size; n++) {
            const btn = document.querySelector(`.number-btn[data-number="${n}"]`);
            if (!btn) continue;
            const countEl = document.getElementById(`count-${n}`);
            const remaining = this.size - counts[n];
            if (countEl) {
                countEl.textContent = remaining > 0 ? remaining : "";
            }
            // 该数字已填满（出现 size 次）则变灰
            btn.classList.toggle("disabled", counts[n] >= this.size);
        }
    },

    /**
     * 验证解答
     */
    async checkSolution() {
        if (!this.puzzle) return;

        // 检查是否填满
        let filled = true;
        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                if (this.userGrid[r][c] === 0) {
                    filled = false;
                    break;
                }
            }
            if (!filled) break;
        }

        if (!filled) {
            this._setStatus("Not filled yet, keep going");
            return;
        }

        this._setLoading(true);
        try {
            const result = await API.validateSolution(
                this.puzzle.puzzle_id,
                this.userGrid,
                this.puzzle._solution
            );
            if (result.valid) {
                this._setStatus("Congratulations! Correct!");
                this._onComplete();
            } else {
                // 标记错误单元格
                const errorCells = result.error_cells || [];
                Board.markErrors(errorCells);
                this._setStatus(`${errorCells.length} error(s) found`);
            }
        } catch (e) {
            this._setStatus(`Validation failed: ${e.message}`);
        } finally {
            this._setLoading(false);
        }
    },

    /**
     * 通关处理
     */
    _onComplete() {
        if (this.puzzle) {
            Storage.markCompleted(this.puzzle.puzzle_id);
            this.completed = true;
            this._updateCompletedBadge();
            this._updateBoardCompletedBorder();
            // 通关后清除当前槽位存档（已通关无需继续）
            Storage.clearProgress(this.size, this.difficulty);
            this._updateLoadButton();
        }
    },

    /**
     * 根据通关状态切换棋盘金色边框
     */
    _updateBoardCompletedBorder() {
        const board = document.getElementById("board");
        if (board) board.classList.toggle("completed", this.completed);
    },

    /**
     * 更新通关标记显示
     */
    _updateCompletedBadge() {
        const badge = document.getElementById("completed-badge");
        badge.style.display = this.completed ? "inline-block" : "none";
    },

    /* ==================== 进度存档 ==================== */

    /**
     * 保存当前进度（填数 + 笔记）
     */
    saveProgress() {
        if (!this.puzzle) {
            this._setStatus("Start a game first before saving");
            return;
        }
        // 序列化 notes：Set -> 数组
        const notesData = {};
        for (const key in this.notes) {
            if (this.notes[key] && this.notes[key].size > 0) {
                notesData[key] = [...this.notes[key]];
            }
        }
        const ok = Storage.saveProgress(this.size, this.difficulty, {
            puzzle_id: this.puzzle.puzzle_id,
            userGrid: this.userGrid,
            notes: notesData,
            noteMode: this.noteMode,
            completed: this.completed,
        });
        if (ok) {
            this._updateLoadButton();
            this._setStatus(`Progress saved (${this.size}×${this.size} ${this._difficultyLabel(this.difficulty)})`);
        } else {
            this._setStatus("Save failed, please retry");
        }
    },

    /**
     * 读取已保存的进度
     * @param {number} size - 棋盘尺寸（不传则使用当前尺寸）
     * @param {string} difficulty - 难度（不传则使用当前难度）
     */
    async loadProgress(size, difficulty) {
        const loadSize = size || this.size;
        const loadDiff = difficulty || this.difficulty;
        const data = Storage.loadProgress(loadSize, loadDiff);
        if (!data) {
            this._setStatus(`No saved progress for ${loadSize}×${loadSize} ${this._difficultyLabel(loadDiff)}`);
            return;
        }

        this._setLoading(true);
        this._setStatus("Loading progress...");
        try {
            // 按 puzzle_id 重新加载谜题数据（cages / solution）
            const puzzle = await API.getPuzzleById(data.puzzle_id);
            // 初始化棋盘（会重置 userGrid/notes/history）
            this._loadPuzzle(puzzle);

            // 恢复尺寸/难度，保持与存档一致
            this.difficulty = loadDiff;
            this._setSize(loadSize);
            document.getElementById("difficulty-select").value = this.difficulty;

            // 恢复填数
            for (let r = 0; r < this.size; r++) {
                for (let c = 0; c < this.size; c++) {
                    const val = data.userGrid[r][c];
                    this.userGrid[r][c] = val;
                    Board.setCellValue(r, c, val);
                }
            }

            // 恢复笔记：数组 -> Set
            this.notes = {};
            for (const key in data.notes) {
                this.notes[key] = new Set(data.notes[key]);
                const [r, c] = key.split(",").map(Number);
                Board.setCellNotes(r, c, this.notes[key]);
            }

            // 恢复标记模式
            this.noteMode = !!data.noteMode;
            document.getElementById("note-btn").classList.toggle("active", this.noteMode);

            // 恢复通关状态
            this.completed = !!data.completed;
            this._updateCompletedBadge();
            this._updateBoardCompletedBorder();

            // 刷新数字条计数与高亮
            Board._updateHighlights(this.userGrid);
            this._updateNumberPad();
            this._updateUndoButton();

            this._setStatus("Progress restored");
        } catch (e) {
            this._setStatus(`Load failed: ${e.message}`);
            console.error(e);
        } finally {
            this._setLoading(false);
        }
    },

    /**
     * 根据当前尺寸+难度是否有存档启用/禁用读取按钮
     */
    _updateLoadButton() {
        const btn = document.getElementById("load-btn");
        if (btn) btn.disabled = !Storage.hasProgress(this.size, this.difficulty);
    },

    /**
     * 键盘事件
     */
    _handleKeydown(e) {
        // Shift+Tab 切换计算器：未激活则开启并聚焦，已激活则关闭
        if (e.key === "Tab" && e.shiftKey) {
            e.preventDefault();
            if (!this.calcActive) {
                // 未激活：开启联动并聚焦输入框
                this._toggleCalcActive();
                const display = document.getElementById("calc-display");
                display.focus();
                display.select();
            } else {
                // 已激活：关闭联动并失焦
                this._toggleCalcActive();
                document.getElementById("calc-display").blur();
            }
            return;
        }

        // 计算器输入框聚焦时，不拦截键盘（交由计算器自身处理）
        if (document.activeElement === document.getElementById("calc-display")) return;

        if (!this.puzzle || !Board.selectedCell) return;
        const { row, col } = Board.selectedCell;

        // 数字键
        if (e.key >= "1" && e.key <= "9") {
            const num = parseInt(e.key);
            if (num <= this.size) {
                this._inputNumber(num);
                e.preventDefault();
            }
        }
        // 方向键移动
        else if (e.key === "ArrowUp" && row > 0) {
            Board.selectCell(row - 1, col);
            e.preventDefault();
        } else if (e.key === "ArrowDown" && row < this.size - 1) {
            Board.selectCell(row + 1, col);
            e.preventDefault();
        } else if (e.key === "ArrowLeft" && col > 0) {
            Board.selectCell(row, col - 1);
            e.preventDefault();
        } else if (e.key === "ArrowRight" && col < this.size - 1) {
            Board.selectCell(row, col + 1);
            e.preventDefault();
        }
        // Esc/删除：擦除当前格
        else if (e.key === "Escape" || e.key === "Delete") {
            this.eraseSelected();
            e.preventDefault();
        }
        // N 切换标记模式
        else if (e.key === "n" || e.key === "N") {
            this.toggleNoteMode();
            e.preventDefault();
        }
        // Z 撤销
        else if (e.key === "z" || e.key === "Z") {
            this.undo();
            e.preventDefault();
        }
    },

    /**
     * 设置加载状态
     */
    _setLoading(loading) {
        document.getElementById("loading").style.display = loading ? "block" : "none";
        document.getElementById("board").style.opacity = loading ? "0.5" : "1";
    },

    /**
     * 设置状态文字
     */
    _setStatus(text) {
        document.getElementById("status-text").textContent = text;
    },

    /**
     * 难度标签
     */
    _difficultyLabel(diff) {
        const labels = {
            beginner: "Beginner",
            easy: "Easy",
            medium: "Medium",
            hard: "Hard",
            expert: "Expert",
        };
        return labels[diff] || diff;
    },

    /* ==================== 迷你计算器 ==================== */

    /**
     * 初始化迷你计算器
     */
    _initCalculator() {
        const display = document.getElementById("calc-display");

        // 计算器联动开关
        document.getElementById("calc-toggle").addEventListener("click", () => {
            this._toggleCalcActive();
        });

        // 允许在显示框中直接输入数字
        display.addEventListener("input", () => {
            // 只保留数字和负号
            let val = display.value.replace(/[^\d-]/g, "");
            // 负号只允许在开头
            val = val.replace(/(?!^)-/g, "");
            this.calc.display = val || "0";
            this.calc.fresh = false;
            // 不实时刷新，避免光标跳动
        });

        // 失焦时刷新显示
        display.addEventListener("blur", () => {
            this._calcRender();
        });

        // 按键处理：数字直接输入，Enter 等号（保持聚焦以支持连续运算），Backspace 归零，+/- 运算
        display.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                this._calcEquals();
            } else if (e.key === "Backspace") {
                e.preventDefault();
                this._calcClear();
            } else if (e.key === "+" || e.key === "-") {
                e.preventDefault();
                this._calcOp(e.key);
            } else if (e.key >= "0" && e.key <= "9") {
                e.preventDefault();
                this._calcInputDigit(parseInt(e.key));
            }
        });

        document.getElementById("calc-plus").addEventListener("click", () => {
            this._calcOp("+");
        });
        document.getElementById("calc-minus").addEventListener("click", () => {
            this._calcOp("-");
        });
        document.getElementById("calc-clear").addEventListener("click", () => {
            this._calcClear();
        });
        document.getElementById("calc-equals").addEventListener("click", () => {
            this._calcEquals();
        });

        this._calcRender();
    },

    /**
     * 切换计算器联动开关
     */
    _toggleCalcActive() {
        this.calcActive = !this.calcActive;
        const bar = document.getElementById("calc-bar");
        const toggle = document.getElementById("calc-toggle");
        if (this.calcActive) {
            bar.classList.remove("calc-off");
            toggle.classList.add("active");
            toggle.title = "Disable calculator link";
        } else {
            bar.classList.add("calc-off");
            toggle.classList.remove("active");
            toggle.title = "Enable calculator link";
        }
    },

    /**
     * 数字条输入数字到计算器
     */
    _calcInputDigit(digit) {
        if (this.calc.fresh) {
            // 新输入：替换当前显示
            this.calc.display = String(digit);
            this.calc.fresh = false;
        } else {
            // 追加数字
            this.calc.display = this.calc.display === "0" ? String(digit) : this.calc.display + digit;
        }
        this._calcRender();
    },

    /**
     * 获取当前显示数值
     */
    _calcValue() {
        return parseInt(this.calc.display, 10) || 0;
    },

    /**
     * 刷新显示
     */
    _calcRender() {
        document.getElementById("calc-display").value = this.calc.display;
    },

    /**
     * 运算符按钮
     */
    _calcOp(op) {
        const current = this._calcValue();
        if (this.calc.pending !== null && this.calc.op && !this.calc.fresh) {
            // 连续运算：先算出中间结果
            this.calc.pending = this._calcCompute(this.calc.pending, current, this.calc.op);
        } else {
            this.calc.pending = current;
        }
        this.calc.op = op;
        this.calc.fresh = true;
        // 清空输入栏，等待输入下一个数字
        this.calc.display = "";
        this._calcRender();
    },

    /**
     * 等号按钮
     */
    _calcEquals() {
        if (this.calc.pending === null || !this.calc.op) return;
        const current = this._calcValue();
        const result = this._calcCompute(this.calc.pending, current, this.calc.op);
        this.calc.display = String(result);
        // 结果作为新的 pending，允许继续 +/- 运算
        this.calc.pending = result;
        this.calc.op = null;
        this.calc.fresh = true;
        this._calcRender();
    },

    /**
     * 归零
     */
    _calcClear() {
        this.calc.display = "0";
        this.calc.pending = null;
        this.calc.op = null;
        this.calc.fresh = true;
        this._calcRender();
    },

    /**
     * 执行运算
     */
    _calcCompute(a, b, op) {
        if (op === "+") return a + b;
        if (op === "-") return a - b;
        return b;
    },
};

// 启动应用
document.addEventListener("DOMContentLoaded", () => {
    App.init();
});
