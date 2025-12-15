# --- СЮДА ВСТАВИТЬ КОД МОДЕЛИ ---
from typing import List

def simulate_ecosystem(grid: List[List[int]], steps: int) -> List[List[int]]:
    n = len(grid)
    current = [row[:] for row in grid]          # copy of the original grid

    for _ in range(steps):
        next_grid = [[0]*n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                val = current[i][j]

                # count neighbors
                rabbits = wolves = grass = 0
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        if di == 0 and dj == 0:
                            continue
                        ni = (i + di) % n
                        nj = (j + dj) % n
                        nval = current[ni][nj]
                        if   nval == 2: rabbits += 1
                        elif nval == 3: wolves   += 1
                        elif nval == 1: grass    += 1

                # apply evolution rules
                if val == 3:                     # wolf
                    next_grid[i][j] = 3 if rabbits > 0 else 0
                elif val == 2:                   # rabbit
                    if wolves > 0:
                        next_grid[i][j] = 3            # eaten by a wolf
                    elif grass == 0:
                        next_grid[i][j] = 0            # starved
                    else:
                        next_grid[i][j] = 2            # survives
                elif val == 1:                   # grass
                    next_grid[i][j] = 2 if rabbits > 0 else 1
                else:                           # empty
                    if rabbits == 3:
                        next_grid[i][j] = 2          # rabbit born
                    elif grass >= 2:
                        next_grid[i][j] = 1          # grass grows
                    else:
                        next_grid[i][j] = 0          # remains empty

        current = next_grid   # move to the next step

    return current


# --- ВАЛИДАТОР ---
import unittest

class TestAIReasoningLab_Module4(unittest.TestCase):
    def run_step(self, grid):
        return simulate_ecosystem(grid, 1)

    def test_wolf_dies_hunger(self):
        """Волк умирает без зайцев"""
        # W 0 0
        # 0 0 0
        # 0 0 0
        grid = [[0]*3 for _ in range(3)]
        grid[0][0] = 3
        res = self.run_step(grid)
        self.assertEqual(res[0][0], 0)

    def test_rabbit_eaten_by_wolf(self):
        """Заяц превращается в Волка, если Волк рядом"""
        # W R 0
        # 0 0 0
        # 0 0 0
        grid = [[0]*3 for _ in range(3)]
        grid[0][0] = 3 # Wolf
        grid[0][1] = 2 # Rabbit
        res = self.run_step(grid)
        # Wolf (0,0) -> нет зайцев рядом? Стоп, тороидальность!
        # (0,0) соседи: (0,1)-Rabbit. Значит Волк (0,0) выживает?
        # Правило 1: Волк выживает, если >0 зайцев. Да.
        self.assertEqual(res[0][0], 3)

        # Rabbit (0,1) -> есть Волк (0,0). Превращается в Волка.
        self.assertEqual(res[0][1], 3)

    def test_rabbit_starves(self):
        """Заяц умирает без травы"""
        # 0 R 0
        # 0 0 0
        # 0 0 0
        grid = [[0]*3 for _ in range(3)]
        grid[0][1] = 2
        res = self.run_step(grid)
        self.assertEqual(res[0][1], 0)

    def test_grass_eaten(self):
        """Трава становится Зайцем, если рядом Заяц"""
        # 0 R 0
        # 0 G 0
        # 0 0 0
        grid = [[0]*3 for _ in range(3)]
        grid[0][1] = 2 # R
        grid[1][1] = 1 # G

        res = self.run_step(grid)
        # R (0,1): Волков нет, Трава (1,1) рядом -> Живет (2)
        self.assertEqual(res[0][1], 2)
        # G (1,1): Заяц рядом -> Становится 2
        self.assertEqual(res[1][1], 2)

    def test_toroidal(self):
        """Проверка границ"""
        # R 0 0
        # 0 0 0
        # 0 0 G
        # R в (0,0), G в (2,2). Они соседи по диагонали через край.
        grid = [[0]*3 for _ in range(3)]
        grid[0][0] = 2
        grid[2][2] = 1

        res = self.run_step(grid)
        # R (0,0) видит G (2,2)? Да -> Живет.
        self.assertEqual(res[0][0], 2)
        # G (2,2) видит R (0,0)? Да -> Становится 2.
        self.assertEqual(res[2][2], 2)

    def test_empty_birth(self):
        """Рождение на пустой клетке"""
        # R R R
        # 0 X 0
        # 0 0 0
        # X(1,1) имеет 3 зайцев сверху -> должен родиться Заяц
        grid = [[0]*3 for _ in range(3)]
        grid[0][0]=2; grid[0][1]=2; grid[0][2]=2

        res = self.run_step(grid)
        self.assertEqual(res[1][1], 2)

if __name__ == '__main__':
    print("\n🚀 ЗАПУСК МОДУЛЯ 4: SIMULATION (LOGIC CHAINS)")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
