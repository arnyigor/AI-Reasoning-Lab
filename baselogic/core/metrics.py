"""
Улучшенная система метрик для BaseLogic.
Отслеживает производительность, точность и другие показатели.
"""

import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import json
from pathlib import Path

from .types import ModelMetrics, CategoryMetrics, PerformanceMetrics, TestResult


@dataclass
class MetricsCollector:
    """Сборщик метрик для отслеживания производительности"""
    
    model_name: str
    max_history_size: int = 1000
    
    # Метрики запросов
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Временные метрики
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    total_response_time: float = 0.0
    
    # Метрики тестов
    test_results: List[TestResult] = field(default_factory=list)
    category_metrics: Dict[str, CategoryMetrics] = field(default_factory=dict)
    
    # Метрики ошибок
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Метрики производительности
    start_time: Optional[datetime] = None
    last_request_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Инициализация после создания объекта"""
        self.start_time = datetime.now()
    
    def record_request(self, response_time: float, success: bool, error_type: Optional[str] = None) -> None:
        """Записывает метрики запроса"""
        self.total_requests += 1
        self.last_request_time = datetime.now()
        
        if success:
            self.successful_requests += 1
            self.response_times.append(response_time)
            self.total_response_time += response_time
        else:
            self.failed_requests += 1
            if error_type:
                self.error_counts[error_type] += 1
                self.error_history.append({
                    'timestamp': datetime.now(),
                    'error_type': error_type,
                    'response_time': response_time
                })
    
    def record_test_result(self, test_result: TestResult) -> None:
        """Записывает результат теста"""
        self.test_results.append(test_result)

        # Обновляем метрики по категориям
        category = test_result['category']
        if category not in self.category_metrics:
            self.category_metrics[category] = {
                'tests': 0,
                'correct': 0,
                'accuracy': 0.0,
                'avg_time_ms': 0.0
            }

        cat_metrics = self.category_metrics[category]
        cat_metrics['tests'] += 1
        if test_result['is_correct']:
            cat_metrics['correct'] += 1

        # Пересчитываем средние значения
        cat_metrics['accuracy'] = cat_metrics['correct'] / cat_metrics['tests']

        # Обновляем среднее время для категории
        category_times = [r['execution_time_ms'] for r in self.test_results if r['category'] == category]
        cat_metrics['avg_time_ms'] = statistics.mean(category_times) if category_times else 0.0

        # Обрабатываем специфические метрики для новых типов тестов
        self._update_extended_metrics(test_result, cat_metrics)

    def _is_extended_test_category(self, category: str) -> bool:
        """Определяет, является ли категория тестом с расширенными метриками"""
        extended_categories = [
            't15_multi_hop_reasoning',
            't16_counterfactual_reasoning',
            't17_proof_verification',
            't18_constrained_optimization'
        ]
        return category in extended_categories

    def _update_extended_metrics(self, test_result: TestResult, cat_metrics: Dict[str, Any]) -> None:
        """Обновляет расширенные метрики для специфических типов тестов (автоматически для новых категорий)"""
        # Проверяем, является ли тест категорией с расширенными метриками
        if not self._is_extended_test_category(test_result['category']):
            return

        verification_details = test_result.get('verification_details', {})

        # Обработка метрик для multi-hop reasoning
        if test_result['category'] == 't15_multi_hop_reasoning':
            chain_length = verification_details.get('chain_length', 0)
            if 'chain_length_avg' not in cat_metrics:
                cat_metrics['chain_length_avg'] = []
            cat_metrics['chain_length_avg'].append(chain_length)
            cat_metrics['chain_length_avg'] = statistics.mean(cat_metrics['chain_length_avg'])

            # Chain retention score
            coverage = verification_details.get('chain_completeness', 0.0)
            if 'chain_retention_score' not in cat_metrics:
                cat_metrics['chain_retention_score'] = []
            cat_metrics['chain_retention_score'].append(coverage)
            cat_metrics['chain_retention_score'] = statistics.mean(cat_metrics['chain_retention_score'])

        # Обработка метрик для proof verification
        elif test_result['category'] == 't17_proof_verification':
            if 'proof_verification_accuracy' not in cat_metrics:
                cat_metrics['proof_verification_accuracy'] = cat_metrics['accuracy']

        # Обработка метрик для counterfactual reasoning
        elif test_result['category'] == 't16_counterfactual_reasoning':
            depth_score = verification_details.get('total_score', 0.0)
            if 'counterfactual_depth_score' not in cat_metrics:
                cat_metrics['counterfactual_depth_score'] = []
            cat_metrics['counterfactual_depth_score'].append(depth_score)
            cat_metrics['counterfactual_depth_score'] = statistics.mean(cat_metrics['counterfactual_depth_score'])

        # Обработка метрик для constrained optimization
        elif test_result['category'] == 't18_constrained_optimization':
            constraint_score = verification_details.get('total_score', 0.0)
            if 'constraint_awareness_score' not in cat_metrics:
                cat_metrics['constraint_awareness_score'] = []
            cat_metrics['constraint_awareness_score'].append(constraint_score)
            cat_metrics['constraint_awareness_score'] = statistics.mean(cat_metrics['constraint_awareness_score'])
    
    def get_overall_metrics(self) -> ModelMetrics:
        """Возвращает общие метрики модели"""
        avg_time = statistics.mean(self.response_times) if self.response_times else 0.0
        min_time = min(self.response_times) if self.response_times else 0.0
        max_time = max(self.response_times) if self.response_times else 0.0
        
        return {
            'accuracy': self.get_overall_accuracy(),
            'avg_time_ms': avg_time * 1000,  # Конвертируем в миллисекунды
            'min_time_ms': min_time * 1000,
            'max_time_ms': max_time * 1000,
            'runs_count': len(set(r['test_id'].split('_')[0] for r in self.test_results)),
            'total_tests': len(self.test_results)
        }
    
    def get_overall_accuracy(self) -> float:
        """Возвращает общую точность"""
        if not self.test_results:
            return 0.0
        correct = sum(1 for r in self.test_results if r['is_correct'])
        return correct / len(self.test_results)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Возвращает метрики производительности"""
        return PerformanceMetrics(
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            avg_response_time=statistics.mean(self.response_times) if self.response_times else 0.0,
            min_response_time=min(self.response_times) if self.response_times else 0.0,
            max_response_time=max(self.response_times) if self.response_times else 0.0,
            total_data_processed=sum(len(r['prompt']) + len(r['llm_response']) for r in self.test_results)
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Возвращает сводку ошибок"""
        return {
            'total_errors': self.failed_requests,
            'error_types': dict(self.error_counts),
            'recent_errors': list(self.error_history)[-10:],  # Последние 10 ошибок
            'error_rate': (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0.0
        }
    
    def get_uptime(self) -> timedelta:
        """Возвращает время работы"""
        if not self.start_time:
            return timedelta(0)
        return datetime.now() - self.start_time
    
    def get_requests_per_minute(self) -> float:
        """Возвращает количество запросов в минуту"""
        uptime = self.get_uptime()
        if uptime.total_seconds() == 0:
            return 0.0
        return (self.total_requests / uptime.total_seconds()) * 60
    
    def export_metrics(self, file_path: Path) -> bool:
        """Экспортирует метрики в JSON файл (включая расширенные метрики для новых тестов)"""
        try:
            # Собираем расширенные метрики для новых категорий тестов
            extended_category_metrics = {}
            for category, metrics in self.category_metrics.items():
                if self._is_extended_test_category(category):
                    extended_category_metrics[category] = dict(metrics)  # Копируем все метрики
                else:
                    extended_category_metrics[category] = {
                        k: v for k, v in metrics.items()
                        if k in ['tests', 'correct', 'accuracy', 'avg_time_ms']  # Только базовые метрики
                    }

            export_data = {
                'model_name': self.model_name,
                'export_timestamp': datetime.now().isoformat(),
                'overall_metrics': self.get_overall_metrics(),
                'performance_metrics': self.get_performance_metrics().__dict__,
                'category_metrics': extended_category_metrics,  # Используем расширенные метрики
                'error_summary': self.get_error_summary(),
                'uptime_seconds': self.get_uptime().total_seconds(),
                'requests_per_minute': self.get_requests_per_minute(),
                'test_results_count': len(self.test_results),
                'has_extended_metrics': bool(extended_category_metrics)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            return True
        except Exception as e:
            print(f"Ошибка экспорта метрик: {e}")
            return False
    
    def reset(self) -> None:
        """Сбрасывает все метрики"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times.clear()
        self.total_response_time = 0.0
        self.test_results.clear()
        self.category_metrics.clear()
        self.error_counts.clear()
        self.error_history.clear()
        self.start_time = datetime.now()
        self.last_request_time = None


class MetricsManager:
    """Менеджер метрик для управления метриками всех моделей"""
    
    def __init__(self):
        self.collectors: Dict[str, MetricsCollector] = {}
        self.global_metrics: Dict[str, Any] = defaultdict(int)
    
    def get_collector(self, model_name: str) -> MetricsCollector:
        """Получает или создает сборщик метрик для модели"""
        if model_name not in self.collectors:
            self.collectors[model_name] = MetricsCollector(model_name)
        return self.collectors[model_name]
    
    def record_request(self, model_name: str, response_time: float, success: bool, error_type: Optional[str] = None) -> None:
        """Записывает метрики запроса"""
        collector = self.get_collector(model_name)
        collector.record_request(response_time, success, error_type)
        
        # Обновляем глобальные метрики
        self.global_metrics['total_requests'] += 1
        if success:
            self.global_metrics['successful_requests'] += 1
        else:
            self.global_metrics['failed_requests'] += 1
    
    def record_test_result(self, model_name: str, test_result: TestResult) -> None:
        """Записывает результат теста"""
        collector = self.get_collector(model_name)
        collector.record_test_result(test_result)
        
        # Обновляем глобальные метрики
        self.global_metrics['total_tests'] += 1
        if test_result['is_correct']:
            self.global_metrics['correct_tests'] += 1
    
    def get_model_metrics(self, model_name: str) -> Optional[ModelMetrics]:
        """Возвращает метрики конкретной модели"""
        if model_name not in self.collectors:
            return None
        return self.collectors[model_name].get_overall_metrics()
    
    def get_all_models_metrics(self) -> Dict[str, ModelMetrics]:
        """Возвращает метрики всех моделей"""
        return {name: collector.get_overall_metrics() 
                for name, collector in self.collectors.items()}
    
    def get_global_summary(self) -> Dict[str, Any]:
        """Возвращает глобальную сводку"""
        total_models = len(self.collectors)
        total_accuracy = 0.0
        total_avg_time = 0.0
        
        for collector in self.collectors.values():
            metrics = collector.get_overall_metrics()
            total_accuracy += metrics['accuracy']
            total_avg_time += metrics['avg_time_ms']
        
        return {
            'total_models': total_models,
            'total_requests': self.global_metrics['total_requests'],
            'total_tests': self.global_metrics['total_tests'],
            'overall_accuracy': total_accuracy / total_models if total_models > 0 else 0.0,
            'average_response_time_ms': total_avg_time / total_models if total_models > 0 else 0.0,
            'success_rate': (self.global_metrics['successful_requests'] / self.global_metrics['total_requests'] * 100) 
                           if self.global_metrics['total_requests'] > 0 else 0.0
        }
    
    def export_all_metrics(self, directory: Path) -> bool:
        """Экспортирует метрики всех моделей"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            
            # Экспортируем метрики каждой модели
            for model_name, collector in self.collectors.items():
                safe_name = model_name.replace(':', '_').replace('/', '_')
                file_path = directory / f"{safe_name}_metrics.json"
                collector.export_metrics(file_path)
            
            # Экспортируем глобальную сводку
            global_summary = self.get_global_summary()
            global_summary['export_timestamp'] = datetime.now().isoformat()
            
            with open(directory / "global_metrics.json", 'w', encoding='utf-8') as f:
                json.dump(global_summary, f, ensure_ascii=False, indent=2, default=str)
            
            return True
        except Exception as e:
            print(f"Ошибка экспорта всех метрик: {e}")
            return False
    
    def reset_all(self) -> None:
        """Сбрасывает все метрики"""
        for collector in self.collectors.values():
            collector.reset()
        self.global_metrics.clear()


# Глобальный экземпляр менеджера метрик
_metrics_manager: Optional[MetricsManager] = None


def get_metrics_manager() -> MetricsManager:
    """Получает глобальный менеджер метрик"""
    global _metrics_manager
    if _metrics_manager is None:
        _metrics_manager = MetricsManager()
    return _metrics_manager


def record_request_metrics(model_name: str, response_time: float, success: bool, error_type: Optional[str] = None) -> None:
    """Записывает метрики запроса"""
    manager = get_metrics_manager()
    manager.record_request(model_name, response_time, success, error_type)


def record_test_metrics(model_name: str, test_result: TestResult) -> None:
    """Записывает метрики теста"""
    manager = get_metrics_manager()
    manager.record_test_result(model_name, test_result)


def get_model_metrics_summary(model_name: str) -> Optional[Dict[str, Any]]:
    """Возвращает сводку метрик модели"""
    manager = get_metrics_manager()
    collector = manager.get_collector(model_name)
    
    if not collector.test_results:
        return None
    
    return {
        'model_name': model_name,
        'overall_metrics': collector.get_overall_metrics(),
        'performance_metrics': collector.get_performance_metrics().__dict__,
        'category_metrics': collector.category_metrics,
        'error_summary': collector.get_error_summary(),
        'uptime': str(collector.get_uptime()),
        'requests_per_minute': collector.get_requests_per_minute()
    }
