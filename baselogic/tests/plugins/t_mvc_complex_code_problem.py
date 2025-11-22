import random
import re
import string
import asyncio
import inspect
from typing import Dict, Any

# Предполагаем, что базовый класс доступен, как в твоем примере
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

class MVCCDBTestGenerator(AbstractTestGenerator):
    def generate(self) -> Dict[str, Any]:
        prompt = (
            """
            #### Роль и контекст
            Ты — архитектор баз данных и эксперт по Python. Твоя специализация — создание высокопроизводительных систем хранения данных с нуля без использования внешних зависимостей. Ты глубоко понимаешь принципы ACID, MVCC (Multi-Version Concurrency Control) и асинхронного ввода-вывода.

            #### Основная задача
            Разработать на чистом Python (Standard Library only) потокобезопасную in-memory базу данных `AsyncMVCCStore`, поддерживающую транзакционность с уровнем изоляции **Snapshot Isolation**.
            
            Модуль должен быть полностью автономным. Внутри модуля должен быть реализован свой тестовый фреймворк, запускающий сценарии при старте скрипта.

            #### Функциональные требования к `AsyncMVCCStore`
            1.  **Хранение данных:** Ключ-значение (Key-Value), где ключ — строка, значение — любой сериализуемый объект.
            2.  **MVCC (Многоверсионность):**
                - Каждая запись должна хранить историю версий.
                - Читающие транзакции видят состояние данных на момент своего начала (Snapshot).
                - Читающие транзакции **никогда** не блокируют пишущие, и наоборот.
            3.  **Транзакции:**
                - Метод `begin_transaction()` возвращает объект транзакции.
                - Поддержка методов транзакции: `get(key)`, `set(key, value)`, `delete(key)`, `commit()`, `rollback()`.
                - **Conflict Detection:** При коммите (commit) транзакция должна проверить, не были ли изменены данные другими параллельными транзакциями, завершившимися после начала текущей. При конфликте — выбрасывать исключение `WriteConflictError`.
            4.  **Garbage Collection (Vacuum):**
                - Фоновый процесс или механизм очистки старых версий данных, которые больше не видны ни одной активной транзакции. Это критично для памяти.
            5.  **Асинхронность:**
                - Все операции ввода-вывода (в данном контексте эмулируемые или логические блокировки) должны быть асинхронными (`async/await`).

            #### Требования и ограничения
            - **Язык:** Python 3.10+.
            - **Библиотеки:** ТОЛЬКО стандартная библиотека (asyncio, collections, time, typing, weakref и т.д.). Запрещены внешние БД или либы.
            - **Производительность:**
                - Решение должно обрабатывать > 50,000 транзакций в секунду в одном потоке event loop.
                - Эффективное использование памяти (не хранить бесконечную историю версий). Использовать `__slots__` для оптимизации структур данных.
            - **Код:** Соблюдение SOLID, Type Hinting, Docstrings.

            #### Сценарии тестирования (должны быть реализованы в коде)
            1.  **Atomicity:** Проверка, что при ошибке или rollback ни одно изменение транзакции не попадает в базу.
            2.  **Isolation (Snapshot):**
                - Запустить Tx1. Изменить ключ A в Tx2 и закоммитить. Проверить, что Tx1 все еще видит старое значение A.
            3.  **Concurrency & Conflicts:**
                - Запустить Tx1 и Tx2 одновременно. Обе читают ключ X. Обе пытаются изменить X. Первая, кто сделает commit — успех, вторая — ошибка `WriteConflictError`.
            4.  **Vacuuming:**
                - Проверка, что память очищается от старых версий после завершения старых транзакций.

            #### Формат ответа
            Единый блок кода Python:
            1.  Реализация `AsyncMVCCStore` и вспомогательных классов.
            2.  Класс `TestFramework` для запуска тестов.
            3.  Набор тестов, покрывающий требования.
            4.  Блок `if __name__ == "__main__":`, запускающий тесты и выводящий отчет.
            
            Не пиши пояснений текстом, только код. Если решение не оптимизировано по памяти или скорости, оно будет считаться неверным.
            """
        )

        # Скрытый валидатор. Этот код будет выполнен ПОСЛЕ кода модели.
        # Он проверит "честность" изоляции и корректность разрешения конфликтов.
        hidden_tests = """
import asyncio

async def run_hidden_verification():
    print("\\n--- ЗАПУСК СКРЫТЫХ ПРОВЕРОК (HARD MODE) ---")
    try:
        store = AsyncMVCCStore()
    except NameError:
        print("ОШИБКА: Класс AsyncMVCCStore не найден.")
        return False

    # Тест 1: Lost Update Anomaly (должна быть предотвращена)
    # Сценарий: Счетчик. T1 и T2 читают X=0. T1 пишет X=1. T2 пишет X=1. 
    # В Snapshot Isolation T2 должен упасть при коммите (или T1), если они пересекаются.
    print("Тест 1: Проверка Lost Update...")
    
    # Инициализация
    t_init = await store.begin_transaction()
    await t_init.set("counter", 0)
    await t_init.commit()

    t1 = await store.begin_transaction()
    t2 = await store.begin_transaction()

    val1 = await t1.get("counter")
    val2 = await t2.get("counter")

    await t1.set("counter", val1 + 1)
    await t2.set("counter", val2 + 1)

    # Первый коммит должен пройти
    try:
        await t1.commit()
    except Exception as e:
        print(f"ОШИБКА: Первый коммит упал: {e}")
        return False

    # Второй коммит ОБЯЗАН упасть (Write Conflict)
    try:
        await t2.commit()
        print("ОШИБКА: Второй коммит прошел успешно (Lost Update не предотвращен!)")
        return False
    except Exception:
        # Мы ожидаем любую ошибку, сигнализирующую о конфликте
        pass
    
    # Проверка итогового значения
    t_final = await store.begin_transaction()
    res = await t_final.get("counter")
    if res != 1:
        print(f"ОШИБКА: Неверное итоговое значение счетчика: {res}, ожидалось 1")
        return False
    
    print("Тест 1: УСПЕХ")

    # Тест 2: High Load & Vacuum (утечка памяти)
    print("Тест 2: Нагрузочный тест с проверкой очистки версий...")
    # Создаем много коротких транзакций обновления одного ключа
    for i in range(5000):
        tx = await store.begin_transaction()
        await tx.set("heavy_key", i)
        await tx.commit()
    
    # Проверяем, что старые версии не висят вечно (доступ к приватному API может потребоваться, 
    # но мы проверим косвенно через скорость или доступные методы, если модель их предоставила.
    # Для универсальности просто проверим консистентность).
    
    tx_check = await store.begin_transaction()
    val = await tx_check.get("heavy_key")
    if val != 4999:
        print(f"ОШИБКА: Значение после нагрузки неверно: {val}")
        return False
    
    print("Тест 2: УСПЕХ")
    return True

# Запуск скрытого теста
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
if not loop.run_until_complete(run_hidden_verification()):
    raise AssertionError("Скрытые проверки MVCC не пройдены")
"""

        return {
            'prompt': prompt,
            'expected_output': {
                'function_name': "AsyncMVCCStore", # Маркер, что класс существует
                'tests': hidden_tests
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        # 1. Извлечение кода (улучшенное)
        code_match = re.search(r"```python\n(.*?)\n```", llm_output, re.DOTALL)
        if not code_match:
            code_match = re.search(r"(class AsyncMVCCStore.*if __name__ == .__main__.:.*?)\Z", llm_output, re.DOTALL | re.MULTILINE)

        if not code_match:
            # Попытка найти хотя бы класс, если форматирование сбито
            code_match = re.search(r"import.*class AsyncMVCCStore.*", llm_output, re.DOTALL)

        if not code_match:
            return {'is_correct': False, 'details': {'error': 'Код Python не найден'}}

        code_to_exec = code_match.group(1) if len(code_match.groups()) > 0 else code_match.group(0)

        # Санитизация
        replacements = {'—': '-', '‘': "'", '’': "'", '“': '"', '”': '"'}
        for old, new in replacements.items():
            code_to_exec = code_to_exec.replace(old, new)

        # 2. Выполнение
        try:
            # Создаем изолированный скоуп
            local_scope = {}
            # Переопределяем print, чтобы не засорять логи, или оставляем для дебага
            # exec(code_to_exec, {'print': lambda *args: None}, local_scope)

            # Важно: Модель может использовать asyncio.run() внутри if name == main.
            # Мы должны вырезать блок main, чтобы запустить тесты самостоятельно,
            # ИЛИ позволить ему выполниться, но перехватить контекст.
            # Лучшая стратегия: загрузить определения классов, потом запустить свои тесты.

            # Удаляем блок if __name__ == "__main__": чтобы код модели не заблокировал выполнение
            code_without_main = re.sub(r'if __name__ == .__main__.:.*', '', code_to_exec, flags=re.DOTALL)

            exec(code_without_main, {}, local_scope)

            if 'AsyncMVCCStore' not in local_scope:
                return {'is_correct': False, 'details': {'error': 'Класс AsyncMVCCStore не найден'}}

            # Запуск скрытых тестов
            # Нам нужно внедрить класс в скоуп теста
            test_scope = local_scope.copy()
            exec(expected_output['tests'], test_scope)

            return {'is_correct': True, 'details': {'status': 'MVCC тесты пройдены успешно'}}

        except AssertionError as e:
            return {'is_correct': False, 'details': {'error': 'Логическая ошибка теста', 'msg': str(e)}}
        except Exception as e:
            return {'is_correct': False, 'details': {'error': 'Runtime Error', 'traceback': str(e)}}