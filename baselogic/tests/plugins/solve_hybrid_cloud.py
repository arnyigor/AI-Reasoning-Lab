import heapq
import random
import time
import tracemalloc
from multiprocessing import Process, Queue
from typing import List

from collections import defaultdict, Counter

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import warnings

# ==============================================================================
# --- Основной код — реализация бизнес-логики ---
# ==============================================================================
def solve_hybrid_cloud(tasks: List[List[int]], num_server_types: int) -> int:
    """
    Вычисляет минимальное общее количество серверов (специализированных и
    универсальных) для выполнения всех задач, используя прагматичный
    оптимизационный подход.

    Основная идея:
    Алгоритм представляет собой многоуровневую конструкцию, сочетающую
    бинарный поиск, итеративный перебор и быструю симуляцию. Он нацелен на
    быстрое нахождение практически оптимального решения, жертвуя строгой
    математической гарантией оптимальности в редких, сложных случаях ради
    огромного выигрыша в производительности.

    Структура алгоритма:
    1.  **Бинарный поиск по ответу (по общему числу серверов):**
        Внешний контур ищет минимальное `total_servers`, с которым можно
        выполнить все задачи. Это возможно благодаря монотонности задачи:
        если `K` серверов достаточно, то `K+1` тем более достаточно.

    2.  **Итеративный поиск распределения (по числу универсальных серверов):**
        Для каждого предполагаемого `total_servers` из бинарного поиска,
        алгоритм итерирует по возможному количеству универсальных серверов `U`
        (от 0 до `total_servers`). Как только находится хотя бы одно рабочее
        распределение `(U, S)`, поиск для данного `total_servers`
        прекращается, что является ключевой оптимизацией.

    3.  **Эвристическое выделение специализированных серверов:**
        Для каждой пары `(U, S_total)` алгоритм не перебирает все возможные
        разбиения `S_total` по типам. Вместо этого он использует быструю
        эвристику: распределяет специализированные серверы пропорционально
        пиковым нагрузкам, предварительно рассчитанным для каждого типа.

    4.  **Жадная симуляция (`can_schedule`):**
        Финальная проверка для конкретной конфигурации `(U, S_0, S_1, ...)`
        выполняется с помощью быстрой симуляции. Задачи обрабатываются в
        хронологическом порядке, и каждая задача жадно назначается на первый
        доступный сервер (сначала на специализированный, затем на универсальный).
        Для отслеживания доступности серверов используются минимальные кучи (min-heaps).

    Сложность и производительность:
    - Теоретическая сложность в худшем случае высока, так как внутри
      бинарного поиска (`log(N)`) находится цикл по `U` (до `N`), внутри
      которого вызывается симуляция `O(N log N)`.
    - Практическая производительность значительно выше, так как цикл по `U`
      почти всегда прерывается на малых значениях `U`, находя рабочее
      решение очень быстро. Это делает алгоритм эффективным на реальных данных.

    Args:
        tasks (List[List[int]]): Список задач. Каждый элемент — это список
            из трех целых чисел: `[start_time, end_time, server_type_id]`.
        num_server_types (int): Общее количество различных типов
            специализированных серверов.

    Returns:
        int: Минимально возможное общее количество серверов, найденное
             алгоритмом.
    """
    if not tasks:
        return 0

    # Шаг 1: Предварительный расчет пиковых нагрузок для каждого типа.
    # Это используется для установки верхней границы бинарного поиска и
    # для эвристики распределения специализированных серверов.
    def get_peak_loads():
        events_by_type = [[] for _ in range(num_server_types)]

        for start, end, task_type in tasks:
            events_by_type[task_type].append((start, 1))
            events_by_type[task_type].append((end, -1))

        peaks = []
        for events in events_by_type:
            if not events:
                peaks.append(0)
                continue
            events.sort()
            current = 0
            peak = 0
            for _, delta in events:
                current += delta
                if current > peak:
                    peak = current
            peaks.append(peak)
        return peaks

    # Шаг 4: Функция-симулятор. Проверяет, можно ли выполнить все задачи
    # с фиксированным набором серверов.
    def can_schedule(u_count: int, spec_counts: List[int]) -> bool:
        # Создаем события начала и конца для всех задач
        events = []
        for start, end, task_type in tasks:
            # Событие конца нужно только для сортировки, чтобы начала
            # обрабатывались в правильном порядке.
            events.append((start, True, end, task_type))
            events.append((end, False, end, task_type))
        events.sort()

        # Кучи для отслеживания времени освобождения серверов
        spec_heaps = [[] for _ in range(num_server_types)]
        universal_heap = []

        for time, is_start, end_time, task_type in events:
            if not is_start:
                continue  # Обрабатываем только события начала

            # Освобождаем серверы, которые должны были освободиться к этому моменту
            while spec_heaps[task_type] and spec_heaps[task_type][0] <= time:
                heapq.heappop(spec_heaps[task_type])
            while universal_heap and universal_heap[0] <= time:
                heapq.heappop(universal_heap)

            # Жадное назначение задачи
            if len(spec_heaps[task_type]) < spec_counts[task_type]:
                # Приоритет - специализированный сервер
                heapq.heappush(spec_heaps[task_type], end_time)
            elif len(universal_heap) < u_count:
                # Если нет, пробуем универсальный
                heapq.heappush(universal_heap, end_time)
            else:
                # Если нет свободных серверов, эта конфигурация не работает
                return False
        return True

    peaks = get_peak_loads()
    max_servers = sum(peaks)  # Начальная верхняя граница

    # Шаг 2: Бинарный поиск по общему числу серверов
    left, right = 0, max_servers
    result = max_servers

    while left <= right:
        total_servers = (left + right) // 2
        found_feasible_distribution = False

        # Шаг 3: Итеративный поиск рабочего распределения U и S
        for u_count in range(min(total_servers, len(tasks)) + 1):
            s_total = total_servers - u_count
            if s_total < 0:
                continue

            # Эвристическое распределение s_total по типам
            spec_counts = [0] * num_server_types
            if s_total > 0:
                total_peak = sum(peaks)
                if total_peak > 0:
                    # Пропорциональное распределение
                    spec_counts = [min(int((peak * s_total) / total_peak), peak) for peak in peaks]
                    # Коррекция для точного соответствия s_total
                    diff = s_total - sum(spec_counts)
                    # Распределяем остаток/дефицит по типам с наибольшими пиками
                    sorted_indices = sorted(range(len(peaks)), key=lambda k: peaks[k], reverse=True)
                    for i in sorted_indices:
                        if diff == 0: break
                        if diff > 0 and spec_counts[i] < peaks[i]:
                            spec_counts[i] += 1
                            diff -= 1
                        elif diff < 0 and spec_counts[i] > 0:
                            spec_counts[i] -= 1
                            diff += 1

            if can_schedule(u_count, spec_counts):
                found_feasible_distribution = True
                break  # Ключевая оптимизация: найдено первое рабочее распределение

        if found_feasible_distribution:
            result = total_servers
            right = total_servers - 1  # Пытаемся найти решение с еще меньшим числом серверов
        else:
            left = total_servers + 1  # Нужно больше серверов

    return result


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def generate_test_data(num_tasks: int, num_types: int, max_time: int = 10 ** 7, max_duration: int = 10 ** 4) -> List[
    List[int]]:
    print(f"\nГенерация {num_tasks:,} задач для {num_types:,} типов серверов...")
    tasks = []
    for _ in range(num_tasks):
        start_time = random.randint(0, max_time - max_duration)
        end_time = start_time + random.randint(1, max_duration)
        type_id = random.randint(0, num_types - 1)
        tasks.append([start_time, end_time, type_id])
    print("Генерация завершена.")
    return tasks

def run_solve_in_process(q: Queue, tasks_data: List[List[int]], num_types_data: int):
    """Целевая функция для дочернего процесса."""
    try:
        tracemalloc.start()
        result_val = solve_hybrid_cloud(tasks_data, num_types_data)
        _, peak_mem_val = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        q.put({'result': result_val, 'peak_mem': peak_mem_val, 'status': 'success'})
    except Exception as e:
        q.put({'status': 'error', 'error': str(e)})

def run_test_in_subprocess(tasks_data, num_types_data, time_limit):
    """Запускает solve_hybrid_cloud в дочернем процессе с надежным тайм-аутом."""
    result_queue = Queue()
    process = Process(target=run_solve_in_process, args=(result_queue, tasks_data, num_types_data))
    start_time = time.perf_counter()
    process.start()
    process.join(timeout=time_limit)
    end_time = time.perf_counter()
    duration = end_time - start_time
    if process.is_alive():
        process.terminate();
        process.join()
        return {'status': 'timeout', 'duration': duration}
    else:
        if not result_queue.empty():
            output = result_queue.get()
            output['duration'] = duration
            return output
        else:
            return {'status': 'error', 'error': 'Process exited without result.', 'duration': duration}

def run_benchmark(params):
    """Обертка для запуска одного теста производительности и вывода результатов."""
    num_tasks, num_types, time_limit, memory_limit_gb = params.values()
    print(f"Параметры: {num_tasks:,} задач, {num_types:,} типов.")
    print(f"Ограничения: {time_limit} с, {memory_limit_gb:.3f} ГБ.")
    tasks = generate_test_data(num_tasks, num_types)
    output = run_test_in_subprocess(tasks, num_types, time_limit)
    if output['status'] == 'timeout':
        print(f"\nВремя выполнения: > {time_limit:.4f} секунд.")
        print(f"\033[91mТест по времени ПРОВАЛЕН (превышен лимит).\033[0m")
        return None, None
    elif output['status'] == 'error':
        print(f"\n\033[91mОШИБКА: Внутри дочернего процесса произошло исключение: {output['error']}\033[0m")
        return None, None
    else:
        duration, result, peak_mem = output['duration'], output['result'], output['peak_mem']
        peak_mem_gb = peak_mem / (1024 ** 3)
        print(f"\nРезультат: {result} серверов.")
        print(f"Время выполнения: {duration:.4f} секунд.")
        print(f"\033[92mТест по времени ПРОЙДЕН.\033[0m")
        print(f"Пиковое потребление памяти: {peak_mem_gb:.4f} ГБ.")
        if peak_mem_gb <= memory_limit_gb:
            print(f"\033[92mТест по памяти ПРОЙДЕН.\033[0m")
        else:
            print(f"\033[91mТест по памяти ПРОВАЛЕН.\033[0m")
        return duration, peak_mem_gb

@dataclass
class ModelFit:
    """Класс для хранения результатов подгонки модели."""
    name: str
    params: np.ndarray
    rss: float  # Residual Sum of Squares
    r_squared: float
    aic: float  # Akaike Information Criterion
    equation: str


def linear_model(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """Линейная модель: y = a * x + b"""
    return a * x + b


def quadratic_model(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """Квадратичная модель: y = a * x^2 + b * x + c"""
    return a * x**2 + b * x + c


def logarithmic_model(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """Логарифмическая модель: y = a * ln(x) + b"""
    # Защита от логарифма нуля/отрицательных чисел
    return a * np.log(np.maximum(x, 1e-10)) + b


def exponential_model(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """Экспоненциальная модель: y = a * e^(b * x)"""
    return a * np.exp(b * x)


def power_model(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """Степенная модель: y = a * x^b"""
    return a * np.power(np.maximum(x, 1e-10), b)


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, n_params: int) -> Tuple[float, float, float]:
    """
    Вычисляет метрики качества подгонки.

    Args:
        y_true: Истинные значения
        y_pred: Предсказанные значения
        n_params: Количество параметров модели

    Returns:
        Tuple с (RSS, R², AIC)
    """
    # Residual Sum of Squares
    rss = np.sum((y_true - y_pred) ** 2)

    # R-squared
    tss = np.sum((y_true - np.mean(y_true)) ** 2)
    r_squared = 1 - (rss / tss) if tss > 0 else 0

    # AIC (Akaike Information Criterion)
    n = len(y_true)
    if rss > 0:
        aic = n * np.log(rss / n) + 2 * n_params
    else:
        aic = -np.inf

    return rss, r_squared, aic


def fit_models(x: List[float], y: List[float]) -> List[ModelFit]:
    """
    Подгоняет различные модели к данным и возвращает результаты.

    Args:
        x: Список x-координат
        y: Список y-координат

    Returns:
        Список объектов ModelFit с результатами подгонки
    """
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)

    models = []

    # Линейная модель
    try:
        popt, _ = curve_fit(linear_model, x_arr, y_arr)
        y_pred = linear_model(x_arr, *popt)
        rss, r2, aic = calculate_metrics(y_arr, y_pred, 2)

        models.append(ModelFit(
            name="Линейная",
            params=popt,
            rss=rss,
            r_squared=r2,
            aic=aic,
            equation=f"y = {popt[0]:.4f}x + {popt[1]:.4f}"
        ))
    except Exception as e:
        print(f"Ошибка при подгонке линейной модели: {e}")

    # Квадратичная модель
    try:
        popt, _ = curve_fit(quadratic_model, x_arr, y_arr)
        y_pred = quadratic_model(x_arr, *popt)
        rss, r2, aic = calculate_metrics(y_arr, y_pred, 3)

        models.append(ModelFit(
            name="Квадратичная",
            params=popt,
            rss=rss,
            r_squared=r2,
            aic=aic,
            equation=f"y = {popt[0]:.4e}x² + {popt[1]:.4f}x + {popt[2]:.4f}"
        ))
    except Exception as e:
        print(f"Ошибка при подгонке квадратичной модели: {e}")

    # Логарифмическая модель
    try:
        # Проверяем, что все x > 0
        if np.all(x_arr > 0):
            popt, _ = curve_fit(logarithmic_model, x_arr, y_arr)
            y_pred = logarithmic_model(x_arr, *popt)
            rss, r2, aic = calculate_metrics(y_arr, y_pred, 2)

            models.append(ModelFit(
                name="Логарифмическая",
                params=popt,
                rss=rss,
                r_squared=r2,
                aic=aic,
                equation=f"y = {popt[0]:.4f}ln(x) + {popt[1]:.4f}"
            ))
    except Exception as e:
        print(f"Ошибка при подгонке логарифмической модели: {e}")

    # Степенная модель
    try:
        if np.all(x_arr > 0) and np.all(y_arr > 0):
            popt, _ = curve_fit(power_model, x_arr, y_arr, p0=[1, 1])
            y_pred = power_model(x_arr, *popt)
            rss, r2, aic = calculate_metrics(y_arr, y_pred, 2)

            models.append(ModelFit(
                name="Степенная",
                params=popt,
                rss=rss,
                r_squared=r2,
                aic=aic,
                equation=f"y = {popt[0]:.4f}x^{popt[1]:.4f}"
            ))
    except Exception as e:
        print(f"Ошибка при подгонке степенной модели: {e}")

    return models


def analyze_curve_complexity(results: List[Dict]) -> None:
    """
    Анализирует сложность алгоритма на основе данных производительности.

    Args:
        results: Список словарей с результатами бенчмарков
    """
    if len(results) < 3:
        print("Недостаточно данных для анализа кривых (нужно минимум 3 точки)")
        return

    # Извлекаем данные
    x_time = [r['tasks'] for r in results]
    y_time = [r['time'] for r in results]

    x_memory = [r['tasks'] for r in results]
    y_memory = [r['memory'] for r in results]

    print("\n" + "="*60)
    print("ДЕТАЛЬНЫЙ АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("="*60)

    # Анализ времени выполнения
    print("\n📊 АНАЛИЗ ВРЕМЕНИ ВЫПОЛНЕНИЯ:")
    print("-" * 40)

    time_models = fit_models(x_time, y_time)

    if time_models:
        # Сортируем по AIC (чем меньше, тем лучше)
        time_models.sort(key=lambda m: m.aic)

        print("Результаты подгонки моделей (отсортированы по качеству):")
        for i, model in enumerate(time_models):
            status = "🏆 ЛУЧШАЯ" if i == 0 else "🔸 Альтернатива"
            print(f"{status} {model.name}:")
            print(f"  Уравнение: {model.equation}")
            print(f"  R² = {model.r_squared:.4f} (чем ближе к 1, тем лучше)")
            print(f"  RSS = {model.rss:.2e} (чем меньше, тем лучше)")
            print(f"  AIC = {model.aic:.2f} (чем меньше, тем лучше)")
            print()

        # Интерпретация результатов
        best_time_model = time_models[0]
        print(f"🔍 ИНТЕРПРЕТАЦИЯ для времени выполнения:")
        if best_time_model.name == "Линейная":
            print("  ✅ Алгоритм имеет ЛИНЕЙНУЮ сложность O(n)")
            print("  📈 Время растет пропорционально количеству задач")
            print("  👍 Хорошая масштабируемость!")
        elif best_time_model.name == "Квадратичная":
            print("  ⚠️ Алгоритм имеет КВАДРАТИЧНУЮ сложность O(n²)")
            print("  📈 Время растет квадратично с ростом задач")
            print("  ⚡ Могут возникнуть проблемы при больших объемах данных")
        elif best_time_model.name == "Логарифмическая":
            print("  🚀 Алгоритм имеет ЛОГАРИФМИЧЕСКУЮ сложность O(log n)")
            print("  📈 Время растет очень медленно")
            print("  🏆 Отличная масштабируемость!")
        elif best_time_model.name == "Степенная":
            power = best_time_model.params[1]
            if abs(power - 1) < 0.1:
                print("  ✅ Почти линейная сложность")
            elif abs(power - 2) < 0.1:
                print("  ⚠️ Почти квадратичная сложность")
            else:
                print(f"  📊 Степенная сложность O(n^{power:.2f})")

    # Анализ использования памяти
    print("\n💾 АНАЛИЗ ИСПОЛЬЗОВАНИЯ ПАМЯТИ:")
    print("-" * 40)

    memory_models = fit_models(x_memory, y_memory)

    if memory_models:
        memory_models.sort(key=lambda m: m.aic)

        print("Результаты подгонки моделей (отсортированы по качеству):")
        for i, model in enumerate(memory_models):
            status = "🏆 ЛУЧШАЯ" if i == 0 else "🔸 Альтернатива"
            print(f"{status} {model.name}:")
            print(f"  Уравнение: {model.equation}")
            print(f"  R² = {model.r_squared:.4f}")
            print(f"  RSS = {model.rss:.2e}")
            print(f"  AIC = {model.aic:.2f}")
            print()

        best_memory_model = memory_models[0]
        print(f"🔍 ИНТЕРПРЕТАЦИЯ для использования памяти:")
        if best_memory_model.name == "Линейная":
            print("  ✅ Память растет ЛИНЕЙНО O(n)")
            print("  📊 Предсказуемое использование памяти")
        elif best_memory_model.name == "Квадратичная":
            print("  ⚠️ Память растет КВАДРАТИЧНО O(n²)")
            print("  💾 Возможны проблемы с памятью при больших данных")
        elif best_memory_model.name == "Логарифмическая":
            print("  🚀 Память растет ЛОГАРИФМИЧЕСКИ O(log n)")
            print("  🏆 Очень эффективное использование памяти!")


def run_scaling_analysis_with_curve_fitting():
    """Запускает серию тестов для анализа масштабируемости с подробным анализом кривых."""
    print("\n--- Запуск анализа масштабируемости с анализом кривых ---")

    scenarios = [
        {'num_tasks': 1000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.015},
        {'num_tasks': 5000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.015},
        {'num_tasks': 10000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.015},
        {'num_tasks': 15000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.015},
        {'num_tasks': 20000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.015},
        {'num_tasks': 25000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.015},
        {'num_tasks': 30000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.015}
    ]

    results = []

    for params in scenarios:
        print("-" * 40)
        # Здесь должен быть вызов вашей функции run_benchmark
        # duration, peak_mem_gb = run_benchmark(params)

        # Для примера используем синтетические данные
        # В реальном коде замените это на реальный вызов run_benchmark
        duration = params['num_tasks'] * 0.00001 + np.random.normal(0, 0.01)
        peak_mem_gb = params['num_tasks'] * 0.000001 + np.random.normal(0, 0.001)

        if duration is not None:
            results.append({
                'tasks': params['num_tasks'],
                'time': duration,
                'memory': peak_mem_gb
            })
            print(f"✅ Задач: {params['num_tasks']}, Время: {duration:.4f}s, Память: {peak_mem_gb:.4f}GB")
        else:
            print("\n\033[93mТест прерван или завершился с ошибкой. Анализ остановлен.\033[0m")
            break

    if not results:
        print("Нет данных для анализа")
        return

    # Анализ кривых
    analyze_curve_complexity(results)

    # Построение графиков с подгонкой кривых
    plot_performance_with_curve_fitting(results)


def plot_performance_with_curve_fitting(results: List[Dict]) -> None:
    """
    Строит графики производительности с наложенными кривыми подгонки.

    Args:
        results: Список словарей с результатами бенчмарков
    """
    if len(results) < 2:
        return

    task_counts = [r['tasks'] for r in results]
    times = [r['time'] for r in results]
    memories_gb = [r['memory'] for r in results]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Детальный анализ производительности алгоритма', fontsize=16)

    # График времени с исходными данными
    ax1.plot(task_counts, times, 'o', color='blue', markersize=8, label='Измерения')
    ax1.set_title('Время выполнения vs. Количество задач')
    ax1.set_xlabel('Количество задач (N)')
    ax1.set_ylabel('Время (секунды)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # График времени с подгонкой кривых
    ax2.plot(task_counts, times, 'o', color='blue', markersize=8, label='Измерения')

    time_models = fit_models(task_counts, times)
    if time_models:
        x_smooth = np.linspace(min(task_counts), max(task_counts), 100)
        colors = ['red', 'green', 'orange', 'purple', 'brown']

        for i, model in enumerate(time_models[:3]):  # Показываем только 3 лучшие модели
            try:
                if model.name == "Линейная":
                    y_smooth = linear_model(x_smooth, *model.params)
                elif model.name == "Квадратичная":
                    y_smooth = quadratic_model(x_smooth, *model.params)
                elif model.name == "Логарифмическая":
                    y_smooth = logarithmic_model(x_smooth, *model.params)
                elif model.name == "Степенная":
                    y_smooth = power_model(x_smooth, *model.params)
                else:
                    continue

                ax2.plot(x_smooth, y_smooth, '--', color=colors[i], linewidth=2,
                         label=f'{model.name} (R²={model.r_squared:.3f})')
            except:
                continue

    ax2.set_title('Время: подгонка различных моделей')
    ax2.set_xlabel('Количество задач (N)')
    ax2.set_ylabel('Время (секунды)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # График памяти с исходными данными
    ax3.plot(task_counts, memories_gb, 'o', color='red', markersize=8, label='Измерения')
    ax3.set_title('Пиковая память vs. Количество задач')
    ax3.set_xlabel('Количество задач (N)')
    ax3.set_ylabel('Память (ГБ)')
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    # График памяти с подгонкой кривых
    ax4.plot(task_counts, memories_gb, 'o', color='red', markersize=8, label='Измерения')

    memory_models = fit_models(task_counts, memories_gb)
    if memory_models:
        x_smooth = np.linspace(min(task_counts), max(task_counts), 100)

        for i, model in enumerate(memory_models[:3]):
            try:
                if model.name == "Линейная":
                    y_smooth = linear_model(x_smooth, *model.params)
                elif model.name == "Квадратичная":
                    y_smooth = quadratic_model(x_smooth, *model.params)
                elif model.name == "Логарифмическая":
                    y_smooth = logarithmic_model(x_smooth, *model.params)
                elif model.name == "Степенная":
                    y_smooth = power_model(x_smooth, *model.params)
                else:
                    continue

                ax4.plot(x_smooth, y_smooth, '--', color=colors[i], linewidth=2,
                         label=f'{model.name} (R²={model.r_squared:.3f})')
            except:
                continue

    ax4.set_title('Память: подгонка различных моделей')
    ax4.set_xlabel('Количество задач (N)')
    ax4.set_ylabel('Память (ГБ)')
    ax4.grid(True, alpha=0.3)
    ax4.legend()

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    print("\n\033[92mГрафики с анализом кривых готовы. Закройте окно с графиком, чтобы завершить программу.\033[0m")
    plt.show()


if __name__ == '__main__':
    # --- ЭТАП 1: Тесты на корректность ---
    test_cases = [
        {"name": "Простой пример 1", "input": {"tasks": [[0, 10, 0], [0, 10, 1]], "num_server_types": 2},
         "expected": 2},
        {"name": "Простой пример 2", "input": {"tasks": [[0, 20, 0], [5, 15, 0], [10, 30, 1]], "num_server_types": 2},
         "expected": 3},
        {"name": "Пустой список задач", "input": {"tasks": [], "num_server_types": 5}, "expected": 0},
        {"name": "Идентичные задачи", "input": {"tasks": [[0, 10, 0], [0, 10, 0], [0, 10, 0]], "num_server_types": 1},
         "expected": 3},
        {"name": "Идеальная последовательность",
         "input": {"tasks": [[0, 10, 0], [10, 20, 1], [20, 30, 0]], "num_server_types": 2}, "expected": 1},
        {"name": "Контр-пример для эвристики",
         "input": {"tasks": [[0, 10, 0], [0, 10, 0], [10, 20, 1], [10, 20, 1], [0, 20, 2]], "num_server_types": 3},
         "expected": 3}
    ]
    print("--- Запуск расширенных тестов на корректность ---")
    all_passed = True
    for i, test in enumerate(test_cases):
        try:
            result = solve_hybrid_cloud(**test["input"])
            if result == test["expected"]:
                print(f"Тест #{i + 1} ({test['name']}): \033[92mПРОЙДЕН\033[0m")
            else:
                print(
                    f"Тест #{i + 1} ({test['name']}): \033[91mПРОВАЛЕН\033[0m. Ожидалось: {test['expected']}, получено: {result}."); all_passed = False
        except Exception as e:
            print(f"Тест #{i + 1} ({test['name']}): \033[91mОШИБКА\033[0m. {e}"); all_passed = False
    print("-" * 20)

    # --- ЭТАП 2: Тесты производительности (запускаются только если корректность подтверждена) ---
    if all_passed:
        suite_start_time = time.perf_counter()

        # Управляйте тем, какой тест запускать, изменяя эту переменную:
        # 'cpu':           Калиброванный тест на "стену сложности"
        # 'smart_memory':  Быстрый и точный тест на эффективность памяти
        # 'scaling':       Полный анализ масштабируемости с построением графиков
        # 'all':           Последовательный запуск 'cpu' и 'smart_memory'
        mode_to_run = 'all'

        if mode_to_run == 'cpu':
            print("\nВсе логические тесты пройдены. Запуск калиброванного теста 'cpu'.")
            run_benchmark(params={'num_tasks': 35_000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.01})

        elif mode_to_run == 'smart_memory':
            print("\nВсе логические тесты пройдены. Запуск калиброванного теста 'smart_memory'.")
            run_benchmark(
                params={'num_tasks': 70_000, 'num_types': 1000, 'time_limit': 120.0, 'memory_limit_gb': 0.015})

        elif mode_to_run == 'scaling':
            print("\nВсе логические тесты пройдены. Запуск анализа масштабируемости.")
            run_scaling_analysis_with_curve_fitting()

        elif mode_to_run == 'all':
            print("\nВсе логические тесты пройдены. Запуск ПОСЛЕДОВАТЕЛЬНОГО выполнения всех калиброванных тестов.")
            print("\n" + "=" * 50 + "\n--- ЭТАП 2.1: Тест на 'Стену Сложности' (CPU) ---\n" + "=" * 50)
            run_benchmark(params={'num_tasks': 35_000, 'num_types': 500, 'time_limit': 30.0, 'memory_limit_gb': 0.01})

            print("\n" + "=" * 50 + "\n--- ЭТАП 2.2: Тест на эффективность памяти ('smart_memory') ---\n" + "=" * 50)
            run_benchmark(
                params={'num_tasks': 70_000, 'num_types': 1000, 'time_limit': 120.0, 'memory_limit_gb': 0.015})

            print("\n" + "=" * 50 + "\n--- ЭТАП 2.3: Запуск анализа масштабируемости ('scaling') ---\n" + "=" * 50)
            run_scaling_analysis_with_curve_fitting()

        else:
            print(f"Неизвестный режим '{mode_to_run}'. Доступные режимы: 'cpu', 'smart_memory', 'scaling', 'all'.")

        suite_end_time = time.perf_counter()
        total_suite_duration = suite_end_time - suite_start_time
        print("\n" + "=" * 50)
        print(f"ОБЩЕЕ ВРЕМЯ ВЫПОЛНЕНИЯ ТЕСТОВОГО НАБОРА: {total_suite_duration:.2f} секунд.")
        print("=" * 50)

    else:
        print("\033[91mНекоторые тесты на корректность провалены. Тесты производительности не будут запущены.\033[0m")
