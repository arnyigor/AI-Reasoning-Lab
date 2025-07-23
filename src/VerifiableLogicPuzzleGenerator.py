import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from constraint import Problem, AllDifferentConstraint

# --- ИСПРАВЛЕННЫЙ ГЕНЕРАТОР НА ОСНОВЕ CSP (Архитектура v7.1 - "Правильная Модель") ---

class VerifiableLogicPuzzleGenerator:
    """
    Генератор логических головоломок, использующий полноценный CSP-решатель
    с корректной моделью данных для гарантии единственности решения.
    """

    def __init__(self, themes: Dict[str, Dict[str, List[str]]], story_elements: Dict[str, str]):
        self.themes = themes
        self.story_elements = story_elements
        self.difficulty: int = 0
        self.num_items: int = 0
        self.is_circular: bool = False
        self.categories: Dict[str, List[str]] = {}
        self.solution: Optional[pd.DataFrame] = None
        self.cat_keys: List[str] = []

    # --- Методы _select_data_for_difficulty, _generate_solution, _format_clue, _generate_clue_pool
    # --- остаются такими же, как в вашем исходном коде. Копируем их без изменений. ---

    def _select_data_for_difficulty(self, difficulty: int):
        self.difficulty = difficulty
        if 1 <= difficulty <= 3: self.num_items = 4; self.is_circular = False
        elif 4 <= difficulty <= 6: self.num_items = 5; self.is_circular = False
        elif 7 <= difficulty <= 8: self.num_items = 6; self.is_circular = True
        else: self.num_items = 7; self.is_circular = True

        selected_theme_name = random.choice(list(self.themes.keys()))
        base_categories = self.themes[selected_theme_name]
        self.story_elements["scenario"] = f"Тайна в сеттинге: {selected_theme_name}"
        self.cat_keys = list(base_categories.keys())

        if len(self.cat_keys) < 3 and difficulty >= 9:
            raise ValueError("Для сложности 9+ требуется как минимум 3 категории.")

        self.categories = {key: random.sample(values, self.num_items) for key, values in base_categories.items()}
        print(f"\n[Генератор]: Тема: '{selected_theme_name}', Сложность: {difficulty}/10, Размер: {self.num_items}x{len(self.cat_keys)}, Геометрия: {'Круговая' if self.is_circular else 'Линейная'}.")

    def _generate_solution(self):
        solution_data = {cat: random.sample(items, self.num_items) for cat, items in self.categories.items()}
        self.solution = pd.DataFrame(solution_data)
        self.solution.index = range(1, self.num_items + 1)

    # Вспомогательные методы _generate_clue_pool и _format_clue нужно скопировать из вашего кода,
    # они остаются без изменений. Я добавлю их "заглушки" для полноты.
    def _generate_clue_pool(self) -> Dict[str, List[Tuple[str, Any]]]:
        pool: Dict[str, List[Tuple[str, Any]]] = {
            'positional': [], 'direct_link': [], 'negative_direct_link': [], 'conditional_link': [],
            'relative_pos': [], 'opposite_link': [], 'transitive_spatial_link': []
        }
        cat_keys = list(self.categories.keys())
        cat_pairs = [(cat_keys[i], cat_keys[j]) for i in range(len(cat_keys)) for j in range(i + 1, len(cat_keys))]
        assert self.solution is not None

        for i_pos in range(1, self.num_items + 1):
            i_idx = i_pos - 1
            row = self.solution.loc[i_pos]

            for cat1, cat2 in cat_pairs: pool['direct_link'].append(('direct_link', (cat1, row[cat1], cat2, row[cat2])))
            for j_pos in range(1, self.num_items + 1):
                if i_pos == j_pos: continue
                other_row = self.solution.loc[j_pos]
                for cat1, cat2 in cat_pairs: pool['negative_direct_link'].append(('negative_direct_link', (cat1, row[cat1], cat2, other_row[cat2])))

            pool['positional'].append(('positional', (i_pos, random.choice(cat_keys), row[random.choice(cat_keys)])))
            cond_cat, then_cat = random.sample(cat_keys, 2)
            pool['conditional_link'].append(('conditional_link', (cond_cat, row[cond_cat], then_cat, row[then_cat])))

            next_i_pos = (i_idx + 1) % self.num_items + 1
            next_row = self.solution.loc[next_i_pos]
            if self.is_circular or i_idx < self.num_items - 1:
                cat1, cat2 = random.sample(cat_keys, 2)
                pool['relative_pos'].append(('relative_pos', (cat1, row[cat1], cat2, next_row[cat2])))

            if self.is_circular:
                opposite_i_pos = (i_idx + self.num_items // 2) % self.num_items + 1
                opposite_row = self.solution.loc[opposite_i_pos]
                cat1, cat2 = random.sample(cat_keys, 2)
                pool['opposite_link'].append(('opposite_link', (cat1, row[cat1], cat2, opposite_row[cat2])))

        if (self.is_circular or self.num_items >= 3) and len(cat_keys) >= 3:
            for i in range(1, self.num_items - 1):
                p_left_row = self.solution.loc[i]
                p_mid_row = self.solution.loc[i+1]
                p_right_row = self.solution.loc[i+2]
                c1, c2, c3 = random.sample(cat_keys, 3)
                p_left = (c1, p_left_row[c1])
                p_middle = (c2, p_mid_row[c2])
                p_right = (c3, p_right_row[c3])
                pool['transitive_spatial_link'].append(('transitive_spatial_link', (p_left, p_middle, p_right)))

        for clue_list in pool.values():
            random.shuffle(clue_list)
        return pool

    def _format_clue(self, clue: Tuple[str, Any]) -> str:
        clue_type, params = clue
        s = self.story_elements
        if clue_type == 'direct_link': return f"Характеристикой {s[params[0]]} {params[1]} является {s[params[2]]} {params[3]}."
        if clue_type == 'negative_direct_link': return f"{s[params[0]].capitalize()} {params[1]} НЕ находится в одной локации с {s[params[2]]} {params[3]}."
        if clue_type == 'positional': return f"В {s['position']} №{params[0]} находится {s[params[1]]} {params[2]}."
        if clue_type == 'relative_pos': return f"{s[params[0]].capitalize()} {params[1]} находится в локации непосредственно слева от локации, где {s[params[2]]} {params[3]}."
        if clue_type == 'opposite_link': return f"{s[params[0]].capitalize()} {params[1]} и {s[params[2]]} {params[3]} находятся в локациях друг напротив друга."
        if clue_type == 'conditional_link': return f"**Если** в локации находится {s[params[0]]} {params[1]}, **то** там же находится и {s[params[2]]} {params[3]}."
        if clue_type == 'transitive_spatial_link':
            p_left, p_middle, p_right = params
            return f"{s[p_middle[0]].capitalize()} {p_middle[1]} находится в локации между той, где {s[p_left[0]]} {p_left[1]}, и той, где {s[p_right[0]]} {p_right[1]}."
        return ""

    # --- НОВЫЕ И ИСПРАВЛЕННЫЕ МЕТОДЫ ---

    def _create_csp_problem(self, clues: List[Tuple[str, Any]]) -> Problem:
        """Создает и настраивает объект Problem с ПРАВИЛЬНОЙ моделью данных."""
        problem = Problem()
        positions = range(1, self.num_items + 1)

        # 1. Переменные - это сами сущности (Иванов, IT, Кофе).
        #    Домен (значения) - это их позиции (1, 2, 3...).
        all_items = [item for sublist in self.categories.values() for item in sublist]
        problem.addVariables(all_items, positions)

        # 2. Ограничения по категориям: все сущности в одной категории
        #    должны находиться на РАЗНЫХ позициях.
        for cat, items in self.categories.items():
            problem.addConstraint(AllDifferentConstraint(), items)

        # 3. Добавляем ограничения на основе подсказок.
        for clue_type, params in clues:
            self._add_clue_as_constraint(problem, clue_type, params)

        return problem

    def _add_clue_as_constraint(self, problem: Problem, clue_type: str, params: Any):
        """Транслирует одну подсказку в ограничение для CSP-решателя."""
        if clue_type == 'positional':
            pos_idx, _, val = params
            problem.addConstraint(lambda pos: pos == pos_idx, [val])

        elif clue_type in ['direct_link', 'conditional_link']:
            # Для "A связано с B" и "Если A, то B" ограничение одно и то же:
            # Позиция(A) == Позиция(B)
            _, val1, _, val2 = params
            problem.addConstraint(lambda pos1, pos2: pos1 == pos2, [val1, val2])

        elif clue_type == 'negative_direct_link':
            _, val1, _, val2 = params
            problem.addConstraint(lambda pos1, pos2: pos1 != pos2, [val1, val2])

        elif clue_type == 'relative_pos':
            # val1 находится слева от val2
            _, val1, _, val2 = params
            if self.is_circular:
                # p2 должен быть (p1 % N) + 1
                problem.addConstraint(lambda p1, p2: (p1 % self.num_items) + 1 == p2, [val1, val2])
            else:
                # p1 + 1 == p2
                problem.addConstraint(lambda p1, p2: p1 + 1 == p2, [val1, val2])

        elif clue_type == 'opposite_link':
            # Работает только для четного числа N в круговой геометрии
            if self.is_circular and self.num_items % 2 == 0:
                _, val1, _, val2 = params
                offset = self.num_items // 2
                problem.addConstraint(lambda p1, p2: abs(p1 - p2) == offset, [val1, val2])

        elif clue_type == 'transitive_spatial_link':
            # p_middle (c2, v2) между p_left (c1, v1) и p_right (c3, v3)
            (c1, v1), (c2, v2), (c3, v3) = params
            # Это означает, что их позиции идут последовательно: p, p+1, p+2
            # Ограничение: Позиция(v2) == Позиция(v1) + 1 И Позиция(v3) == Позиция(v2) + 1
            problem.addConstraint(lambda p1, p2: p1 + 1 == p2, [v1, v2])
            problem.addConstraint(lambda p2, p3: p2 + 1 == p3, [v2, v3])

    def _check_solvability(self, clues: List[Tuple[str, Any]]) -> int:
        """
        Проверяет, сколько решений имеет головоломка.
        Оптимизировано для быстрой проверки: ищет не более 2-х решений.
        """
        problem = self._create_csp_problem(clues)
        # Используем итератор для скорости: нам не нужны сами решения, только их количество.
        # Прекращаем поиск, как только найдем 2 решения.
        it = problem.getSolutionIter()
        count = 0
        try:
            next(it)
            count += 1
            next(it)
            count += 1
        except StopIteration:
            pass # Если решений 0 или 1, итератор закончится
        return count

    def generate(self, difficulty: int = 5):
        """Основной метод генерации головоломки."""
        self._select_data_for_difficulty(difficulty)
        self._generate_solution()
        assert self.solution is not None

        full_clue_pool = self._generate_clue_pool()
        all_clues = [clue for clue_list in full_clue_pool.values() for clue in clue_list]
        random.shuffle(all_clues)

        print("[Генератор]: Этап 1: Поиск минимального набора подсказок...")

        minimal_clues = list(all_clues)
        # Идем в обратном порядке, чтобы удаление не сбивало индексы
        for i in range(len(minimal_clues) - 1, -1, -1):
            clue_to_test = minimal_clues.pop(i)

            # Проверяем, что без этой подсказки решение перестает быть уникальным
            num_solutions = self._check_solvability(minimal_clues)

            if num_solutions == 1:
                # Подсказка избыточна, оставляем ее удаленной
                print(f"  - Успешно удалена избыточная подсказка. Осталось: {len(minimal_clues)}")
            else:
                # Подсказка необходима, возвращаем ее обратно
                minimal_clues.insert(i, clue_to_test)

        print(f"[Генератор]: Этап 2: Генерация вопроса и форматирование...")
        primary_subject_category = self.cat_keys[0]
        id_item = random.choice(self.categories[primary_subject_category])
        attribute_category = random.choice([c for c in self.cat_keys if c != primary_subject_category])

        solution_row = self.solution[self.solution[primary_subject_category] == id_item]
        answer_item = solution_row[attribute_category].values[0]

        question = f"Какой {self.story_elements[attribute_category]} у {self.story_elements[primary_subject_category]} по имени {id_item}?"
        answer_for_check = f"Ответ для проверки: {answer_item}"

        print(f"\n**Сценарий: {self.story_elements['scenario']} (Сложность: {difficulty}/10)**\n")
        print(f"Условия ({len(minimal_clues)} подсказок):\n")
        final_clues_text = sorted([self._format_clue(c) for c in minimal_clues])
        for i, clue_text in enumerate(final_clues_text, 1): print(f"{i}. {clue_text}")
        print("\n" + "="*40 + "\n")
        print(f"Вопрос: {question}")
        print("\n" + "="*40 + "\n")
        print(answer_for_check)
        print("\n--- Скрытое Решение для самопроверки ---\n", self.solution)

if __name__ == '__main__':
    THEMES = {
        "Офисная Тайна": { "Сотрудник": ["Иванов", "Петров", "Смирнов", "Кузнецов", "Волков", "Соколов", "Лебедев", "Орлов"], "Отдел": ["Финансы", "Маркетинг", "IT", "HR", "Продажи", "Логистика", "Безопасность", "Аналитика"], "Проект": ["Альфа", "Омега", "Квант", "Зенит", "Титан", "Орион", "Спектр", "Импульс"], "Напиток": ["Кофе", "Зеленый чай", "Черный чай", "Вода", "Латте", "Капучино", "Эспрессо", "Сок"]},
        "Загадка Тихого Квартала": { "Житель": ["Белов", "Чернов", "Рыжов", "Зеленин", "Серов", "Сидоров", "Поляков", "Морозов"], "Профессия": ["Врач", "Инженер", "Художник", "Программист", "Учитель", "Юрист", "Архитектор", "Писатель"], "Улица": ["Кленовая", "Цветочная", "Солнечная", "Вишневая", "Парковая", "Речная", "Лесная", "Озерная"], "Хобби": ["Рыбалка", "Садоводство", "Фотография", "Шахматы", "Коллекционирование", "Музыка", "Спорт", "Кулинария"]},
        "Стимпанк-Алхимия": { "Изобретатель": ["Alastair", "Isadora", "Bartholomew", "Genevieve", "Percival", "Seraphina", "Thaddeus", "Odette"], "Гильдия": ["Artificers", "Clockwork", "Alchemists", "Aethernauts", "Iron-Wrights", "Illuminators", "Cartographers", "Innovators"], "Автоматон": ["Cogsworth", "Steam-Golem", "Brass-Scarab", "Chrono-Spider", "Aether-Wisp", "The Oraculum", "The Geographer", "The Archivist"], "Эликсир": ["Philosopher's Dew", "Liquid-Luck", "Elixir of Vigor", "Draught of Genius", "Quicksilver-Tonic", "Sun-Stone-Solution", "Aether-in-a-Bottle", "Glimmer-Mist"]},
    }
    puzzle_story_elements = {
        "scenario": "", "position": "локация",
        "Сотрудник": "сотрудник", "Отдел": "отдел", "Проект": "проект", "Напиток": "напиток",
        "Житель": "житель", "Профессия": "профессия", "Улица": "улица", "Хобби": "хобби",
        "Изобретатель": "изобретатель", "Гильдия": "гильдия", "Автоматон": "автоматон", "Эликсир": "эликсир",
    }

    generator = VerifiableLogicPuzzleGenerator(themes=THEMES, story_elements=puzzle_story_elements)

    print("--- ГЕНЕРАЦИЯ ЭКСПЕРТНОЙ ЗАДАЧИ (АРХИТЕКТУРА v7.1) ---")
    generator.generate(difficulty=1)
    generator.generate(difficulty=5)
    generator.generate(difficulty=7)
    generator.generate(difficulty=10)
