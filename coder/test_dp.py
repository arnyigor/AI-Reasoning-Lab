# --- СЮДА ВСТАВИТЬ КОД МОДЕЛИ ---
from typing import List, Dict, Optional
from functools import lru_cache


def optimize_cloud_resources(
        tasks: List[Dict],
        max_cpu: int,
        max_ram: int
) -> int:
    """
    Return the maximum total profit that can be obtained while respecting
    CPU/RAM limits, group‑uniqueness and explicit dependencies.
    """

    # ------------------------------------------------------------------
    # 1. Prepare data ---------------------------------------------------
    # ------------------------------------------------------------------
    # Sort by id (guaranteed: dependency id < task id)
    tasks = sorted(tasks, key=lambda x: x["id"])
    n = len(tasks)

    # Map original group ids to compact indices 0 .. G-1
    unique_groups = {t["group_id"] for t in tasks}
    grp2idx = {g: i for i, g in enumerate(sorted(unique_groups))}
    G = len(unique_groups)

    # Map task id → index (needed for dependencies)
    id_to_index = {t["id"]: i for i, t in enumerate(tasks)}

    # Augment each task with compact fields and parent index
    augmented: List[Dict] = []
    for idx, t in enumerate(tasks):
        dep_id: Optional[int] = t.get("depends_on")
        if dep_id is not None:
            parent_idx = id_to_index[dep_id]
        else:
            parent_idx = None

        augmented.append(
            {
                "cpu": t["cpu"],
                "ram": t["ram"],
                "profit": t["profit"],
                "group": grp2idx[t["group_id"]],
                "parent": parent_idx,
            }
        )

    # ------------------------------------------------------------------
    # 2. Memoised DFS -----------------------------------------------
    # ------------------------------------------------------------------
    @lru_cache(maxsize=None)
    def dfs(
            pos: int,          # current index in augmented
            cpu_left: int,
            ram_left: int,
            used_grp_mask: int,
            sel_mask: int,
    ) -> int:
        """
        Return the maximal profit obtainable from tasks[pos:] given
        remaining resources and already chosen groups/tasks.
        """
        if pos == n:
            return 0

        task = augmented[pos]
        best = dfs(pos + 1, cpu_left, ram_left, used_grp_mask, sel_mask)  # skip

        # ------------------------------------------------------------------
        # try to take this task
        # ------------------------------------------------------------------
        g_bit = 1 << task["group"]
        if (used_grp_mask & g_bit) == 0:          # group free
            if task["cpu"] <= cpu_left and task["ram"] <= ram_left:
                # dependency satisfied ?
                parent_ok = True
                p = task["parent"]
                if p is not None:
                    if (sel_mask >> p) & 1 == 0:   # parent NOT chosen
                        parent_ok = False
                if parent_ok:
                    new_sel_mask = sel_mask | (1 << pos)
                    profit_taken = (
                            task["profit"]
                            + dfs(
                        pos + 1,
                        cpu_left - task["cpu"],
                        ram_left - task["ram"],
                        used_grp_mask | g_bit,
                        new_sel_mask,
                        )
                    )
                    if profit_taken > best:
                        best = profit_taken

        return best

    # ------------------------------------------------------------------
    # 3. Start recursion -----------------------------------------------
    # ------------------------------------------------------------------
    return dfs(0, max_cpu, max_ram, 0, 0)


# ----------------------------------------------------------------------
# Example from the statement – should print 60
# ----------------------------------------------------------------------
if __name__ == "__main__":
    tasks_example = [
        {"id": 1, "group_id": 1, "cpu": 10, "ram": 10, "profit": 10,
         "depends_on": None},
        {"id": 2, "group_id": 1, "cpu": 10, "ram": 10, "profit": 20,
         "depends_on": None},
        {"id": 3, "group_id": 2, "cpu": 20, "ram": 20, "profit": 50,
         "depends_on": 1},
    ]
    print(optimize_cloud_resources(tasks_example, max_cpu=50, max_ram=50))

# ...

# --- ВАЛИДАТОР ---
import unittest

class TestAIReasoningLab_Module2(unittest.TestCase):
    def test_basic_knapsack(self):
        """Базовый тест: просто рюкзак, без групп и зависимостей"""
        tasks = [
            {'id': 1, 'group_id': 1, 'cpu': 10, 'ram': 10, 'profit': 10, 'depends_on': None},
            {'id': 2, 'group_id': 2, 'cpu': 10, 'ram': 10, 'profit': 20, 'depends_on': None},
        ]
        # Берем обоих
        self.assertEqual(optimize_cloud_resources(tasks, 25, 25), 30)
        # Берем только дорогого
        self.assertEqual(optimize_cloud_resources(tasks, 15, 15), 20)

    def test_group_constraint(self):
        """Тест ограничений групп (XOR выбор)"""
        tasks = [
            {'id': 1, 'group_id': 100, 'cpu': 10, 'ram': 10, 'profit': 10, 'depends_on': None},
            {'id': 2, 'group_id': 100, 'cpu': 10, 'ram': 10, 'profit': 50, 'depends_on': None}, # Выгоднее
            {'id': 3, 'group_id': 200, 'cpu': 10, 'ram': 10, 'profit': 5, 'depends_on': None},
        ]
        # Должен выбрать id:2 (profit 50) и id:3 (profit 5). id:1 игнорируется, т.к. в группе 100 уже есть лучший.
        self.assertEqual(optimize_cloud_resources(tasks, 50, 50), 55)

    def test_dependency_chain(self):
        """Тест зависимостей: Child требует Parent"""
        tasks = [
            {'id': 1, 'group_id': 1, 'cpu': 10, 'ram': 10, 'profit': 10, 'depends_on': None},       # Parent
            {'id': 2, 'group_id': 2, 'cpu': 10, 'ram': 10, 'profit': 100, 'depends_on': 1},         # Child
        ]
        # Хватает ресурсов на обоих -> 110
        self.assertEqual(optimize_cloud_resources(tasks, 30, 30), 110)

        # Не хватает ресурсов на обоих -> берем только Parent (10) или ничего.
        # Child (100) взять нельзя, т.к. на Parent не хватит места.
        # Но подождите, если мы не можем взять обоих, мы можем взять только 1? Да.
        # Profit = 10.
        self.assertEqual(optimize_cloud_resources(tasks, 15, 15), 10)

    def test_conflict_dependency_vs_group(self):
        """
        Сложный случай:
        Task A (Group 1) - дешевый, нужен для C.
        Task B (Group 1) - дорогой, но не позволяет взять C.
        Task C (Group 2) - супер дорогой, зависит от A.

        Нужно понять, что выгоднее: (A + C) или (B).
        """
        tasks = [
            {'id': 1, 'group_id': 1, 'cpu': 10, 'ram': 10, 'profit': 10, 'depends_on': None}, # A
            {'id': 2, 'group_id': 1, 'cpu': 10, 'ram': 10, 'profit': 20, 'depends_on': None}, # B (Лучше A)
            {'id': 3, 'group_id': 2, 'cpu': 10, 'ram': 10, 'profit': 50, 'depends_on': 1},    # C (Требует A)
        ]
        # Вариант 1: Взять B (Group 1) = 20. C взять нельзя (нет A). Итого 20.
        # Вариант 2: Взять A (Group 1) + C (Group 2) = 10 + 50 = 60.
        # Оптимум = 60.
        self.assertEqual(optimize_cloud_resources(tasks, 100, 100), 60)

    def test_complex_tree(self):
        """Цепочка 1 <- 2 <- 3"""
        tasks = [
            {'id': 1, 'group_id': 1, 'cpu': 5, 'ram': 5, 'profit': 10, 'depends_on': None},
            {'id': 2, 'group_id': 2, 'cpu': 5, 'ram': 5, 'profit': 20, 'depends_on': 1},
            {'id': 3, 'group_id': 3, 'cpu': 5, 'ram': 5, 'profit': 100, 'depends_on': 2},
        ]
        # Чтобы взять 3, нужно 2, которому нужно 1.
        # Total cost: 15 CPU, 15 RAM. Total profit: 130.
        self.assertEqual(optimize_cloud_resources(tasks, 20, 20), 130)

        # Если ресурсов 10 -> хватит только на (1+2)=30 profit, или просто (1)=10. Макс 30.
        # (3 взять нельзя, т.к. нужно 1+2+3=15 cpu).
        self.assertEqual(optimize_cloud_resources(tasks, 10, 10), 30)

if __name__ == '__main__':
    print("\n🚀 ЗАПУСК МОДУЛЯ 2: DYNAMIC PROGRAMMING")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
