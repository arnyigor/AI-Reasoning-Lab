#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматической оптимизации настроек Ollama с интеграцией в .env файл
"""

import sys
from pathlib import Path


def estimate_model_layers(model_size_gb):
    """Оценка количества слоев в модели на основе размера"""
    if model_size_gb <= 1:
        return 12
    elif model_size_gb <= 4:
        return 24
    elif model_size_gb <= 8:
        return 32
    elif model_size_gb <= 16:
        return 40
    elif model_size_gb <= 32:
        return 48
    else:
        return 60


def calculate_context_overhead(context_size):
    """Расчет дополнительной памяти для контекста"""
    return (context_size / 1024) * 0.01


def optimize_ollama_config(model_size_gb, available_vram_gb, ram_gb=None):
    """Расширенная оптимизация конфигурации с учетом всех факторов"""
    total_layers = estimate_model_layers(model_size_gb)
    usable_vram = available_vram_gb - 2.0

    if usable_vram <= 0:
        usable_vram = available_vram_gb * 0.5

    # Полная загрузка в GPU
    if model_size_gb <= usable_vram * 0.75:
        context_size = 16384 if usable_vram > 10 else 8192
        context_overhead = calculate_context_overhead(context_size)

        if model_size_gb + context_overhead <= usable_vram:
            return {
                'gpu_layers': -1,
                'context_size': context_size,
                'strategy': 'full_gpu',
                'num_gpu': 1,
                'cpu_threads': 8,
                'keep_alive': '30m',
                'low_vram': False,
                'flash_attention': True,
                'numa': False,
                'parallel': 1,
                'max_loaded': 1
            }

    # Гибридная загрузка
    if model_size_gb <= usable_vram * 1.8:
        available_for_layers = usable_vram * 0.8
        layers_ratio = available_for_layers / model_size_gb
        gpu_layers = max(5, int(total_layers * layers_ratio))
        context_size = 8192 if usable_vram > 6 else 4096

        return {
            'gpu_layers': min(gpu_layers, total_layers - 2),
            'context_size': context_size,
            'strategy': 'hybrid',
            'num_gpu': 1,
            'cpu_threads': 12,
            'keep_alive': '15m',
            'low_vram': True,
            'flash_attention': False,
            'numa': True,
            'parallel': 1,
            'max_loaded': 1
        }

    # CPU-фокусированная загрузка
    gpu_layers = min(8, max(2, int(usable_vram / model_size_gb * total_layers)))
    context_size = 4096 if ram_gb and ram_gb >= 16 else 2048

    return {
        'gpu_layers': gpu_layers,
        'context_size': context_size,
        'strategy': 'cpu_focused',
        'num_gpu': 0,
        'cpu_threads': 16,
        'keep_alive': '5m',
        'low_vram': True,
        'flash_attention': False,
        'numa': True,
        'parallel': 1,
        'max_loaded': 1
    }


def find_env_file():
    """Поиск .env файла в текущей и родительских папках"""
    current_path = Path.cwd()

    # Ищем .env в текущей папке и родительских
    for path in [current_path] + list(current_path.parents):
        env_file = path / '.env'
        if env_file.exists():
            return env_file

    # Если не найден, создаем в текущей папке
    return current_path / '.env'


def read_env_file(env_path):
    """Читает .env файл и возвращает список строк"""
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    return []


def update_env_file(env_path, config):
    """Обновляет .env файл с новыми настройками Ollama"""
    lines = read_env_file(env_path)

    # Создаем карту настроек Ollama
    ollama_settings = {
        'OLLAMA_USE_PARAMS': 'true',
        'OLLAMA_GPU_LAYERS': str(config['gpu_layers']),
        'OLLAMA_CONTEXT_SIZE': str(config['context_size']),
        'OLLAMA_NUM_GPU': str(config['num_gpu']),
        'OLLAMA_CPU_THREADS': str(config['cpu_threads']),
        'OLLAMA_KEEP_ALIVE': config['keep_alive'],
        'OLLAMA_LOW_VRAM': str(config['low_vram']).lower(),
        'OLLAMA_FLASH_ATTENTION': str(config['flash_attention']).lower(),
        'OLLAMA_USE_NUMA': str(config['numa']).lower(),
        'OLLAMA_NUM_PARALLEL': str(config['parallel']),
        'OLLAMA_MAX_LOADED_MODELS': str(config['max_loaded'])
    }

    # Находим секцию Ollama или создаем её
    ollama_section_start = -1
    ollama_section_end = -1

    for i, line in enumerate(lines):
        if '=== ОПТИМИЗАЦИЯ OLLAMA ===' in line or 'OLLAMA_USE_PARAMS' in line:
            ollama_section_start = i
        if ollama_section_start != -1 and line.strip() == '' and i > ollama_section_start + 1:
            ollama_section_end = i
            break

    # Если секция найдена, обновляем её
    if ollama_section_start != -1:
        # Обновляем существующие переменные
        updated_vars = set()

        for i in range(ollama_section_start, len(lines)):
            line = lines[i].strip()
            if '=' in line and not line.startswith('#'):
                var_name = line.split('=')[0].strip()
                if var_name in ollama_settings:
                    lines[i] = f"{var_name}={ollama_settings[var_name]}\n"
                    updated_vars.add(var_name)

            # Прекращаем, если достигли конца секции
            if line == '' and i > ollama_section_start + 3:
                ollama_section_end = i
                break

        # Добавляем отсутствующие переменные
        missing_vars = set(ollama_settings.keys()) - updated_vars
        if missing_vars:
            insert_pos = ollama_section_end if ollama_section_end != -1 else len(lines)
            for var_name in missing_vars:
                lines.insert(insert_pos, f"{var_name}={ollama_settings[var_name]}\n")
                insert_pos += 1

    else:
        # Создаем новую секцию Ollama в конце файла
        if lines and not lines[-1].endswith('\n'):
            lines.append('\n')

        lines.append('\n')
        lines.append('# === АВТОМАТИЧЕСКИ СГЕНЕРИРОВАННЫЕ НАСТРОЙКИ OLLAMA ===\n')
        lines.append('OLLAMA_USE_PARAMS=true\n')

        for var_name, value in ollama_settings.items():
            if var_name != 'OLLAMA_USE_PARAMS':  # Уже добавлено выше
                lines.append(f"{var_name}={value}\n")

        lines.append('\n')

    # Записываем обновленный файл
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    return ollama_settings


def generate_detailed_config(model_size_gb, available_vram_gb, ram_gb=None, model_name="unknown"):
    """Генерирует детальную конфигурацию с рекомендациями"""
    config = optimize_ollama_config(model_size_gb, available_vram_gb, ram_gb)

    output = []
    output.append("=" * 70)
    output.append(f"ОПТИМАЛЬНАЯ КОНФИГУРАЦИЯ ДЛЯ МОДЕЛИ: {model_name}")
    output.append("=" * 70)
    output.append(f"Размер модели: {model_size_gb:.1f} ГБ")
    output.append(f"Доступная VRAM: {available_vram_gb:.1f} ГБ")
    if ram_gb:
        output.append(f"Доступная RAM: {ram_gb:.1f} ГБ")
    output.append("")

    # Основные параметры
    output.append("ОСНОВНЫЕ ПАРАМЕТРЫ:")
    output.append(f"├─ Стратегия загрузки: {config['strategy'].upper()}")
    output.append(f"├─ Слоев в GPU: {config['gpu_layers']}")
    output.append(f"├─ Размер контекста: {config['context_size']:,}")
    output.append(f"├─ Количество GPU: {config['num_gpu']}")
    output.append(f"├─ Потоков CPU: {config['cpu_threads']}")
    output.append(f"└─ Keep Alive: {config['keep_alive']}")
    output.append("")

    # ENV переменные, которые будут установлены
    output.append("ПЕРЕМЕННЫЕ .ENV (БУДУТ ОБНОВЛЕНЫ):")
    output.append("```")
    output.append("OLLAMA_USE_PARAMS=true")
    output.append(f"OLLAMA_GPU_LAYERS={config['gpu_layers']}")
    output.append(f"OLLAMA_CONTEXT_SIZE={config['context_size']}")
    output.append(f"OLLAMA_NUM_GPU={config['num_gpu']}")
    output.append(f"OLLAMA_CPU_THREADS={config['cpu_threads']}")
    output.append(f"OLLAMA_KEEP_ALIVE={config['keep_alive']}")
    output.append(f"OLLAMA_LOW_VRAM={str(config['low_vram']).lower()}")
    output.append(f"OLLAMA_FLASH_ATTENTION={str(config['flash_attention']).lower()}")
    output.append(f"OLLAMA_USE_NUMA={str(config['numa']).lower()}")
    output.append(f"OLLAMA_NUM_PARALLEL={config['parallel']}")
    output.append(f"OLLAMA_MAX_LOADED_MODELS={config['max_loaded']}")
    output.append("```")
    output.append("")

    # Рекомендации по производительности
    output.append("РЕКОМЕНДАЦИИ ПО ПРОИЗВОДИТЕЛЬНОСТИ:")

    if config['strategy'] == 'full_gpu':
        output.append("✅ Модель полностью помещается в VRAM - максимальная скорость")
        output.append("✅ Рекомендуется использовать большой контекст для сложных задач")
        output.append("⚠️  Следите за температурой GPU при длительной работе")
    elif config['strategy'] == 'hybrid':
        output.append("⚡ Гибридный режим - хороший баланс скорости и памяти")
        output.append("💡 Попробуйте увеличить gpu_layers, если есть свободная VRAM")
        output.append("💡 Рассмотрите возможность уменьшения контекста для ускорения")
    else:
        output.append("🐌 CPU-режим - медленно, но работает с большими моделями")
        output.append("💡 Убедитесь в наличии достаточного объема RAM")
        output.append("💡 Используйте SSD для swap, если RAM недостаточно")
        output.append("💡 Рассмотрите квантизацию модели (Q4_K_M, Q5_K_M)")

    output.append("")
    output.append("=" * 70)

    return "\n".join(output), config


def interactive_script():
    """Интерактивный скрипт для ввода параметров и обновления .env"""
    print("🔧 ОПТИМИЗАТОР НАСТРОЕК OLLAMA С ИНТЕГРАЦИЕЙ .ENV")
    print("=" * 55)

    try:
        # Ввод размера модели
        print("\n📏 Введите размер модели:")
        print("Примеры: 3.8 (для 4B модели), 7.2 (для 7B), 13.5 (для 13B)")
        model_size_input = input("Размер модели в ГБ: ").strip()
        model_size_gb = float(model_size_input)

        # Ввод видеопамяти
        print("\n🎮 Введите объем доступной видеопамяти:")
        print("Примеры: 8 (RTX 3070), 12 (RTX 4070 Ti), 24 (RTX 4090)")
        vram_input = input("Видеопамять в ГБ: ").strip()
        available_vram_gb = float(vram_input)

        # Опциональный ввод RAM
        print("\n💾 Введите объем RAM (опционально, Enter для пропуска):")
        ram_input = input("RAM в ГБ: ").strip()
        ram_gb = float(ram_input) if ram_input else None

        # Опциональное название модели
        print("\n🏷️  Введите название модели (опционально):")
        model_name = input("Название модели: ").strip()
        if not model_name:
            model_name = "unknown"

        # Генерация конфигурации
        print("\n⚙️  Генерация оптимальной конфигурации...")
        config_output, config = generate_detailed_config(model_size_gb, available_vram_gb, ram_gb, model_name)

        print("\n" + config_output)

        # Поиск .env файла
        env_file = find_env_file()
        print(f"\n📄 Найден .env файл: {env_file}")

        # Предложение обновить .env
        print(f"\n🔄 Обновить файл {env_file} с оптимальными настройками?")
        print("   Это изменит секцию OLLAMA в вашем .env файле")
        update_env = input("Обновить .env? (y/N): ").lower().strip().startswith('y')

        if update_env:
            try:
                updated_settings = update_env_file(env_file, config)
                print(f"\n✅ Файл {env_file} успешно обновлен!")
                print("\n📝 Обновленные переменные:")
                for key, value in updated_settings.items():
                    print(f"   {key}={value}")

                print(f"\n🚀 Теперь ваш OllamaClient будет использовать оптимизированные настройки!")
                print(f"💡 Перезапустите ваше приложение для применения изменений.")

            except Exception as e:
                print(f"❌ Ошибка при обновлении .env файла: {e}")
        else:
            print("⏭️  .env файл не изменен")

        # Сохранение отчета в файл
        print("\n💾 Сохранить отчет о конфигурации в файл? (y/N): ", end="")
        save_input = input().lower().strip()
        save_to_file = save_input.startswith('y')

        if save_to_file:
            safe_model_name = model_name.replace(':', '_').replace('/', '_').replace(' ', '_')
            filename = f"ollama_config_{safe_model_name}.txt"

            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(config_output)
                print(f"✅ Отчет сохранен в файл: {filename}")
            except Exception as e:
                print(f"❌ Ошибка сохранения файла: {e}")

    except ValueError as e:
        print(f"❌ Ошибка ввода: {e}")
        print("Пожалуйста, вводите числовые значения.")
        return False
    except KeyboardInterrupt:
        print("\n👋 Выход из программы.")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

    return True


def main():
    """Главная функция программы"""
    try:
        interactive_script()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
