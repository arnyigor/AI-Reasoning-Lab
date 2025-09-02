import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class ModelHistoryService:
    """Сервис для управления историей использованных моделей"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.history_file = self.project_root / "model_history.json"
        self._ensure_history_file()

    def _ensure_history_file(self):
        """Создает файл истории моделей если он не существует"""
        if not self.history_file.exists():
            self.history_file.write_text(json.dumps({
                "providers": {},
                "last_updated": datetime.now().isoformat()
            }, indent=2))

    def _load_history(self) -> Dict[str, Any]:
        """Загружает историю моделей из файла"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"providers": {}, "last_updated": datetime.now().isoformat()}

    def _save_history(self, history: Dict[str, Any]):
        """Сохраняет историю моделей в файл"""
        history["last_updated"] = datetime.now().isoformat()
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def save_model(self, provider: str, model_name: str):
        """Сохраняет модель для провайдера"""
        history = self._load_history()

        if provider not in history["providers"]:
            history["providers"][provider] = []

        models = history["providers"][provider]

        # Удаляем дубликаты и добавляем в начало
        if model_name in models:
            models.remove(model_name)
        models.insert(0, model_name)

        # Ограничиваем количество сохраненных моделей до 10 на провайдер
        history["providers"][provider] = models[:10]

        self._save_history(history)

    def get_models_for_provider(self, provider: str) -> List[str]:
        """Получает список моделей для провайдера"""
        history = self._load_history()
        return history["providers"].get(provider, [])

    def get_all_providers(self) -> List[str]:
        """Получает список всех провайдеров с сохраненными моделями"""
        history = self._load_history()
        return list(history["providers"].keys())

    def get_all_models(self) -> Dict[str, List[str]]:
        """Получает все сохраненные модели по провайдерам"""
        history = self._load_history()
        return history["providers"]