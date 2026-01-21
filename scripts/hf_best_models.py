import sqlite3
import math
import re
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from contextlib import contextmanager

from huggingface_hub import HfApi

# Файл базы данных
DB_FILE = "gguf_history_v5.db"

class RankingMode(Enum):
    STABLE = "stable"
    TRENDING = "trending"

class RankingHistoryManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    config_hash TEXT,
                    mode TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    run_id INTEGER,
                    model_id TEXT,
                    rank INTEGER,
                    velocity REAL,
                    score REAL,
                    FOREIGN KEY(run_id) REFERENCES runs(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model_run ON snapshots(model_id, run_id)")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _generate_config_key(self, params: Dict[str, Any]) -> str:
        return f"{params.get('mode')}_{params.get('min')}_{params.get('max')}"

    def get_last_state(self, config_hash: str) -> Dict[str, Dict]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id FROM runs WHERE config_hash = ? ORDER BY id DESC LIMIT 1",
                (config_hash,)
            )
            row = cursor.fetchone()
            if not row: return {}

            last_run_id = row[0]
            cursor = conn.execute(
                "SELECT model_id, rank, velocity FROM snapshots WHERE run_id = ?",
                (last_run_id,)
            )
            return {r[0]: {"rank": r[1], "velocity": r[2]} for r in cursor.fetchall()}

    def save_snapshot(self, models: List[Any], run_params: Dict[str, Any]):
        config_key = self._generate_config_key(run_params)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (timestamp, config_hash, mode) VALUES (?, ?, ?)",
                (now_iso, config_key, run_params.get('mode'))
            )
            run_id = cur.lastrowid

            data = [
                (run_id, m.id, getattr(m, 'rank', 0), getattr(m, 'velocity', 0), getattr(m, 'combined_score', 0))
                for m in models
            ]
            conn.executemany(
                "INSERT INTO snapshots (run_id, model_id, rank, velocity, score) VALUES (?, ?, ?, ?, ?)",
                data
            )

    def process_ranking(self, current_models: List[Any], run_params: Dict[str, Any]):
        config_key = self._generate_config_key(run_params)
        last_state = self.get_last_state(config_key)
        now = datetime.now(timezone.utc)

        for idx, model in enumerate(current_models, 1):
            model.rank = idx

            dt = getattr(model, 'created_at', now)
            if isinstance(dt, str): dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

            # Расчет возраста
            delta = now - dt.replace(tzinfo=timezone.utc)
            days = max(0.5, delta.days + (delta.seconds / 86400))

            if delta.days < 1:
                hours = delta.seconds // 3600
                model.age_str = f"{hours}h"
            elif delta.days < 30:
                model.age_str = f"{delta.days}d"
            else:
                model.age_str = f"{delta.days // 30}M"

            v_curr = model.downloads / days
            model.velocity = v_curr

            if model.id in last_state:
                prev = last_state[model.id]
                model.rank_delta = prev['rank'] - idx
                model.accel = v_curr - prev['velocity']
            else:
                model.rank_delta = "new"
                model.accel = 0.0

        self.save_snapshot(current_models, run_params)
        return current_models

class GGUFModelRanker:
    def __init__(self):
        self.api = HfApi()
        self.history_manager = RankingHistoryManager()

    def _get_dt(self, m) -> Optional[datetime]:
        dt = getattr(m, 'created_at', None)
        if not dt: return None
        if isinstance(dt, str): return datetime.fromisoformat(dt.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    def extract_parameters(self, m) -> float | None:
        """
        Универсальный экстрактор.
        1. Имя репозитория.
        2. Теги.
        3. Имена файлов (siblings) - для случаев, когда в названии модели нет размера.
        4. Safetensors metadata.
        """
        mid = m.id.lower()
        tags = getattr(m, 'tags', []) or []
        siblings = getattr(m, 'siblings', []) or []

        # --- Вспомогательная функция для regex ---
        def try_parse(text: str) -> float | None:
            # MoE (8x7b)
            moe = re.search(r'(\d+)x(\d+(?:\.\d+)?)b', text)
            if moe: return float(moe.group(1)) * float(moe.group(2))

            # Billions (7b, 30b)
            # Улучшенный regex: требует, чтобы после 'b' не было букв (чтобы не ловить 'bert')
            std = re.search(r'(?:^|[_\-\./])(\d+(?:\.\d+)?)b(?:[_\-\./]|$)', text)
            if std: return float(std.group(1))

            # Millions (270m)
            mill = re.search(r'(?:^|[_\-\./])(\d+(?:\.\d+)?)m(?:[_\-\./]|$)', text)
            if mill: return float(mill.group(1)) / 1000.0
            return None

        # 1. Проверка ID репозитория
        res = try_parse(mid)
        if res: return res

        # 2. Проверка Safetensors (самый точный источник, если есть)
        st_info = getattr(m, 'safetensors', None)
        if st_info and hasattr(st_info, 'total') and st_info.total:
            return round(st_info.total / 1_000_000_000, 1)

        # 3. Проверка тегов
        for tag in tags:
            # Ищем теги, которые выглядят ровно как "30b" или "7b"
            if re.match(r'^\d+(?:\.\d+)?b$', tag.lower()):
                return float(tag[:-1])

        # 4. ПРОРЫВ: Проверка имен файлов (Siblings)
        # Это спасет GLM-4.7 и другие модели с "плохими" названиями репо.
        # Мы ищем первый попавшийся файл, в названии которого есть размер.
        for file_info in siblings:
            fname = getattr(file_info, 'rfilename', '').lower()
            # Пропускаем служебные файлы, смотрим только на .gguf или .safetensors
            if not (fname.endswith('.gguf') or fname.endswith('.safetensors')):
                continue

            res = try_parse(fname)
            if res: return res

        return None

    def _score_stable(self, m):
        dl, lk = getattr(m, 'downloads', 0) or 0, getattr(m, 'likes', 0) or 0
        norm_dl = min(1.0, math.log10(dl + 1) / 6.0)
        norm_lk = min(1.0, math.log10(lk + 1) / 4.0)
        return (0.4 * norm_dl) + (0.6 * norm_lk)

    def _score_trending(self, m):
        dt = self._get_dt(m)
        if not dt: return 0.0

        delta = datetime.now(timezone.utc) - dt
        hours = delta.total_seconds() / 3600.0

        # 1. СТРОГИЙ ФИЛЬТР ВРЕМЕНИ: не старше 7 дней
        if hours > 168: return 0.0

        dl = getattr(m, 'downloads', 0) or 0
        lk = getattr(m, 'likes', 0) or 0

        # 2. ПРАВИЛО 2 ЧАСОВ (Зачистка ботов)
        # Если лайков НЕТ:
        if lk == 0:
            # Если модель вышла менее 2 часов назад - даем ей шанс (еще не успели лайкнуть)
            if hours < 2.0:
                pass
                # Если модели больше 2 часов и 0 лайков - это мусор, удаляем (даже если 1000 загрузок)
            else:
                return 0.0

        # 3. Формула рейтинга
        points = (lk * 100) + (math.log10(dl + 1) * 10)
        gravity = 1.2
        score = points / pow(hours + 2.0, gravity)

        return score

    def get_top_gguf_models(self, mode=RankingMode.STABLE, min_params=None, max_params=None, top_n=10):
        run_params = {"mode": mode.value, "min": min_params, "max": max_params, "n": top_n}

        candidates = []
        raw_models = []

        # === ЭТАП 1: СБОР ДАННЫХ ===
        if mode == RankingMode.STABLE:
            print(f"🔄 Запрос к HF API (Mode: STABLE, Sort: downloads)...")
            # STABLE: Классика — сортировка по загрузкам
            raw_models = list(self.api.list_models(
                filter="gguf",
                sort="downloads",
                direction=-1,
                limit=3000,
                full=True
            ))
        else:
            print(f"🔄 Запрос к HF API (Mode: TRENDING, Strategy: Anti-Spam Hybrid)...")
            # TRENDING: Гибридная стратегия (Лайки + Новизна)
            # Берем 4000, чтобы пробить слой спама от ботов

            print("   👉 Загрузка популярных (Top Likes)...")
            by_likes = list(self.api.list_models(
                filter="gguf",
                sort="likes",
                direction=-1,
                limit=4000,
                full=True
            ))

            print("   👉 Загрузка свежих (Last Modified)...")
            by_date = list(self.api.list_models(
                filter="gguf",
                sort="lastModified",
                direction=-1,
                limit=4000,
                full=True
            ))

            # Объединяем списки и убираем дубликаты
            seen_ids = set()
            for m in by_likes + by_date:
                if m.id not in seen_ids:
                    raw_models.append(m)
                    seen_ids.add(m.id)

        # === ЭТАП 2: ФИЛЬТРАЦИЯ И ОЦЕНКА ===
        for m in raw_models:
            # 1. Проверка тегов (только текстовые модели)
            tags = (getattr(m, 'pipeline_tag', '') or '').lower()
            model_tags = [t.lower() for t in (getattr(m, 'tags', []) or [])]

            is_text = "text-generation" in tags or any(x in model_tags for x in ['text-generation', 'conversational', 'text-generation-inference'])
            if not is_text: continue

            # 2. Определение параметров (размера)
            p = self.extract_parameters(m)
            m.parsed_params = p

            # 3. Умная фильтрация по размеру
            if p is not None:
                # Если размер известен - фильтруем строго
                if min_params and p < min_params: continue
                if max_params and p > max_params: continue
            else:
                # Если размер НЕИЗВЕСТЕН (автор не указал нигде):
                # В STABLE - пропускаем (рискованно).
                # В TRENDING - оставляем, ТОЛЬКО если есть хайп (> 5 лайков).
                # Это позволяет GLM-4.7 остаться в списке, даже если парсер не нашел цифры.
                likes = getattr(m, 'likes', 0) or 0
                if mode == RankingMode.STABLE: continue
                if likes < 5: continue

            # 4. Расчет очков
            if mode == RankingMode.TRENDING:
                m.combined_score = self._score_trending(m)
            else:
                m.combined_score = self._score_stable(m)

            # 5. Порог отсечения (убирает совсем слабые модели и ботов с 0 рейтингом)
            if m.combined_score > 0.1:
                candidates.append(m)

        # === ЭТАП 3: СОРТИРОВКА И ВОЗВРАТ ===
        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        return self.history_manager.process_ranking(candidates[:top_n], run_params)

    def _smart_truncate(self, text, length=75):
        if len(text) <= length: return text
        part = (length - 3) // 2
        return text[:part] + "..." + text[-part:]

    def print_top_models(self, models, title="TOP"):
        WIDTH = 190
        print(f"\n{'='*WIDTH}")
        print(f"{title:^190}")
        print(f"{'='*WIDTH}")

        header = f"{'#':^3} | {'ΔR':^4} | {'AGE':^5} | {'MODEL ID':<75} | {'SZ (B)':^7} | {'DLs':^9} | {'❤':^6} | {'VELOCITY':^9} | {'ACCEL':^11}"
        print(header)
        print("-" * WIDTH)

        for m in models:
            d_r = "🆕" if m.rank_delta == "new" else (f"+{m.rank_delta}" if m.rank_delta > 0 else (f"{m.rank_delta}" if m.rank_delta < 0 else "—"))

            v_str = f"{m.velocity/1000:.1f}k" if m.velocity >= 1000 else f"{m.velocity:.0f}"

            if m.rank_delta == "new": a_str = "—"
            else: a_str = f"{m.accel:+.2f}"

            p_str = f"{m.parsed_params:.1f}" if m.parsed_params else "?"
            dl_str = f"{m.downloads/1000:.1f}k" if m.downloads >= 1000 else str(m.downloads)

            mid = self._smart_truncate(m.id, 75)

            print(f"{m.rank:^3} | {d_r:^4} | {m.age_str:^5} | {mid:<75} | {p_str:^7} | {dl_str:>9} | {m.likes:>6} | {v_str:>9} | {a_str:>11}")
        print("=" * WIDTH)

if __name__ == "__main__":
    ranker = GGUFModelRanker()

    ranker.print_top_models(
        ranker.get_top_gguf_models(RankingMode.STABLE, 7, 35, top_n=20),
        "🏛️ STABLE RANKING (7B - 35B)"
    )

    ranker.print_top_models(
        ranker.get_top_gguf_models(RankingMode.TRENDING, 7, 35, top_n=20),
        "🚀 TRENDING RANKING (7B - 35B)"
    )