import json
import re
import math
from datetime import datetime, timezone
from huggingface_hub import HfApi

class GGUFModelRanker:
    def __init__(self):
        self.api = HfApi()
        self._SIZE_LABEL_RE = re.compile(
            r'(?P<main>\d+(?:\.\d+)?)\s*[xX]?\s*(?P<second>\d+(?:\.\d+)?)(?P<unit>[BbMm])?',
            re.IGNORECASE
        )

    # ------------------------------------------------------------------
    #   Парсинг параметров
    # ------------------------------------------------------------------
    def _parse_size_label(self, label: str) -> float | None:
        if not label: return None
        m = self._SIZE_LABEL_RE.search(label)
        if not m: return None

        main_val = float(m.group('main'))
        unit = m.group('unit')

        # Логика MoE (например, 8x7B)
        if 'x' in label.lower() and m.group('second'):
            second_val = float(m.group('second'))
            main_val = main_val * second_val

        if unit and unit.lower() == 'm':
            return main_val / 1000.0
        return main_val

    def extract_parameters(self, model_info) -> float | None:
        # 1. size_label
        if hasattr(model_info, 'general') and getattr(model_info.general, 'size_label', None):
            val = self._parse_size_label(model_info.general.size_label)
            if val: return val

        # 2. Regex по имени (используем .id вместо .modelId)
        name = getattr(model_info, 'id', '').lower()

        patterns = [
            r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)b', # MoE: 8x7b
            r'(\d+(?:\.\d+)?)[b]',               # 7b, 13.5b
        ]

        for p in patterns:
            match = re.search(p, name)
            if match:
                vals = match.groups()
                if len(vals) == 2:
                    return float(vals[0]) * float(vals[1])
                return float(vals[0])
        return None

    # ------------------------------------------------------------------
    #   Расчет рейтинга (FIX: createdAt -> created_at)
    # ------------------------------------------------------------------
    def calculate_score(self, model, weights=(0.45, 0.35, 0.2)):
        downloads = getattr(model, 'downloads', 0) or 0
        likes = getattr(model, 'likes', 0) or 0

        log_downloads = math.log10(downloads + 1)
        log_likes = math.log10(likes + 1)

        MAX_LOG_DOWNLOADS = 7.5
        MAX_LOG_LIKES = 5.0

        norm_download = min(1.0, log_downloads / MAX_LOG_DOWNLOADS)
        norm_like = min(1.0, log_likes / MAX_LOG_LIKES)

        # Новизна
        recency_score = 0.5

        # FIX: Используем created_at
        created_at = getattr(model, 'created_at', None)

        if created_at:
            try:
                # Библиотека теперь часто возвращает datetime объект, а не строку
                if isinstance(created_at, str):
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_dt = created_at

                # Приводим к UTC для корректного вычитания
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)

                delta_days = (datetime.now(timezone.utc) - created_dt).days

                if delta_days < 14:
                    recency_score = 1.0
                else:
                    recency_score = max(0.0, 1.0 - (delta_days / 180.0))
            except Exception as e:
                # print(f"Date parsing error: {e}") # Debug
                pass

        score = (
                weights[0] * norm_download +
                weights[1] * norm_like +
                weights[2] * recency_score
        )
        return score

    # ------------------------------------------------------------------
    #   Главный метод выборки
    # ------------------------------------------------------------------
    def get_top_gguf_models(self,
                            pipeline_filter="text-generation",
                            min_params=None,
                            max_params=None,
                            min_downloads=50,
                            limit_candidates=2000,
                            top_n=50):

        print(f"📡 Запрос к API Hugging Face (fetch limit: {limit_candidates})...")

        models_iter = self.api.list_models(
            filter="gguf",
            sort="downloads",
            direction=-1,
            limit=limit_candidates,
            full=True
        )

        candidates = []
        print("⚙️ Обработка и фильтрация...")

        for model in models_iter:
            if getattr(model, 'private', False): continue

            dls = getattr(model, 'downloads', 0) or 0
            if dls < min_downloads: continue

            if pipeline_filter:
                tag = getattr(model, 'pipeline_tag', '')
                if tag and pipeline_filter.lower() not in tag.lower():
                    continue

            p_val = self.extract_parameters(model)

            # Фильтрация по параметрам
            if min_params is not None:
                if p_val is None or p_val < min_params: continue
            if max_params is not None:
                if p_val is None or p_val > max_params: continue

            model.parsed_params = p_val
            model.combined_score = self.calculate_score(model)
            candidates.append(model)

        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        return candidates[:top_n]

    # ------------------------------------------------------------------
    #   Вывод (FIX: modelId -> id, createdAt -> created_at)
    # ------------------------------------------------------------------
    def print_top_models(self, models):
        print("\n" + "=" * 160)
        print(f"{'🏆 ТОП GGUF МОДЕЛЕЙ (Сортировка: Downloads + Likes + CreatedAt)':^160}")
        print("=" * 160)

        # Добавил колонку UPDATED
        h = f"{'#':^3} | {'MODEL ID':<100} | {'PARAMS':^8} | {'DLs':^9} | {'LIKES':^7} | {'CREATED':^12} | {'UPDATED':^12} | {'SCORE':^6}"
        print(h)
        print("-" * 160)

        for i, m in enumerate(models, 1):
            name = getattr(m, 'id', 'N/A')
            if len(name) > 100: name = name[:100] + "..."

            p_str = f"{m.parsed_params:.1f}B" if getattr(m, 'parsed_params', None) else "?"

            dls = getattr(m, 'downloads', 0)
            if dls > 1000000: dls_str = f"{dls/1000000:.1f}M"
            elif dls > 1000: dls_str = f"{dls/1000:.1f}k"
            else: dls_str = str(dls)

            # Дата создания
            created_at = getattr(m, 'created_at', None)
            created_str = str(created_at).split(' ')[0] if created_at else "N/A"

            # Дата обновления (lastModified)
            updated_at = getattr(m, 'lastModified', None) # В API это поле lastModified
            if updated_at:
                # Иногда это строка, иногда datetime
                if isinstance(updated_at, str):
                    updated_str = updated_at.split('T')[0]
                else:
                    updated_str = str(updated_at).split(' ')[0]
            else:
                updated_str = "N/A"

            score = getattr(m, 'combined_score', 0.0)
            likes = getattr(m, 'likes', 0)

            print(f"{i:^3} | {name:<100} | {p_str:^8} | {dls_str:>9} | {likes:>7} | {created_str:^12} | {updated_str:^12} | {score:.3f}")
        print("=" * 160)

# ------------------------------------------------------------------
#   Точка входа
# ------------------------------------------------------------------
if __name__ == "__main__":
    ranker = GGUFModelRanker()

    # Сценарий: Найти лучшие модели 6B-20B
    try:
        top = ranker.get_top_gguf_models(
            pipeline_filter="text-generation",
            min_params=6.0,
            max_params=121.0,
            min_downloads=5000,
            limit_candidates=10000,
            top_n=25
        )
        ranker.print_top_models(top)
    except Exception as e:
        print(f"\n❌ Произошла ошибка при выполнении: {e}")
        import traceback
        traceback.print_exc()