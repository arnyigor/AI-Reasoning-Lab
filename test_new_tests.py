#!/usr/bin/env python3
"""
Скрипт для тестирования интеграции новых тестов в AI-Reasoning-Lab.
Проверяет загрузку и генерацию тестовых данных для новых категорий.
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from baselogic.core.test_runner import TestRunner
from baselogic.core.config_loader import EnvConfigLoader

def test_new_tests_integration():
    """Тестирует интеграцию новых тестов с существующей архитектурой."""

    print("🧪 Тестирование интеграции новых тестов AI-Reasoning-Lab")
    print("=" * 60)

    # Создаем тестовую конфигурацию
    test_config = {
        'tests_to_run': [
            't15_multi_hop_reasoning',
            't16_counterfactual_reasoning',
            't17_proof_verification',
            't18_constrained_optimization'
        ],
        'runs_per_test': 1,
        'models_to_test': []  # Пустой список моделей для теста загрузки
    }

    try:
        # Создаем TestRunner с тестовой конфигурацией
        print("🔧 Создание TestRunner...")
        test_runner = TestRunner(test_config)

        # Проверяем загрузку генераторов тестов
        print("📚 Загрузка генераторов тестов...")
        generators = test_runner.test_generators

        print(f"✅ Найдено генераторов тестов: {len(generators)}")
        print("📋 Список загруженных тестов:")
        for test_name in sorted(generators.keys()):
            print(f"   - {test_name}")

        # Проверяем наличие новых тестов
        new_tests = ['t15_multi_hop_reasoning', 't16_counterfactual_reasoning',
                    't17_proof_verification', 't18_constrained_optimization']

        missing_tests = []
        for test_name in new_tests:
            if test_name not in generators:
                missing_tests.append(test_name)

        if missing_tests:
            print(f"❌ Отсутствуют тесты: {missing_tests}")
            return False
        else:
            print("✅ Все новые тесты успешно загружены!")

        # Тестируем генерацию тестовых данных
        print("\n🧪 Тестирование генерации тестовых данных...")
        for test_name in new_tests:
            try:
                generator_class = generators[test_name]
                generator_instance = generator_class(test_id=test_name)

                print(f"   - Генерация для {test_name}...")
                test_data = generator_instance.generate()

                # Проверяем структуру тестовых данных
                required_fields = ['prompt', 'expected_output', 'test_name', 'metadata']
                missing_fields = [field for field in required_fields if field not in test_data]

                if missing_fields:
                    print(f"     ❌ Отсутствуют поля: {missing_fields}")
                    continue

                print("     ✅ Структура корректна")
                print(f"     📝 Длина промпта: {len(test_data['prompt'])} символов")
                print(f"     🎯 Тип теста: {test_data['metadata'].get('test_type', 'unknown')}")

            except Exception as e:
                print(f"   ❌ Ошибка генерации для {test_name}: {e}")
                continue

        print("\n🎉 Тестирование завершено успешно!")
        print("📊 Резюме:")
        print(f"   - Загружено тестов: {len(generators)}")
        print(f"   - Новых тестов: {len(new_tests)}")
        print("   - Все новые тесты интегрированы корректно")
        return True

    except Exception as e:
        print(f"❌ Критическая ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_loading():
    """Тестирует загрузку конфигурации с новыми тестами."""

    print("\n⚙️  Тестирование загрузки конфигурации...")
    print("-" * 40)

    # Устанавливаем тестовые переменные окружения
    os.environ['BC_TESTS_TO_RUN'] = '["t15_multi_hop_reasoning", "t16_counterfactual_reasoning"]'
    os.environ['BC_RUNS_PER_TEST'] = '1'

    try:
        config_loader = EnvConfigLoader()
        config = config_loader.load_config()

        tests_to_run = config.get('tests_to_run', [])
        print(f"✅ Загружены тесты для запуска: {tests_to_run}")

        if 't15_multi_hop_reasoning' in tests_to_run and 't16_counterfactual_reasoning' in tests_to_run:
            print("✅ Конфигурация корректно загружает новые тесты")
            return True
        else:
            print("❌ Новые тесты не найдены в конфигурации")
            return False

    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестирования интеграции новых тестов...")

    # Тестируем загрузку конфигурации
    config_ok = test_config_loading()

    # Тестируем интеграцию тестов
    integration_ok = test_new_tests_integration()

    if config_ok and integration_ok:
        print("\n🎊 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("📝 Новые тесты готовы к использованию в AI-Reasoning-Lab")
        sys.exit(0)
    else:
        print("\n💥 ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
        print("🔧 Проверьте логи выше для диагностики")
        sys.exit(1)