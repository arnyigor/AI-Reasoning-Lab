import os
from typing import Dict, List, Any
from app.core.config import settings

class ModelDiscoveryService:
    def __init__(self):
        self.config_loader = None  # Will be initialized if needed

    def discover_models(self) -> List[Dict[str, Any]]:
        """Обнаружение доступных моделей из переменных окружения"""
        models = []

        # Ищем переменные окружения с префиксом BC_MODELS_
        for key, value in os.environ.items():
            if key.startswith('BC_MODELS_'):
                parts = key.split('_')
                if len(parts) >= 3:
                    try:
                        index = int(parts[2])
                        if index >= len(models):
                            models.extend([{}] * (index - len(models) + 1))

                        param_name = '_'.join(parts[3:]).lower()
                        models[index][param_name] = value
                    except (ValueError, IndexError):
                        continue

        # Фильтруем только модели с именем
        valid_models = []
        for model in models:
            if model and 'name' in model:
                # Добавляем client_type если не указан
                if 'client_type' not in model:
                    model['client_type'] = 'ollama'  # default

                # Форматируем модель для frontend
                formatted_model = {
                    'id': f"model_{len(valid_models)}",
                    'name': model['name'],
                    'client_type': model.get('client_type', 'ollama'),
                    'api_base': model.get('api_base', ''),
                    'temperature': float(model.get('generation_temperature', 0.7)),
                    'max_tokens': int(model.get('generation_max_tokens', 1000)),
                    'description': f"{model['name']} ({model.get('client_type', 'ollama')})"
                }
                valid_models.append(formatted_model)

        return valid_models

    def get_available_client_types(self) -> List[str]:
        """Получение списка доступных типов клиентов"""
        return ['ollama', 'lmstudio', 'jan', 'openai_compatible', 'gemini']