/* 本地存储：通关记录管理 */

const Storage = {
    COMPLETED_KEY: "killer_sudoku_completed",
    PROGRESS_KEY: "killer_sudoku_progress",

    /**
     * 获取所有已通关的谜题 ID 集合
     */
    getCompleted() {
        try {
            const data = localStorage.getItem(this.COMPLETED_KEY);
            return data ? new Set(JSON.parse(data)) : new Set();
        } catch (e) {
            return new Set();
        }
    },

    /**
     * 标记某谜题为已通关
     */
    markCompleted(puzzleId) {
        const completed = this.getCompleted();
        completed.add(puzzleId);
        try {
            localStorage.setItem(this.COMPLETED_KEY, JSON.stringify([...completed]));
        } catch (e) {
            console.error("无法保存通关记录:", e);
        }
    },

    /**
     * 检查某谜题是否已通关
     */
    isCompleted(puzzleId) {
        return this.getCompleted().has(puzzleId);
    },

    /**
     * 获取已通关数量
     */
    getCompletedCount() {
        return this.getCompleted().size;
    },

    /* ==================== 进度存档（按尺寸+难度分槽） ==================== */

    /**
     * 生成存档槽位 key
     * @param {number} size - 棋盘尺寸
     * @param {string} difficulty - 难度
     * @returns {string} 槽位 key，如 "9x9_expert"
     */
    _slotKey(size, difficulty) {
        return `${size}x${size}_${difficulty}`;
    },

    /**
     * 读取所有存档（整个字典）
     * @returns {object} { slotKey: progressData, ... }
     */
    _readAll() {
        try {
            const data = localStorage.getItem(this.PROGRESS_KEY);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            return {};
        }
    },

    /**
     * 写入整个存档字典
     * @param {object} all - 存档字典
     */
    _writeAll(all) {
        try {
            localStorage.setItem(this.PROGRESS_KEY, JSON.stringify(all));
            return true;
        } catch (e) {
            console.error("无法保存进度:", e);
            return false;
        }
    },

    /**
     * 保存当前游戏进度到指定槽位（按尺寸+难度）
     * @param {number} size - 棋盘尺寸
     * @param {string} difficulty - 难度
     * @param {object} data - 进度数据 { puzzle_id, size, difficulty, userGrid, notes, noteMode, completed }
     */
    saveProgress(size, difficulty, data) {
        const all = this._readAll();
        all[this._slotKey(size, difficulty)] = {
            ...data,
            size,
            difficulty,
            savedAt: Date.now(),
        };
        return this._writeAll(all);
    },

    /**
     * 读取指定槽位的游戏进度
     * @param {number} size - 棋盘尺寸
     * @param {string} difficulty - 难度
     * @returns {object|null} 进度数据，无存档返回 null
     */
    loadProgress(size, difficulty) {
        const all = this._readAll();
        return all[this._slotKey(size, difficulty)] || null;
    },

    /**
     * 是否存在指定槽位的存档
     * @param {number} size - 棋盘尺寸
     * @param {string} difficulty - 难度
     */
    hasProgress(size, difficulty) {
        const all = this._readAll();
        return !!all[this._slotKey(size, difficulty)];
    },

    /**
     * 获取所有已存档的槽位列表
     * @returns {Array<{size:number, difficulty:string, savedAt:number}>} 存档列表
     */
    getAllProgress() {
        const all = this._readAll();
        return Object.values(all).map((d) => ({
            size: d.size,
            difficulty: d.difficulty,
            savedAt: d.savedAt,
        }));
    },

    /**
     * 清除指定槽位的存档
     * @param {number} size - 棋盘尺寸
     * @param {string} difficulty - 难度
     */
    clearProgress(size, difficulty) {
        const all = this._readAll();
        delete all[this._slotKey(size, difficulty)];
        this._writeAll(all);
    },
};
