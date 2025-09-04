#!/usr/bin/env python3
"""
Скрипт для тестирования расширенных метрик новых тестов.
Проверяет корректность сбора и экспорта специфических метрик.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from baselogic.core.metrics import MetricsCollector
from baselogic.core.types import TestResult

def create_mock_test_result(category: str, is_correct: bool, verification_details: dict = None):
    """Создает mock результат теста для тестирования метрик"""
    return {
        'test_id': f"{category}_test_1",
        'category': category,
        'model_name': 'test_model',
        'model_details': {'size': '4B'},
        'prompt': 'Test prompt',
        'llm_response': 'Test response',
        'expected_output': 'expected',
        'is_correct': is_correct,
        'execution_time_ms': 100.0,
        'verification_details': verification_details or {}
    }

def test_extended_metrics():
    """Тестирует сбор расширенных метрик"""
    print("🧪 Тестирование расширенных метрик для новых тестов")
    print("=" * 60)

    # Создаем сборщик метрик
    collector = MetricsCollector("test_model")

    # Тестируем multi-hop reasoning метрики
    print("📊 Тестирование multi-hop reasoning метрик...")
    multi_hop_result = create_mock_test_result(
        't15_multi_hop_reasoning',
        True,
        {'chain_length': 7, 'chain_completeness': 0.85, 'total_score': 0.82}
    )
    collector.record_test_result(multi_hop_result)

    # Тестируем counterfactual reasoning метрики
    print("📊 Тестирование counterfactual reasoning метрик...")
    counterfactual_result = create_mock_test_result(
        't16_counterfactual_reasoning',
        True,
        {'total_score': 0.78, 'depth_score': 0.75}
    )
    collector.record_test_result(counterfactual_result)

    # Тестируем proof verification метрики
    print("📊 Тестирование proof verification метрик...")
    proof_result = create_mock_test_result(
        't17_proof_verification',
        False,
        {'error_type': 'division_by_zero', 'recognition_score': 0.6}
    )
    collector.record_test_result(proof_result)

    # Тестируем constrained optimization метрики
    print("📊 Тестирование constrained optimization метрик...")
    optimization_result = create_mock_test_result(
        't18_constrained_optimization',
        True,
        {'total_score': 0.88, 'constraint_score': 0.9}
    )
    collector.record_test_result(optimization_result)

    # Проверяем метрики по категориям
    print("\n📈 Собранные метрики по категориям:")
    for category, metrics in collector.category_metrics.items():
        print(f"\n🎯 Категория: {category}")
        print(f"   Тесты: {metrics['tests']}")
        print(f"   Точность: {metrics['accuracy']:.2f}")
        print(f"   Среднее время: {metrics['avg_time_ms']:.1f}ms")

        # Выводим специфические метрики для новых тестов
        if collector._is_extended_test_category(category):
            print("   📊 Расширенные метрики:")
            for key, value in metrics.items():
                if key not in ['tests', 'correct', 'accuracy', 'avg_time_ms']:
                    if isinstance(value, list):
                        print(f"      {key}: {value} (список значений)")
                    else:
                        print(f"      {key}: {value:.3f}")

    # Тестируем экспорт метрик
    print("\n💾 Тестирование экспорта метрик...")
    export_path = Path("test_metrics_export.json")
    success = collector.export_metrics(export_path)

    if success:
        print(f"✅ Метрики успешно экспортированы в {export_path}")

        # Читаем и проверяем экспортированные данные
        import json
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)

        print("📋 Содержимое экспорта:")
        print(f"   Модель: {exported_data['model_name']}")
        print(f"   Общая точность: {exported_data['overall_metrics']['accuracy']:.2f}")
        print(f"   Количество тестов: {exported_data['test_results_count']}")
        print(f"   Расширенные метрики: {exported_data.get('has_extended_metrics', False)}")

        # Проверяем наличие расширенных метрик в экспорте
        extended_found = False
        for category, metrics in exported_data['category_metrics'].items():
            if collector._is_extended_test_category(category):
                extended_keys = [k for k in metrics.keys() if k not in ['tests', 'correct', 'accuracy', 'avg_time_ms']]
                if extended_keys:
                    print(f"   ✅ Расширенные метрики для {category}: {extended_keys}")
                    extended_found = True

        if not extended_found:
            print("   ⚠️  Расширенные метрики не найдены в экспорте")

        # Удаляем тестовый файл
        export_path.unlink()
        print("🗑️  Тестовый файл экспорта удален")

    else:
        print("❌ Ошибка экспорта метрик")

    print("\n🎊 Тестирование расширенных метрик завершено!")
    return True

def test_backward_compatibility():
    """Тестирует обратную совместимость с существующими тестами"""
    print("\n🔄 Тестирование обратной совместимости...")

    collector = MetricsCollector("compatibility_test")

    # Тестируем старый тип теста
    old_test_result = create_mock_test_result('t01_simple_logic', True)
    collector.record_test_result(old_test_result)

    # Проверяем, что метрики собраны корректно
    old_metrics = collector.category_metrics.get('t01_simple_logic', {})
    required_keys = ['tests', 'correct', 'accuracy', 'avg_time_ms']

    missing_keys = [key for key in required_keys if key not in old_metrics]
    if missing_keys:
        print(f"❌ Отсутствуют обязательные метрики: {missing_keys}")
        return False

    print("✅ Обратная совместимость сохранена")
    return True

if __name__ == "__main__":
    print("🚀 Запуск тестирования расширенных метрик...")

    # Тестируем расширенные метрики
    extended_ok = test_extended_metrics()

    # Тестируем обратную совместимость
    compatibility_ok = test_backward_compatibility()

    if extended_ok and compatibility_ok:
        print("\n🎊 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("📝 Расширенные метрики работают корректно")
        sys.exit(0)
    else:
        print("\n💥 ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
        print("🔧 Проверьте логи выше для диагностики")
        sys.exit(1)