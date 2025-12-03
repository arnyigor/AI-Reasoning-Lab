import re
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
                - Фоновый процесс или механизм очистки старых версий данных, которые больше не видны ни одной активной транзакции.
            5.  **Асинхронность:**
                - Все операции ввода-вывода должны быть асинхронными (`async/await`).
            
            #### Требования к коду
            - **Язык:** Python 3.10+
            - **Библиотеки:** ТОЛЬКО стандартная библиотека (asyncio, typing, collections и т.д.)
            - **Импорты:** Все необходимые импорты должны быть в начале файла
            - **Типы данных:** Используй встроенные типы `list`, `dict`, `set` вместо `List`, `Dict`, `Set`
            - **Аннотации типов:** Используй `X | None` вместо `Optional[X]`
            - **Forward References:** Для классов, определённых ниже, используй строковые аннотации: `-> "Transaction"`
            - **Оптимизация:** Используй `__slots__` для классов Version и Transaction
            - **Производительность:** Решение должно обрабатывать > 50,000 транзакций в секунду
            
            #### Сценарии тестирования (должны быть реализованы в коде)
            1.  **Atomicity:** При rollback ни одно изменение не должно попасть в базу
            2.  **Isolation (Snapshot):** Tx1 не видит изменения Tx2, сделанные после старта Tx1
            3.  **Concurrency & Conflicts:** Первая транзакция коммитится, вторая получает `WriteConflictError`
            4.  **Vacuuming:** Память очищается от старых версий после завершения транзакций
            
            #### Формат ответа
            Выведи ТОЛЬКО исполняемый Python-код, состоящий из:
            1.  Импорты
            2.  Класс `WriteConflictError`
            3.  Класс `AsyncMVCCStore` и вспомогательные классы
            4.  Класс `TestFramework` для запуска тестов
            5.  Набор тестов
            6.  Блок `if __name__ == "__main__":` с запуском тестов
            
            #### КРИТИЧЕСКИ ВАЖНО:
            1. Начни ответ СРАЗУ со строки `import asyncio` (никакого текста перед этим)
            2. НЕ используй Markdown-блоки кода (никаких ```
            3. НЕ пиши пояснений текстом
            4. Внимательно проверяй синтаксис f-строк (не используй символы вроде `?` внутри `{}`)
            5. Убедись, что все импорты присутствуют в начале файла
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
                'function_name': "AsyncMVCCStore",  # Маркер, что класс существует
                'tests': hidden_tests
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        # ШАГ 1: Удаляем <think> блоки (если модель их вставила)
        cleaned_output = re.sub(r'<think>.*?</think>', '', llm_output, flags=re.DOTALL).strip()

        # ШАГ 2: Пытаемся найти Markdown блок (``````)
        code_match = re.search(r"``````", cleaned_output, re.DOTALL | re.IGNORECASE)

        if code_match:
            code_to_exec = code_match.group(1)
        else:
            # ШАГ 3: Fallback для "чистого кода" без Markdown
            # Ищем первый импорт (import или from)
            start_pattern = re.compile(r'^(import |from )', re.MULTILINE)
            match = start_pattern.search(cleaned_output)

            if match:
                # Берём весь текст начиная с первого импорта
                code_to_exec = cleaned_output[match.start():]
            else:
                # Если импортов нет, проверяем, есть ли хоть что-то похожее на код
                if 'class ' in cleaned_output or 'def ' in cleaned_output:
                    code_to_exec = cleaned_output
                else:
                    return {
                        'is_correct': False,
                        'details': {'error': 'Код не найден (нет импортов, классов или функций)'}
                    }

        # ШАГ 4: Санитизация "кривых" символов
        replacements = {'—': '-', ''': "'", ''': "'", '"': '"', '"': '"'}
        for old, new in replacements.items():
            code_to_exec = code_to_exec.replace(old, new)

        # ШАГ 5: Удаляем блок if __name__ == "__main__":
        code_without_main = re.sub(
            r'if __name__\s*==\s*[\'"]__main__[\'"]\s*:.*$',
            '',
            code_to_exec,
            flags=re.DOTALL | re.MULTILINE
        )

        try:
            # ШАГ 6: Выполняем код модели
            local_scope = {}
            exec(code_without_main, {}, local_scope)

            # ШАГ 7: Проверяем, что класс AsyncMVCCStore есть
            if 'AsyncMVCCStore' not in local_scope:
                return {
                    'is_correct': False,
                    'details': {'error': 'Класс AsyncMVCCStore не найден после выполнения кода'}
                }

            # ШАГ 8: Готовим скоуп для скрытых тестов
            test_scope = local_scope.copy()

            # Добавляем asyncio, если его нет (на всякий случай)
            if 'asyncio' not in test_scope:
                import asyncio
                test_scope['asyncio'] = asyncio

            # ШАГ 9: Запускаем скрытые тесты
            exec(expected_output['tests'], test_scope)

            return {
                'is_correct': True,
                'details': {'status': 'MVCC тесты пройдены успешно'}
            }

        except AssertionError as e:
            return {
                'is_correct': False,
                'details': {'error': 'Логическая ошибка теста', 'msg': str(e)}
            }
        except SyntaxError as e:
            return {
                'is_correct': False,
                'details': {
                    'error': 'Синтаксическая ошибка в коде',
                    'msg': str(e),
                    'line': e.lineno
                }
            }
        except Exception as e:
            return {
                'is_correct': False,
                'details': {'error': 'Runtime Error', 'traceback': str(e)}
            }
