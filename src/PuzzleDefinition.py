# PuzzleDefinition.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
from ortools.sat.python import cp_model

class PuzzleDefinition(ABC):
    """
    Абстрактный базовый класс (интерфейс), определяющий "контракт"
    для любого типа логической головоломки.

    Этот класс спроектирован для работы с `CorePuzzleGenerator`. Любая новая
    головоломка (Детектив, Планировщик, 2D-расположение) должна наследоваться
    от этого класса и реализовать все его абстрактные методы.

    Это позволяет ядру-генератору оставаться полностью универсальным и не зависеть
    от деталей конкретной головоломки, будь то "Загадка Эйнштейна" или что-то еще.
    """

    CLUE_STRENGTH = {
        # Самые сильные - задают точные позиции или связи
        'positional': 10,
        'direct_link': 9,
        # Сильные структурные
        'three_in_a_row': 8,
        'opposite_link': 7,
        # Средней силы - задают порядок или соседство
        'relative_pos': 6,
        'ordered_chain': 6,
        'at_edge': 5,
        # Слабые - числовые и негативные
        'is_even': 4,
        'sum_equals': 4,
        'negative_direct_link': 3,
        # Самые слабые - отсекают мало вариантов
        'distance_greater_than': 2,
    }

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Возвращает человекочитаемое имя типа головоломки.
        Используется для логирования.

        Returns:
            str: Имя головоломки, например, "Загадка Эйнштейна".
        """
        pass

    @abstractmethod
    def generate_solution(self) -> pd.DataFrame:
        """
        Создает и возвращает одно случайное, но полное и корректное
        решение головоломки в виде таблицы pandas.

        Это "скрытый ответ", на основе которого будут генерироваться все подсказки.

        Returns:
            pd.DataFrame: Таблица, где индексы - это позиции (или временные слоты),
                          а колонки - категории.
        """
        pass

    @abstractmethod
    def design_core_puzzle(self, solution: pd.DataFrame) -> Tuple[List, List]:
        """
        Проектирует стартовое ядро головоломки. Это ключевой метод,
        определяющий "характер" и сложность головоломки.

        Args:
            solution (pd.DataFrame): Полное решение, сгенерированное ранее.

        Returns:
            Tuple[List, List]: Кортеж из двух списков:
                - `core_puzzle`: Список "ядерных" подсказок (якоря + самые сложные).
                - `remaining_clues`: Список всех остальных подсказок для последующего
                                     добавления.
        """
        pass

    @abstractmethod
    def get_anchors(self, solution: pd.DataFrame) -> set:
        """
        Возвращает набор "якорных" подсказок.

        Якоря - это минимальный набор улик, необходимый для устранения
        фундаментальной симметрии в задаче (например, вращательной
        или зеркальной в круговых головоломках).

        Args:
            solution (pd.DataFrame): Полное решение.

        Returns:
            set: Множество якорных подсказок.
        """
        pass

    @abstractmethod
    def create_base_model_and_vars(self) -> Tuple[cp_model.CpModel, Dict[str, Any]]:
        """
        Создает базовую модель решателя OR-Tools и все ее переменные.

        Этот метод определяет "мир" головоломки: сколько в нем измерений (1D, 2D),
        какие существуют категории и какие базовые правила на них действуют
        (например, "все элементы в одной категории должны быть уникальны").

        Returns:
            Tuple[cp_model.CpModel, Dict[str, Any]]: Кортеж, содержащий:
                - `model`: Объект модели OR-Tools.
                - `variables`: Словарь, связывающий имена сущностей (напр., 'Иванов')
                               с их переменными в модели.
        """
        pass

    @abstractmethod
    def add_clue_constraint(self, model: cp_model.CpModel, variables: Dict[str, Any], clue: Tuple[str, Any]):
        """
        "Переводит" одну подсказку с человеческого языка на язык математических
        ограничений решателя OR-Tools.

        Этот метод содержит всю логику для каждого типа подсказок
        (`relative_pos`, `sum_equals`, `conditional_if_then` и т.д.).

        Args:
            model (cp_model.CpModel): Модель, в которую добавляется ограничение.
            variables (Dict[str, Any]): Словарь с переменными модели.
            clue (Tuple[str, Any]): Подсказка в формате (тип, параметры).
        """
        pass

    @abstractmethod
    def format_clue(self, clue: Tuple[str, Any]) -> str:
        """
        Форматирует одну подсказку из внутреннего представления в
        красивый, человекочитаемый текст.

        Args:
            clue (Tuple[str, Any]): Подсказка в формате (тип, параметры).

        Returns:
            str: Текстовое представление подсказки.
        """
        pass

    @abstractmethod
    def quality_audit_and_select_question(self, puzzle: List[Tuple[str, Any]], solution: pd.DataFrame) -> Tuple[List, Optional[Dict]]:
        """
        Проводит финальную проверку качества головоломки и выбирает
        самый "интересный" вопрос.

        "Интересность" определяется длиной логического пути, необходимого
        для нахождения ответа. Если все возможные вопросы слишком просты,
        метод может забраковать всю головоломку.

        Args:
            puzzle (List[Tuple[str, Any]]): Финальный, минимизированный набор подсказок.
            solution (pd.DataFrame): Полное решение для проверки.

        Returns:
            Tuple[List, Optional[Dict]]: Кортеж, содержащий:
                - `final_puzzle`: Итоговый набор подсказок (может быть изменен).
                - `question_data`: Словарь с вопросом и ответом, или `None`, если
                                   головоломка отбракована.
        """
        pass

    @abstractmethod
    def print_puzzle(self, final_clues: List[Tuple[str, Any]], question_data: Dict[str, str], solution: pd.DataFrame):
        """
        Полностью отвечает за красивый вывод готовой головоломки в консоль.

        Args:
            final_clues (List[Tuple[str, Any]]): Итоговый набор подсказок.
            question_data (Dict[str, str]): Словарь с вопросом и ответом.
            solution (pd.DataFrame): Полное решение для самопроверки.
        """
        pass