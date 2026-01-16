import json
import re
from datetime import datetime

from huggingface_hub import HfApi


class GGUFModelRanker:
    def __init__(self):
        self.api = HfApi()

    # ------------------------------------------------------------------
    #   Парсер для general.size_label
    # ------------------------------------------------------------------
    _SIZE_LABEL_RE = re.compile(
        r'(?P<main>\d+(?:\.\d+)?)\s*[xX]\s*'
        r'(?P<second>\d+(?:\.\d+)?)(?P<unit>[BbMm])?',  # unit optional
        re.IGNORECASE
    )

    def _parse_size_label(self, label: str) -> float | None:
        """
        Извлекает значение «основного» параметра из строки вида '256x20B'.
        Возвращает число в миллиардах (если первый показатель задан в миллионах).
        Если строка не распознаётся – возвращается None.
        """
        m = self._SIZE_LABEL_RE.search(label)
        if not m:
            return None

        main_val = float(m.group('main'))          # первое число
        unit     = m.group('unit')                # может быть B/M/None

        # Если второй показатель закодирован в миллиардах (20B), то первый
        # обычно в миллионах. Переведём его в миллиарды.
        if unit == 'b':
            return main_val / 1000.0              # 256M → 0,256B

        # Иначе считаем, что число уже в миллиардах (или без уточнения)
        return main_val

    # ------------------------------------------------------------------
    #   Основная функция извлечения параметров
    # ------------------------------------------------------------------
    def extract_parameters(self, model_info):
        """Извлекает количество параметров из названия модели, тегов или size_label."""
        # 1) Попытка взять значение из general.size_label (если доступно)
        if hasattr(model_info, 'general') and getattr(model_info.general, 'size_label', None):
            label = model_info.general.size_label
            params_from_label = self._parse_size_label(label)
            if params_from_label is not None:
                return params_from_label

        # 2) Обычные паттерны – название модели / теги (без изменений)
        name = getattr(model_info, 'modelId', '').lower()
        param_patterns = [
            r'(\d+\.?\d*)\s*[bm]b',
            r'(\d+\.?\d*)b',
            r'(\d+)\s*billi',
            r'(\d+)\s*m',
        ]

        for pattern in param_patterns:
            match = re.search(pattern, name)
            if match:
                value = float(match.group(1))
                if 'm' in name or 'million' in name:
                    return value / 1000.0
                return value

        if hasattr(model_info, 'tags'):
            for tag in model_info.tags:
                tag = tag.lower()
                for pattern in param_patterns:
                    match = re.search(pattern, tag)
                    if match:
                        value = float(match.group(1))
                        if 'm' in tag or 'million' in tag:
                            return value / 1000.0
                        return value

        # Если ничего не найдено – возвращаем None
        return None

    def calculate_score(self, model, weights=(0.5, 0.3, 0.2)):
        """
        Рассчитывает комплексный рейтинг модели на основе:
            - downloads (50%)
            - likes     (30%)
            - recency   (20%)

        Параметры
        ----------
        model   : объект из HfApi.list_models()
        weights : кортеж (download_weight, like_weight, recency_weight)
        """
        # 1. Считаем “raw”‑значения
        download_score = getattr(model, 'downloads', 0) or 0
        like_score = getattr(model, 'likes', 0) or 0

        # 2. Новизна: 1 для последних 7 дней → 0 при 180+ днях
        if hasattr(model, 'createdAt') and model.createdAt:
            try:
                created_date = datetime.fromisoformat(
                    model.createdAt.replace('Z', '+00:00')
                )
                days_old = (datetime.now(created_date.tzinfo) - created_date).days
                recency_score = max(0.0, 1.0 - (days_old / 180))
            except Exception:
                # Если дата непонятна – считаем среднюю новизну
                recency_score = 0.5
        else:
            recency_score = 0.5

        # 3. Нормализация скачиваний и лайков (логарифмический масштаб)
        MAX_DOWNLOADS = 10_000_000  # предел для нормализации
        MAX_LIKES = 10_000

        norm_download = min(
            1.0, (download_score / MAX_DOWNLOADS) ** 0.5
        )
        norm_like = min(
            1.0, (like_score / MAX_LIKES) ** 0.7
        )

        # 4. Итоговый рейтинг
        score = (
                weights[0] * norm_download +
                weights[1] * norm_like +
                weights[2] * recency_score
        )
        return float(score)

    def get_top_gguf_models(self,
                            pipeline_filter=None,
                            min_params=None,
                            max_params=None,
                            min_downloads=0,
                            top_n=50,
                            sort_by='combined'):
        """
        Получает топ GGUF моделей с фильтрацией

        Args:
            pipeline_filter (str): Фильтр по типу задачи ('text-generation', 'text-to-image', и т.д.)
            min_params (float): Минимальное количество параметров в миллиардах
            max_params (float): Максимальное количество параметров в миллиардах
            min_downloads (int): Минимальное количество скачиваний
            top_n (int): Количество моделей для возврата
            sort_by (str): Метод сортировки ('downloads', 'likes', 'newest', 'combined')
        """
        # Получаем все GGUF модели
        print("Загрузка списка GGUF моделей с Hugging Face...")
        all_models = list(self.api.list_models(
            filter="gguf",
            limit=1000  # Загружаем достаточно моделей для фильтрации
        ))

        print(f"Найдено {len(all_models)} GGUF моделей. Применяем фильтры...")

        filtered_models = []
        for model in all_models:
            # Пропускаем приватные модели
            if getattr(model, 'private', True):
                continue

            # Применяем фильтр по количеству скачиваний
            downloads = getattr(model, 'downloads', 0) or 0
            if downloads < min_downloads:
                continue

            # Применяем фильтр по типу задачи
            if pipeline_filter:
                model_pipeline = getattr(model, 'pipeline_tag', '')
                if not model_pipeline or pipeline_filter.lower() not in model_pipeline.lower():
                    continue

            # Применяем фильтр по параметрам
            params = self.extract_parameters(model)
            if params is not None:
                if min_params is not None and params < min_params:
                    continue
                if max_params is not None and params > max_params:
                    continue

            # Добавляем информацию о параметрах в модель
            model.parameters = params
            filtered_models.append(model)

        print(f"После фильтрации осталось {len(filtered_models)} моделей")

        # Сортировка моделей
        if sort_by == 'downloads':
            sorted_models = sorted(filtered_models, key=lambda x: getattr(x, 'downloads', 0) or 0, reverse=True)
        elif sort_by == 'likes':
            sorted_models = sorted(filtered_models, key=lambda x: getattr(x, 'likes', 0) or 0, reverse=True)
        elif sort_by == 'newest':
            sorted_models = sorted(filtered_models,
                                   key=lambda x: getattr(x, 'createdAt', '') or '',
                                   reverse=True)
        else:  # combined
            # Рассчитываем комплексный рейтинг для каждой модели
            for model in filtered_models:
                model.combined_score = self.calculate_score(model)
            sorted_models = sorted(filtered_models, key=lambda x: x.combined_score, reverse=True)

        # Ограничиваем количество моделей
        top_models = sorted_models[:top_n]

        return top_models

    # ────────────────────────────────  format_model_info  ────────────────────────────────
    def format_model_info(self, model):
        """Форматирует информацию о модели для вывода"""
        model_id = getattr(model, 'modelId', 'N/A')
        downloads = getattr(model, 'downloads', 'N/A')
        likes = getattr(model, 'likes', 'N/A')
        pipeline = getattr(model, 'pipeline_tag', 'N/A')
        params = getattr(model, 'parameters', 'N/A')
        created = getattr(model, 'createdAt', 'N/A')

        if pipeline == 'text-generation':
            pipeline_pretty = '🔤 Text Generation'
        elif pipeline == 'text-to-image':
            pipeline_pretty = '🖼️ Text-to-Image'
        elif pipeline == 'image-text-to-text':
            pipeline_pretty = '📸 Image-to-Text'
        elif pipeline == 'automatic-speech-recognition':
            pipeline_pretty = '🎤 Speech Recognition'
        elif pipeline == 'text-to-speech':
            pipeline_pretty = '🗣️ Text-to-Speech'
        else:
            pipeline_pretty = f'🔧 {pipeline}'

        param_str = f"{params:.1f}B" if isinstance(params, (int, float)) else "N/A"
        url = f"https://huggingface.co/{model_id}"  # ← новый атрибут

        return {
            'name': model_id,
            'parameters': param_str,
            'pipeline': pipeline_pretty,
            'downloads': downloads,
            'likes': likes,
            'created': created.split('T')[0] if created != 'N/A' else 'N/A',
            'url': url,  # ← возвращаем
            'score': round(getattr(model, 'combined_score', 0), 3) if hasattr(
                model, 'combined_score') else 'N/A'
        }

    # ────────────────────────────────  print_top_models  ────────────────────────────────
    def print_top_models(self, models):
        """Красиво выводит информацию о топ моделях"""
        # ----- HEADER --------------------------------------------------------------
        print("\n" + "=" * 100)
        print(f"{'🏆 ТОП-50 ЛУЧШИХ GGUF МОДЕЛЕЙ':^100}")
        print("=" * 100)

        # ----- TABLE HEADERS ------------------------------------------------------
        header = (
            f"{'#':^3} | {'МОДЕЛЬ (URL)':^120} | {'ТИП ЗАДАЧИ':^20} | "
            f"{'ПАРАМЕТРЫ':^10} | {'СКАЧИВАНИЙ':^10} | {'ЛАЙКОВ':^6}"
        )
        print(header)
        print("-" * len(header))

        # ----- ROWS ---------------------------------------------------------------
        for i, model in enumerate(models, 1):
            info = self.format_model_info(model)

            # Вставляем ссылку рядом с именем модели
            name_with_link = f"{info['name']} ({info['url']})"

            print(
                f"{i:^3} | {name_with_link[:120]:<120} | {info['pipeline'][:20]:<20} | "
                f"{info['parameters']:^10} | {info['downloads']:^10} | {info['likes']:^6}"
            )

        # ----- FOOTER -------------------------------------------------------------
        print("=" * 100)


# Пример использования
if __name__ == "__main__":
    ranker = GGUFModelRanker()

    # Топ‑50 лучших GGUF моделей (комплексная сортировка)
    print("Получение топ-50 лучших GGUF моделей...")
    top_models = ranker.get_top_gguf_models(
        top_n=50,
        sort_by='combined',
        min_downloads=100
    )
    ranker.print_top_models(top_models)

    # Фильтрация по конкретным критериям
    print("\n" + "=" * 100)
    print("ФИЛЬТРАЦИЯ ПО КОНКРЕТНЫМ КРИТЕРИЯМ")
    print("=" * 100)

    min_params_range = 9.0  # Минимальное кол-во параметров (в млрд.)
    max_params_range = 40.0  # Максимальное кол-во параметров

    text_models = ranker.get_top_gguf_models(
        pipeline_filter="text-generation",
        min_params=min_params_range,
        max_params=max_params_range,
        min_downloads=1000,
        top_n=10,
        sort_by='combined'
    )

    ranker.print_top_models(top_models)

    # Вариант 2: Фильтрация по конкретным критериям
    print("\n" + "=" * 100)
    print("ФИЛЬТРАЦИЯ ПО КОНКРЕТНЫМ КРИТЕРИЯМ")
    print("=" * 100)

    # Топ-10 text-generation моделей
    top_text_models = ranker.get_top_gguf_models(
        pipeline_filter="text-generation",
        min_params=min_params_range,
        max_params=max_params_range,
        min_downloads=1000,
        top_n=10,
        sort_by='combined'
    )

    print(f"\n🔤 ТОП-10 TEXT GENERATION МОДЕЛЕЙ ({min_params_range:,}B-{max_params_range:,}B параметров):")
    ranker.print_top_models(top_text_models)

    # Топ-10 text-to-image моделей
    image_models = ranker.get_top_gguf_models(
        pipeline_filter="text-to-image",
        min_downloads=500,
        top_n=10,
        sort_by='combined'
    )

    print("\n🖼️ ТОП-10 TEXT-TO-IMAGE МОДЕЛЕЙ:")
    ranker.print_top_models(image_models)

    # Сохранение результатов в JSON
    results = [
        {
            'rank': i,
            'model': ranker.format_model_info(model)
        } for i, model in enumerate(top_models, 1)
    ]

    with open('top_50_gguf_models.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Результаты сохранены в файл 'top_50_gguf_models.json'")
