# debug_sandbox_v2.py
import builtins

code_with_class = "class MyTestClass: pass"

print("--- Запуск с исправленными builtins, но без __name__ (ожидаем ошибку) ---")
try:
    faulty_scope = {
        "__builtins__": {
            'print': print,
            '__build_class__': builtins.__build_class__
        }
    }
    exec(code_with_class, faulty_scope)
except NameError as e:
    print(f"ПОЙМАНА ОШИБКА: {e}\n") # Все еще ловим ошибку __name__

print("--- Запуск с исправленным global_scope (ожидаем успех) ---")
try:
    # Создаем полный scope, который имитирует запуск реального скрипта
    correct_scope = {
        "__builtins__": {
            'print': print,
            '__build_class__': builtins.__build_class__
        },
        "__name__": "__main__"  # <--- КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ
    }
    exec(code_with_class, correct_scope)
    print("УСПЕХ: Класс успешно создан.\n")
except Exception as e:
    print(f"НЕОЖИДАННАЯ ОШИБКА: {e}")