import random
import pandas as pd
from typing import Dict, List, Any, Tuple
import copy

# --- Класс-решатель (Constraint Satisfaction Problem Solver) ---
# Этот класс остается без изменений, его логика корректна.
class ConstraintSatisfactionSolver:
    """
    Решает головоломку методом исключения (удовлетворения ограничений).
    Это мозг, который проверяет, решаема ли задача с данным набором подсказок.
    """
    def __init__(self, categories: Dict[str, List[str]]):
        self.categories = categories
        self.num_items = len(next(iter(categories.values())))
        self.cat_keys = list(categories.keys())
        self.possibilities = {
            cat: [list(items) for _ in range(self.num_items)]
            for cat, items in categories.items()
        }

    def _propagate_constraints(self) -> bool:
        made_change = False
        for i in range(self.num_items):
            for cat in self.cat_keys:
                if len(self.possibilities[cat][i]) == 1:
                    value_to_remove = self.possibilities[cat][i][0]
                    for j in range(self.num_items):
                        if i != j and value_to_remove in self.possibilities[cat][j]:
                            self.possibilities[cat][j].remove(value_to_remove)
                            made_change = True
        return made_change

    def solve(self, clues: List[Tuple]):
        for clue in clues:
            self._apply_clue(clue)
        while self._propagate_constraints():
            pass

    def _apply_clue(self, clue: Tuple):
        clue_type = clue[0]
        params = clue[1:]
        if clue_type == 'direct_link':
            cat1, val1, cat2, val2 = params
            for i in range(self.num_items):
                if val1 not in self.possibilities[cat1][i]:
                    if val2 in self.possibilities[cat2][i]: self.possibilities[cat2][i].remove(val2)
                if val2 not in self.possibilities[cat2][i]:
                    if val1 in self.possibilities[cat1][i]: self.possibilities[cat1][i].remove(val1)
        elif clue_type == 'positional':
            pos_idx, cat, val = params[0] - 1, params[1], params[2]
            if val in self.possibilities[cat][pos_idx]: self.possibilities[cat][pos_idx] = [val]
        elif clue_type == 'relative_pos':
            cat, val_left, val_right = params
            if val_right in self.possibilities[cat][0]: self.possibilities[cat][0].remove(val_right)
            if val_left in self.possibilities[cat][-1]: self.possibilities[cat][-1].remove(val_left)
            for i in range(self.num_items - 1):
                if val_left not in self.possibilities[cat][i] and val_right in self.possibilities[cat][i+1]:
                    self.possibilities[cat][i+1].remove(val_right)
                if val_right not in self.possibilities[cat][i+1] and val_left in self.possibilities[cat][i]:
                    self.possibilities[cat][i].remove(val_left)

    def get_status(self) -> str:
        is_solved = True
        for cat in self.cat_keys:
            for i in range(self.num_items):
                if len(self.possibilities[cat][i]) == 0: return "contradiction"
                if len(self.possibilities[cat][i]) > 1: is_solved = False
        return "solved" if is_solved else "unsolved"

# --- Улучшенный класс-генератор ---
class AdvancedLogicPuzzleGenerator:
    """
    Генерирует логические головоломки с настраиваемой сложностью,
    гарантируя единственность решения и отсутствие прямого ответа в условиях.
    """
    def __init__(self, categories: Dict[str, List[str]], story_elements: Dict[str, str], primary_subject_category: str):
        if primary_subject_category not in categories:
            raise ValueError(f"Основная категория '{primary_subject_category}' не найдена в списке категорий.")
        self.categories = categories
        self.story_elements = story_elements
        self.num_items = len(next(iter(categories.values())))
        self.cat_keys = list(categories.keys())
        self.primary_subject_category = primary_subject_category
        self.solution = None
        self.CLUE_DIFFICULTY = {'positional': 1, 'direct_link': 2, 'relative_pos': 4, 'neighbor': 5}

    def _generate_solution(self):
        solution_data = {cat: random.sample(items, len(items)) for cat, items in self.categories.items()}
        self.solution = pd.DataFrame(solution_data)
        self.solution.index = range(1, self.num_items + 1)

    def _generate_all_possible_clues(self) -> Dict[str, List[Tuple]]:
        pool = {clue_type: [] for clue_type in self.CLUE_DIFFICULTY.keys()}
        cat_pairs = [(self.cat_keys[i], self.cat_keys[j]) for i in range(len(self.cat_keys)) for j in range(i + 1, len(self.cat_keys))]
        for _, row in self.solution.iterrows():
            for cat1, cat2 in cat_pairs: pool['direct_link'].append(('direct_link', cat1, row[cat1], cat2, row[cat2]))
        for pos, row in self.solution.iterrows():
            for cat in self.cat_keys: pool['positional'].append(('positional', pos, cat, row[cat]))
        for i in range(1, self.num_items):
            for cat in self.cat_keys: pool['relative_pos'].append(('relative_pos', cat, self.solution.loc[i, cat], self.solution.loc[i + 1, cat]))
        for i in range(1, self.num_items):
            cat1, cat2 = random.sample(self.cat_keys, 2)
            pool['neighbor'].append(('neighbor', cat1, self.solution.loc[i, cat1], cat2, self.solution.loc[i+1, cat2]))
        for clue_type in pool: random.shuffle(pool[clue_type])
        return pool

    def _format_clue(self, clue: Tuple) -> str:
        clue_type, params = clue[0], clue[1:]
        s = self.story_elements
        if clue_type == 'direct_link': return f"{s[params[0]].capitalize()} {params[1]} связан с {s[params[2]]} {params[3]}."
        if clue_type == 'positional': return f"В {s['position']} №{params[0]} находится {s[params[1]]} {params[2]}."
        if clue_type == 'relative_pos': return f"{s[params[0]].capitalize()} {params[1]} находится непосредственно слева от {s[params[0]]} {params[2]}."
        if clue_type == 'neighbor': return f"{s[params[0]].capitalize()} {params[1]} находится рядом с {s[params[2]]} {params[3]}."
        return ""

    def generate(self, difficulty: int = 5):
        if not 1 <= difficulty <= 10: raise ValueError("Сложность должна быть между 1 и 10.")

        self._generate_solution()

        # --- ИСПРАВЛЕНИЕ 1: Генерируем вопрос и "запрещенную" подсказку в самом начале ---
        id_category = self.primary_subject_category
        id_item = random.choice(self.categories[id_category])
        attribute_category = random.choice([c for c in self.cat_keys if c != id_category])
        solution_row = self.solution[self.solution[id_category] == id_item]
        answer_item = solution_row[attribute_category].values[0]

        # Эта подсказка-ответ не должна появиться в условиях
        forbidden_clue = ('direct_link', id_category, id_item, attribute_category, answer_item)

        all_clues_pool = self._generate_all_possible_clues()
        # Удаляем запрещенную подсказку из пула, чтобы она никогда не была выбрана
        if forbidden_clue in all_clues_pool['direct_link']:
            all_clues_pool['direct_link'].remove(forbidden_clue)

        # --- ИСПРАВЛЕНИЕ 2: Новый алгоритм выбора и минимизации подсказок ---
        if difficulty <= 3: clue_weights = ['positional'] * 5 + ['direct_link'] * 5
        elif difficulty <= 7: clue_weights = ['positional'] * 2 + ['direct_link'] * 5 + ['relative_pos'] * 3
        else: clue_weights = ['direct_link'] * 4 + ['relative_pos'] * 5 + ['neighbor'] * 1

        # Шаг А: Находим избыточный, но решаемый набор подсказок
        solvable_clues = []
        for _ in range(300): # Ограничитель
            solver = ConstraintSatisfactionSolver(self.categories)
            solver.solve(solvable_clues)
            if solver.get_status() == "solved": break
            clue_type_to_add = random.choice(clue_weights)
            if all_clues_pool[clue_type_to_add]:
                new_clue = all_clues_pool[clue_type_to_add].pop()
                if new_clue not in solvable_clues: solvable_clues.append(new_clue)
        else:
            print("\n[Генератор]: Не удалось найти первоначальное решение. Попробуйте снова.")
            return

        # Шаг Б: Минимизируем набор подсказок, удаляя лишние
        print(f"\n[Генератор]: Найдено избыточное решение с {len(solvable_clues)} подсказками. Начинаю минимизацию...")

        minimal_clues = list(solvable_clues)
        random.shuffle(minimal_clues) # Перемешиваем, чтобы удалять в случайном порядке

        for i in range(len(minimal_clues) - 1, -1, -1): # Идем в обратном порядке для безопасного удаления
            clue_to_test = minimal_clues[i]

            temp_clues = minimal_clues[:i] + minimal_clues[i+1:]

            solver = ConstraintSatisfactionSolver(self.categories)
            solver.solve(temp_clues)

            if solver.get_status() == 'solved':
                # Если задача все еще решаема без этой подсказки, значит, она была лишней.
                minimal_clues.pop(i)

        final_clues = minimal_clues
        print(f"[Генератор]: Минимизация завершена. Финальное количество подсказок: {len(final_clues)}")

        # Формулируем финальный вопрос и ответ
        question = f"Какой {self.story_elements[attribute_category]} у {self.story_elements[id_category]} по имени {id_item}?"
        answer_for_check = f"Ответ для проверки: {answer_item}"

        # Вывод результата
        print(f"\n**Сценарий: {self.story_elements['scenario']} (Сложность: {difficulty}/10)**\n")
        print("Условия:\n")
        final_clues_text = sorted([self._format_clue(c) for c in final_clues])
        for i, clue_text in enumerate(final_clues_text, 1): print(f"{i}. {clue_text}")
        print("\n" + "="*40 + "\n")
        print(f"Вопрос: {question}")
        print("\n" + "="*40 + "\n")
        print(answer_for_check)
        print("\n--- Скрытое Решение для самопроверки ---\n", self.solution)


if __name__ == '__main__':
    puzzle_categories = {
        "Ученый": ["Орлов", "Лебедев", "Соколов", "Воробьев", "Ястребов"],
        "Область": ["Биоинженерия", "Физика", "Нейробиология", "Астрофизика", "Химия"],
        "Суперкомпьютер": ["Титан", "Фугаку", "Секвойя", "Ломоносов", "Тяньхэ-2"],
        "Напиток": ["Чай", "Кофе", "Молоко", "Вода", "Сок"],
        "Музыка": ["Классика", "Джаз", "Эмбиент", "Рок", "Электроника"]
    }

    puzzle_story = {
        "scenario": "Тайна пяти лабораторий",
        "position": "лаборатория",
        "Ученый": "ученый",
        "Область": "специалист",
        "Суперкомпьютер": "суперкомпьютер",
        "Напиток": "напиток",
        "Музыка": "музыкальный жанр"
    }

    generator = AdvancedLogicPuzzleGenerator(
        categories=puzzle_categories,
        story_elements=puzzle_story,
        primary_subject_category="Ученый"
    )

    print("--- ГЕНЕРАЦИЯ СЛОЖНОЙ ЗАДАЧИ С МИНИМИЗАЦИЕЙ ---")
    generator.generate(difficulty=10)
