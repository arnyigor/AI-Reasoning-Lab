from typing import List, Dict, Any, Optional
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from app.models.test import TestResult
from app.models.session import Session

class AnalyticsService:
    def __init__(self):
        self.results_dir = Path("results")
        self.export_dir = Path("web/backend/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def get_leaderboard(self, limit: int = 20, timeframe_days: int = 30) -> List[Dict[str, Any]]:
        """Получение таблицы лидеров моделей"""
        all_results = self._load_all_results(timeframe_days)

        model_stats = {}
        for result in all_results:
            model_name = result.get("model_name", "unknown")
            if model_name not in model_stats:
                model_stats[model_name] = {
                    "model_name": model_name,
                    "total_tests": 0,
                    "successful_tests": 0,
                    "total_accuracy": 0,
                    "total_execution_time": 0,
                    "test_count": 0
                }

            stats = model_stats[model_name]
            stats["total_tests"] += 1
            if result.get("success", False):
                stats["successful_tests"] += 1
            if result.get("accuracy") is not None:
                stats["total_accuracy"] += result["accuracy"]
                stats["test_count"] += 1
            if result.get("execution_time") is not None:
                stats["total_execution_time"] += result["execution_time"]

        # Вычисление итоговых метрик
        leaderboard = []
        for model_name, stats in model_stats.items():
            if stats["test_count"] > 0:
                avg_accuracy = stats["total_accuracy"] / stats["test_count"]
            else:
                avg_accuracy = 0

            success_rate = (stats["successful_tests"] / stats["total_tests"]) * 100 if stats["total_tests"] > 0 else 0
            avg_execution_time = stats["total_execution_time"] / stats["total_tests"] if stats["total_tests"] > 0 else 0

            leaderboard.append({
                "model_name": model_name,
                "total_tests": stats["total_tests"],
                "success_rate": round(success_rate, 2),
                "average_accuracy": round(avg_accuracy, 4),
                "average_execution_time": round(avg_execution_time, 2),
                "score": round(avg_accuracy * success_rate / 100, 4)  # Композитный скор
            })

        # Сортировка по композитному скору
        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        return leaderboard[:limit]

    def compare_models(self, model_names: List[str], timeframe_days: int = 30) -> Dict[str, Any]:
        """Сравнение нескольких моделей"""
        all_results = self._load_all_results(timeframe_days)

        comparison = {}
        for model_name in model_names:
            model_results = [r for r in all_results if r.get("model_name") == model_name]

            if not model_results:
                comparison[model_name] = {
                    "total_tests": 0,
                    "success_rate": 0,
                    "average_accuracy": 0,
                    "average_execution_time": 0,
                    "best_accuracy": 0,
                    "worst_accuracy": 0
                }
                continue

            accuracies = [r.get("accuracy", 0) for r in model_results if r.get("accuracy") is not None]
            execution_times = [r.get("execution_time", 0) for r in model_results if r.get("execution_time") is not None]
            successful_tests = sum(1 for r in model_results if r.get("success", False))

            comparison[model_name] = {
                "total_tests": len(model_results),
                "success_rate": round((successful_tests / len(model_results)) * 100, 2) if model_results else 0,
                "average_accuracy": round(sum(accuracies) / len(accuracies), 4) if accuracies else 0,
                "average_execution_time": round(sum(execution_times) / len(execution_times), 2) if execution_times else 0,
                "best_accuracy": round(max(accuracies), 4) if accuracies else 0,
                "worst_accuracy": round(min(accuracies), 4) if accuracies else 0,
                "accuracy_std": round(self._calculate_std(accuracies), 4) if len(accuracies) > 1 else 0
            }

        return comparison

    def get_session_history(self, limit: int = 50, offset: int = 0,
                          model_filter: Optional[str] = None,
                          date_from: Optional[str] = None,
                          date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение истории сессий с фильтрами"""
        all_sessions = self._load_all_sessions()

        # Применение фильтров
        filtered_sessions = all_sessions

        if model_filter:
            filtered_sessions = [s for s in filtered_sessions if s.get("model_name") == model_filter]

        if date_from:
            date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            filtered_sessions = [s for s in filtered_sessions if datetime.fromisoformat(s["created_at"].replace('Z', '+00:00')) >= date_from_dt]

        if date_to:
            date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            filtered_sessions = [s for s in filtered_sessions if datetime.fromisoformat(s["created_at"].replace('Z', '+00:00')) <= date_to_dt]

        # Сортировка по дате (новые сначала)
        filtered_sessions.sort(key=lambda x: x["created_at"], reverse=True)

        return filtered_sessions[offset:offset + limit]

    def export_results(self, session_ids: List[str], format: str = "json") -> str:
        """Экспорт результатов в различных форматах"""
        export_data = []
        for session_id in session_ids:
            results = self._load_session_results(session_id)
            export_data.extend(results)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.{format}"

        if format == "json":
            return self._export_json(export_data, filename)
        elif format == "csv":
            return self._export_csv(export_data, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_performance_trends(self, model_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Получение трендов производительности модели"""
        all_results = self._load_all_results(days)
        model_results = [r for r in all_results if r.get("model_name") == model_name]

        # Группировка по дням
        daily_stats = {}
        for result in model_results:
            date = result["timestamp"][:10]  # YYYY-MM-DD
            if date not in daily_stats:
                daily_stats[date] = {
                    "date": date,
                    "total_tests": 0,
                    "successful_tests": 0,
                    "total_accuracy": 0,
                    "accuracy_count": 0
                }

            stats = daily_stats[date]
            stats["total_tests"] += 1
            if result.get("success", False):
                stats["successful_tests"] += 1
            if result.get("accuracy") is not None:
                stats["total_accuracy"] += result["accuracy"]
                stats["accuracy_count"] += 1

        # Вычисление дневных метрик
        trends = []
        for date, stats in sorted(daily_stats.items()):
            avg_accuracy = stats["total_accuracy"] / stats["accuracy_count"] if stats["accuracy_count"] > 0 else 0
            success_rate = (stats["successful_tests"] / stats["total_tests"]) * 100

            trends.append({
                "date": date,
                "total_tests": stats["total_tests"],
                "success_rate": round(success_rate, 2),
                "average_accuracy": round(avg_accuracy, 4)
            })

        return trends

    def _load_all_results(self, timeframe_days: int = 30) -> List[Dict[str, Any]]:
        """Загрузка всех результатов за указанный период"""
        all_results = []
        cutoff_date = datetime.now() - timedelta(days=timeframe_days)

        if not self.results_dir.exists():
            return all_results

        for result_file in self.results_dir.glob("*.json"):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Проверка даты
                if isinstance(data, list):
                    for result in data:
                        if self._is_recent_result(result, cutoff_date):
                            all_results.append(result)
                elif isinstance(data, dict):
                    if self._is_recent_result(data, cutoff_date):
                        all_results.append(data)
            except Exception:
                continue

        return all_results

    def _load_all_sessions(self) -> List[Dict[str, Any]]:
        """Загрузка всех сессий"""
        sessions = []
        if not self.results_dir.exists():
            return sessions

        for result_file in self.results_dir.glob("*.json"):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, dict) and "session_id" in data:
                    sessions.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "session_id" in item:
                            sessions.append(item)
            except Exception:
                continue

        return sessions

    def _load_session_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Загрузка результатов конкретной сессии"""
        results = []
        if not self.results_dir.exists():
            return results

        for result_file in self.results_dir.glob("*.json"):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, dict) and data.get("session_id") == session_id:
                    results.append(data)
                elif isinstance(data, list):
                    results.extend([item for item in data if item.get("session_id") == session_id])
            except Exception:
                continue

        return results

    def _is_recent_result(self, result: Dict[str, Any], cutoff_date: datetime) -> bool:
        """Проверка, является ли результат достаточно свежим"""
        timestamp_str = result.get("timestamp")
        if not timestamp_str:
            return False

        try:
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            result_date = datetime.fromisoformat(timestamp_str)
            return result_date >= cutoff_date
        except Exception:
            return False

    def _calculate_std(self, values: List[float]) -> float:
        """Вычисление стандартного отклонения"""
        if len(values) <= 1:
            return 0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _export_json(self, data: List[Dict[str, Any]], filename: str) -> str:
        """Экспорт в JSON"""
        filepath = self.export_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(filepath)

    def _export_csv(self, data: List[Dict[str, Any]], filename: str) -> str:
        """Экспорт в CSV"""
        if not data:
            return ""

        filepath = self.export_dir / filename

        # Определение всех возможных колонок
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())

        fieldnames = sorted(all_keys)

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                writer.writerow(item)

        return str(filepath)