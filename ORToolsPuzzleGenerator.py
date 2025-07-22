import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

# Импортируем необходимые классы из ortools
from ortools.sat.python import cp_model

class ORToolsPuzzleGenerator:
    """
    Генератор логических головоломок на движке Google OR-Tools.
    Архитектура v9.1 "Упорство".

    Использует стратегию "Интеллектуальный Архитектор" для создания
    гарантированно сложных и элегантных головоломок, а также
    механизм повторных попыток для надежности.
    1. Создает "скелет" из самых сложных типов подсказок.
    2. Добавляет подсказки до достижения уникального решения.
    3. Минимизирует только вспомогательные подсказки, сохраняя сложное ядро.
    """

    def __init__(self, themes: Dict[str, Dict[str, List[str]]], story_elements: Dict[str, str]):
        """Инициализирует генератор с темами и элементами истории."""
        self.themes = themes
        self.story_elements = story_elements
        self.difficulty: int = 0
        self.num_items: int = 0
        self.is_circular: bool = False
        self.categories: Dict[str, List[str]] = {}
        self.solution: Optional[pd.DataFrame] = None
        self.cat_keys: List[str] = []

    def generate_with_retries(self, difficulty: int = 5, max_attempts: int = 5):
        """
        Пытается сгенерировать головоломку, автоматически перезапускаясь в случае неудачи.

        Args:
            difficulty (int): Уровень сложности головоломки.
            max_attempts (int): Максимальное количество попыток генерации.
        """
        for attempt in range(1, max_attempts + 1):
            print("-" * 50)
            print(f"Попытка генерации #{attempt}/{max_attempts} для сложности {difficulty}/10")
            print("-" * 50)
            try:
                if self._try_generate(difficulty):
                    # Если генерация успешна, выходим из цикла
                    return
            except (ValueError, IndexError) as e:
                # Ловим возможные ошибки, например, нехватку данных для категорий
                print(f"[КРИТИЧЕСКАЯ ОШИБКА ГЕНЕРАЦИИ]: {e}")
                print("Прерывание попыток.")
                return

        print("\n" + "="*50)
        print(f"[ГЕНЕРАТОР]: НЕ УДАЛОСЬ сгенерировать корректную головоломку за {max_attempts} попыток.")
        print("="*50)

    def _try_generate(self, difficulty: int) -> bool:
        """
        Одна попытка сгенерировать головоломку.
        Возвращает True в случае успеха, False в случае неудачи.
        """
        self._select_data_for_difficulty(difficulty)
        self._generate_solution()
        assert self.solution is not None

        full_clue_pool_by_type = self._generate_clue_pool()

        # --- Этап 1: Создание "Скелета Сложности" ---
        print("[Архитектор]: Этап 1: Создание 'Скелета Сложности'...")
        SKELETON_RECIPES = {
            10: {'transitive_spatial_link': 2, 'opposite_link': 2, 'conditional_link': 2},
            9:  {'transitive_spatial_link': 1, 'opposite_link': 2, 'conditional_link': 1},
            8:  {'opposite_link': 2, 'relative_pos': 2},
            7:  {'opposite_link': 1, 'relative_pos': 3},
            6:  {'relative_pos': 2, 'direct_link': 2},
            5:  {'relative_pos': 1, 'direct_link': 3},
        }

        skeleton_clues = []
        recipe = SKELETON_RECIPES.get(self.difficulty, {'direct_link': self.num_items})
        for clue_type, count in recipe.items():
            clues_to_add = full_clue_pool_by_type.get(clue_type, [])
            if len(clues_to_add) >= count:
                skeleton_clues.extend(clues_to_add[:count])
                full_clue_pool_by_type[clue_type] = clues_to_add[count:]
                print(f"  - Добавлен в скелет: {count} x '{clue_type}'")
            else:
                print(f"  - [ВНИМАНИЕ] Недостаточно подсказок типа '{clue_type}' для скелета.")

        # --- Этап 2: Достижение Решаемости ---
        print("[Архитектор]: Этап 2: Добавление подсказок до достижения уникального решения...")
        CLUE_PRIORITY = ['positional', 'relative_pos', 'negative_direct_link', 'conditional_link', 'direct_link', 'opposite_link', 'transitive_spatial_link']

        remaining_clues_flat = [clue for clue_type in CLUE_PRIORITY for clue in full_clue_pool_by_type.get(clue_type, [])]
        random.shuffle(remaining_clues_flat) # Добавляем случайности в порядок добавления

        current_clues = list(skeleton_clues)

        solution_found = False
        for clue_to_add in remaining_clues_flat:
            current_clues.append(clue_to_add)
            if self._check_solvability(current_clues) == 1:
                print(f"  - Уникальное решение найдено с {len(current_clues)} подсказками.")
                solution_found = True
                break

        if not solution_found:
            print("[Архитектор]: [ОШИБКА] Не удалось достичь уникального решения. Попытка не удалась.")
            return False

        # --- Этап 3: Финальная "Шлифовка" ---
        print("[Архитектор]: Этап 3: Минимизация вспомогательных подсказок...")
        auxiliary_clues = [c for c in current_clues if c not in skeleton_clues]
        random.shuffle(auxiliary_clues)

        for i in range(len(auxiliary_clues) - 1, -1, -1):
            clue_to_test = auxiliary_clues.pop(i)
            if self._check_solvability(skeleton_clues + auxiliary_clues) != 1:
                auxiliary_clues.insert(i, clue_to_test)

        final_clues = skeleton_clues + auxiliary_clues
        print(f"  - Минимизация завершена. Итоговое количество подсказок: {len(final_clues)}")

        # --- Вывод результата ---
        self._print_puzzle(final_clues)

        return True

    def _select_data_for_difficulty(self, difficulty: int):
        """Выбирает параметры головоломки (размер, геометрию) на основе сложности."""
        self.difficulty = difficulty
        if 1 <= difficulty <= 3: self.num_items = 4; self.is_circular = False
        elif 4 <= difficulty <= 6: self.num_items = 5; self.is_circular = False
        elif 7 <= difficulty <= 8: self.num_items = 6; self.is_circular = True
        else: self.num_items = 7; self.is_circular = True

        selected_theme_name = random.choice(list(self.themes.keys()))
        base_categories = self.themes[selected_theme_name]
        self.story_elements["scenario"] = f"Тайна в сеттинге: {selected_theme_name}"
        self.cat_keys = list(base_categories.keys())

        if len(self.cat_keys) < 4 and difficulty >= 9:
            raise ValueError("Для сложности 9+ требуется как минимум 4 категории.")

        self.categories = {key: random.sample(values, self.num_items) for key, values in base_categories.items()}
        print(f"\n[Генератор]: Тема: '{selected_theme_name}', Сложность: {difficulty}/10, Размер: {self.num_items}x{len(self.cat_keys)}, Геометрия: {'Круговая' if self.is_circular else 'Линейная'}.")

    def _generate_solution(self):
        """Создает эталонное решение, которое мы будем использовать для генерации подсказок."""
        solution_data = {cat: random.sample(items, self.num_items) for cat, items in self.categories.items()}
        self.solution = pd.DataFrame(solution_data, index=range(1, self.num_items + 1))

    def _generate_clue_pool(self) -> Dict[str, List[Tuple[str, Any]]]:
        """Создает полный пул всех возможных 'правдивых' подсказок на основе решения."""
        pool: Dict[str, List[Tuple[str, Any]]] = {
            'positional': [], 'direct_link': [], 'negative_direct_link': [], 'conditional_link': [],
            'relative_pos': [], 'opposite_link': [], 'transitive_spatial_link': []
        }
        cat_keys = list(self.categories.keys())
        cat_pairs = [(cat_keys[i], cat_keys[j]) for i in range(len(cat_keys)) for j in range(i + 1, len(cat_keys))]
        assert self.solution is not None

        for i_pos in range(1, self.num_items + 1):
            row = self.solution.loc[i_pos]
            for cat1, cat2 in cat_pairs: pool['direct_link'].append(('direct_link', (cat1, row[cat1], cat2, row[cat2])))
            for j_pos in range(1, self.num_items + 1):
                if i_pos == j_pos: continue
                other_row = self.solution.loc[j_pos]
                for cat1, cat2 in cat_pairs: pool['negative_direct_link'].append(('negative_direct_link', (cat1, row[cat1], cat2, other_row[cat2])))

            pool['positional'].append(('positional', (i_pos, random.choice(cat_keys), row[random.choice(cat_keys)])))
            cond_cat, then_cat = random.sample(cat_keys, 2)
            pool['conditional_link'].append(('conditional_link', (cond_cat, row[cond_cat], then_cat, row[then_cat])))

            if self.is_circular or i_pos < self.num_items:
                next_i_pos = (i_pos % self.num_items) + 1
                next_row = self.solution.loc[next_i_pos]
                cat1, cat2 = random.sample(cat_keys, 2)
                pool['relative_pos'].append(('relative_pos', (cat1, row[cat1], cat2, next_row[cat2])))

            if self.is_circular:
                opposite_i_idx = (i_pos - 1 + self.num_items // 2) % self.num_items
                opposite_i_pos = opposite_i_idx + 1
                opposite_row = self.solution.loc[opposite_i_pos]
                cat1, cat2 = random.sample(cat_keys, 2)
                pool['opposite_link'].append(('opposite_link', (cat1, row[cat1], cat2, opposite_row[cat2])))

        if (self.is_circular or self.num_items >= 3) and len(cat_keys) >= 3:
            for i in range(1, self.num_items - 1):
                p_left_row, p_mid_row, p_right_row = self.solution.loc[i], self.solution.loc[i+1], self.solution.loc[i+2]
                c1, c2, c3 = random.sample(cat_keys, 3)
                p_left, p_middle, p_right = (c1, p_left_row[c1]), (c2, p_mid_row[c2]), (c3, p_right_row[c3])
                pool['transitive_spatial_link'].append(('transitive_spatial_link', (p_left, p_middle, p_right)))

        for clue_list in pool.values(): random.shuffle(clue_list)
        return pool

    def _create_or_tools_model(self, clues: List[Tuple[str, Any]]) -> cp_model.CpModel:
        """Создает модель CP-SAT и переменные."""
        model = cp_model.CpModel()
        positions_domain = (1, self.num_items)

        variables = {
            item: model.NewIntVar(positions_domain[0], positions_domain[1], item)
            for items in self.categories.values() for item in items
        }

        for items in self.categories.values():
            model.AddAllDifferent([variables[item] for item in items])

        for clue_type, params in clues:
            self._add_clue_as_or_tools_constraint(model, variables, clue_type, params)

        return model

    def _add_clue_as_or_tools_constraint(self, model, variables, clue_type, params):
        """Транслирует одну подсказку в ограничение CP-SAT."""
        get_var = lambda val: variables.get(val)

        if clue_type == 'positional':
            pos_idx, _, val = params
            if get_var(val) is not None: model.Add(get_var(val) == pos_idx)
        elif clue_type in ['direct_link', 'conditional_link']:
            _, val1, _, val2 = params
            if get_var(val1) is not None and get_var(val2) is not None: model.Add(get_var(val1) == get_var(val2))
        elif clue_type == 'negative_direct_link':
            _, val1, _, val2 = params
            if get_var(val1) is not None and get_var(val2) is not None: model.Add(get_var(val1) != get_var(val2))
        elif clue_type == 'relative_pos':
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is None or p2 is None: return
            if self.is_circular:
                allowed_pairs = [(i, (i % self.num_items) + 1) for i in range(1, self.num_items + 1)]
                model.AddAllowedAssignments([p1, p2], allowed_pairs)
            else:
                model.Add(p1 + 1 == p2)
        elif clue_type == 'opposite_link':
            if self.is_circular:
                _, val1, _, val2 = params
                p1, p2 = get_var(val1), get_var(val2)
                if p1 is None or p2 is None: return
                offset = self.num_items // 2
                b1 = model.NewBoolVar('')
                model.Add(p1 - p2 == offset).OnlyEnforceIf(b1)
                b2 = model.NewBoolVar('')
                model.Add(p2 - p1 == offset).OnlyEnforceIf(b2)
                model.Add(b1 + b2 >= 1)
        elif clue_type == 'transitive_spatial_link':
            (c1, v1), (c2, v2), (c3, v3) = params
            p1, p2, p3 = get_var(v1), get_var(v2), get_var(v3)
            if p1 is None or p2 is None or p3 is None: return
            model.Add(p1 + 1 == p2)
            model.Add(p2 + 1 == p3)

    def _check_solvability(self, clues: List[Tuple[str, Any]]) -> int:
        """Проверяет количество решений с помощью CP-SAT."""
        model = self._create_or_tools_model(clues)

        class SolutionCounter(cp_model.CpSolverSolutionCallback):
            def __init__(self, limit):
                super().__init__()
                self._solution_count = 0
                self._limit = limit
            def on_solution_callback(self):
                self._solution_count += 1
                if self._solution_count >= self._limit:
                    self.StopSearch()
            @property
            def solution_count(self):
                return self._solution_count

        solver = cp_model.CpSolver()
        solution_counter = SolutionCounter(limit=2)
        solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count

    def _print_puzzle(self, final_clues: List[Tuple[str, Any]]):
        """Форматирует и выводит готовую головоломку."""
        assert self.solution is not None
        primary_subject_category = self.cat_keys[0]
        id_item = random.choice(self.categories[primary_subject_category])
        attribute_category = random.choice([c for c in self.cat_keys if c != primary_subject_category])

        solution_row = self.solution[self.solution[primary_subject_category] == id_item]
        answer_item = solution_row[attribute_category].values[0]

        question = f"Какой {self.story_elements[attribute_category]} у {self.story_elements[primary_subject_category]} по имени {id_item}?"
        answer_for_check = f"Ответ для проверки: {answer_item}"

        print(f"\n**Сценарий: {self.story_elements['scenario']} (Сложность: {self.difficulty}/10)**\n")
        print(f"Условия ({len(final_clues)} подсказок):\n")
        final_clues_text = sorted([self._format_clue(c) for c in final_clues])
        for i, clue_text in enumerate(final_clues_text, 1): print(f"{i}. {clue_text}")
        print("\n" + "="*40 + "\n")
        print(f"Вопрос: {question}")
        print("\n" + "="*40 + "\n")
        print(answer_for_check)
        print("\n--- Скрытое Решение для самопроверки ---\n", self.solution)

    def _format_clue(self, clue: Tuple[str, Any]) -> str:
        """Преобразует подсказку из внутреннего формата в читаемый текст."""
        clue_type, params = clue
        s = self.story_elements
        try:
            if clue_type == 'direct_link': return f"Характеристикой {s[params[0]]} {params[1]} является {s[params[2]]} {params[3]}."
            if clue_type == 'negative_direct_link': return f"{s[params[0]].capitalize()} {params[1]} НЕ находится в одной локации с {s[params[2]]} {params[3]}."
            if clue_type == 'positional': return f"В {s['position']} №{params[0]} находится {s[params[1]]} {params[2]}."
            if clue_type == 'relative_pos': return f"{s[params[0]].capitalize()} {params[1]} находится в локации непосредственно слева от локации, где {s[params[2]]} {params[3]}."
            if clue_type == 'opposite_link': return f"{s[params[0]].capitalize()} {params[1]} и {s[params[2]]} {params[3]} находятся в локациях друг напротив друга."
            if clue_type == 'conditional_link': return f"**Если** в локации находится {s[params[0]]} {params[1]}, **то** там же находится и {s[params[2]]} {params[3]}."
            if clue_type == 'transitive_spatial_link':
                p_left, p_middle, p_right = params
                return f"{s[p_middle[0]].capitalize()} {p_middle[1]} находится в локации между той, где {s[p_left[0]]} {p_left[1]}, и той, где {s[p_right[0]]} {p_right[1]}."
        except KeyError as e:
            # Отладочное сообщение, если в story_elements чего-то не хватает
            return f"[Ошибка форматирования: не найден ключ {e}]"
        return ""


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

    generator = ORToolsPuzzleGenerator(themes=THEMES, story_elements=puzzle_story_elements)

    print("--- ГЕНЕРАЦИЯ ЭКСПЕРТНОЙ ЗАДАЧИ (АРХИТЕКТУРА v9.1) ---")
    generator.generate_with_retries(difficulty=10, max_attempts=5)
