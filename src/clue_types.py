# clue_types.py

from enum import Enum, auto

class ClueType(Enum):
    """
    Перечисление всех возможных типов подсказок в системе.
    Использование Enum вместо строк предотвращает опечатки и делает код
    более читаемым и надежным.
    """
    # --- Простые/прямые факты ---
    POSITIONAL = auto()           # (Позиция, Категория, Значение)
    DIRECT_LINK = auto()          # (Кат1, Знач1, Кат2, Знач2) - находятся в одной позиции
    NEGATIVE_DIRECT_LINK = auto() # (Кат1, Знач1, Кат2, Знач2) - НЕ находятся в одной позиции

    # --- Относительные и позиционные отношения ---
    RELATIVE_POS = auto()         # (Кат1, Знач1, Кат2, Знач2) - находятся рядом
    AT_EDGE = auto()              # (Категория, Значение) - находится с краю (поз. 1 или N)
    IS_EVEN = auto()              # (Категория, Значение, Четность) - находится в четной/нечетной позиции
    DISTANCE_GREATER_THAN = auto()# (Кат1, Знач1, Кат2, Знач2, Дистанция)

    # --- Арифметические отношения ---
    SUM_EQUALS = auto()           # (Кат1, Знач1, Кат2, Знач2, Сумма)

    # --- Структурные/групповые отношения ---
    THREE_IN_A_ROW = auto()       # ((К,З), (К,З), (К,З)) - в 3-х соседних позициях
    ORDERED_CHAIN = auto()        # ((К,З), (К,З), (К,З)) - p1 < p2 < p3

    # --- Условная логика ---
    IF_THEN = auto()              # (Условие, Следствие)
    IF_NOT_THEN_NOT = auto()      # (НЕ Условие, НЕ Следствие)
    EITHER_OR = auto()            # (Факт1, Факт2) - XOR
    IF_AND_ONLY_IF = auto()       # (Факт1, Факт2) - Эквивалентность
    NEITHER_NOR_POS = auto()      # ([(Кат1, Зн1), (Кат2, Зн2), ...], Позиция)

# --- НОВЫЙ СЛОВАРЬ ---
# Рейтинг силы улик. 3 - самые сильные, 1 - самые слабые.
# Сила определяет, насколько сильно улика сужает пространство поиска.
CLUE_STRENGTH = {
    # --- Уровень 3: Мощные структурные и условные связи ---
    ClueType.IF_THEN: 3,
    ClueType.IF_NOT_THEN_NOT: 3,
    ClueType.IF_AND_ONLY_IF: 3,
    ClueType.RELATIVE_POS: 3,
    ClueType.ORDERED_CHAIN: 3,

    # --- Уровень 2: Сильные ограничения ---
    ClueType.EITHER_OR: 2,
    ClueType.SUM_EQUALS: 2,
    ClueType.THREE_IN_A_ROW: 2,
    ClueType.DIRECT_LINK: 2, # Хотя это и простая улика, она очень сильная

    # --- Уровень 1: Слабые или очень специфичные ограничения ---
    ClueType.NEGATIVE_DIRECT_LINK: 1,
    ClueType.NEITHER_NOR_POS: 1,
    ClueType.AT_EDGE: 1,
    ClueType.IS_EVEN: 1,
    ClueType.DISTANCE_GREATER_THAN: 1,
    ClueType.POSITIONAL: 1 # Позиционные улики тоже считаем базовыми
}