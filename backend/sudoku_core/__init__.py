"""数独核心库：杀手数独的生成、求解、验证。"""

from .models import (
    BOARD_CONFIGS,
    BoardConfig,
    Cage,
    Puzzle,
    Difficulty,
    get_board_config,
)
from .solver import KillerSudokuSolver
from .cage_builder import CageBuilder
from .generator import KillerSudokuGenerator
from .validator import KillerSudokuValidator
from .difficulty import DifficultyEvaluator, DIFFICULTY_PARAMS

__all__ = [
    "BOARD_CONFIGS",
    "BoardConfig",
    "Cage",
    "Puzzle",
    "Difficulty",
    "get_board_config",
    "KillerSudokuSolver",
    "CageBuilder",
    "KillerSudokuGenerator",
    "KillerSudokuValidator",
    "DifficultyEvaluator",
    "DIFFICULTY_PARAMS",
]
