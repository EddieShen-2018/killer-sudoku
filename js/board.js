/* 棋盘渲染与交互模块 */

const Board = {
    size: 9,
    cages: [],
    cellToCage: {}, // "r,c" -> cage index
    selectedCell: null, // {row, col}
    onCellSelect: null, // 单元格选中回调
    onNumberInput: null, // 数字输入回调

    boardEl: null,

    /**
     * 初始化棋盘
     */
    init(puzzleData) {
        this.size = puzzleData.size;
        this.cages = puzzleData.cages;
        this.selectedCell = null;
        this._buildCellToCageMap();
        this._render();
    },

    /**
     * 构建单元格到笼的映射
     */
    _buildCellToCageMap() {
        this.cellToCage = {};
        this.cages.forEach((cage, idx) => {
            cage.cells.forEach((cell) => {
                this.cellToCage[`${cell[0]},${cell[1]}`] = idx;
            });
        });
    },

    /**
     * 渲染棋盘
     */
    _render() {
        this.boardEl = document.getElementById("board");
        this.boardEl.innerHTML = "";
        this.boardEl.className = `board size-${this.size}`;
        this.boardEl.style.gridTemplateColumns = `repeat(${this.size}, 1fr)`;
        this.boardEl.style.gridTemplateRows = `repeat(${this.size}, 1fr)`;

        const boxRows = this._getBoxRows();
        const boxCols = this._getBoxCols();

        for (let r = 0; r < this.size; r++) {
            for (let c = 0; c < this.size; c++) {
                const cell = this._createCell(r, c, boxRows, boxCols);
                this.boardEl.appendChild(cell);
            }
        }
    },

    /**
     * 获取宫的行数
     */
    _getBoxRows() {
        const map = { 4: 2, 6: 2, 9: 3 };
        return map[this.size] || 3;
    },

    /**
     * 获取宫的列数
     */
    _getBoxCols() {
        const map = { 4: 2, 6: 3, 9: 3 };
        return map[this.size] || 3;
    },

    /**
     * 创建单元格 DOM
     */
    _createCell(r, c, boxRows, boxCols) {
        const cell = document.createElement("div");
        cell.className = "cell";
        cell.dataset.row = r;
        cell.dataset.col = c;
        cell.id = `cell-${r}-${c}`;

        // 宫格分隔线
        if ((c + 1) % boxCols === 0 && c < this.size - 1) {
            cell.classList.add("box-right");
        }
        if ((r + 1) % boxRows === 0 && r < this.size - 1) {
            cell.classList.add("box-bottom");
        }

        // 笼边界
        this._applyCageBorders(cell, r, c);

        // 笼和数字（左上角单元格显示）
        const cageIdx = this.cellToCage[`${r},${c}`];
        if (cageIdx !== undefined) {
            const cage = this.cages[cageIdx];
            // 找到笼内最左上角的单元格
            const topLeft = this._findTopLeftCell(cage.cells);
            if (topLeft[0] === r && topLeft[1] === c) {
                const sumEl = document.createElement("div");
                sumEl.className = "cage-sum";
                sumEl.textContent = cage.target_sum;
                cell.appendChild(sumEl);
            }
        }

        // 数字显示容器
        const valueEl = document.createElement("div");
        valueEl.className = "cell-value";
        valueEl.id = `value-${r}-${c}`;
        cell.appendChild(valueEl);

        // 标记容器
        const notesEl = document.createElement("div");
        notesEl.className = "cell-notes";
        notesEl.id = `notes-${r}-${c}`;
        notesEl.style.display = "none";
        cell.appendChild(notesEl);

        // 点击事件
        cell.addEventListener("click", () => {
            this.selectCell(r, c);
        });

        return cell;
    },

    /**
     * 应用笼边界样式
     * 如果单元格的某方向相邻单元格不在同一笼，则该方向画粗边框
     */
    _applyCageBorders(cell, r, c) {
        const cageIdx = this.cellToCage[`${r},${c}`];
        if (cageIdx === undefined) return;

        // 上
        if (r === 0 || this.cellToCage[`${r - 1},${c}`] !== cageIdx) {
            cell.classList.add("cage-top");
        }
        // 下
        if (r === this.size - 1 || this.cellToCage[`${r + 1},${c}`] !== cageIdx) {
            cell.classList.add("cage-bottom");
        }
        // 左
        if (c === 0 || this.cellToCage[`${r},${c - 1}`] !== cageIdx) {
            cell.classList.add("cage-left");
        }
        // 右
        if (c === this.size - 1 || this.cellToCage[`${r},${c + 1}`] !== cageIdx) {
            cell.classList.add("cage-right");
        }
    },

    /**
     * 找到笼内最左上角的单元格
     */
    _findTopLeftCell(cells) {
        let best = cells[0];
        for (const cell of cells) {
            if (cell[0] < best[0] || (cell[0] === best[0] && cell[1] < best[1])) {
                best = cell;
            }
        }
        return best;
    },

    /**
     * 选中单元格
     */
    selectCell(r, c) {
        this.selectedCell = { row: r, col: c };
        this._updateHighlights();
        if (this.onCellSelect) {
            this.onCellSelect(r, c);
        }
    },

    /**
     * 清除选中
     */
    clearSelection() {
        this.selectedCell = null;
        this._updateHighlights();
    },

    /**
     * 更新高亮：选中格、同数字、同行同列同宫
     */
    _updateHighlights(userGrid) {
        // 清除所有高亮
        const cells = this.boardEl.querySelectorAll(".cell");
        cells.forEach((cell) => {
            cell.classList.remove("selected", "same-number", "related");
        });

        if (!this.selectedCell) return;

        const { row: sr, col: sc } = this.selectedCell;
        const selectedValue = userGrid ? userGrid[sr][sc] : 0;
        const boxRows = this._getBoxRows();
        const boxCols = this._getBoxCols();
        const boxR = Math.floor(sr / boxRows) * boxRows;
        const boxC = Math.floor(sc / boxCols) * boxCols;

        cells.forEach((cell) => {
            const r = parseInt(cell.dataset.row);
            const c = parseInt(cell.dataset.col);

            // 同行同列同宫
            if (r === sr || c === sc ||
                (r >= boxR && r < boxR + boxRows && c >= boxC && c < boxC + boxCols)) {
                cell.classList.add("related");
            }

            // 同数字高亮
            if (selectedValue && userGrid && userGrid[r][c] === selectedValue) {
                cell.classList.add("same-number");
            }
        });

        // 选中格
        const selectedEl = document.getElementById(`cell-${sr}-${sc}`);
        if (selectedEl) {
            selectedEl.classList.remove("related");
            selectedEl.classList.add("selected");
        }
    },

    /**
     * 设置单元格的值
     */
    setCellValue(r, c, value) {
        const valueEl = document.getElementById(`value-${r}-${c}`);
        const notesEl = document.getElementById(`notes-${r}-${c}`);
        if (valueEl) {
            valueEl.textContent = value || "";
        }
        if (notesEl) {
            notesEl.style.display = value ? "none" : notesEl.dataset.hasNotes === "true" ? "grid" : "none";
        }
    },

    /**
     * 设置单元格的标记（小字候选）
     */
    setCellNotes(r, c, notes) {
        const notesEl = document.getElementById(`notes-${r}-${c}`);
        const valueEl = document.getElementById(`value-${r}-${c}`);
        if (!notesEl) return;

        notesEl.innerHTML = "";
        const hasNotes = notes && notes.size > 0;
        notesEl.dataset.hasNotes = hasNotes ? "true" : "false";

        if (hasNotes) {
            // 构建 notes 网格
            const noteSize = this.size <= 9 ? 3 : 4;
            notesEl.style.gridTemplateColumns = `repeat(${noteSize}, 1fr)`;
            notesEl.style.gridTemplateRows = `repeat(${noteSize}, 1fr)`;

            for (let n = 1; n <= this.size; n++) {
                const noteEl = document.createElement("div");
                noteEl.className = "note";
                noteEl.textContent = notes.has(n) ? n : "";
                notesEl.appendChild(noteEl);
            }
            notesEl.style.display = "grid";
            if (valueEl) valueEl.textContent = "";
        } else {
            notesEl.style.display = "none";
        }
    },

    /**
     * 标记错误单元格
     */
    markErrors(errorCells) {
        // 先清除
        this.boardEl.querySelectorAll(".cell.error").forEach((c) => {
            c.classList.remove("error");
        });
        // 标记
        errorCells.forEach((cell) => {
            const el = document.getElementById(`cell-${cell[0]}-${cell[1]}`);
            if (el) el.classList.add("error");
        });
    },

    /**
     * 清除错误标记
     */
    clearErrors() {
        this.boardEl.querySelectorAll(".cell.error").forEach((c) => {
            c.classList.remove("error");
        });
    },
};
