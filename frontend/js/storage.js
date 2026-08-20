/* 本地存储：通关记录管理 */

const Storage = {
    COMPLETED_KEY: "killer_sudoku_completed",

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
};
