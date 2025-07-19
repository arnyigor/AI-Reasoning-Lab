import random
import pandas as pd
from typing import Dict, List, Tuple, TextIO, Optional
import copy

# --- Умный Решатель (Версия 5.2 - без изменений) ---
class ConstraintSatisfactionSolver:
    """
    Финальная версия решателя. Полностью переписан для корректной обработки
    всех типов ограничений, включая сложные косвенные связи между категориями.
    Работает в цикле, пока не перестанут происходить изменения.
    """
    def __init__(self, categories: Dict[str, List[str]], verbose: bool = False, log_file_handle: Optional[TextIO] = None):
        self.num_items = len(next(iter(categories.values())))
        self.cat_keys = list(categories.keys())
        self.possibilities = {cat: [list(items) for _ in range(self.num_items)] for cat, items in categories.items()}
        self.clues = []
        self.verbose = verbose
        self.log_file_handle = log_file_handle

    def _log(self, message: str):
        if self.verbose:
            log_message = f"[SOLVER LOG] {message}\n"
            if self.log_file_handle:
                self.log_file_handle.write(log_message)
            else:
                print(log_message.strip())

    def _propagate(self) -> bool:
        made_change = False
        # 1. Уникальность: если значение найдено, его больше нигде нет
        for i in range(self.num_items):
            for cat in self.cat_keys:
                if len(self.possibilities[cat][i]) == 1:
                    val = self.possibilities[cat][i][0]
                    for j in range(self.num_items):
                        if i != j and val in self.possibilities[cat][j]:
                            self._log(f"Propagate Unary: '{val}' is in pos {i+1}, removing from pos {j+1} in cat '{cat}'.")
                            self.possibilities[cat][j].remove(val)
                            made_change = True

        # 2. Применяем все типы подсказок на основе текущего состояния
        for clue_type, params in self.clues:
            if clue_type == 'direct_link':
                cat1, val1, cat2, val2 = params
                for i in range(self.num_items):
                    if val1 not in self.possibilities[cat1][i] and val2 in self.possibilities[cat2][i]: self._log(f"Clue '{clue_type}': Since '{val1}' cannot be at pos {i+1}, removing '{val2}'."); self.possibilities[cat2][i].remove(val2); made_change = True
                    if val2 not in self.possibilities[cat2][i] and val1 in self.possibilities[cat1][i]: self._log(f"Clue '{clue_type}': Since '{val2}' cannot be at pos {i+1}, removing '{val1}'."); self.possibilities[cat1][i].remove(val1); made_change = True
            elif clue_type == 'negative_direct_link':
                cat1, val1, cat2, val2 = params
                for i in range(self.num_items):
                    if self.possibilities[cat1][i] == [val1] and val2 in self.possibilities[cat2][i]: self._log(f"Clue '{clue_type}': Pos {i+1} is '{val1}', so removing '{val2}'."); self.possibilities[cat2][i].remove(val2); made_change = True
                    if self.possibilities[cat2][i] == [val2] and val1 in self.possibilities[cat1][i]: self._log(f"Clue '{clue_type}': Pos {i+1} is '{val2}', so removing '{val1}'."); self.possibilities[cat1][i].remove(val1); made_change = True
            elif clue_type == 'relative_pos':
                cat, left, right = params
                for i in range(self.num_items - 1):
                    if left not in self.possibilities[cat][i] and right in self.possibilities[cat][i+1]: self._log(f"Clue '{clue_type}': '{left}' cannot be at pos {i+1}, so '{right}' cannot be at pos {i+2}."); self.possibilities[cat][i+1].remove(right); made_change = True
                    if right not in self.possibilities[cat][i+1] and left in self.possibilities[cat][i]: self._log(f"Clue '{clue_type}': '{right}' cannot be at pos {i+2}, so '{left}' cannot be at pos {i+1}."); self.possibilities[cat][i].remove(left); made_change = True

            # --- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ ЛОГИКИ ---
            elif clue_type == 'indirect_relative_link':
                cat1, val1, cat2, val2 = params
                for i in range(self.num_items - 1):
                    # Если val1 не может быть слева, то val2 не может быть справа
                    if val1 not in self.possibilities[cat1][i] and val2 in self.possibilities[cat2][i+1]:
                        self._log(f"Clue '{clue_type}': '{val1}'({cat1}) cannot be at pos {i+1}, so '{val2}'({cat2}) cannot be at pos {i+2}.")
                        self.possibilities[cat2][i+1].remove(val2); made_change = True
                    # Если val2 не может быть справа, то val1 не может быть слева
                    if val2 not in self.possibilities[cat2][i+1] and val1 in self.possibilities[cat1][i]:
                        self._log(f"Clue '{clue_type}': '{val2}'({cat2}) cannot be at pos {i+2}, so '{val1}'({cat1}) cannot be at pos {i+1}.")
                        self.possibilities[cat1][i].remove(val1); made_change = True
        return made_change

    def solve(self, clues: List[Tuple]):
        self.clues = clues
        # Применяем позиционные подсказки один раз для установки "якорей"
        for clue_type, params in clues:
            if clue_type == 'positional':
                pos_idx, cat, val = params[0] - 1, params[1], params[2]
                if val in self.possibilities[cat][pos_idx]:
                    self._log(f"Applying positional clue: Pos {pos_idx+1} in '{cat}' is set to '{val}'.")
                    self.possibilities[cat][pos_idx] = [val]

        # Запускаем основной цикл распространения до полной стабилизации
        while self._propagate():
            pass

    def get_status(self) -> str:
        is_solved = True
        for cat in self.cat_keys:
            for i in range(self.num_items):
                if len(self.possibilities[cat][i]) == 0: return "contradiction"
                if len(self.possibilities[cat][i]) > 1: is_solved = False
        return "solved" if is_solved else "unsolved"

# --- Генератор Элегантных Головоломок (Финальная Архитектура) ---
class ElegantLogicPuzzleGenerator:
    def __init__(self, themes: Dict[str, Dict[str, List[str]]]):
        self.themes = themes
        self.story_elements = {}
        self.categories = {}
        self.solution = None
        self.num_items = 0

    def _select_data_for_difficulty(self, difficulty: int):
        if 1 <= difficulty <= 3: self.num_items = 4
        elif 4 <= difficulty <= 6: self.num_items = 5
        elif 7 <= difficulty <= 8: self.num_items = 6
        else: self.num_items = 7 # Экспертный уровень

        # --- УЛУЧШЕНИЕ: Выбор темы и автоматическое создание story_elements ---
        selected_theme_name = random.choice(list(self.themes.keys()))
        base_categories_for_theme = self.themes[selected_theme_name]

        # Автоматически создаем словарь для описания истории
        self.story_elements = {"scenario": f"Тайна в сеттинге: {selected_theme_name}", "position": "локация"}
        for key in base_categories_for_theme.keys():
            self.story_elements[key] = key.lower() # Просто используем ключ в нижнем регистре

        print(f"\n[Генератор]: Выбрана тема: '{selected_theme_name}'.")
        print(f"[Генератор]: Уровень сложности {difficulty}/10. Размер сетки: {self.num_items}x{len(base_categories_for_theme)}.")

        for cat_name, cat_values in base_categories_for_theme.items():
            if len(cat_values) < self.num_items:
                raise ValueError(f"Недостаточно элементов в категории '{cat_name}' для сложности {difficulty} (нужно {self.num_items}, доступно {len(cat_values)})")
        self.categories = {key: random.sample(values, self.num_items) for key, values in base_categories_for_theme.items()}

    def _generate_solution(self):
        solution_data = {cat: random.sample(items, self.num_items) for cat, items in self.categories.items()}
        self.solution = pd.DataFrame(solution_data)
        self.solution.index = range(1, self.num_items + 1)

    def _generate_clue_pool(self) -> List[Tuple]:
        pool, cat_keys = [], list(self.categories.keys())
        cat_pairs = [(cat_keys[i], cat_keys[j]) for i in range(len(cat_keys)) for j in range(i + 1, len(cat_keys))]
        for i in range(1, self.num_items + 1):
            row = self.solution.loc[i]
            for cat1, cat2 in cat_pairs: pool.append(('direct_link', (cat1, row[cat1], cat2, row[cat2])))
            for j in range(1, self.num_items + 1):
                if i == j: continue
                other_row = self.solution.loc[j]
                for cat1, cat2 in cat_pairs: pool.append(('negative_direct_link', (cat1, row[cat1], cat2, other_row[cat2])))
        for pos, row in self.solution.iterrows():
            for cat in cat_keys: pool.append(('positional', (pos, cat, row[cat])))
        for i in range(1, self.num_items):
            for cat in cat_keys: pool.append(('relative_pos', (cat, self.solution.loc[i, cat], self.solution.loc[i + 1, cat])))
            for cat1, cat2 in cat_pairs: pool.append(('indirect_relative_link', (cat1, self.solution.loc[i, cat1], cat2, self.solution.loc[i+1, cat2])))
        random.shuffle(pool)
        return pool

    def _format_clue(self, clue: Tuple) -> str:
        clue_type, params = clue
        s = self.story_elements
        if clue_type == 'direct_link': return f"{s[params[0]].capitalize()} {params[1]} связан с {s[params[2]]} {params[3]}."
        if clue_type == 'negative_direct_link': return f"{s[params[0]].capitalize()} {params[1]} НЕ связан с {s[params[2]]} {params[3]}."
        if clue_type == 'positional': return f"В {s['position']} №{params[0]} находится {s[params[1]]} {params[2]}."
        if clue_type == 'relative_pos': return f"{s[params[0]].capitalize()} {params[1]} находится непосредственно слева от {s[params[0]]} {params[2]}."
        if clue_type == 'indirect_relative_link': return f"{s[params[0]].capitalize()} {params[1]} находится в {s['position']} слева от той, где {s[params[2]]} {params[3]}."
        return ""

    def generate(self, difficulty: int = 5, verbose_solver: bool = False, log_file_path: Optional[str] = None):
        if not 1 <= difficulty <= 10: raise ValueError("Сложность должна быть между 1 и 10.")

        try:
            self._select_data_for_difficulty(difficulty)
        except ValueError as e:
            print(f"[ОШИБКА ГЕНЕРАЦИИ]: {e}"); return

        self._generate_solution()

        primary_subject_category = list(self.categories.keys())[0]
        id_item = random.choice(self.categories[primary_subject_category])
        attribute_category = random.choice([c for c in self.categories.keys() if c != primary_subject_category])
        solution_row = self.solution[self.solution[primary_subject_category] == id_item]
        answer_item = solution_row[attribute_category].values[0]
        forbidden_clue_params = (primary_subject_category, id_item, attribute_category, answer_item)
        clue_pool = self._generate_clue_pool()
        clue_pool = [c for c in clue_pool if not (c[0] == 'direct_link' and c[1] == forbidden_clue_params)]

        log_file = open(log_file_path, 'w', encoding='utf-8') if verbose_solver and log_file_path else None

        try:
            print("[Генератор]: Этап 1: Архитектурное построение...")
            final_clues = []
            if difficulty >= 9:
                target_counts = {'positional': 1, 'indirect_relative_link': self.num_items -1, 'relative_pos': self.num_items * 2, 'negative_direct_link': self.num_items - 2}
            elif difficulty >= 7:
                target_counts = {'positional': 1, 'indirect_relative_link': 2, 'relative_pos': self.num_items * 2, 'direct_link': 2}
            elif difficulty >= 4:
                target_counts = {'positional': 1, 'relative_pos': self.num_items, 'direct_link': self.num_items - 1}
            else:
                target_counts = {'positional': self.num_items - 2, 'direct_link': self.num_items}

            temp_pool = list(clue_pool)
            for clue_type, count in target_counts.items():
                found = 0
                for i in range(len(temp_pool) - 1, -1, -1):
                    if temp_pool[i][0] == clue_type:
                        final_clues.append(temp_pool.pop(i)); found += 1
                        if found >= count: break

            while True:
                solver = ConstraintSatisfactionSolver(self.categories, verbose=verbose_solver, log_file_handle=log_file)
                solver.solve(final_clues)
                if solver.get_status() == "solved": break
                if not temp_pool: print("\n[Генератор]: Не удалось найти решение. Перезапуск..."); self.generate(difficulty, verbose_solver, log_file_path); return
                final_clues.append(temp_pool.pop())

            print(f"[Генератор]: Этап 1 завершен. Найдено решаемое решение с {len(final_clues)} подсказками.")

            print("[Генератор]: Этап 2: Финальная очистка...")
            minimal_clues = list(final_clues)
            random.shuffle(minimal_clues)
            for i in range(len(minimal_clues) - 1, -1, -1):
                temp_clues = minimal_clues[:i] + minimal_clues[i+1:]
                # Для минимизации создаем новый решатель без логирования, чтобы не засорять лог
                solver = ConstraintSatisfactionSolver(self.categories)
                solver.solve(temp_clues)
                if solver.get_status() == 'solved':
                    minimal_clues.pop(i)

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
            if verbose_solver:
                print("\n--- Скрытое Решение для самопроверки ---\n", self.solution)

        finally:
            if log_file:
                log_file.close()
                print(f"\n[Генератор]: Лог работы решателя сохранен в файл '{log_file_path}'.")

if __name__ == '__main__':
    # --- УЛУЧШЕНИЕ: Большой пул разнообразных тем ---
    THEMES = {
        "Киберпанк-Нуар": {
            "Детектив": ["Kaito", "Jyn", "Silas", "Nyx", "Roric", "Anya", "Vex", "Lira"],
            "Корпорация": ["OmniCorp", "Cygnus", "Stellarix", "Neuro-Link", "Aether-Dyne", "Volkov", "Helios", "Rift-Tech"],
            "Имплант": ["Kiroshi Optics", "Mantis Blades", "Synth-Lungs", "Grit-Weave", "Chrono-Core", "Neural-Port", "Echo-Dampers", "Reflex-Booster"],
            "Напиток": ["Synth-Caff", "N-Kola", "Slurm", "Chromantica", "Glycerin-Tea", "De-Tox", "Synth-Ale", "Glitter-Stim"],
            "Район": ["Neon-Sprawl", "The Core", "Iron-District", "Aetheria", "The Undercity", "Zenith-Heights", "The Shambles", "Port-Kailash"]
        },
        "Стимпанк-Алхимия": {
            "Изобретатель": ["Alastair", "Isadora", "Bartholomew", "Genevieve", "Percival", "Seraphina", "Thaddeus", "Odette"],
            "Гильдия": ["Artificers", "Clockwork", "Alchemists", "Aethernauts", "Iron-Wrights", "Illuminators", "Cartographers", "Innovators"],
            "Автоматон": ["Cogsworth", "Steam-Golem", "Brass-Scarab", "Chrono-Spider", "Aether-Wisp", "The Oraculum", "The Geographer", "The Archivist"],
            "Эликсир": ["Philosopher's Dew", "Liquid-Luck", "Elixir of Vigor", "Draught of Genius", "Quicksilver-Tonic", "Sun-Stone-Solution", "Aether-in-a-Bottle", "Glimmer-Mist"],
            "Материал": ["Aetherium-Crystal", "Orichalcum-Gear", "Voltaic-Coil", "Soul-Bronze", "Quicksilver-Core", "Obsidian-Lens", "Dragon-Scale-Hide", "Glimmer-Weave"]
        },
        "Космическая Опера": {
            "Капитан": ["Jax", "Zara", "Kaelen", "Riona", "Nero", "Lyra", "Orion", "Vesper"],
            "Фракция": ["Galactic Concord", "Star-Nomads", "Crimson Fleet", "Cy-Borg Collective", "Celestial Empire", "The Void-Traders", "The Syndicate", "The Sovereignty"],
            "Корабль": ["The Firehawk", "The Void-Chaser", "The Leviathan", "The Stardust", "The Nebula-Runner", "The Orion's Belt", "The Quasar", "The Pulsar"],
            "Груз": ["Kyber-Crystals", "Bio-Gel", "Star-Maps", "Xen-Artifacts", "Helium-3", "Graviton-Cores", "Psionic-Relics", "Cryo-Pods"],
            "Планета": ["Xylos", "Cygnus X-1", "Kepler-186f", "Astraeus", "Eridanus Prime", "Solara", "Triton", "Rhea"]
        },
        "Фэнтези-Расследование": {
            "Герой": ["Eldrin", "Lyra", "Kael", "Seraphina", "Roric", "Faelan", "Gwen", "Darian"],
            "Королевство": ["Aethelgard", "Glimmerwood", "Iron-Hold", "The Shadow-Fells", "Sunstone-Empire", "The Crystal-Spires", "The Azure-Coast", "The Northern-Reach"],
            "Артефакт": ["The Dragon-Orb", "The Shadow-Veil", "The Sun-Stone", "The Moon-Blade", "The Chronos-Key", "The Soul-Gem", "The Iron-Treaty", "The Star-Chart"],
            "Существо": ["Gryphon", "Dragon", "Hydra", "Manticore", "Phoenix", "Basilisk", "Wyvern", "Kraken"],
            "Локация": ["The Mystic Forest", "The Sunken City", "The Dragon's Peak", "The Shadow-Keep", "The Crystal-Caves", "The Sun-Temple", "The Whispering-Plains", "The Iron-Fortress"]
        }
    }

    # Генератор теперь принимает только словарь тем
    generator = ElegantLogicPuzzleGenerator(themes=THEMES)

    print("--- ГЕНЕРАЦИЯ ЭКСПЕРТНОЙ ЗАДАЧИ (ФИНАЛЬНАЯ АРХИТЕКТУРА) ---")
    generator.generate(difficulty=1, verbose_solver=False, log_file_path="solver_debug_log.log")
