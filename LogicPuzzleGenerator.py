import random
import pandas as pd
from typing import Dict, List, Tuple, TextIO, Optional, Any

# --- Умный Решатель (Версия 7.1 - без изменений) ---
class ConstraintSatisfactionSolver:
    """
    Финальная, отлаженная версия решателя.
    Корректно обрабатывает все типы ограничений, включая сложные
    транзитивные пространственные связи.
    """
    def __init__(self, categories: Dict[str, List[str]], is_circular: bool = False, verbose: bool = False, log_file_handle: Optional[TextIO] = None):
        self.num_items = len(next(iter(categories.values())))
        self.cat_keys = list(categories.keys())
        self.possibilities = {cat: [list(items) for _ in range(self.num_items)] for cat, items in categories.items()}
        self.clues: List[Tuple[str, Any]] = []
        self.is_circular = is_circular
        self.verbose = verbose
        self.log_file_handle = log_file_handle

    def _log(self, message: str):
        if self.verbose:
            log_message = f"[SOLVER LOG] {message}\n"
            if self.log_file_handle: self.log_file_handle.write(log_message)
            else: print(log_message.strip())

    def _propagate(self) -> bool:
        made_change = False
        for i in range(self.num_items):
            for cat in self.cat_keys:
                if len(self.possibilities[cat][i]) == 1:
                    val = self.possibilities[cat][i][0]
                    for j in range(self.num_items):
                        if i != j and val in self.possibilities[cat][j]:
                            self._log(f"Propagate Unary: '{val}' is in pos {i+1}, removing from pos {j+1}.")
                            self.possibilities[cat][j].remove(val)
                            made_change = True

        for clue_type, params in self.clues:
            if clue_type == 'direct_link':
                cat1, val1, cat2, val2 = params
                for i in range(self.num_items):
                    if val1 not in self.possibilities[cat1][i] and val2 in self.possibilities[cat2][i]: self.possibilities[cat2][i].remove(val2); made_change = True
                    if val2 not in self.possibilities[cat2][i] and val1 in self.possibilities[cat1][i]: self.possibilities[cat1][i].remove(val1); made_change = True
            elif clue_type == 'negative_direct_link':
                cat1, val1, cat2, val2 = params
                for i in range(self.num_items):
                    if self.possibilities[cat1][i] == [val1] and val2 in self.possibilities[cat2][i]: self.possibilities[cat2][i].remove(val2); made_change = True
                    if self.possibilities[cat2][i] == [val2] and val1 in self.possibilities[cat1][i]: self.possibilities[cat1][i].remove(val1); made_change = True
            elif clue_type == 'conditional_link':
                cond_cat, cond_val, then_cat, then_val = params
                for i in range(self.num_items):
                    if self.possibilities[cond_cat][i] == [cond_val] and self.possibilities[then_cat][i] != [then_val]:
                        if then_val in self.possibilities[then_cat][i]:
                            self.possibilities[then_cat][i] = [then_val]; made_change = True
                    if then_val not in self.possibilities[then_cat][i] and cond_val in self.possibilities[cond_cat][i]:
                        self.possibilities[cond_cat][i].remove(cond_val); made_change = True
            elif clue_type in ['relative_pos', 'opposite_link']:
                made_change = self._propagate_spatial(clue_type, params) or made_change
        return made_change

    def _propagate_spatial(self, clue_type: str, params: Any) -> bool:
        made_change = False
        for i in range(self.num_items):
            if clue_type == 'relative_pos':
                cat1, val1, cat2, val2 = params
                next_i = (i + 1) % self.num_items
                if not self.is_circular and i == self.num_items - 1: continue
                if val1 not in self.possibilities[cat1][i] and val2 in self.possibilities[cat2][next_i]: self.possibilities[cat2][next_i].remove(val2); made_change = True
                if val2 not in self.possibilities[cat2][next_i] and val1 in self.possibilities[cat1][i]: self.possibilities[cat1][i].remove(val1); made_change = True

            elif clue_type == 'opposite_link':
                if not self.is_circular: continue
                opposite_i = (i + self.num_items // 2) % self.num_items
                cat1, val1, cat2, val2 = params
                if self.possibilities[cat1][i] == [val1] and self.possibilities[cat2][opposite_i] != [val2]:
                    if val2 in self.possibilities[cat2][opposite_i]: self.possibilities[cat2][opposite_i] = [val2]; made_change = True
                if self.possibilities[cat2][opposite_i] == [val2] and self.possibilities[cat1][i] != [val1]:
                    if val1 in self.possibilities[cat1][i]: self.possibilities[cat1][i] = [val1]; made_change = True
        return made_change

    def solve(self, clues: List[Tuple[str, Any]]):
        unpacked_clues = []
        for clue_type, params in clues:
            if clue_type == 'transitive_spatial_link':
                p_left, p_middle, p_right = params
                unpacked_clues.append(('relative_pos', (p_left[0], p_left[1], p_middle[0], p_middle[1])))
                unpacked_clues.append(('relative_pos', (p_middle[0], p_middle[1], p_right[0], p_right[1])))
            else:
                unpacked_clues.append((clue_type, params))
        self.clues = unpacked_clues

        for clue_type, params in self.clues:
            if clue_type == 'positional':
                pos_idx, cat, val = params[0] - 1, params[1], params[2]
                if val in self.possibilities[cat][pos_idx]: self.possibilities[cat][pos_idx] = [val]

        while self._propagate(): pass

    def get_status(self) -> str:
        is_solved = True
        for cat in self.cat_keys:
            for i in range(self.num_items):
                if len(self.possibilities[cat][i]) == 0: return "contradiction"
                if len(self.possibilities[cat][i]) > 1: is_solved = False
        return "solved" if is_solved else "unsolved"

# --- Генератор Элегантных Головоломок (Архитектура v5.0 - Принуждение к сложной логике) ---
class ElegantLogicPuzzleGenerator:
    def __init__(self, themes: Dict[str, Dict[str, List[str]]], story_elements: Dict[str, str]):
        self.themes = themes
        self.story_elements = story_elements
        self.categories: Dict[str, List[str]] = {}
        self.solution: Optional[pd.DataFrame] = None
        self.num_items = 0
        self.is_circular = False

    def _select_data_for_difficulty(self, difficulty: int):
        if 1 <= difficulty <= 3: self.num_items = 4; self.is_circular = False
        elif 4 <= difficulty <= 6: self.num_items = 5; self.is_circular = False
        elif 7 <= difficulty <= 8: self.num_items = 6; self.is_circular = True
        else: self.num_items = 7; self.is_circular = True

        selected_theme_name = random.choice(list(self.themes.keys()))
        base_categories_for_theme = self.themes[selected_theme_name]
        self.story_elements["scenario"] = f"Тайна в сеттинге: {selected_theme_name}"

        print(f"\n[Генератор]: Выбрана тема: '{selected_theme_name}'.")
        print(f"[Генератор]: Уровень сложности {difficulty}/10. Размер сетки: {self.num_items}x{len(base_categories_for_theme)}. Геометрия: {'Круговая' if self.is_circular else 'Линейная'}.")

        cat_keys = list(base_categories_for_theme.keys())
        if len(cat_keys) < 3 and difficulty >= 9:
            raise ValueError("Для сложности 9+ требуется как минимум 3 категории для генерации сложных транзитивных подсказок.")

        for cat_name, cat_values in base_categories_for_theme.items():
            if len(cat_values) < self.num_items: raise ValueError(f"Недостаточно элементов в '{cat_name}' для сложности {difficulty}")
        self.categories = {key: random.sample(values, self.num_items) for key, values in base_categories_for_theme.items()}

    def _generate_solution(self):
        solution_data = {cat: random.sample(items, self.num_items) for cat, items in self.categories.items()}
        self.solution = pd.DataFrame(solution_data)
        self.solution.index = range(1, self.num_items + 1)

    def _generate_clue_pool(self) -> Dict[str, List[Tuple[str, Any]]]:
        # --- ИЗМЕНЕНИЕ: Возвращаем словарь, разделенный по типам, для приоритетного построения ---
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
        # --- ИЗМЕНЕНИЕ: Более конкретная формулировка для direct_link ---
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

    def generate(self, difficulty: int = 5, verbose_solver: bool = False, log_file_path: Optional[str] = None):
        max_attempts = 10
        for attempt in range(max_attempts):
            print(f"\n--- Попытка генерации #{attempt + 1}/{max_attempts} ---")
            try:
                if self._try_generate(difficulty, verbose_solver, log_file_path):
                    return
            except (ValueError, IndexError) as e:
                print(f"[ОШИБКА ГЕНЕРАЦИИ]: {e}")
                return
        print(f"\n[Генератор]: НЕ УДАЛОСЬ сгенерировать корректную головоломку за {max_attempts} попыток.")

    def _try_generate(self, difficulty: int, verbose_solver: bool, log_file_path: Optional[str]):
        self._select_data_for_difficulty(difficulty)
        self._generate_solution()

        primary_subject_category = list(self.categories.keys())[0]
        id_item = random.choice(self.categories[primary_subject_category])
        attribute_category = random.choice([c for c in self.categories.keys() if c != primary_subject_category])
        assert self.solution is not None
        solution_row = self.solution[self.solution[primary_subject_category] == id_item]
        answer_item = solution_row[attribute_category].values[0]
        forbidden_clue_params = (primary_subject_category, id_item, attribute_category, answer_item)

        clue_pool_by_type = self._generate_clue_pool()
        # Удаляем подсказку, которая напрямую дает ответ
        clue_pool_by_type['direct_link'] = [c for c in clue_pool_by_type['direct_link'] if c[1] != forbidden_clue_params]

        log_file = open(log_file_path, 'w', encoding='utf-8') if verbose_solver and log_file_path else None

        try:
            print("[Генератор]: Этап 1: Архитектурное построение...")
            final_clues = []
            # --- ИЗМЕНЕНИЕ: Новые, более строгие "рецепты" ---
            if difficulty >= 9: # Levels 9-10. Без прямых ссылок, упор на логику.
                target_counts = {'positional': 1, 'transitive_spatial_link': 2, 'conditional_link': 2, 'opposite_link': 2, 'negative_direct_link': self.num_items}
            elif difficulty >= 7: # Levels 7-8. Круговые, но проще.
                target_counts = {'positional': 1, 'opposite_link': 1, 'relative_pos': self.num_items, 'conditional_link': 1, 'negative_direct_link': self.num_items - 1}
            elif difficulty >= 4: # Levels 4-6. Линейные, с пространственными связями.
                target_counts = {'positional': 1, 'relative_pos': self.num_items - 1, 'direct_link': self.num_items - 1}
            else: # Levels 1-3. Простые прямые связи.
                target_counts = {'positional': 1, 'direct_link': self.num_items}

            # Собираем "скелет" головоломки
            for clue_type, count in target_counts.items():
                clues_to_add = clue_pool_by_type[clue_type][:count]
                if len(clues_to_add) < count:
                    print(f"[ПРЕДУПРЕЖДЕНИЕ]: Недостаточно подсказок типа '{clue_type}'. Найдено {len(clues_to_add)}, требуется {count}.")
                final_clues.extend(clues_to_add)
                clue_pool_by_type[clue_type] = clue_pool_by_type[clue_type][count:]

            # --- ИЗМЕНЕНИЕ: Приоритетное добавление подсказок для достижения решения ---
            priority_order = ['negative_direct_link', 'relative_pos', 'conditional_link', 'opposite_link', 'transitive_spatial_link', 'direct_link', 'positional']

            while True:
                solver = ConstraintSatisfactionSolver(self.categories, self.is_circular, verbose_solver, log_file)
                solver.solve(final_clues)
                if solver.get_status() == "solved": break

                # Ищем подсказку для добавления согласно приоритету
                added_clue = False
                for clue_type in priority_order:
                    if clue_pool_by_type[clue_type]:
                        final_clues.append(clue_pool_by_type[clue_type].pop(0))
                        added_clue = True
                        break
                if not added_clue:
                    print("\n[Генератор]: Не удалось найти решение: закончились все типы подсказок. Попытка не удалась.")
                    return False

            print(f"[Генератор]: Этап 1 завершен. Найдено решаемое решение с {len(final_clues)} подсказками.")

            print("[Генератор]: Этап 2: Финальная очистка...")
            minimal_clues = list(final_clues)
            random.shuffle(minimal_clues)
            for i in range(len(minimal_clues) - 1, -1, -1):
                temp_clues = minimal_clues[:i] + minimal_clues[i+1:]
                solver = ConstraintSatisfactionSolver(self.categories, self.is_circular)
                solver.solve(temp_clues)
                if solver.get_status() == 'solved': minimal_clues.pop(i)

            final_clues = minimal_clues
            print(f"[Генератор]: Очистка завершена. Финальное количество подсказок: {len(final_clues)}")

            question = f"Какой {self.story_elements[attribute_category]} у {self.story_elements[primary_subject_category]} по имени {id_item}?"
            answer_for_check = f"Ответ для проверки: {answer_item}"

            print(f"\n**Сценарий: {self.story_elements['scenario']} (Сложность: {difficulty}/10)**\n")
            print("Условия:\n")
            final_clues_text = sorted([self._format_clue(c) for c in final_clues])
            for i, clue_text in enumerate(final_clues_text, 1): print(f"{i}. {clue_text}")
            print("\n" + "="*40 + "\n")
            print(f"Вопрос: {question}")
            print("\n" + "="*40 + "\n")
            print(answer_for_check)
            print("\n--- Скрытое Решение для самопроверки ---\n", self.solution)
            return True

        finally:
            if log_file: log_file.close()

if __name__ == '__main__':
    THEMES = {
        "Офисная Тайна": { "Сотрудник": ["Иванов", "Петров", "Смирнов", "Кузнецов", "Волков", "Соколов", "Лебедев", "Орлов"], "Отдел": ["Финансы", "Маркетинг", "IT", "HR", "Продажи", "Логистика", "Безопасность", "Аналитика"], "Проект": ["Альфа", "Омега", "Квант", "Зенит", "Титан", "Орион", "Спектр", "Импульс"], "Напиток": ["Кофе", "Зеленый чай", "Черный чай", "Вода", "Латте", "Капучино", "Эспрессо", "Сок"], "Этаж": ["3-й", "4-й", "5-й", "6-й", "7-й", "8-й", "9-й", "10-й"] },
        "Загадка Тихого Квартала": { "Житель": ["Белов", "Чернов", "Рыжов", "Зеленин", "Серов", "Сидоров", "Поляков", "Морозов"], "Профессия": ["Врач", "Инженер", "Художник", "Программист", "Учитель", "Юрист", "Архитектор", "Писатель"], "Улица": ["Кленовая", "Цветочная", "Солнечная", "Вишневая", "Парковая", "Речная", "Лесная", "Озерная"], "Хобби": ["Рыбалка", "Садоводство", "Фотография", "Шахматы", "Коллекционирование", "Музыка", "Спорт", "Кулинария"], "Питомец": ["Собака", "Кошка", "Попугай", "Хомяк", "Рыбки", "Черепаха", "Кролик", "Шиншилла"] },
        "Киберпанк-Нуар": { "Детектив": ["Kaito", "Jyn", "Silas", "Nyx", "Roric", "Anya", "Vex", "Lira"], "Корпорация": ["OmniCorp", "Cygnus", "Stellarix", "Neuro-Link", "Aether-Dyne", "Volkov", "Helios", "Rift-Tech"], "Имплант": ["Kiroshi Optics", "Mantis Blades", "Synth-Lungs", "Grit-Weave", "Chrono-Core", "Neural-Port", "Echo-Dampers", "Reflex-Booster"], "Напиток": ["Synth-Caff", "N-Kola", "Slurm", "Chromantica", "Glycerin-Tea", "De-Tox", "Synth-Ale", "Glitter-Stim"], "Район": ["Neon-Sprawl", "The Core", "Iron-District", "Aetheria", "The Undercity", "Zenith-Heights", "The Shambles", "Port-Kailash"] },
        "Стимпанк-Алхимия": { "Изобретатель": ["Alastair", "Isadora", "Bartholomew", "Genevieve", "Percival", "Seraphina", "Thaddeus", "Odette"], "Гильдия": ["Artificers", "Clockwork", "Alchemists", "Aethernauts", "Iron-Wrights", "Illuminators", "Cartographers", "Innovators"], "Автоматон": ["Cogsworth", "Steam-Golem", "Brass-Scarab", "Chrono-Spider", "Aether-Wisp", "The Oraculum", "The Geographer", "The Archivist"], "Эликсир": ["Philosopher's Dew", "Liquid-Luck", "Elixir of Vigor", "Draught of Genius", "Quicksilver-Tonic", "Sun-Stone-Solution", "Aether-in-a-Bottle", "Glimmer-Mist"], "Материал": ["Aetherium-Crystal", "Orichalcum-Gear", "Voltaic-Coil", "Soul-Bronze", "Quicksilver-Core", "Obsidian-Lens", "Dragon-Scale-Hide", "Glimmer-Weave"] }
    }
    puzzle_story_elements = {
        "scenario": "", "position": "локация",
        "Сотрудник": "сотрудник", "Отдел": "отдел", "Проект": "проект", "Напиток": "напиток", "Этаж": "этаж",
        "Житель": "житель", "Профессия": "профессия", "Улица": "улица", "Хобби": "хобби", "Питомец": "питомец",
        "Детектив": "детектив", "Корпорация": "корпорация", "Имплант": "имплант", "Район": "район",
        "Изобретатель": "изобретатель", "Гильдия": "гильдия", "Автоматон": "автоматон", "Эликсир": "эликсир", "Материал": "материал",
    }

    generator = ElegantLogicPuzzleGenerator(themes=THEMES, story_elements=puzzle_story_elements)

    print("--- ГЕНЕРАЦИЯ ЭКСПЕРТНОЙ ЗАДАЧИ (АРХИТЕКТУРА v5.0) ---")
    generator.generate(difficulty=1, verbose_solver=False)
    generator.generate(difficulty=5, verbose_solver=False)
    generator.generate(difficulty=7, verbose_solver=False)
    generator.generate(difficulty=10, verbose_solver=False)
