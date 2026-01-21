import sqlite3
import math
import re
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
from contextlib import contextmanager

from huggingface_hub import HfApi

# Файл базы данных
DB_FILE = "gguf_history_v3.db"

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
            days = max(0.5, (now - dt.replace(tzinfo=timezone.utc)).days)

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
        mid = m.id.lower()
        tags = getattr(m, 'tags', []) or []

        # 1. MoE в имени (8x7b)
        moe = re.search(r'(\d+)x(\d+(?:\.\d+)?)b', mid)
        if moe: return float(moe.group(1)) * float(moe.group(2))

        # 2. Обычные миллиарды (7b)
        std = re.search(r'(?:^|[_\-\./])(\d+(?:\.\d+)?)b', mid)
        if std: return float(std.group(1))

        # 3. Миллионы (270m)
        mill = re.search(r'(?:^|[_\-\./])(\d+(?:\.\d+)?)m', mid)
        if mill: return float(mill.group(1)) / 1000.0

        # 4. Поиск в тегах (fallback)
        for tag in tags:
            t_match = re.match(r'^(\d+(?:\.\d+)?)b$', tag.lower())
            if t_match: return float(t_match.group(1))

        return None

    def _score_stable(self, m):
        dl, lk = getattr(m, 'downloads', 0) or 0, getattr(m, 'likes', 0) or 0
        norm_dl = min(1.0, math.log10(dl + 1) / 6.0)
        norm_lk = min(1.0, math.log10(lk + 1) / 4.0)
        dt = self._get_dt(m)
        days = (datetime.now(timezone.utc) - dt).days if dt else 365
        rec = 1.0 if days < 30 else max(0.0, 1.0 - ((days - 30) / 335.0))
        return (0.25 * norm_dl) + (0.45 * norm_lk) + (0.30 * rec)

    def _score_trending(self, m):
        dt = self._get_dt(m)
        if not dt or (datetime.now(timezone.utc) - dt).days > 45: return 0.0
        dl, lk = getattr(m, 'downloads', 0) or 0, getattr(m, 'likes', 0) or 0
        days = max(0.5, (datetime.now(timezone.utc) - dt).days)
        v = math.log10((dl / days) + 1) / 3.5
        ratio = min(1.0, (lk / dl * 50.0)) if dl > 50 else 0
        return v * ratio * (1.3 if days < 7 else 1.0)

    def get_top_gguf_models(self, mode=RankingMode.STABLE, min_params=None, max_params=None, top_n=10):
        print(f"🔄 Запрос к HF API (Mode: {mode.value}, Params: {min_params}-{max_params}B)...")
        run_params = {"mode": mode.value, "min": min_params, "max": max_params, "n": top_n}

        models = self.api.list_models(filter="gguf", sort="downloads", direction=-1, limit=2000, full=True)
        candidates = []
        for m in models:
            tags = (getattr(m, 'pipeline_tag', '') or '').lower()
            if "text-generation" not in tags: continue

            p = self.extract_parameters(m)
            if min_params and (p is None or p < min_params): continue
            if max_params and (p is None or p > max_params): continue

            m.parsed_params = p
            m.combined_score = self._score_trending(m) if mode == RankingMode.TRENDING else self._score_stable(m)

            if m.combined_score > 0.001: candidates.append(m)

        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        return self.history_manager.process_ranking(candidates[:top_n], run_params)

    def _smart_truncate(self, text, length=80):
        """Обрезает строку посередине, если она слишком длинная"""
        if len(text) <= length: return text
        part = (length - 3) // 2
        return text[:part] + "..." + text[-part:]

    def print_top_models(self, models, title="TOP"):
        # Увеличиваем ширину таблицы для вместимости длинных имен
        TABLE_WIDTH = 185
        print(f"\n{'='*TABLE_WIDTH}")
        print(f"{title:^185}")
        print(f"{'='*TABLE_WIDTH}")

        # Расширенный заголовок, имя модели увеличено до 80 символов
        header = f"{'#':^3} | {'ΔR':^4} | {'MODEL ID':<80} | {'SZ (B)':^7} | {'DLs':^9} | {'❤':^6} | {'VELOCITY':^9} | {'ACCEL':^11} | {'SCORE':^6}"
        print(header)
        print("-" * TABLE_WIDTH)

        for m in models:
            d_r = "🆕" if m.rank_delta == "new" else (f"+{m.rank_delta}" if m.rank_delta > 0 else (f"{m.rank_delta}" if m.rank_delta < 0 else "—"))

            v_str = f"{m.velocity/1000:.1f}k" if m.velocity >= 1000 else f"{m.velocity:.0f}"

            # Ускорение: Точное значение с 2 знаками после запятой
            if m.rank_delta == "new": a_str = "—"
            else: a_str = f"{m.accel:+.2f}"

            p_str = f"{m.parsed_params:.1f}" if m.parsed_params else "?"
            dl_str = f"{m.downloads/1000:.1f}k" if m.downloads >= 1000 else str(m.downloads)

            # Обрезка до 80 символов (достаточно для большинства имен)
            mid = self._smart_truncate(m.id, 80)

            print(f"{m.rank:^3} | {d_r:^4} | {mid:<80} | {p_str:^7} | {dl_str:>9} | {m.likes:>6} | {v_str:>9} | {a_str:>11} | {m.combined_score:.3f}")
        print("=" * TABLE_WIDTH)

if __name__ == "__main__":
    ranker = GGUFModelRanker()

    # Можно менять диапазоны и количество топ-моделей
    ranker.print_top_models(
        ranker.get_top_gguf_models(RankingMode.STABLE, 7, 35, top_n=20),
        "🏛️ STABLE RANKING (7B - 35B)"
    )

    ranker.print_top_models(
        ranker.get_top_gguf_models(RankingMode.TRENDING, 7, 35, top_n=20),
        "🚀 TRENDING RANKING (7B - 35B)"
    )