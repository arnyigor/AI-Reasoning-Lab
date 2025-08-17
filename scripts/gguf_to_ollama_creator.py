import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

def create_ollama_model(
        gguf_path: str,
        model_name: Optional[str] = None,
        template: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        system_message: Optional[str] = None,
        auto_name_strategy: str = "smart"  # "simple", "smart", "folder"
) -> str:
    """
    Создает модель в Ollama из GGUF файла.

    Args:
        gguf_path: Путь к файлу .gguf
        model_name: Имя модели в Ollama (если None - определяется автоматически)
        template: Шаблон для промптов (опционально)
        parameters: Словарь параметров модели (temperature, top_p, etc.)
        system_message: Системное сообщение по умолчанию
        auto_name_strategy: Стратегия автоматического определения имени
                          - "simple": имя файла без расширения
                          - "smart": умное извлечение без квантизации
                          - "folder": имя папки модели

    Returns:
        Вывод команды ollama create
    """
    # Проверяем путь к GGUF файлу
    gguf_path_obj = Path(gguf_path).resolve()

    if not gguf_path_obj.exists():
        raise FileNotFoundError(f"Файл {gguf_path_obj} не найден")

    if gguf_path_obj.suffix.lower() != ".gguf":
        raise ValueError(f"Файл {gguf_path_obj} не является .gguf файлом")

    # Определяем имя модели автоматически
    if model_name is None:
        model_name = _extract_model_name_from_path(gguf_path_obj, auto_name_strategy)
        print(f"[INFO] Автоматически определено имя модели: '{model_name}'")

    # Проверяем доступность ollama
    try:
        subprocess.run(["ollama", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("Ollama не установлен или недоступен. Убедитесь, что ollama находится в PATH")

    print(f"[INFO] Создаем модель '{model_name}' из {gguf_path_obj}")

    # Создаем содержимое Modelfile
    modelfile_content = _create_modelfile_content(
        gguf_path_obj,
        template,
        parameters,
        system_message
    )

    # Создаем временный Modelfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='_Modelfile', delete=False) as f:
        f.write(modelfile_content)
        modelfile_path = f.name

    try:
        print(f"[INFO] Создан временный Modelfile: {modelfile_path}")
        print(f"[INFO] Содержимое Modelfile:\n{modelfile_content}")

        # Выполняем команду ollama create
        result = subprocess.run(
            ["ollama", "create", model_name, "-f", modelfile_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=300
        )

        print(f"[SUCCESS] Модель '{model_name}' успешно создана")
        if result.stdout.strip():
            print(f"[OUTPUT] {result.stdout}")

        return result.stdout

    except subprocess.TimeoutExpired:
        raise RuntimeError("Превышено время ожидания создания модели (5 минут)")
    except subprocess.CalledProcessError as e:
        error_msg = f"Ошибка при создании модели: {e.stderr}"
        print(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    finally:
        # Удаляем временный файл
        try:
            Path(modelfile_path).unlink()
            print(f"[INFO] Удален временный Modelfile: {modelfile_path}")
        except Exception as e:
            print(f"[WARNING] Не удалось удалить временный файл {modelfile_path}: {e}")

def _extract_model_name_from_path(gguf_path: Path, strategy: str = "smart") -> str:
    """
    Извлекает имя модели из пути к файлу.

    Args:
        gguf_path: Путь к GGUF файлу
        strategy: Стратегия извлечения имени

    Returns:
        Предложенное имя модели
    """
    if strategy == "simple":
        # Простое имя файла без расширения
        return gguf_path.stem

    elif strategy == "folder":
        # Имя папки с моделью (предпоследняя папка в пути)
        parts = gguf_path.parts
        if len(parts) >= 2:
            folder_name = parts[-2]  # предпоследняя папка
            # Убираем суффиксы типа "-GGUF", "-text-GGUF"
            clean_name = re.sub(r'-?(text-)?GGUF$', '', folder_name, flags=re.IGNORECASE)
            return clean_name.lower()
        else:
            return gguf_path.stem

    elif strategy == "smart":
        # Умное извлечение: убираем квантизацию и форматирование
        filename = gguf_path.stem

        # Паттерны для удаления квантизации (Q4_0, Q8_0, f16, etc.)
        quantization_patterns = [
            r'-?Q\d+(_[KM0])?$',  # Q4_0, Q8_0, Q4_K_M, etc.
            r'-?f16$',            # f16
            r'-?f32$',            # f32
            r'-?bf16$',           # bf16
            r'-?fp16$',           # fp16
            r'-?int8$',           # int8
            r'-?int4$',           # int4
        ]

        clean_name = filename
        for pattern in quantization_patterns:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)

        # Убираем лишние дефисы и приводим к нижнему регистру
        clean_name = re.sub(r'-+$', '', clean_name)  # убираем конечные дефисы
        clean_name = clean_name.lower()

        return clean_name if clean_name else filename.lower()

    else:
        # По умолчанию простая стратегия
        return gguf_path.stem

def _create_modelfile_content(
        gguf_path: Path,
        template: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        system_message: Optional[str] = None
) -> str:
    """
    Создает содержимое Modelfile.
    """
    content = f'FROM "{gguf_path}"\n\n'

    # Добавляем системное сообщение
    if system_message:
        content += f'SYSTEM """{system_message}"""\n\n'

    # Добавляем шаблон
    if template:
        content += f'TEMPLATE """{template}"""\n\n'

    # Добавляем параметры
    if parameters:
        for param, value in parameters.items():
            if isinstance(value, str):
                content += f'PARAMETER {param} "{value}"\n'
            else:
                content += f'PARAMETER {param} {value}\n'
        content += '\n'

    return content.strip()

def list_ollama_models() -> str:
    """Показывает список доступных моделей в Ollama."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при получении списка моделей: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Ollama не установлен или недоступен")

# ------------------------------
# Примеры использования
# ------------------------------
if __name__ == "__main__":
    # Читаем путь к GGUF файлу из переменной окружения
    gguf_file = os.getenv("GGUF_MODEL_PATH")

    if not gguf_file:
        raise ValueError("Путь к модели не найден. Убедитесь, что переменная GGUF_MODEL_PATH задана в .env файле.")

    # Демонстрация разных стратегий автоопределения имени
    path_obj = Path(gguf_file)

    print("Примеры автоматического определения имени:")
    print(f"📁 Путь: {gguf_file}")
    print(f"  • simple:  {_extract_model_name_from_path(path_obj, 'simple')}")
    print(f"  • smart:   {_extract_model_name_from_path(path_obj, 'smart')}")
    print(f"  • folder:  {_extract_model_name_from_path(path_obj, 'folder')}")
    print()

    model_parameters = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
    }

    try:
        # Вариант 1: Автоматическое имя со smart стратегией
        print("🚀 Создание модели с автоматическим именем (smart):")
        output = create_ollama_model(
            gguf_path=gguf_file,
            model_name=None,  # Автоматическое определение
            auto_name_strategy="smart",
            parameters=model_parameters,
            system_message="Ты полезный ИИ-ассистент."
        )

        print("\n" + "="*50)
        print("📋 Список моделей в Ollama:")
        print(list_ollama_models())

    except Exception as e:
        print(f"[ОШИБКА] {e}")

    # Другие примеры:

    # Вариант 2: Использовать имя папки
    # create_ollama_model(gguf_path=gguf_file, auto_name_strategy="folder")

    # Вариант 3: Простое имя файла
    # create_ollama_model(gguf_path=gguf_file, auto_name_strategy="simple")
