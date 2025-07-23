# PuzzleDefinition.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
from ortools.sat.python import cp_model

class PuzzleDefinition(ABC):
    """
    Абстрактный базовый класс (интерфейс) для определения конкретного типа головоломки.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя/название этой конфигурации головоломки."""
        pass

    @abstractmethod
    def generate_solution(self) -> pd.DataFrame:
        """Генерирует полное, корректное решение (таблицу)."""
        pass

    @abstractmethod
    def generate_clue_pool(self, solution: pd.DataFrame) -> Dict[str, List[Tuple[str, Any]]]:
        """Генерирует полный пул всех возможных подсказок на основе решения."""
        pass

    @abstractmethod
    def get_anchors(self, solution: pd.DataFrame) -> set:
        """Возвращает набор "якорных" подсказок для устранения симметрии."""
        pass

    @abstractmethod
    def design_core_puzzle(self, solution: pd.DataFrame) -> Tuple[List, List]:
        """Проектирует ядро из сложных подсказок и возвращает остальные."""
        pass

    @abstractmethod
    def create_base_model_and_vars(self) -> Tuple[cp_model.CpModel, Dict[str, Any]]:
        """Создает базовую модель OR-Tools и все переменные для этой головоломки."""
        pass

    @abstractmethod
    def add_clue_constraint(self, model: cp_model.CpModel, variables: Dict[str, Any], clue: Tuple[str, Any]):
        """Добавляет одно конкретное ограничение (подсказку) в модель."""
        pass

    @abstractmethod
    def format_clue(self, clue: Tuple[str, Any]) -> str:
        """Форматирует одну подсказку в человекочитаемый текст."""
        pass

    @abstractmethod
    def quality_audit_and_select_question(self, puzzle: List[Tuple[str, Any]], solution: pd.DataFrame) -> Tuple[List, Optional[Dict]]:
        """Проводит аудит качества и выбирает лучший вопрос."""
        pass

    @abstractmethod
    def print_puzzle(self, final_clues: List[Tuple[str, Any]], question_data: Dict[str, str], solution: pd.DataFrame):
        """Печатает финальную головоломку в консоль."""
        pass