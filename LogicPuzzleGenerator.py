import random
import pandas as pd
from typing import Dict, List, Tuple

# --- Умный Решатель (Версия 5.0 - Финальная) ---
class ConstraintSatisfactionSolver:
    def __init__(self, categories: Dict[str, List[str]]):
        self.num_items = len(next(iter(categories.values())))
        self.cat_keys = list(categories.keys())
        self.possibilities = {cat: [list(items) for _ in range(self.num_items)] for cat, items in categories.items()}
        self.clues = []

    def _propagate(self) -> bool:
        made_change = False
        for i in range(self.num_items):
            for cat in self.cat_keys:
                if len(self.possibilities[cat][i]) == 1:
                    val = self.possibilities[cat][i][0]
                    for j in range(self.num_items):
                        if i != j and val in self.possibilities[cat][j]:
                            self.possibilities[cat][j].remove(val); made_change = True

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
            elif clue_type == 'relative_pos':
                cat, left, right = params
                for i in range(self.num_items - 1):
                    if left not in self.possibilities[cat][i] and right in self.possibilities[cat][i+1]: self.possibilities[cat][i+1].remove(right); made_change = True
                    if right not in self.possibilities[cat][i+1] and left in self.possibilities[cat][i]: self.possibilities[cat][i].remove(left); made_change = True
            elif clue_type == 'indirect_relative_link':
                cat1, val1, cat2, val2 = params
                for i in range(self.num_items - 1):
                    if self.possibilities[cat1][i] == [val1] and self.possibilities[cat2][i+1] != [val2]:
                        if val2 in self.possibilities[cat2][i+1]: self.possibilities[cat2][i+1] = [val2]; made_change = True
                    if self.possibilities[cat2][i+1] == [val2] and self.possibilities[cat1][i] != [val1]:
                        if val1 in self.possibilities[cat1][i]: self.possibilities[cat1][i] = [val1]; made_change = True
        return made_change

    def solve(self, clues: List[Tuple]):
        self.clues = clues
        for clue_type, params in clues:
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

# --- Генератор Элегантных Головоломок (Финальная Архитектура) ---
class ElegantLogicPuzzleGenerator:
    def __init__(self, base_categories: Dict[str, List[str]], story_elements: Dict[str, str]):
        self.base_categories = base_categories
        self.story_elements = story_elements
        self.categories = {}
        self.solution = None
        self.num_items = 0

    def _select_data_for_difficulty(self, difficulty: int):
        if 1 <= difficulty <= 3: self.num_items = 4
        elif 4 <= difficulty <= 6: self.num_items = 5
        elif 7 <= difficulty <= 8: self.num_items = 6
        else: self.num_items = 8

        for cat_name, cat_values in self.base_categories.items():
            if len(cat_values) < self.num_items:
                raise ValueError(f"Недостаточно элементов в категории '{cat_name}' для сложности {difficulty} (нужно {self.num_items}, доступно {len(cat_values)})")

        self.categories = {key: random.sample(values, self.num_items) for key, values in self.base_categories.items()}
        print(f"\n[Генератор]: Уровень сложности {difficulty}/10. Размер сетки: {self.num_items}x{len(self.categories)}.")

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
        if clue_type == 'indirect_relative_link': return f"{s[params[0]].capitalize()} {params[1]} находится в лаборатории слева от той, где {s[params[2]]} {params[3]}."
        return ""

    def generate(self, difficulty: int = 5):
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

        # --- Этап 1: Архитектурное построение ---
        print("[Генератор]: Этап 1: Построение по архитектурному плану 'Цепочки и Мосты'...")
        final_clues = []
        if difficulty >= 9: # Эксперт
            target_counts = {'positional': 1, 'indirect_relative_link': self.num_items, 'relative_pos': self.num_items * 2, 'negative_direct_link': self.num_items - 2, 'direct_link': 1}
        elif difficulty >= 7: # Сложный
            target_counts = {'positional': 1, 'relative_pos': self.num_items * 2, 'negative_direct_link': 2, 'direct_link': self.num_items - 2}
        elif difficulty >= 4: # Средний
            target_counts = {'positional': 1, 'relative_pos': self.num_items, 'direct_link': self.num_items - 1}
        else: # Простой
            target_counts = {'positional': 2, 'relative_pos': self.num_items - 2, 'direct_link': self.num_items}

        temp_pool = list(clue_pool)
        for clue_type, count in target_counts.items():
            found = 0
            for i in range(len(temp_pool) - 1, -1, -1):
                if temp_pool[i][0] == clue_type:
                    final_clues.append(temp_pool.pop(i)); found += 1
                    if found >= count: break

        # Добираем случайные, если архитектурного плана не хватило
        while True:
            solver = ConstraintSatisfactionSolver(self.categories)
            solver.solve(final_clues)
            if solver.get_status() == "solved": break
            if not temp_pool: print("\n[Генератор]: Не удалось найти решение. Перезапуск..."); self.generate(difficulty); return
            final_clues.append(temp_pool.pop())

        print(f"[Генератор]: Этап 1 завершен. Найдено решаемое решение с {len(final_clues)} подсказками.")

        # --- Этап 2: Финальная Минимизация ---
        print("[Генератор]: Этап 2: Финальная очистка для максимальной элегантности...")
        minimal_clues = list(final_clues)
        random.shuffle(minimal_clues)
        for i in range(len(minimal_clues) - 1, -1, -1):
            temp_clues = minimal_clues[:i] + minimal_clues[i+1:]
            solver = ConstraintSatisfactionSolver(self.categories)
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

if __name__ == '__main__':
    base_puzzle_categories = {
        "Ученый": ["Орлов", "Лебедев", "Соколов", "Воробьев", "Ястребов", "Сидоров", "Петров", "Иванов"],
        "Область": ["Биоинженерия", "Физика", "Нейробиология", "Астрофизика", "Химия", "Кибернетика", "Геология", "Экология"],
        "Суперкомпьютер": ["Титан", "Фугаку", "Секвойя", "Ломоносов", "Тяньхэ-2", "Summit", "Sierra", "Piz Daint"],
        "Напиток": ["Чай", "Кофе", "Молоко", "Вода", "Сок", "Лимонад", "Кефир", "Морс"],
        "Музыка": ["Классика", "Джаз", "Эмбиент", "Рок", "Электроника", "Хип-хоп", "Фолк", "Блюз"]
    }
    puzzle_story = { "scenario": "Тайна исследовательского центра", "position": "лаборатория", "Ученый": "ученый", "Область": "специалист", "Суперкомпьютер": "суперкомпьютер", "Напиток": "напиток", "Музыка": "музыкальный жанр" }

    generator = ElegantLogicPuzzleGenerator(base_categories=base_puzzle_categories, story_elements=puzzle_story)

    print("--- ГЕНЕРАЦИЯ ЭКСПЕРТНОЙ ЗАДАЧИ (ФИНАЛЬНАЯ АРХИТЕКТУРА) ---")
    generator.generate(difficulty=10)
