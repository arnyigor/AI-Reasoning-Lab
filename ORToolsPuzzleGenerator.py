import random
from typing import Dict, List, Tuple, Any, Optional

import pandas as pd
from ortools.sat.python import cp_model


class ORToolsPuzzleGenerator:
    """
    Генератор логических головоломок на движке Google OR-Tools.
    Архитектура v9.9 "Защитник".

    Финальная версия, объединяющая интеллектуальную минимизацию и надежный
    механизм проверки для гарантии "честности" головоломок.
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

    def generate_with_retries(self, difficulty: int = 5, max_attempts: int = 20):
        """Пытается сгенерировать головоломку, перезапускаясь в случае неудачи."""
        for attempt in range(1, max_attempts + 1):
            print("-" * 50)
            print(f"Попытка генерации #{attempt}/{max_attempts} для сложности {difficulty}/10")
            print("-" * 50)
            try:
                if self._try_generate(difficulty):
                    return
            except (ValueError, IndexError) as e:
                print(f"[КРИТИЧЕСКАЯ ОШИБКА ГЕНЕРАЦИИ]: {e}")
                print("Прерывание попыток.")
                return
        print("\n" + "=" * 50)
        print(f"[ГЕНЕРАТОР]: НЕ УДАЛОСЬ сгенерировать корректную головоломку за {max_attempts} попыток.")
        print("=" * 50)

    def _try_generate(self, difficulty: int) -> bool:
        """
        Архитектура v9.9 "Защитник".
        - Использует логику "Следопыта" для честной минимизации.
        - Добавляет финальный, абсолютно надежный этап проверки, который гарантирует,
          что субъект вопроса и ответ физически присутствуют в тексте финальных подсказок.
        """
        self._select_data_for_difficulty(difficulty)
        self._generate_solution()
        assert self.solution is not None

        full_clue_pool_by_type = self._generate_clue_pool()

        # --- Этап 1: Создание "Скелета Сложности" ---
        print("[Архитектор]: Этап 1: Устойчивое создание 'Скелета Сложности'...")
        SKELETON_RECIPES = {
            10: {'arithmetic_link': 2, 'transitive_spatial_link': 1, 'opposite_link': 1, 'conditional_link': 1},
            9: {'arithmetic_link': 1, 'transitive_spatial_link': 1, 'opposite_link': 1, 'conditional_link': 1},
            8: {'arithmetic_link': 1, 'opposite_link': 1, 'relative_pos': 2},
            7: {'opposite_link': 1, 'relative_pos': 3},
            6: {'relative_pos': 2, 'direct_link': 2},
            5: {'relative_pos': 1, 'direct_link': 3},
            4: {'direct_link': 4},
        }
        skeleton_clues = []
        recipe = SKELETON_RECIPES.get(self.difficulty, {'direct_link': self.num_items})
        for clue_type, target_count in recipe.items():
            added_count = 0
            candidate_clues = full_clue_pool_by_type.get(clue_type, [])
            random.shuffle(candidate_clues)
            for candidate_clue in candidate_clues:
                if added_count >= target_count: break
                if self._check_solvability(skeleton_clues + [candidate_clue]) > 0:
                    skeleton_clues.append(candidate_clue)
                    added_count += 1
            if added_count < target_count:
                print(
                    f"  - [ВНИМАНИЕ] Не удалось добавить нужное количество ({target_count}) непротиворечивых подсказок типа '{clue_type}'. Добавлено: {added_count}.")
            else:
                print(f"  - Успешно добавлен в скелет: {added_count} x '{clue_type}'")

        # --- Этап 2: Добавление подсказок до уникального решения ---
        print("[Стратег]: Этап 2: Добавление подсказок по приоритету до достижения уникального решения...")
        CLUE_PRIORITY = ['positional', 'arithmetic_link', 'transitive_spatial_link', 'opposite_link', 'relative_pos',
                         'conditional_link', 'direct_link', 'negative_direct_link']
        flat_pool = {clue for clues in full_clue_pool_by_type.values() for clue in clues}
        skeleton_set = set(skeleton_clues)
        remaining_clues = [clue for clue in flat_pool if clue not in skeleton_set]
        remaining_clues.sort(key=lambda c: CLUE_PRIORITY.index(c[0]))
        current_clues = list(skeleton_clues)

        solution_found = False
        if self._check_solvability(current_clues) == 1:
            solution_found = True
            print(f"  - Уникальное решение найдено уже на этапе скелета с {len(current_clues)} подсказками.")
        if not solution_found:
            for clue_to_add in remaining_clues:
                current_clues.append(clue_to_add)
                if self._check_solvability(current_clues) == 1:
                    print(f"  - Уникальное решение найдено с {len(current_clues)} подсказками.")
                    solution_found = True
                    break
        if not solution_found:
            print("[Стратег]: [ОШИБКА] Не удалось достичь уникального решения. Попытка не удалась.")
            return False

        # --- Этап 3: "Честная" Минимизация ---
        print("[Следопыт]: Этап 3: Минимизация до критически необходимого набора подсказок...")
        final_clues = list(current_clues)
        random.shuffle(final_clues)
        for i in range(len(final_clues) - 1, -1, -1):
            clue_to_remove = final_clues.pop(i)
            if self._check_solvability(final_clues) != 1:
                final_clues.insert(i, clue_to_remove)
        print(f"  - Минимизация завершена. Итоговое количество подсказок: {len(final_clues)}")

        # --- Этап 4: Генерация Вопроса ---
        print("[Защитник]: Этап 4: Генерация вопроса из оставшихся улик...")
        primary_subject_category = self.cat_keys[0]
        id_item = random.choice(self.categories[primary_subject_category])
        attribute_category = random.choice([c for c in self.cat_keys if c != primary_subject_category])
        solution_row = self.solution[self.solution[primary_subject_category] == id_item]
        answer_item = solution_row[attribute_category].values[0]

        question_data = {
            "question": f"Какой {self.story_elements[attribute_category]} у {self.story_elements[primary_subject_category]} по имени {id_item}?",
            "answer": f"Ответ для проверки: {answer_item}"
        }
        print(f"  - Сгенерирован вопрос о '{id_item}'. Ожидаемый ответ: '{answer_item}'.")

        # --- ЭТАП 5: ФИНАЛЬНАЯ ПРОВЕРКА "ЗАЩИТНИК" ---
        print("[Защитник]: Этап 5: Проверка наличия вопроса и ответа в тексте подсказок...")
        all_clues_text = " ".join([self._format_clue(c) for c in final_clues])

        subject_found = id_item in all_clues_text
        answer_found = answer_item in all_clues_text

        if not subject_found:
            print(
                f"  - [ПРОВЕРКА НЕ ПРОЙДЕНА]: Субъект вопроса ('{id_item}') отсутствует в финальных подсказках. Попытка бракуется.")
            return False

        if not answer_found:
            print(
                f"  - [ПРОВЕРКА НЕ ПРОЙДЕНА]: Ответ ('{answer_item}') отсутствует в финальных подсказках. Попытка бракуется.")
            return False

        print("  - [ПРОВЕРКА ПРОЙДЕНА]: Вопрос и ответ присутствуют в тексте. Головоломка считается честной.")

        # --- Финальный вызов ---
        self._print_puzzle(final_clues, question_data)
        return True

    def _select_data_for_difficulty(self, difficulty: int):
        self.difficulty = difficulty
        if 1 <= difficulty <= 3:
            self.num_items = 4; self.is_circular = False
        elif 4 <= difficulty <= 6:
            self.num_items = 5; self.is_circular = False
        elif 7 <= difficulty <= 8:
            self.num_items = 6; self.is_circular = True
        else:
            self.num_items = 7; self.is_circular = True
        selected_theme_name = random.choice(list(self.themes.keys()))
        base_categories = self.themes[selected_theme_name]
        self.story_elements["scenario"] = f"Тайна в сеттинге: {selected_theme_name}"
        self.cat_keys = list(base_categories.keys())
        if len(self.cat_keys) < 4 and difficulty >= 9:
            raise ValueError("Для сложности 9+ требуется как минимум 4 категории.")
        self.categories = {key: random.sample(values, self.num_items) for key, values in base_categories.items()}
        print(
            f"\n[Генератор]: Тема: '{selected_theme_name}', Сложность: {difficulty}/10, Размер: {self.num_items}x{len(self.cat_keys)}, Геометрия: {'Круговая' if self.is_circular else 'Линейная'}.")

    def _generate_solution(self):
        solution_data = {cat: random.sample(items, self.num_items) for cat, items in self.categories.items()}
        self.solution = pd.DataFrame(solution_data, index=range(1, self.num_items + 1))

    def _generate_clue_pool(self) -> Dict[str, List[Tuple[str, Any]]]:
        pool: Dict[str, List[Any]] = {
            'positional': [], 'direct_link': [], 'negative_direct_link': [], 'conditional_link': [],
            'relative_pos': [], 'opposite_link': [], 'transitive_spatial_link': [],
            'arithmetic_link': []
        }
        unique_clues = {key: set() for key in pool}
        cat_keys = list(self.categories.keys())
        assert self.solution is not None

        for i_pos in range(1, self.num_items + 1):
            row = self.solution.loc[i_pos]
            chosen_cat = random.choice(cat_keys)
            chosen_val = row[chosen_cat]
            unique_clues['positional'].add(('positional', (i_pos, chosen_cat, chosen_val)))
            for j_pos in range(1, self.num_items + 1):
                other_row = self.solution.loc[j_pos]
                cat1, cat2 = random.sample(cat_keys, 2)
                if i_pos == j_pos:
                    unique_clues['direct_link'].add(('direct_link', (cat1, row[cat1], cat2, row[cat2])))
                    unique_clues['conditional_link'].add(('conditional_link', (cat1, row[cat1], cat2, row[cat2])))
                else:
                    unique_clues['negative_direct_link'].add(
                        ('negative_direct_link', (cat1, row[cat1], cat2, other_row[cat2])))
            if self.is_circular or i_pos < self.num_items:
                next_i_pos = (i_pos % self.num_items) + 1
                next_row = self.solution.loc[next_i_pos]
                cat1, cat2 = random.sample(cat_keys, 2)
                unique_clues['relative_pos'].add(('relative_pos', (cat1, row[cat1], cat2, next_row[cat2])))
            if self.is_circular and self.num_items % 2 == 0:
                opposite_i_idx = (i_pos - 1 + self.num_items // 2) % self.num_items
                opposite_i_pos = opposite_i_idx + 1
                if opposite_i_pos != i_pos:
                    opposite_row = self.solution.loc[opposite_i_pos]
                    cat1, cat2 = random.sample(cat_keys, 2)
                    unique_clues['opposite_link'].add(('opposite_link', (cat1, row[cat1], cat2, opposite_row[cat2])))

        if len(cat_keys) >= 3:
            if self.is_circular:
                for pos_mid in range(1, self.num_items + 1):
                    pos_left = (pos_mid - 2 + self.num_items) % self.num_items + 1
                    pos_right = (pos_mid % self.num_items) + 1
                    c1, c2, c3 = random.sample(cat_keys, 3)
                    p_left = (c1, self.solution.loc[pos_left, c1])
                    p_mid = (c2, self.solution.loc[pos_mid, c2])
                    p_right = (c3, self.solution.loc[pos_right, c3])
                    unique_clues['transitive_spatial_link'].add(('transitive_spatial_link', (p_left, p_mid, p_right)))
            else:
                for pos_mid in range(2, self.num_items):
                    pos_left, pos_right = pos_mid - 1, pos_mid + 1
                    c1, c2, c3 = random.sample(cat_keys, 3)
                    p_left = (c1, self.solution.loc[pos_left, c1])
                    p_mid = (c2, self.solution.loc[pos_mid, c2])
                    p_right = (c3, self.solution.loc[pos_right, c3])
                    unique_clues['transitive_spatial_link'].add(('transitive_spatial_link', (p_left, p_mid, p_right)))

        all_items_flat = [(cat, item) for cat, items in self.categories.items() for item in items]
        random.shuffle(all_items_flat)
        for i in range(len(all_items_flat)):
            for j in range(i + 1, len(all_items_flat)):
                (cat1, item1) = all_items_flat[i]
                (cat2, item2) = all_items_flat[j]
                if cat1 == cat2: continue
                pos1 = self.solution[self.solution[cat1] == item1].index[0]
                pos2 = self.solution[self.solution[cat2] == item2].index[0]
                if pos1 > 0 and pos2 > 0 and pos1 == pos2 * 2:
                    unique_clues['arithmetic_link'].add(('arithmetic_link', (cat1, item1, cat2, item2, 'twice')))
                elif pos1 > 0 and pos2 > 0 and pos2 == pos1 * 2:
                    unique_clues['arithmetic_link'].add(('arithmetic_link', (cat2, item2, cat1, item1, 'twice')))
                if abs(pos1 - pos2) == 2:
                    unique_clues['arithmetic_link'].add(('arithmetic_link', (cat1, item1, cat2, item2, 'diff_2')))

        for key in pool:
            pool[key] = list(unique_clues[key])
            random.shuffle(pool[key])
        return pool

    def _create_or_tools_model(self, clues: List[Tuple[str, Any]]) -> cp_model.CpModel:
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
            b = model.NewBoolVar('')
            model.Add(p1 + 1 == p2).OnlyEnforceIf(b)
            model.Add(p2 + 1 == p3).OnlyEnforceIf(b)
            model.Add(p3 + 1 == p2).OnlyEnforceIf(b.Not())
            model.Add(p2 + 1 == p1).OnlyEnforceIf(b.Not())
        elif clue_type == 'arithmetic_link':
            cat1, item1, cat2, item2, op = params
            p1, p2 = get_var(item1), get_var(item2)
            if p1 is None or p2 is None: return
            if op == 'twice':
                model.Add(p1 == 2 * p2)
            elif op == 'diff_2':
                b1 = model.NewBoolVar('')
                model.Add(p1 - p2 == 2).OnlyEnforceIf(b1)
                b2 = model.NewBoolVar('')
                model.Add(p2 - p1 == 2).OnlyEnforceIf(b2)
                model.Add(b1 + b2 >= 1)

    def _check_solvability(self, clues: List[Tuple[str, Any]]) -> int:
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

    def _print_puzzle(self, final_clues: List[Tuple[str, Any]], question_data: Dict[str, str]):
        """Просто печатает готовую головоломку и вопрос."""
        assert self.solution is not None
        question = question_data['question']
        answer_for_check = question_data['answer']

        print(f"\n**Сценарий: {self.story_elements['scenario']} (Сложность: {self.difficulty}/10)**\n")
        print(f"Условия ({len(final_clues)} подсказок):\n")
        final_clues_text = sorted([self._format_clue(c) for c in final_clues])
        for i, clue_text in enumerate(final_clues_text, 1): print(f"{i}. {clue_text}")
        print("\n" + "=" * 40 + "\n")
        print(f"Вопрос: {question}")
        print("\n" + "=" * 40 + "\n")
        print(answer_for_check)
        print("\n--- Скрытое Решение для самопроверки ---\n", self.solution)

    def _format_clue(self, clue: Tuple[str, Any]) -> str:
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
            if clue_type == 'arithmetic_link':
                cat1, item1, cat2, item2, op = params
                if op == 'twice':
                    return f"Номер локации, где {s[cat1]} {item1}, в два раза больше номера локации, где {s[cat2]} {item2}."
                if op == 'diff_2':
                    return f"Между локациями, где {s[cat1]} {item1}, и где {s[cat2]} {item2}, находится ровно одна другая локация."
        except KeyError as e:
            return f"[Ошибка форматирования: не найден ключ {e} в story_elements]"
        return f"[Неизвестный тип подсказки: {clue_type}]"


if __name__ == '__main__':
    THEMES = {
        "Офисная Тайна": {
            "Сотрудник": ["Иванов", "Петров", "Смирнов", "Кузнецов", "Волков", "Соколов", "Лебедев", "Орлов"],
            "Отдел": ["Финансы", "Маркетинг", "IT", "HR", "Продажи", "Логистика", "Безопасность", "Аналитика"],
            "Проект": ["Альфа", "Омега", "Квант", "Зенит", "Титан", "Орион", "Спектр", "Импульс"],
            "Напиток": ["Кофе", "Зеленый чай", "Черный чай", "Вода", "Латте", "Капучино", "Эспрессо", "Сок"]},
        "Загадка Тихого Квартала": {
            "Житель": ["Белов", "Чернов", "Рыжов", "Зеленин", "Серов", "Сидоров", "Поляков", "Морозов"],
            "Профессия": ["Врач", "Инженер", "Художник", "Программист", "Учитель", "Юрист", "Архитектор", "Писатель"],
            "Улица": ["Кленовая", "Цветочная", "Солнечная", "Вишневая", "Парковая", "Речная", "Лесная", "Озерная"],
            "Хобби": ["Рыбалка", "Садоводство", "Фотография", "Шахматы", "Коллекционирование", "Музыка", "Спорт",
                      "Кулинария"]},
        "Стимпанк-Алхимия": {
            "Изобретатель": ["Alastair", "Isadora", "Bartholomew", "Genevieve", "Percival", "Seraphina", "Thaddeus",
                             "Odette"],
            "Гильдия": ["Artificers", "Clockwork", "Alchemists", "Aethernauts", "Iron-Wrights", "Illuminators",
                        "Cartographers", "Innovators"],
            "Автоматон": ["Cogsworth", "Steam-Golem", "Brass-Scarab", "Chrono-Spider", "Aether-Wisp", "The Oraculum",
                          "The Geographer", "The Archivist"],
            "Эликсир": ["Philosopher's Dew", "Liquid-Luck", "Elixir of Vigor", "Draught of Genius", "Quicksilver-Tonic",
                        "Sun-Stone-Solution", "Aether-in-a-Bottle", "Glimmer-Mist"]},
        "Космическая Одиссея": {
            "Капитан": ["Рейнольдс", "Шепард", "Адама", "Старбак", "Пикар", "Соло", "Акбар", "Рипли"],
            "Корабль": ["Серенити", "Нормандия", "Галактика", "Звёздный Крейсер", "Энтерпрайз", "Сокол", "Прометей",
                        "Ностромо"],
            "Сектор": ["Орион", "Андромеда", "Плеяды", "Центавра", "Гидра", "Войд", "Квазар", "Небула"],
            "Аномалия": ["Червоточина", "Грави-колодец", "Темпоральный сдвиг", "Нейтронная буря", "Пси-поле",
                         "Ксено-артефакт", "Сингулярность", "Эхо Пустоты"]
        },
        "Тайна в Фэнтези-Таверне": {
            "Посетитель": ["Гном-кузнец", "Эльф-лучник", "Орк-берсерк", "Человек-маг", "Хоббит-вор", "Драконид-паладин",
                           "Полурослик-бард", "Гоблин-алхимик"],
            "Напиток": ["Драконья Горечь", "Эльфийский Эль", "Гномье Крепкое", "Орочья Брага", "Слёзы Грифона",
                        "Сок мандрагоры", "Лунная Роса", "Гоблинский Грог"],
            "Артефакт": ["Рунный клинок", "Посох молний", "Амулет невидимости", "Кольцо регенерации",
                         "Сапоги-скороходы", "Плащ из тени", "Свиток огня", "Философский камень"],
            "Квест": ["Убить дракона", "Найти сокровище", "Спасти принцессу", "Охранять караван", "Сварить зелье",
                      "Расшифровать карту", "Украсть реликвию", "Победить в турнире"]
        },
        "Загадка Гранд-Отеля 'Нуар'": {
            "Гость": ["Детектив Харди", "Певица Лола", "Магнат Вандербильт", "Актриса Монро", "Гангстер Капоне",
                      "Профессор Мориарти", "Шпионка Романова", "Контрабандист Рик"],
            "Этаж": ["Пентхаус", "Библиотека", "Бальный зал", "Джаз-клуб", "Сигарная комната", "Винный погреб",
                     "Терраса", "Казино"],
            "Предмет": ["Жемчужное ожерелье", "Револьвер с гравировкой", "Зашифрованная записка", "Пустая ампула",
                        "Окровавленный кинжал", "Компромат в папке", "Ключ от сейфа", "Бриллиантовое колье"],
            "Алиби": ["Играл в покер", "Слушал джаз", "Был на встрече", "Пил виски в баре", "Читал в библиотеке",
                      "Танцевал в зале", "Был на террасе", "Делал ставку в казино"]
        }

    }
    puzzle_story_elements = {
        "scenario": "", "position": "локация",
        "Сотрудник": "сотрудник", "Отдел": "отдел", "Проект": "проект", "Напиток": "напиток",
        "Житель": "житель", "Профессия": "профессия", "Улица": "улица", "Хобби": "хобби",
        "Изобретатель": "изобретатель", "Гильдия": "гильдия", "Автоматон": "автоматон", "Эликсир": "эликсир",
        "Капитан": "капитан", "Корабль": "корабль", "Сектор": "сектор", "Аномалия": "аномалия",
        "Посетитель": "посетитель", "Артефакт": "артефакт", "Квест": "квест",
        "Гость": "гость", "Этаж": "этаж", "Предмет": "предмет", "Алиби": "алиби"
    }

    generator = ORToolsPuzzleGenerator(themes=THEMES, story_elements=puzzle_story_elements)

    print("--- ГЕНЕРАЦИЯ ЭКСПЕРТНОЙ ЗАДАЧИ (АРХИТЕКТУРА v9.6) ---")
    generator.generate_with_retries(difficulty=10, max_attempts=20)
