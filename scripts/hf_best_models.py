import sqlite3
import math
import re
import requests
import time
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from contextlib import contextmanager
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- КОНФИГУРАЦИЯ ---
DB_FILE = "gguf_history_v14_clean.db"
HF_JSON_API = "https://huggingface.co/models-json"
PAGES_TO_FETCH = 40  # Глубина сканирования

# Словарь исключений (мусор)
BLACKLIST_KEYWORDS = ['lora', 'adapter', 'diffusion', 'image', 'text-to-speech', 'tts', 'music']

class RankingMode(Enum):
    STABLE = "stable"
    TRENDING = "trending"

@dataclass
class ModelInfo:
    id: str
    downloads: int
    likes: int
    timestamp: datetime
    tags: List[str]
    pipeline_tag: str
    size_bytes: Optional[float] = None

    # Вычисляемые поля
    rank: int = 0
    velocity: float = 0.0
    accel: float = 0.0
    combined_score: float = 0.0
    age_str: str = ""
    rank_delta: Any = 0
    parsed_params_b: float = 0.0

    @property
    def author(self) -> str:
        if '/' in self.id:
            return self.id.split('/')[0]
        return "unknown"

    @property
    def name(self) -> str:
        if '/' in self.id:
            return self.id.split('/', 1)[1]
        return self.id

# --- DATABASE MANAGER ---
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

    def get_last_state(self, config_hash: str) -> Tuple[Dict[str, Dict], Optional[datetime]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp FROM runs WHERE config_hash = ? ORDER BY id DESC LIMIT 1",
                (config_hash,)
            )
            row = cursor.fetchone()
            if not row: return {}, None

            last_run_id = row[0]
            last_ts = datetime.fromisoformat(row[1])

            cursor = conn.execute(
                "SELECT model_id, rank, velocity FROM snapshots WHERE run_id = ?",
                (last_run_id,)
            )
            state = {r[0]: {"rank": r[1], "velocity": r[2]} for r in cursor.fetchall()}
            return state, last_ts

    def save_snapshot(self, models: List[ModelInfo], run_params: Dict[str, Any]):
        if not models: return
        config_key = self._generate_config_key(run_params)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (timestamp, config_hash, mode) VALUES (?, ?, ?)",
                (now_iso, config_key, run_params.get('mode'))
            )
            run_id = cur.lastrowid

            data = [
                (run_id, m.id, m.rank, m.velocity, m.combined_score)
                for m in models
            ]
            conn.executemany(
                "INSERT INTO snapshots (run_id, model_id, rank, velocity, score) VALUES (?, ?, ?, ?, ?)",
                data
            )

# --- FETCHER ---
class HFFetcher:
    def __init__(self):
        self.session = requests.Session()
        retries = Retry(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        })

    def _fetch_stream(self, strategy: Dict, max_pages: int) -> List[Dict]:
        results = []
        for p in range(max_pages):
            time.sleep(random.uniform(0.3, 0.8))
            params = strategy.copy()
            params['p'] = p
            try:
                resp = self.session.get(HF_JSON_API, params=params, timeout=12)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    if not models: break
                    results.extend(models)
                elif resp.status_code == 429:
                    time.sleep(5)
            except Exception: pass
        return results

    def fetch_deep_scan(self) -> List[ModelInfo]:
        unique_models: Dict[str, ModelInfo] = {}
        strategies = [
            {"sort": "trending", "filter": "gguf"},
            {"sort": "lastModified", "filter": "gguf"},
            {"sort": "downloads", "filter": "gguf"},
            {"sort": "likes", "filter": "gguf"}
        ]

        print(f"📡 SCANNING HF ({len(strategies)} x {PAGES_TO_FETCH} pages)...")
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_strat = {executor.submit(self._fetch_stream, s, PAGES_TO_FETCH): s['sort'] for s in strategies}
            for future in as_completed(future_to_strat):
                data = future.result()
                for item in data:
                    mid = item.get("id")
                    if mid in unique_models: continue

                    if any(bad in mid.lower() for bad in BLACKLIST_KEYWORDS): continue
                    pipeline = item.get("pipeline_tag", "")
                    if pipeline and pipeline not in ['text-generation', 'text-generation-inference', 'conversational', 'fill-mask']: continue

                    dt_str = item.get("lastModified") or item.get("createdAt")
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00')) if dt_str else datetime.now(timezone.utc)

                    meta = item.get("params", {})

                    model = ModelInfo(
                        id=mid,
                        downloads=item.get("downloads", 0),
                        likes=item.get("likes", 0),
                        timestamp=dt,
                        tags=item.get("tags", []),
                        pipeline_tag=pipeline,
                        size_bytes=meta.get("bs") if meta else None
                    )
                    unique_models[mid] = model

        return list(unique_models.values())

# --- RANKER ---
class GGUFModelRanker:
    def __init__(self):
        self.fetcher = HFFetcher()
        self.history = RankingHistoryManager()
        self._cache = None
        self._last_time_delta_str = "new"

    def extract_size_billions(self, m: ModelInfo) -> float | None:
        if m.size_bytes: return round(m.size_bytes / 1_000_000_000, 1)
        mid = m.id.lower()

        moe = re.search(r'(\d+)x(\d+(?:\.\d+)?)b', mid)
        if moe: return float(moe.group(1)) * float(moe.group(2))

        std = re.search(r'(?:^|[_\-\./])(\d+(?:\.\d+)?)b(?:[_\-\./]v\d|[_\-\./]|$)', mid)
        if std: return float(std.group(1))

        mill = re.search(r'(?:^|[_\-\./])(\d+(?:\.\d+)?)m(?:[_\-\./]|$)', mid)
        if mill: return float(mill.group(1)) / 1000.0

        for tag in m.tags:
            if re.match(r'^\d+(?:\.\d+)?b$', tag.lower()): return float(tag[:-1])
        return None

    def prepare_data(self):
        if not self._cache: self._cache = self.fetcher.fetch_deep_scan()
        return self._cache

    def get_ranked_list(self, mode=RankingMode.STABLE, min_b=None, max_b=None, top_n=20):
        models = self.prepare_data()
        run_params = {"mode": mode.value, "min": min_b, "max": max_b, "n": top_n}
        candidates = []

        for m in models:
            sz = self.extract_size_billions(m)
            m.parsed_params_b = sz if sz else 0.0

            if min_b or max_b:
                if sz is None: continue
                if min_b and sz < min_b: continue
                if max_b and sz > max_b: continue

            if sz is None and mode == RankingMode.TRENDING and m.likes < 3: continue

            m.combined_score = self._score_model(m, mode)
            if m.combined_score > 0.001: candidates.append(m)

        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        return self._process_history(candidates[:top_n], run_params)

    def _score_model(self, m: ModelInfo, mode: RankingMode) -> float:
        if mode == RankingMode.STABLE:
            norm_dl = min(1.0, math.log10(m.downloads + 1) / 7.0)
            norm_lk = min(1.0, math.log10(m.likes + 1) / 5.0)
            return (0.4 * norm_dl) + (0.6 * norm_lk)
        else:
            delta = datetime.now(timezone.utc) - m.timestamp
            hours = delta.total_seconds() / 3600.0
            if hours > 720: return 0.0
            if m.likes == 0 and hours > 12.0: return 0.0
            points = (m.likes * 150) + (math.log10(m.downloads + 1) * 30)
            return points / pow(hours + 2.0, 1.4)

    def _process_history(self, models: List[ModelInfo], run_params: Dict):
        config_key = self.history._generate_config_key(run_params)
        last_state, last_ts = self.history.get_last_state(config_key)
        now = datetime.now(timezone.utc)

        if last_ts:
            delta_run = now - last_ts
            if delta_run.days > 0: self._last_time_delta_str = f"{delta_run.days}d"
            elif delta_run.seconds > 3600: self._last_time_delta_str = f"{delta_run.seconds//3600}h"
            elif delta_run.seconds > 60: self._last_time_delta_str = f"{delta_run.seconds//60}m"
            else: self._last_time_delta_str = f"{delta_run.seconds}s"
        else:
            self._last_time_delta_str = "new"

        for idx, m in enumerate(models, 1):
            m.rank = idx
            delta = now - m.timestamp
            days = max(0.5, delta.total_seconds() / 86400)

            if delta.days < 1: m.age_str = f"{int(delta.seconds//3600)}h"
            elif delta.days < 30: m.age_str = f"{delta.days}d"
            else: m.age_str = f"{delta.days // 30}M"

            m.velocity = m.downloads / days

            if m.id in last_state:
                prev = last_state[m.id]
                m.rank_delta = prev['rank'] - idx
                m.accel = m.velocity - prev['velocity']
            else:
                m.rank_delta = "new"
                m.accel = 0.0

        self.history.save_snapshot(models, run_params)
        return models

    # --- ЛОГИКА ВЫРАВНИВАНИЯ (БЕЗ ССЫЛОК) ---
    def _visual_len(self, text: str) -> int:
        """Считает длину текста без учета ANSI-кодов цвета"""
        # Удаляем только коды цветов, ссылок больше нет
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return len(clean_text)

    def _pad_string(self, text: str, width: int, visual_len: int = None) -> str:
        """Добавляет пробелы, основываясь на видимой длине"""
        if visual_len is None:
            visual_len = self._visual_len(text)
        padding = max(0, width - visual_len)
        return text + (" " * padding)

    def print_table(self, models: List[ModelInfo], title: str):
        W = 165
        accel_title = f"ACCEL({self._last_time_delta_str})"
        COL_MODEL_W = 85 # Ширина колонки модели

        print(f"\n{'='*W}")
        print(f"{title:^165}")
        print(f"{'='*W}")

        print(f"{'#':^4} | {'Δ':^4} | {'AGE':^5} | {'MODEL ID (Author / Model)':<{COL_MODEL_W}} | {'SZ(B)':^6} | {'DLs':^8} | {'LIKES':^6} | {accel_title:^11}")
        print("-" * W)

        if not models:
            print(f"{'NO DATA':^165}")

        for m in models:
            dr_str = "🆕"
            if m.rank_delta != "new":
                if m.rank_delta > 0: dr_str = f"▲{m.rank_delta}"
                elif m.rank_delta < 0: dr_str = f"▼{abs(m.rank_delta)}"
                else: dr_str = "—"

            acc_str = "—"
            if m.rank_delta != "new":
                acc_str = f"{m.accel:+.1f}"

            # 1. Готовим видимый текст
            visible_text = f"{m.author}/{m.name}"

            # 2. Обрезка
            if len(visible_text) > (COL_MODEL_W - 2):
                avail_len = COL_MODEL_W - len(m.author) - 5
                trunc_name = m.name[:avail_len] + "..."
                visible_text = f"{m.author}/{trunc_name}"

            # 3. Раскраска (Cyan для автора)
            if '/' in visible_text:
                auth, nm = visible_text.split('/', 1)
                colored_text = f"\033[36m{auth}\033[0m/{nm}"
            else:
                colored_text = visible_text

            # 4. Выравнивание (без ссылок)
            padded_model = self._pad_string(colored_text, COL_MODEL_W, len(visible_text))

            sz_str = f"{m.parsed_params_b:.1f}" if m.parsed_params_b > 0 else "?"
            dl_str = f"{m.downloads/1000:.1f}k" if m.downloads >= 1000 else str(m.downloads)

            print(f"{m.rank:^4} | {dr_str:^4} | {m.age_str:^5} | {padded_model} | {sz_str:^6} | {dl_str:>8} | {m.likes:>6} | {acc_str:>11}")

        print("=" * W)
        print(f"👉 \033[36mCyan\033[0m = Author. Clean format (No Links).")

if __name__ == "__main__":
    ranker = GGUFModelRanker()

    ranker.prepare_data()

    # 1. Stable
    ranker.print_table(
        ranker.get_ranked_list(RankingMode.STABLE, min_b=6, max_b=40, top_n=20),
        "🏛️  STABLE RANKING (6B - 40B)"
    )

    # 2. Trending
    ranker.print_table(
        ranker.get_ranked_list(RankingMode.TRENDING, min_b=0, max_b=200, top_n=20),
        "🚀  GLOBAL TRENDING (ALL SIZES)"
    )

    # 3. Edge
    ranker.print_table(
        ranker.get_ranked_list(RankingMode.TRENDING, min_b=0, max_b=5.5, top_n=15),
        "📱  EDGE / MOBILE TRENDING (< 5.5B)"
    )

    # 4. GGUF PROVIDERS (Специальный режим)
    print("\n🔍 Фильтрация: Только известные GGUF провайдеры...")
    GGUF_KINGS = ['unsloth', 'thebloke', 'maziyarpanahi', 'bartowski', 'mradermacher', 'nousresearch']

    all_models = ranker.prepare_data()
    # Фильтруем
    gguf_only = [m for m in all_models if m.author.lower() in [k.lower() for k in GGUF_KINGS]]
    # Сортируем
    gguf_only.sort(key=lambda m: ranker._score_model(m, RankingMode.STABLE), reverse=True)

    # Переназначаем ранги для красивого вывода
    for i, m in enumerate(gguf_only, 1):
        m.rank = i
        m.rank_delta = "new"
        m.accel = 0.0

    ranker.print_table(
        gguf_only[:20],
        "📦  TOP GGUF PROVIDERS (Unsloth, TheBloke, Bartowski...)"
    )
