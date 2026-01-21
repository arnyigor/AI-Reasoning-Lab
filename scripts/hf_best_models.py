import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any

from huggingface_hub import HfApi

# Файл для хранения истории
HISTORY_FILE = "gguf_ranking_history.json"


class RankingHistoryManager:
    def __init__(self, filepath=HISTORY_FILE, max_history=20):
        self.filepath = filepath
        self.max_history = max_history
        self.data = self._load_data()

    def _load_data(self):
        if not os.path.exists(self.filepath):
            return {}
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_data(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _generate_config_key(self, params: Dict[str, Any]) -> str:
        """Создает уникальный хэш для набора параметров фильтрации."""
        # Сортируем ключи, чтобы порядок не влиял на хэш
        s = json.dumps(params, sort_keys=True)
        return hashlib.md5(s.encode('utf-8')).hexdigest()

    def process_ranking(self, current_models: List[Any], run_params: Dict[str, Any]):
        """
        Сравнивает текущий топ с историей, рассчитывает динамику и сохраняет изменения.
        Возвращает список моделей с добавленным атрибутом .rank_delta
        """
        config_key = self._generate_config_key(run_params)

        # Инициализация ветки истории для этих параметров
        if config_key not in self.data:
            self.data[config_key] = {
                "params": run_params,
                "snapshots": []
            }

        history_entry = self.data[config_key]
        snapshots = history_entry["snapshots"]

        # 1. Формируем текущий "слепок" (только ID и ранг для сравнения)
        current_snapshot_map = {
            getattr(m, 'id'): idx
            for idx, m in enumerate(current_models, 1)
        }
        current_ids_ordered = [getattr(m, 'id') for m in current_models]

        # 2. Получаем последний слепок (если есть)
        last_snapshot_map = {}
        last_ids_ordered = []

        if snapshots:
            last_record = snapshots[-1]
            # last_record['items'] - это список dict {'id': ..., 'rank': ...}
            last_snapshot_map = {item['id']: item['rank'] for item in last_record['items']}
            last_ids_ordered = [item['id'] for item in last_record['items']]

        # 3. Рассчитываем динамику для каждой модели
        for idx, model in enumerate(current_models, 1):
            mid = getattr(model, 'id')
            if not snapshots:
                # Истории нет вообще -> все новые
                model.rank_delta = "new"
                model.prev_rank = None
            elif mid not in last_snapshot_map:
                # В прошлом топе не было -> New
                model.rank_delta = "new"
                model.prev_rank = None
            else:
                prev_rank = last_snapshot_map[mid]
                diff = prev_rank - idx  # Если был 5, стал 3: 5-3 = +2 (рост)
                model.rank_delta = diff
                model.prev_rank = prev_rank

        # 4. Проверяем, изменился ли порядок или состав топа
        # Сравниваем списки ID. Если они идентичны - ничего не пишем (экономим место)
        has_changed = (current_ids_ordered != last_ids_ordered)

        if has_changed:
            print(f"📝 Обнаружены изменения в рейтинге. Сохраняем новую запись в историю (Config: {config_key[:8]})...")

            new_record = {
                "timestamp": datetime.now().isoformat(),
                "items": [
                    {
                        "id": getattr(m, 'id'),
                        "rank": idx,
                        "score": getattr(m, 'combined_score', 0)
                    }
                    for idx, m in enumerate(current_models, 1)
                ]
            }

            snapshots.append(new_record)

            # Ротация (удаляем старые, если больше лимита)
            if len(snapshots) > self.max_history:
                snapshots.pop(0)  # Удаляем самый старый

            self._save_data()
        else:
            print("💤 Рейтинг не изменился с последнего запуска. История не обновлена.")

        return current_models


class GGUFModelRanker:
    def __init__(self):
        self.api = HfApi()
        self.history_manager = RankingHistoryManager()  # Подключаем менеджер истории

        self._SIZE_LABEL_RE = re.compile(
            r'(?P<main>\d+(?:\.\d+)?)\s*[xX]?\s*(?P<second>\d+(?:\.\d+)?)(?P<unit>[BbMm])?',
            re.IGNORECASE
        )

    # --- (Методы парсинга и extract_parameters те же, сокращены для краткости) ---
    def _parse_size_label(self, label: str) -> float | None:
        if not label: return None
        m = self._SIZE_LABEL_RE.search(label)
        if not m: return None
        main_val = float(m.group('main'))
        unit = m.group('unit')
        if 'x' in label.lower() and m.group('second'):
            main_val = main_val * float(m.group('second'))
        if unit and unit.lower() == 'm': return main_val / 1000.0
        return main_val

    def extract_parameters(self, model_info) -> float | None:
        if hasattr(model_info, 'general') and getattr(model_info.general, 'size_label', None):
            val = self._parse_size_label(model_info.general.size_label)
            if val: return val
        name = getattr(model_info, 'id', '').lower()
        patterns = [r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)b', r'(\d+(?:\.\d+)?)[b]']
        for p in patterns:
            match = re.search(p, name)
            if match:
                vals = match.groups()
                if len(vals) == 2: return float(vals[0]) * float(vals[1])
                return float(vals[0])
        return None

    def calculate_score(self, model, weights=(0.25, 0.45, 0.30)):
        downloads = getattr(model, 'downloads', 0) or 0
        likes = getattr(model, 'likes', 0) or 0

        # 1. Логарифмирование для сглаживания (Power Law distribution)
        # Используем меньшие делители, так как GGUF репозитории имеют меньше трафика, чем оригиналы
        log_downloads = math.log10(downloads + 1)
        log_likes = math.log10(likes + 1)

        # Нормализация:
        # 6.0 соответствует 1 млн скачиваний (достаточно для GGUF)
        # 4.0 соответствует 10,000 лайков (реалистичный потолок для топов вроде TheBloke)
        norm_download = min(1.0, log_downloads / 6.0)
        norm_like = min(1.0, log_likes / 4.0)

        # 2. Умная свежесть (Sigmoid вместо Linear)
        # Позволяет моделям "жить" чуть дольше, но резко штрафует совсем старье
        created_at = getattr(model, 'created_at', None)
        recency_score = 0.0
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if created_at.tzinfo is None: created_at = created_at.replace(tzinfo=timezone.utc)

            delta_days = (datetime.now(timezone.utc) - created_at).days

            # "Плато" новизны: первые 30 дней модель считается новой (1.0)
            if delta_days < 30:
                recency_score = 1.0
            else:
                # Мягкое затухание до 0 за год (365 дней), а не за полгода
                recency_score = max(0.0, 1.0 - ((delta_days - 30) / 335.0))

        # 3. Бонус за соотношение Лайки/Скачивания (Engagement Rate)
        # Это "секретный соус" для поиска скрытых жемчужин
        engagement_bonus = 0.0
        if downloads > 1000:
            ratio = likes / downloads
            # Если лайков больше 1% от скачиваний — это очень круто для HF
            if ratio > 0.01: engagement_bonus = 0.05

        final_score = (weights[0] * norm_download) + \
                      (weights[1] * norm_like) + \
                      (weights[2] * recency_score) + \
                      engagement_bonus

        return min(1.0, final_score)


    def get_top_gguf_models(self,
                            pipeline_filter="text-generation",
                            min_params=None,
                            max_params=None,
                            min_downloads=50,
                            limit_candidates=2000,
                            top_n=50):

        # Сохраняем параметры запуска для истории
        run_params = {
            "pipeline": pipeline_filter,
            "min_params": min_params,
            "max_params": max_params,
            "top_n": top_n
        }

        print(f"📡 Запрос к API Hugging Face (fetch limit: {limit_candidates})...")
        models_iter = self.api.list_models(filter="gguf", sort="downloads", direction=-1, limit=limit_candidates,
                                           full=True)

        candidates = []
        print("⚙️ Фильтрация и расчет рейтинга...")

        for model in models_iter:
            if getattr(model, 'private', False): continue
            dls = getattr(model, 'downloads', 0) or 0
            if dls < min_downloads: continue

            if pipeline_filter:
                tag = getattr(model, 'pipeline_tag', '')
                if tag and pipeline_filter.lower() not in tag.lower(): continue

            p_val = self.extract_parameters(model)
            if min_params is not None:
                if p_val is None or p_val < min_params: continue
            if max_params is not None:
                if p_val is None or p_val > max_params: continue

            model.parsed_params = p_val
            model.combined_score = self.calculate_score(model)
            candidates.append(model)

        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        top_models = candidates[:top_n]

        # --- МАГИЯ ИСТОРИИ ---
        # Передаем список в менеджер истории для расчета динамики
        top_models = self.history_manager.process_ranking(top_models, run_params)

        return top_models

    def print_top_models(self, models):
        print("\n" + "=" * 165)
        print(f"{'🏆 ТОП GGUF МОДЕЛЕЙ С ДИНАМИКОЙ':^165}")
        print("=" * 165)

        # Добавил колонку Δ (Delta)
        h = f"{'#':^3} | {'Δ':^6} | {'MODEL ID':<70} | {'PARAMS':^8} | {'DLs':^9} | {'LIKES':^7} | {'CREATED':^12} | {'UPDATED':^12} | {'SCORE':^6}"
        print(h)
        print("-" * 165)

        for i, m in enumerate(models, 1):
            name = getattr(m, 'id', 'N/A')
            if len(name) > 50: name = name[:47] + "..."

            p_str = f"{m.parsed_params:.1f}B" if getattr(m, 'parsed_params', None) else "?"

            dls = getattr(m, 'downloads', 0)
            if dls > 1000000:
                dls_str = f"{dls / 1000000:.1f}M"
            elif dls > 1000:
                dls_str = f"{dls / 1000:.1f}k"
            else:
                dls_str = str(dls)

            created_at = getattr(m, 'created_at', None)
            created_str = str(created_at).split(' ')[0] if created_at else "N/A"

            updated_at = getattr(m, 'lastModified', None)
            updated_str = str(updated_at).split('T')[0] if updated_at else "N/A"

            score = getattr(m, 'combined_score', 0.0)
            likes = getattr(m, 'likes', 0)

            # --- Форматирование Динамики ---
            delta = getattr(m, 'rank_delta', 0)
            if delta == "new":
                delta_str = "🆕"  # New entry
            elif delta == 0:
                delta_str = "➖"  # No change
            elif delta > 0:
                delta_str = f"🟢 +{delta}"  # Rose
            else:
                delta_str = f"🔴 {delta}"  # Fell (delta is negative already)

            print(
                f"{i:^3} | {delta_str:^6} | {name:<70} | {p_str:^8} | {dls_str:>9} | {likes:>7} | {created_str:^12} | {updated_str:^12} | {score:.3f}")
        print("=" * 165)


# ------------------------------------------------------------------
#   Тестирование с разными параметрами
# ------------------------------------------------------------------
if __name__ == "__main__":
    ranker = GGUFModelRanker()

    print("\n🔹 СЦЕНАРИЙ 1: Легкие модели (3B-120B) для локального ПК")
    top_small = ranker.get_top_gguf_models(
        pipeline_filter="text-generation",
        min_params=8.0,
        max_params=22.0,
        limit_candidates=10000,
        top_n=25
    )
    ranker.print_top_models(top_small)

    print("\n🔹 СЦЕНАРИЙ 2: Тяжелые модели (120B+) для серверов")
    # Обратите внимание: для этого сценария будет создана ОТДЕЛЬНАЯ история,
    # и она не перезапишет историю для сценария 1.
    top_large = ranker.get_top_gguf_models(
        pipeline_filter="text-generation",
        min_params=23.0,
        max_params=150.0,
        limit_candidates=10000,
        top_n=25
    )
    ranker.print_top_models(top_large)
