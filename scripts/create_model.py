# scripts/create_model.py

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse, unquote  # ▸ добавьте в начало файла
import requests
from dotenv import load_dotenv
from tqdm import tqdm

# Загружаем переменные окружения из .env файла
load_dotenv()


# --- НОВАЯ ФУНКЦИЯ: Скачивание файла с прогресс-баром ---
def download_file_with_progress(url: str, dest_path: Path):
    """Скачивает файл с URL в dest_path с отображением прогресса."""
    try:
        print(f"[INFO] Запрос на скачивание: {url}")
        with requests.get(url, stream=True, timeout=10) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))

            with open(dest_path, 'wb') as f, tqdm(
                    desc=dest_path.name,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    size = f.write(chunk)
                    bar.update(size)
        print(f"\n[SUCCESS] Файл успешно скачан: {dest_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Ошибка скачивания {url}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


# --- Основная функция, улучшенная ---
def create_ollama_model(
        gguf_source: str, # Может быть URL или локальный путь
        model_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        system_message: Optional[str] = None,
        template: Optional[str] = None,
        auto_name_strategy: str = "smart"
) -> str:
    """
    Создает модель в Ollama из GGUF файла (локального или по URL).
    """
    gguf_path_obj = None

    # --- ИЗМЕНЕНИЕ: Обработка URL и локального пути ---
    if gguf_source.startswith(("http://", "https://")):
        print(f"[INFO] Обнаружен URL: {gguf_source}")

        # 1. Извлекаем «чистое» имя файла (без ?download=… и без %20)
        parsed       = urlparse(gguf_source)
        gguf_filename = Path(unquote(parsed.path)).name          # → Qwen3-4B-…Q4_K_M.gguf
        if not gguf_filename.lower().endswith(".gguf"):
            gguf_filename += ".gguf"                            # подстраховка, чтобы было .gguf

        # 2. Кладём всё в каталог ./models
        models_dir = Path.cwd() / "models"
        models_dir.mkdir(exist_ok=True)
        local_gguf_path = models_dir / gguf_filename

        # 3. Скачиваем только если файла ещё нет
        if local_gguf_path.exists():
            print(f"[INFO] Файл '{local_gguf_path.name}' уже существует – пропускаю скачивание.")
        else:
            if not download_file_with_progress(gguf_source, local_gguf_path):
                raise RuntimeError(f"Не удалось скачать файл {gguf_source}")

        gguf_path_obj = local_gguf_path
        # ───────────────────────────────────────────────────────────────────

    if gguf_path_obj.suffix.lower() != ".gguf":
        raise ValueError(f"Файл {gguf_path_obj} не является .gguf файлом")

    # ... (Ваш код _extract_model_name_from_path и проверка ollama остаются без изменений) ...
    # Я их скопирую для полноты.

    if model_name is None:
        model_name = _extract_model_name_from_path(gguf_path_obj, auto_name_strategy)
        print(f"[INFO] Автоматически определено имя модели: '{model_name}'")

    try:
        subprocess.run(["ollama", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("Ollama не установлен или недоступен.")

    print(f"[INFO] Создаем модель '{model_name}' из {gguf_path_obj}")

    modelfile_content = _create_modelfile_content(
        gguf_path_obj,
        template,
        parameters,
        system_message
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='_Modelfile', delete=False) as f:
        f.write(modelfile_content)
        modelfile_path = f.name

    try:
        print(f"[INFO] Создан временный Modelfile: {modelfile_path}")
        print(f"[INFO] Содержимое Modelfile:\n---\n{modelfile_content}\n---")

        result = subprocess.run(
            ["ollama", "create", model_name, "-f", modelfile_path],
            check=True,
            capture_output=True,
            text=True,
            timeout=600 # Увеличено до 10 минут для больших моделей
        )
        print(f"[SUCCESS] Модель '{model_name}' успешно создана")
        if result.stdout.strip():
            print(f"[OUTPUT] {result.stdout}")
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError("Превышено время ожидания создания модели (10 минут)")
    except subprocess.CalledProcessError as e:
        error_msg = f"Ошибка при создании модели: {e.stderr}"
        print(f"[ERROR] {error_msg}")
        raise RuntimeError(error_msg)
    finally:
        try:
            Path(modelfile_path).unlink()
            print(f"[INFO] Удален временный Modelfile: {modelfile_path}")
        except Exception as e:
            print(f"[WARNING] Не удалось удалить временный файл {modelfile_path}: {e}")

# --- Ваши существующие функции _extract_model_name_from_path и _create_modelfile_content ---
# (Я их не меняю, просто вставляю для полноты)
def _extract_model_name_from_path(gguf_path: Path, strategy: str = "smart") -> str:
    # ... (ваш код без изменений) ...
    if strategy == "simple":
        return gguf_path.stem
    elif strategy == "smart":
        filename = gguf_path.stem
        quant_patterns = [r'-?Q\d+_[KM0LS]?$', r'-?[fbi]\d+$']
        clean_name = filename
        for p in quant_patterns: clean_name = re.sub(p, '', clean_name, flags=re.I)
        return re.sub(r'-+$', '', clean_name).lower() or filename.lower()
    return gguf_path.stem

def _create_modelfile_content(gguf_path: Path, template: Optional[str], parameters: Optional[Dict[str, Any]], system_message: Optional[str]) -> str:
    # --- ИЗМЕНЕНИЕ: Путь в кавычках для совместимости с пробелами ---
    content = f'FROM "{gguf_path.resolve()}"\n\n'
    if system_message: content += f'SYSTEM """{system_message}"""\n\n'
    if template: content += f'TEMPLATE """{template}"""\n\n'
    if parameters:
        for param, value in parameters.items():
            content += f'PARAMETER {param} {value}\n' # Ollama сама разберет типы
        content += '\n'
    return content.strip()

# --- НОВЫЙ БЛОК: Логика для запуска из .env ---
def prepare_models_from_env():
    """
    Запускает процесс подготовки для всех моделей,
    сконфигурированных в .env файле.
    """
    print("--- Запуск подготовки моделей из .env файла ---")
    i = 0
    configs_found = 0
    while True:
        prefix = f"PREPARE_MODEL_{i}_"
        if f"{prefix}ENABLED" not in os.environ:
            break

        is_enabled = os.getenv(f"{prefix}ENABLED", "false").lower() == 'true'
        if is_enabled:
            configs_found += 1
            print("\n" + "="*60)
            print(f"⚙️ Обработка конфигурации PREPARE_MODEL_{i}")

            gguf_source = os.getenv(f"{prefix}GGUF_URL") # Может быть URL или путь
            model_name = os.getenv(f"{prefix}NAME")
            system_prompt = os.getenv(f"{prefix}SYSTEM_PROMPT") # Поддержка нового имени

            if not gguf_source or not model_name:
                print(f"[ERROR] Для PREPARE_MODEL_{i} должны быть указаны NAME и GGUF_URL. Пропуск.")
                i += 1
                continue

            params = {}
            for key, value in os.environ.items():
                if key.startswith(f"{prefix}PARAMS_"):
                    param_key = key.replace(f"{prefix}PARAMS_", "").lower()
                    params[param_key] = value

            try:
                create_ollama_model(
                    gguf_source=gguf_source,
                    model_name=model_name,
                    parameters=params,
                    system_message=system_prompt
                )
            except Exception as e:
                print(f"[FATAL ERROR] Не удалось обработать PREPARE_MODEL_{i}: {e}")

        i += 1

    if configs_found == 0:
        print("Не найдено включенных моделей для подготовки (PREPARE_MODEL_*_ENABLED=\"true\").")

    print("\n" + "="*60)
    print("--- Подготовка моделей завершена ---")


if __name__ == "__main__":
    prepare_models_from_env()
