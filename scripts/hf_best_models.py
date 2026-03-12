import sqlite3
import math
import os
import re
import json
import hashlib
import asyncio

import requests
import time
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from contextlib import contextmanager
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rapidfuzz import fuzz
from huggingface_hub import HfApi, get_safetensors_metadata, ModelInfo

from config import (
    DB_FILE,
    MD_REPORT_FILE,
    HF_API,
    HF_JSON_API,
    HF_TOKEN,
    SEARCH_LIMIT,
    PAGES_TO_FETCH,
    DEEP_SCAN_CACHE_TTL,
    BLACKLIST_KEYWORDS,
    GGUF_KINGS,
)


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
    similarity_score: float = 0.0
    categories: List[str] = field(default_factory=list)

    @property
    def author(self) -> str:
        if "/" in self.id:
            return self.id.split("/")[0]
        return "unknown"

    @property
    def name(self) -> str:
        if "/" in self.id:
            return self.id.split("/", 1)[1]
        return self.id

    @property
    def hf_url(self) -> str:
        return f"https://huggingface.co/{self.id}"


def extract_base_model_name(model_id: str) -> str:
    """
    Извлекает базовое имя модели из полного ID.
    bartowski/Qwen3-32B-GGUF -> qwen3-32b
    unsloth/Qwen3-32B-GGUF -> qwen3-32b
    NousResearch/Meta-Llama-3.1-70B-Instruct -> llama-3.1-70b
    """
    name = model_id.lower()

    parts = name.split("/")
    base_name = parts[-1] if len(parts) > 1 else parts[0]

    base_name = re.sub(r"[-_\.]?gguf$", "", base_name)
    base_name = re.sub(r"[-_\.]?unsloth$", "", base_name)
    base_name = re.sub(r"[-_\.]?thebloke$", "", base_name)
    base_name = re.sub(r"[-_\.]?guff$", "", base_name)

    base_name = re.sub(r"v(\d+(\.\d+)*)", "", base_name)
    base_name = re.sub(r"-instruct$", "", base_name)
    base_name = re.sub(r"-chat$", "", base_name)
    base_name = re.sub(r"-dp$", "", base_name)
    base_name = re.sub(r"-sft$", "", base_name)
    base_name = re.sub(r"-dpo$", "", base_name)
    base_name = re.sub(r"-orca-?\d*$", "", base_name)

    base_name = re.sub(r"(\d+)b", r"\1b", base_name)
    base_name = re.sub(r"(\d+)m", r"\1m", base_name)

    base_name = re.sub(r"[-_]+", "-", base_name)
    base_name = base_name.strip("-")

    return base_name

async def fetch_model_params_batch(
        models: List["ModelInfo"],
        cache_manager: "CacheManager" = None,
        api: HfApi = None,
        max_concurrent: int = 10,
        timeout_seconds: float = 60.0,
) -> Dict[str, float]:
    """
    Асинхронно запрашивает параметры для списка моделей.
    Возвращает dict {model_id: params_b}.
    """
    if not models:
        return {}

    if api is None:
        api = HfApi()

    cache_hits: Dict[str, float] = {}
    models_to_fetch: List["ModelInfo"] = []

    for m in models:
        if cache_manager:
            cached = cache_manager.get_model_params(m.id)
            if cached is not None:
                cache_hits[m.id] = cached
                m.parsed_params_b = cached
                continue
        models_to_fetch.append(m)

    if not models_to_fetch:
        return cache_hits

    results: Dict[str, float] = {}
    completed = 0
    start_time = time.time()

    for m in models_to_fetch:
        if time.time() - start_time > timeout_seconds:
            print(
                f"  [ENRICH] Timeout reached, stopping at {completed}/{len(models_to_fetch)}"
            )
            break

        try:
            params = _fetch_params_sync(m.id, api)
            if params is not None:
                results[m.id] = params
                m.parsed_params_b = params
                if cache_manager:
                    cache_manager.set_model_params(m.id, params)
            completed += 1

            if completed % 5 == 0:
                print(f"  [ENRICH] Progress: {completed}/{len(models_to_fetch)}")

        except Exception as e:
            completed += 1
            print(f"  [ENRICH ERROR] {m.id}: {e}")

    print(
        f"  [ENRICH] Completed {completed}/{len(models_to_fetch)} in {time.time() - start_time:.1f}s"
    )
    return {**cache_hits, **results}


def _fetch_params_sync(model_id: str, api: HfApi) -> Optional[float]:
    """
    Синхронная обёртка для получения параметров модели.
    """
    try:
        info = api.model_info(model_id)

        if hasattr(info, "gguf") and info.gguf:
            gguf_info = info.gguf
            if isinstance(gguf_info, dict):
                total = gguf_info.get("total")
                if total and isinstance(total, (int, float)):
                    return total / 1e9

                params = gguf_info.get("parameters")
                if params:
                    if isinstance(params, (int, float)):
                        return params / 1e9
                    elif isinstance(params, str):
                        if "b" in params.lower():
                            match = re.search(r"([\d.]+)", params)
                            return float(match.group(1)) if match else None
                        elif "m" in params.lower():
                            match = re.search(r"([\d.]+)", params)
                            return float(match.group(1)) / 1000 if match else None

        try:
            metadata = get_safetensors_metadata(model_id)
            if hasattr(metadata, "parameter_count") and metadata.parameter_count:
                total_params = sum(metadata.parameter_count.values())
                return total_params / 1e9
        except Exception:
            pass

        config = getattr(info, "config", None)
        if config and isinstance(config, dict):
            hidden_size = config.get("hidden_size")
            num_layers = config.get("num_layers", config.get("n_layers", 0))
            num_heads = config.get("num_attention_heads", config.get("n_heads", 0))
            num_key_value_heads = config.get("num_key_value_heads", num_heads)
            vocab_size = config.get("vocab_size", 0)

            if hidden_size and num_layers and num_heads and vocab_size:
                approx_params = (
                                        hidden_size * num_layers * 3 + vocab_size * hidden_size
                                ) * 2
                if num_key_value_heads != num_heads:
                    approx_params += hidden_size * num_layers * 2
                return approx_params / 1e9

    except Exception:
        pass

    return None


class CacheManager:
    def __init__(self, db_path: str = "hf_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                data TEXT,
                timestamp TEXT,
                ttl_seconds INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_params_cache (
                model_id TEXT PRIMARY KEY,
                params_b REAL,
                fetched_at TEXT
            )
        """)

        self.conn.commit()

    def get(self, key: str) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data, ttl_seconds FROM cache WHERE key = ? AND ttl_seconds IS NOT NULL",
            (key,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        data, ttl = row
        cached_time = datetime.fromisoformat(self._get_timestamp(key))
        elapsed = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if elapsed > ttl:
            return None
        return data

    def set(self, key: str, data: str, ttl_seconds: int = 3600):
        cursor = self.conn.cursor()
        cursor.execute(
            "REPLACE INTO cache (key, data, timestamp, ttl_seconds) VALUES (?, ?, ?, ?)",
            (key, data, datetime.now(timezone.utc).isoformat(), ttl_seconds),
        )
        self.conn.commit()

    def _get_timestamp(self, key: str) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT timestamp FROM cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else datetime.now(timezone.utc).isoformat()

    def get_model_params(self, model_id: str) -> Optional[float]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT params_b, fetched_at FROM model_params_cache WHERE model_id = ?",
            (model_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        params = row[0]

        suspicious_versions = [
            4.0,
            4.1,
            4.2,
            4.3,
            4.4,
            4.5,
            4.6,
            4.7,
            4.8,
            4.9,
            3.5,
            3.0,
            2.0,
            1.0,
            1.5,
            2.5,
            3.1,
            3.2,
            3.3,
            3.4,
        ]

        if params < 0.5 or params > 1000 or params in suspicious_versions:
            cursor.execute(
                "DELETE FROM model_params_cache WHERE model_id = ?", (model_id,)
            )
            self.conn.commit()
            return None
        return params

    def validate_and_cleanup_params_cache(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT model_id, params_b FROM model_params_cache")
        invalid_count = 0

        suspicious_versions = [
            4.0,
            4.1,
            4.2,
            4.3,
            4.4,
            4.5,
            4.6,
            4.7,
            4.8,
            4.9,
            3.5,
            3.0,
            2.0,
            1.0,
            1.5,
            2.5,
            3.1,
            3.2,
            3.3,
            3.4,
        ]

        for row in cursor.fetchall():
            model_id, params = row
            if params < 0.5 or params > 1000 or params in suspicious_versions:
                cursor.execute(
                    "DELETE FROM model_params_cache WHERE model_id = ?", (model_id,)
                )
                invalid_count += 1

        self.conn.commit()
        return invalid_count

    def set_model_params(self, model_id: str, params_b: float):
        cursor = self.conn.cursor()
        cursor.execute(
            "REPLACE INTO model_params_cache (model_id, params_b, fetched_at) VALUES (?, ?, ?)",
            (model_id, params_b, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


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
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_model_run ON snapshots(model_id, run_id)"
            )

            conn.execute("""
                CREATE TABLE IF NOT EXISTS specialized_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    model_id TEXT,
                    model_data TEXT,
                    author TEXT,
                    fetched_at TEXT,
                    UNIQUE(category, model_id)
                )
            """)

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_spec_category ON specialized_models(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_spec_author ON specialized_models(author)"
            )

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

    def reset_rankings(self):
        """Удаляет только рейтинги (runs, snapshots), сохраняя model_params_cache."""
        with self._connect() as conn:
            conn.execute("DELETE FROM snapshots")
            conn.execute("DELETE FROM runs")

    def _generate_config_key(self, params: Dict[str, Any]) -> str:
        return f"{params.get('mode')}_{params.get('min')}_{params.get('max')}"

    def get_last_state(
            self, config_hash: str
    ) -> Tuple[Dict[str, Dict], Optional[datetime]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp FROM runs WHERE config_hash = ? ORDER BY id DESC LIMIT 1",
                (config_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return {}, None

            last_run_id = row[0]
            last_ts = datetime.fromisoformat(row[1])

            cursor = conn.execute(
                "SELECT model_id, rank, velocity FROM snapshots WHERE run_id = ?",
                (last_run_id,),
            )
            state = {r[0]: {"rank": r[1], "velocity": r[2]} for r in cursor.fetchall()}
            return state, last_ts

    def save_snapshot(self, models: List[ModelInfo], run_params: Dict[str, Any]):
        if not models:
            return
        config_key = self._generate_config_key(run_params)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (timestamp, config_hash, mode) VALUES (?, ?, ?)",
                (now_iso, config_key, run_params.get("mode")),
            )
            run_id = cur.lastrowid

            data = [
                (run_id, m.id, m.rank, m.velocity, m.combined_score) for m in models
            ]
            conn.executemany(
                "INSERT INTO snapshots (run_id, model_id, rank, velocity, score) VALUES (?, ?, ?, ?, ?)",
                data,
            )


# --- FETCHER ---
class HFFetcher:
    def __init__(self):
        self.session = requests.Session()
        retries = Retry(
            total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Authorization": f"Bearer {HF_TOKEN}" if HF_TOKEN else "",
            }
        )
        self.cache = CacheManager()
        self.hf_api = HfApi()
        self._last_deep_scan = None

    def _get_cache_key(self, *args) -> str:
        key_str = "_".join(str(a) for a in args)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cache_valid(self, key: str, ttl: int = DEEP_SCAN_CACHE_TTL) -> bool:
        data = self.cache.get(key)
        return data is not None

    def _save_cache(
            self, key: str, data: List[ModelInfo], ttl: int = DEEP_SCAN_CACHE_TTL
    ):
        models_data = [
            {
                "id": m.id,
                "downloads": m.downloads,
                "likes": m.likes,
                "timestamp": m.timestamp.isoformat(),
                "tags": m.tags,
                "pipeline_tag": m.pipeline_tag,
                "size_bytes": m.size_bytes,
            }
            for m in data
        ]
        self.cache.set(key, json.dumps(models_data), ttl)

    def _load_cache(self, key: str) -> Optional[List[ModelInfo]]:
        data = self.cache.get(key)
        if not data:
            return None

        models_data = json.loads(data)
        models = []
        for m in models_data:
            dt = datetime.fromisoformat(m["timestamp"])
            models.append(
                ModelInfo(
                    id=m["id"],
                    downloads=m["downloads"],
                    likes=m["likes"],
                    timestamp=dt,
                    tags=m.get("tags", []),
                    pipeline_tag=m.get("pipeline_tag", ""),
                    size_bytes=m.get("size_bytes"),
                )
            )
        return models

    def _fetch_stream(self, strategy: Dict, max_pages: int) -> List[Dict]:
        results = []
        for p in range(max_pages):
            time.sleep(random.uniform(0.3, 0.8))
            params = strategy.copy()
            # Если sort вызывает 400, убираем его и фильтруем локально
            if params.get('sort') == 'trending':
                params.pop('sort')
            params["p"] = p
            try:
                resp = self.session.get(HF_JSON_API, params=params, timeout=12)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    if not models:
                        break
                    results.extend(models)
                elif resp.status_code == 429:
                    time.sleep(5)
            except Exception:
                pass
        return results

    def fetch_by_query(
            self,
            query: str,
            author: str = None,
            limit: int = SEARCH_LIMIT,
            pipeline_tag: str = "text-generation",
            use_cache: bool = True,
    ) -> List[Dict]:
        """
        Поиск моделей через официальный HF API.
        """
        cache_key = self._get_cache_key("query", query, author, limit)

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                data = json.loads(cached)
                print(
                    f'  [CACHE] query="{query}" author={author} ({len(data)} results)'
                )
                return data

        params = {
            "search": query,
            "filter": "gguf",
            "pipeline_tag": pipeline_tag,
            "limit": limit,
            "full": "true",
        }

        if author:
            params["author"] = author

        for retry_count in range(3):
            try:
                time.sleep(0.3)
                resp = self.session.get(HF_API, params=params, timeout=15)

                if resp.status_code == 200:
                    data = resp.json()
                    print(
                        f'  [API] query="{query}" author={author} ({len(data)} results)'
                    )
                    if use_cache:
                        self.cache.set(cache_key, json.dumps(data), 1800)
                    return data
                elif resp.status_code == 429:
                    print(f"  [WARN] HF API rate limited, retry {retry_count + 1}/3")
                    time.sleep(5 * (retry_count + 1))
                    continue
                else:
                    print(f"  [ERROR] HF API error: {resp.status_code}")
                    return []
            except Exception as e:
                print(f"  [ERROR] HF API request failed: {e}")
                time.sleep(2)
                continue

        print(f'  [ERROR] Max retries exceeded for query="{query}"')
        return []

    def fetch_specialized(
            self,
            query: str = "",
            author: str = None,
            limit: int = 1000,
            tags: List[str] = None,
            use_cache: bool = True,
    ) -> List[Dict]:
        """
        Fetch specialized models by category tags.
        """
        cache_key = self._get_cache_key(
            "spec", query, author, limit, ",".join(tags) if tags else ""
        )

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                data = json.loads(cached)
                tags_str = ",".join(tags) if tags else "all"
                print(f"  [CACHE] tags={tags_str} ({len(data)} results)")
                return data

        params = {
            "search": query,
            "filter": "gguf",
            "limit": limit,
            "full": "true",
        }

        if tags:
            params["tags"] = ",".join(tags)

        if author:
            params["author"] = author

        for retry_count in range(3):
            try:
                time.sleep(0.3)
                resp = self.session.get(HF_API, params=params, timeout=20)

                if resp.status_code == 200:
                    data = resp.json()
                    tags_str = ",".join(tags) if tags else "all"
                    print(f"  [API] tags={tags_str} ({len(data)} results)")
                    if use_cache:
                        self.cache.set(cache_key, json.dumps(data), 3600)
                    return data
                elif resp.status_code == 429:
                    print(f"  [WARN] HF API rate limited, retry {retry_count + 1}/3")
                    time.sleep(5 * (retry_count + 1))
                    continue
                else:
                    print(f"  [ERROR] HF API error: {resp.status_code}")
                    return []
            except Exception as e:
                print(f"  [ERROR] HF API request failed: {e}")
                time.sleep(2)
                continue

        print(f"  [ERROR] Max retries exceeded for specialized fetch")
        return []

    def fetch_deep_scan(self, force_refresh: bool = False) -> List[ModelInfo]:
        strategies = [
            {"sort": "trending", "filter": "gguf"},
            {"sort": "lastModified", "filter": "gguf"},
            {"sort": "downloads", "filter": "gguf"},
            {"sort": "likes", "filter": "gguf"},
        ]

        cache_key = self._get_cache_key("deep", len(strategies), PAGES_TO_FETCH)

        if not force_refresh:
            cached = self._load_cache(cache_key)
            if cached:
                print(
                    f"[CACHE] Deep scan (less than {DEEP_SCAN_CACHE_TTL // 60} min old, {len(cached)} models)"
                )
                self._last_deep_scan = cached
                return cached
            else:
                print(
                    f"[NETWORK] [CACHE MISS] Empty or invalid cache, fetching from API"
                )

        print(f"[NETWORK] SCANNING HF via HfApi...")
        unique_models: Dict[str, ModelInfo] = {}

        # Используем библиотечный метод, он сам обрабатывает лимиты и параметры
        # direction=-1 — это сортировка по убыванию (как в вашем старом коде)
        # filter="gguf" — это официальный фильтр библиотеки
        try:
            # Получаем итератор моделей
            cursor = self.hf_api.list_models(
                filter="gguf",
                sort="downloads",
                direction=-1,
                limit=500, # Можно поставить больше
                full=True
            )

            for model_info in cursor:
                mid = model_info.id
                if mid in unique_models:
                    continue

                # Фильтрация по blacklist (ваша логика)
                if any(bad in mid.lower() for bad in BLACKLIST_KEYWORDS):
                    continue

                # Преобразование объекта ModelInfo из библиотеки в ваш объект ModelInfo
                model = ModelInfo(
                    id=mid,
                    downloads=model_info.downloads,
                    likes=model_info.likes,
                    timestamp=model_info.lastModified,
                    tags=model_info.tags,
                    pipeline_tag=model_info.pipeline_tag or "",
                    size_bytes=None # Параметры размера часто лежат в meta, если нужно
                )
                unique_models[mid] = model

        except Exception as e:
            print(f"[ERROR] HF API fetch failed: {e}")

        result = list(unique_models.values())
        self._save_cache(cache_key, result, DEEP_SCAN_CACHE_TTL)
        return result


# --- RANKER ---
class GGUFModelRanker:
    def __init__(self):
        self.fetcher = HFFetcher()
        self.history = RankingHistoryManager()
        self._cache = None
        self._last_time_delta_str = "new"
        self._report_buffer = []
        self._search_cache = {}
        self._params_cache = CacheManager()
        self._dedup_cache = {}

    def _fuzzy_match_score(
            self, query: str, m: ModelInfo, fields: List[str] = None
    ) -> float:
        if fields is None:
            fields = ["name"]

        parts = []
        if "author" in fields:
            parts.append(m.author)
        if "name" in fields:
            parts.append(m.name)
        if "tags" in fields and m.tags:
            parts.extend(m.tags)

        target = " ".join(parts)
        target_lower = target.lower()
        query_lower = query.lower()

        if query_lower in target_lower:
            return 100.0

        w_score = fuzz.WRatio(query, target, processor=lambda x: x.lower())
        p_score = fuzz.partial_ratio(query.lower(), target.lower())
        return (w_score + p_score) / 2

    def _adaptive_threshold(
            self, query: str, base: int = 85, min_thresh: int = 70
    ) -> int:
        length_penalty = len(query) * 2
        return max(min_thresh, base - length_penalty)

    def _parse_model_info(
            self, api_data: List[Dict], strict_pipeline_tag: bool = True
    ) -> List[ModelInfo]:
        """
        Парсит результаты HF API в ModelInfo.
        Args:
            api_data: Список словарей с данными моделей из HF API.
            strict_pipeline_tag: Если True, применяет строгую фильтрацию по pipeline_tag.
        """
        models = []
        for item in api_data:
            tags = item.get("tags", [])
            if "gguf" not in tags: # Проверка наличия тега, а не только фильтра API
                continue

            mid = item.get("id")
            if not mid:
                continue

            if any(bad in mid.lower() for bad in BLACKLIST_KEYWORDS):
                continue

            pipeline = item.get("pipeline_tag", "")
            if (
                    strict_pipeline_tag
                    and pipeline
                    and pipeline
                    not in [
                "text-generation",
                "text-generation-inference",
                "conversational",
                "fill-mask",
            ]
            ):
                continue

            dt_str = item.get("lastModified") or item.get("createdAt")
            dt = (
                datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if dt_str
                else datetime.now(timezone.utc)
            )

            meta = item.get("params", {})

            model = ModelInfo(
                id=mid,
                downloads=item.get("downloads", 0),
                likes=item.get("likes", 0),
                timestamp=dt,
                tags=item.get("tags", []),
                pipeline_tag=pipeline,
                size_bytes=meta.get("bs") if meta else None,
            )
            models.append(model)
        return models

    def search_models(
            self,
            query: str,
            mode: RankingMode = RankingMode.STABLE,
            min_b: Optional[float] = None,
            max_b: Optional[float] = None,
            top_n: int = 20,
            author: str = None,
            search_fields: List[str] = None,
            use_hf_api: Optional[bool] = None,
    ) -> List[ModelInfo]:
        if search_fields is None:
            search_fields = ["name"]

        cache_key = f"{query}_{mode.value}_{min_b}_{max_b}_{author}_{use_hf_api}_{'_'.join(search_fields)}"
        if hasattr(self, "_search_cache") and cache_key in self._search_cache:
            return self._search_cache[cache_key]

        source = "unknown"
        models = []

        if use_hf_api is None:
            if author:
                api_results = self.fetcher.fetch_by_query(
                    query, author=author, limit=SEARCH_LIMIT
                )
                if api_results:
                    models = self._parse_model_info(api_results)
                    source = "HF API"
                else:
                    models = self.prepare_data()
                    source = "local cache (API fallback)"
            else:
                models = self.prepare_data()
                source = "local cache"
        elif use_hf_api:
            api_results = self.fetcher.fetch_by_query(
                query, author=author, limit=SEARCH_LIMIT
            )
            models = self._parse_model_info(api_results)
            source = "HF API (forced)"
        else:
            models = self.prepare_data()
            source = "local cache (forced)"

        threshold = self._adaptive_threshold(query)
        candidates = []

        for m in models:
            m.similarity_score = self._fuzzy_match_score(query, m, search_fields)
            if m.similarity_score < threshold:
                continue

            sz = self.extract_size_billions(m)
            m.parsed_params_b = sz if sz else 0.0

            if min_b or max_b:
                if sz is None:
                    continue
                if min_b and sz < min_b:
                    continue
                if max_b and sz > max_b:
                    continue

            if sz is None and mode == RankingMode.TRENDING and m.likes < 3:
                continue

            m.combined_score = self._score_model(m, mode)
            candidates.append(m)

        candidates.sort(
            key=lambda x: (x.combined_score, x.similarity_score), reverse=True
        )

        run_params = {
            "mode": mode.value,
            "min": min_b,
            "max": max_b,
            "n": top_n,
            "query": query,
            "source": source,
        }
        result = self._process_history(candidates[:top_n], run_params)

        if not hasattr(self, "_search_cache"):
            self._search_cache = {}

        result = self._deduplicate_models(result)

        self._search_cache[cache_key] = result
        return result

    def _deduplicate_models(self, models: List[ModelInfo]) -> List[ModelInfo]:
        """
        Дедуплицирует модели по базовому имени.
        Оставляет только лучшего провайдера (по downloads/likes) для каждой базовой модели.
        """
        base_to_models: Dict[str, List[ModelInfo]] = {}

        for m in models:
            base_name = extract_base_model_name(m.id)
            if base_name not in base_to_models:
                base_to_models[base_name] = []
            base_to_models[base_name].append(m)

        result = []
        for base_name, model_list in base_to_models.items():
            if len(model_list) == 1:
                best = model_list[0]
            else:
                best = max(model_list, key=lambda x: (x.downloads, x.likes))
                for m in model_list:
                    if m.id != best.id:
                        m.similarity_score = -1

            result.append(best)

        result.sort(key=lambda x: x.combined_score, reverse=True)
        return result

    def _parse_params_from_name(self, m: ModelInfo) -> Optional[float]:
        """Парсит параметры из названия модели и тегов."""
        mid = m.id.lower()

        moe = re.search(r"(\d+)x(\d+(?:\.\d+)?)b", mid)
        if moe:
            return float(moe.group(1)) * float(moe.group(2))

        std = re.search(
            r"(?:^|[_\-\./])(\d+(?:\.\d+)?)b(?:[_\-\./]v\d|[_\-\./]|$)", mid
        )
        if std:
            return float(std.group(1))

        mill = re.search(r"(?:^|[_\-\./])(\d+(?:\.\d+)?)m(?:[_\-\./]|$)", mid)
        if mill:
            return float(mill.group(1)) / 1000.0

        for tag in m.tags:
            tag_lower = tag.lower()
            if re.match(r"^\d+(?:\.\d+)?b$", tag_lower):
                return float(tag_lower.replace("b", ""))
            if re.match(r"^\d+(?:\.\d+)?m$", tag_lower):
                return float(tag_lower.replace("m", "")) / 1000

        return None

    def extract_size_billions(
            self, m: ModelInfo, fetch_if_missing: bool = False
    ) -> Optional[float]:
        if m.size_bytes:
            return round(m.size_bytes / 1_000_000_000, 1)

        cached = self._params_cache.get_model_params(m.id)
        if cached is not None:
            return cached

        params = self._parse_params_from_name(m)
        if params:
            self._params_cache.set_model_params(m.id, params)
            return params

        if fetch_if_missing:
            try:
                params = _fetch_params_sync(m.id, self.fetcher.hf_api)
                if params:
                    self._params_cache.set_model_params(m.id, params)
                    return params
            except Exception:
                pass

        return None

    def prepare_data(self):
        if not self._cache:
            self._cache = self.fetcher.fetch_deep_scan()
            for m in self._cache:
                sz = self._parse_params_from_name(m)
                m.parsed_params_b = sz if sz else 0.0
        return self._cache

    def get_ranked_list(self, mode, min_b=None, max_b=None, top_n=20):
        models = self.prepare_data()
        run_params = {"mode": mode.value, "min": min_b, "max": max_b, "n": top_n}
        candidates = []

        for m in models:
            sz = self.extract_size_billions(m)
            m.parsed_params_b = sz if sz else 0.0

            if min_b or max_b:
                if sz is None:
                    continue
                if min_b and sz < min_b:
                    continue
                if max_b and sz > max_b:
                    continue

            if sz is None and mode == RankingMode.TRENDING and m.likes < 3:
                continue

            m.combined_score = self._score_model(m, mode)
            if m.combined_score > 0.001:
                candidates.append(m)

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
            if hours > 720:
                return 0.0
            if m.likes == 0 and hours > 12.0:
                return 0.0
            points = (m.likes * 150) + (math.log10(m.downloads + 1) * 30)
            return points / pow(hours + 2.0, 1.4)

    def _process_history(self, models: List[ModelInfo], run_params: Dict):
        config_key = self.history._generate_config_key(run_params)
        last_state, last_ts = self.history.get_last_state(config_key)
        now = datetime.now(timezone.utc)

        if last_ts:
            delta_run = now - last_ts
            if delta_run.days > 0:
                self._last_time_delta_str = f"{delta_run.days}d"
            elif delta_run.seconds > 3600:
                self._last_time_delta_str = f"{delta_run.seconds // 3600}h"
            elif delta_run.seconds > 60:
                self._last_time_delta_str = f"{delta_run.seconds // 60}m"
            else:
                self._last_time_delta_str = f"{delta_run.seconds}s"
        else:
            self._last_time_delta_str = "new"

        for idx, m in enumerate(models, 1):
            m.rank = idx
            delta = now - m.timestamp
            days = max(0.5, delta.total_seconds() / 86400)

            if delta.days < 1:
                m.age_str = f"{int(delta.seconds // 3600)}h"
            elif delta.days < 30:
                m.age_str = f"{delta.days}d"
            else:
                m.age_str = f"{delta.days // 30}M"

            m.velocity = m.downloads / days

            if m.id in last_state:
                prev = last_state[m.id]
                m.rank_delta = prev["rank"] - idx
                m.accel = m.velocity - prev["velocity"]
            else:
                m.rank_delta = "new"
                m.accel = 0.0

        self.history.save_snapshot(models, run_params)
        return models

    # --- ЛОГИКА ВЫВОДА (CONSOLE + MARKDOWN) ---
    def _visual_len(self, text: str) -> int:
        clean_text = re.sub(r"\x1b\[[0-9;]*m", "", text)
        return len(clean_text)

    def _pad_string(self, text: str, width: int, visual_len: int = None) -> str:
        if visual_len is None:
            visual_len = self._visual_len(text)
        padding = max(0, width - visual_len)
        return text + (" " * padding)

    def buffer_markdown_table(self, models: List[ModelInfo], title: str):
        """Добавляет таблицу в буфер отчета Markdown"""
        has_categories = any(hasattr(m, "categories") and m.categories for m in models)

        if has_categories:
            header = "| # | [DELTA] | CATS | Age | Model ID | Size(B) | DLs | Likes |\n|---|---|---|---|---|---|---|---|"
        else:
            header = "| # | [DELTA] | SIM | Age | Model ID | Size(B) | DLs | Likes | Accel |\n|---|---|---|---|---|---|---|---|---|"

        self._report_buffer.append(f"\n## {title}\n")
        self._report_buffer.append(header)

        for m in models:
            dr_str = "NEW"
            if m.rank_delta != "new":
                if m.rank_delta > 0:
                    dr_str = f"UP {m.rank_delta}"
                elif m.rank_delta < 0:
                    dr_str = f"DOWN {abs(m.rank_delta)}"
                else:
                    dr_str = "---"

            acc_str = "---"

            sim_str = f"{m.similarity_score:.0f}" if m.similarity_score > 0 else "---"

            if m.rank_delta != "new":
                acc_str = f"{m.accel:+.1f}"

            model_link = f"[{m.author}/{m.name}]({m.hf_url})"
            sz_str = f"{m.parsed_params_b:.1f}" if m.parsed_params_b > 0 else "?"
            dl_str = (
                f"{m.downloads / 1000:.1f}k"
                if m.downloads >= 1000
                else str(m.downloads)
            )

            if has_categories:
                cats_str = (
                    ", ".join(m.categories)
                    if hasattr(m, "categories") and m.categories
                    else "---"
                )
                row = f"| {m.rank} | {dr_str} | {cats_str} | {m.age_str} | {model_link} | {sz_str} | {dl_str} | {m.likes} |"
            else:
                row = f"| {m.rank} | {dr_str} | {sim_str} | {m.age_str} | {model_link} | {sz_str} | {dl_str} | {m.likes} | {acc_str} |"

            self._report_buffer.append(row)
        self._report_buffer.append(
            f"\n_Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        )

    def save_markdown_report(self):
        """Сохраняет буфер в файл"""
        with open(MD_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# 🏆 Hugging Face Model Ranking Report\n")
            f.write(f"> **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"> **Scan Depth:** {PAGES_TO_FETCH} pages per category\n")
            f.write("\n".join(self._report_buffer))
        print(f"\n📄 Report saved to: {MD_REPORT_FILE}")

    def print_table(self, models: List[ModelInfo], title: str):
        has_categories = any(hasattr(m, "categories") and m.categories for m in models)

        if has_categories:
            W = 190
            col_model_w = 65
            cats_col_w = 20
            header = (
                f"{'#':^4} | {'[DELTA]':^4} | {'CATS':<{cats_col_w}} | {'AGE':^5} | "
                f"{'MODEL ID (Author / Model)':<{col_model_w}} | {'SZ(B)':^6} | {'DLs':^8} | {'LIKES':^6}"
            )
        else:
            W = 175
            col_model_w = 75
            accel_title = f"ACCEL({self._last_time_delta_str})"
            header = (
                f"{'#':^4} | {'[DELTA]':^4} | {'SIM':^4} | {'AGE':^5} | "
                f"{'MODEL ID (Author / Model)':<{col_model_w}} | {'SZ(B)':^6} | {'DLs':^8} | {'LIKES':^6} | {accel_title:^11}"
            )

        print(f"\n{'=' * W}")
        print(f"{title:^{W}}")
        print(f"{'=' * W}")
        print(header)
        print("-" * W)

        if not models:
            print(f"{'NO DATA':^{W}}")

        for m in models:
            dr_str = "NEW"
            if m.rank_delta != "new":
                if m.rank_delta > 0:
                    dr_str = f"UP {m.rank_delta}"
                elif m.rank_delta < 0:
                    dr_str = f"DOWN {abs(m.rank_delta)}"
                else:
                    dr_str = "---"

            acc_str = "---"

            sim_str = f"{m.similarity_score:.0f}" if m.similarity_score > 0 else "---"

            if m.rank_delta != "new":
                acc_str = f"{m.accel:+.1f}"

            visible_text = f"{m.author}/{m.name}"
            if len(visible_text) > (col_model_w - 2):
                avail_len = col_model_w - len(m.author) - 5
                trunc_name = m.name[:avail_len] + "..."
                visible_text = f"{m.author}/{trunc_name}"

            if "/" in visible_text:
                auth, nm = visible_text.split("/", 1)
                colored_text = f"\033[36m{auth}\033[0m/{nm}"
            else:
                colored_text = visible_text

            padded_model = self._pad_string(
                colored_text, col_model_w, len(visible_text)
            )
            sz_str = f"{m.parsed_params_b:.1f}" if m.parsed_params_b > 0 else "?"
            dl_str = (
                f"{m.downloads / 1000:.1f}k"
                if m.downloads >= 1000
                else str(m.downloads)
            )

            if has_categories:
                cats_str = (
                    ", ".join(m.categories)
                    if hasattr(m, "categories") and m.categories
                    else "---"
                )
                print(
                    f"{m.rank:^4} | {dr_str:^4} | {cats_str:<{cats_col_w}} | {m.age_str:^5} | "
                    f"{padded_model} | {sz_str:^6} | {dl_str:>8} | {m.likes:>6}"
                )
            else:
                print(
                    f"{m.rank:^4} | {dr_str:^4} | {sim_str:^4} | {m.age_str:^5} | {padded_model} | {sz_str:^6} | {dl_str:>8} | {m.likes:>6} | {acc_str:>11}"
                )

        print("=" * W)
        if has_categories:
            print(
                f"👉 \033[36mCyan\033[0m = Author. CATS = Categories (VL=Vision-Language, MULTI=Multimodal, THINK=Thinking, TOOLS=Tools, CODE=Code, EMBED=Embedding)."
            )
        else:
            print(
                f"[LINK] \033[36mCyan\033[0m = Author. Clean format (No Links). SIM = Fuzzy Match Score (0-100)."
            )

        # 2. Добавляем в Markdown буфер
        self.buffer_markdown_table(models, title)

    async def enrich_unknown_params(
            self,
            models: List[ModelInfo],
            max_concurrent: int = 10,
            timeout_seconds: float = 60.0,
    ) -> int:
        """
        Обогащает модели с неизвестными параметрами через HF API.
        Возвращает количество успешно обновлённых моделей.
        """
        unknown = [
            m for m in models if m.parsed_params_b == 0 or m.parsed_params_b is None
        ]

        if not unknown:
            return 0

        print(f"  [ENRICH] Fetching params for {len(unknown)} models...")

        try:
            results = await fetch_model_params_batch(
                models=unknown,
                cache_manager=self._params_cache,
                api=self.fetcher.hf_api,
                max_concurrent=max_concurrent,
                timeout_seconds=timeout_seconds,
            )

            enriched_count = len(results)
            for m in unknown:
                if m.id not in results:
                    m.parsed_params_b = 0

            if enriched_count == 0:
                print(f"  [ENRICH] No params fetched from API")

            return enriched_count

        except Exception as e:
            print(f"  [ENRICH ERROR] {e}")
            return 0


# --- SPECIALIZED RANKER ---
class SpecializedRanker:
    CATEGORIES = {
        "VISION-LANGUAGE": {
            "tags": ["vision", "vl", "vision-language", "image-text", "image-to-text"],
        },
        "MULTIMODAL": {"tags": ["multimodal"]},
        "THINKING": {"tags": ["thinking", "reasoning", "cot", "chain-of-thought"]},
        "TOOLS": {"tags": ["tools", "agent", "function-calling", "tool-use"]},
        "CODE": {"tags": ["code", "codegen", "programming", "code-generation"]},
        "EMBEDDING": {"tags": ["embedding", "embedders", "sentence-transformers"]},
    }

    def __init__(self, base_ranker, history_manager, default_author=None):
        self.base = base_ranker
        self.history = history_manager
        self.default_author = default_author
        self._cache = {}
        self._cache_manager = CacheManager("hf_cache.db")

    def _save_to_cache(self, category: str, models: List[ModelInfo]):
        key = f"spec_{category}"
        models_data = [
            {
                "id": m.id,
                "downloads": m.downloads,
                "likes": m.likes,
                "parsed_params_b": m.parsed_params_b,
                "timestamp": m.timestamp.isoformat(),
                "author": m.author,
            }
            for m in models
        ]
        self._cache_manager.set(key, json.dumps(models_data), 3600)

    def _load_from_cache(self, category: str) -> List[ModelInfo]:
        key = f"spec_{category}"
        cached = self._cache_manager.get(key)
        if not cached:
            return []

        models_data = json.loads(cached)
        models = []
        for m in models_data:
            timestamp = (
                datetime.fromisoformat(m["timestamp"])
                if m.get("timestamp")
                else datetime.now(timezone.utc)
            )
            model = ModelInfo(
                id=m["id"],
                downloads=m.get("downloads", 0),
                likes=m.get("likes", 0),
                timestamp=timestamp,
                tags=[],
                pipeline_tag="text-generation",
                size_bytes=None,
            )
            model.parsed_params_b = m.get("parsed_params_b", 0.0)
            models.append(model)
        return models

    def fetch_all(self, author=None, timeout_seconds=60, force_refresh=False):
        author = author or self.default_author
        total_start = time.time()

        for category, config in self.CATEGORIES.items():
            if time.time() - total_start > timeout_seconds:
                print(f"  ⚠️  Timeout reached, stopping fetch")
                break

            cat_start = time.time()
            print(f"  Fetching {category}...")

            tags = config.get("tags", [])

            # Check cache first if not force refresh
            if not force_refresh:
                cached = self._load_from_cache(category)
                if cached and len(cached) > 0:
                    self._cache[category] = cached
                    print(f"  [CACHE] {category}: {len(cached)} models")
                    continue

            # Fetch from API
            api_results = self.base.fetcher.fetch_specialized(
                query="" if not author else author,
                author=author,
                limit=1000,
                tags=tags,
                use_cache=not force_refresh,
            )

            models = []
            if api_results:
                models = self.base._parse_model_info(
                    api_results, strict_pipeline_tag=False
                )
                if tags:
                    models = [
                        m
                        for m in models
                        if any(
                            tag_to_check.lower() in [t.lower() for t in m.tags]
                            for tag_to_check in tags
                        )
                    ]

            if models:
                self._cache[category] = models
                self._save_to_cache(category, models)
                print(f"  [API] {category}: {len(models)} models")
            else:
                # Fallback to local data
                local_models = self.base.prepare_data()
                models = [
                    m
                    for m in local_models
                    if any(
                        tag_to_check.lower() in [t.lower() for t in m.tags]
                        for tag_to_check in tags
                    )
                ]
                if models:
                    self._cache[category] = models
                    self._save_to_cache(category, models)
                    print(f"  [LOCAL] {category}: {len(models)} models")
                else:
                    print(f"  [EMPTY] {category}: No models found")

            self._cache[category] = models
            self._save_to_cache(category, models)
            print(
                f"    {category}: {len(models)} models ({time.time() - cat_start:.1f}s)"
            )

        print(f"  Total fetch time: {time.time() - total_start:.1f}s")

    def _filter_by_author(
            self, models: List[ModelInfo], author: str = None
    ) -> List[ModelInfo]:
        if not author:
            return models
        return [m for m in models if m.author.lower() == author.lower()]

    def _calculate_age(self, m: ModelInfo):
        """Calculate age_str from timestamp"""
        delta = datetime.now(timezone.utc) - m.timestamp
        if delta.days < 1:
            m.age_str = f"{int(delta.seconds // 3600)}h"
        elif delta.days < 30:
            m.age_str = f"{delta.days}d"
        else:
            m.age_str = f"{delta.days // 30}M"

    def _restore_categories_from_cache(self):
        """Restore categories for models loaded from persistent cache."""
        for category, models in self._cache.items():
            for m in models:
                if not hasattr(m, "categories") or not m.categories:
                    m.categories = [category]

    def get_ranking(
            self, category: str, top_n: int = 20, author: str = None
    ) -> List[ModelInfo]:
        if category not in self._cache:
            self._cache[category] = self._load_from_cache(category)
            self._restore_categories_from_cache()

        models = self._filter_by_author(self._cache[category], author)

        for m in models:
            m.parsed_params_b = self.base.extract_size_billions(m) or 0.0
            self._calculate_age(m)
            m.combined_score = self.base._score_model(m, RankingMode.STABLE)

        models.sort(key=lambda x: x.combined_score, reverse=True)
        return models[:top_n]

    def get_universal_models(
            self, min_categories: int = 3, top_n: int = 20, author: str = None
    ) -> List[ModelInfo]:
        # Ensure all categories are loaded and have categories assigned
        for category in self.CATEGORIES:
            if category not in self._cache:
                loaded = self._load_from_cache(category)
                if loaded:
                    self._cache[category] = loaded
                else:
                    print(f"  [CACHE MISS] {category} - fetching from API")
                    api_results = self.base.fetcher.fetch_specialized(
                        query="",
                        author=author,
                        limit=1000,
                        tags=self.CATEGORIES[category]["tags"],
                    )
                    if api_results:
                        models = self.base._parse_model_info(
                            api_results, strict_pipeline_tag=False
                        )
                        self._cache[category] = models
                        self._save_to_cache(category, models)

        self._restore_categories_from_cache()

        model_to_categories = {}

        for category, models in self._cache.items():
            filtered = self._filter_by_author(models, author)
            for m in filtered:
                m_cats = getattr(m, "categories", None)
                if not m_cats:
                    m_cats = [category]
                if m.id not in model_to_categories:
                    model_to_categories[m.id] = {"model": m, "categories": set(m_cats)}
                else:
                    model_to_categories[m.id]["categories"].update(m_cats)

        universal = []
        for data in model_to_categories.values():
            cat_count = len(data.get("categories", set()))
            if cat_count >= min_categories:
                universal.append({"model": data["model"], "cat_count": cat_count})

        for item in universal:
            m = item["model"]
            m.categories = list(item.get("categories", set()))
            m.parsed_params_b = self.base.extract_size_billions(m) or 0.0
            self._calculate_age(m)
            m.combined_score = self.base._score_model(m, RankingMode.STABLE)

        universal.sort(
            key=lambda x: (x["cat_count"], x["model"].combined_score), reverse=True
        )
        return [x["model"] for x in universal[:top_n]]

    def close(self):
        self._cache_manager.close()


if __name__ == "__main__":
    import sys
    import os

    force_refresh = "--force-refresh" in sys.argv or "-f" in sys.argv
    use_emoji = "--no-emoji" not in sys.argv

    print("=" * 80)
    if force_refresh:
        print("[REFRESH] FORCE REFRESH MODE - Rankings reset, params cache preserved")
        ranker = GGUFModelRanker()
        if hasattr(ranker.fetcher, "cache"):
            ranker.fetcher.cache.close()
        if hasattr(ranker, "_params_cache"):
            ranker._params_cache.close()
        import gc

        gc.collect()
        ranker.history.reset_rankings()
        print("  [OK] Rankings reset, model_params_cache preserved")
    else:
        if use_emoji:
            print("[CACHE] MODE - Using cached data")
        else:
            print("[CACHE MODE] Using cached data")

    # --- LOGO & HEADER ---

    ranker = GGUFModelRanker()

    if force_refresh:
        ranker.fetcher.fetch_deep_scan(force_refresh=True)
    ranker.prepare_data()

    # 1. Stable
    ranker.print_table(
        ranker.get_ranked_list(RankingMode.STABLE, min_b=6, max_b=32, top_n=20),
        "[STABLE] RANKING (6B - 32B)",
    )
    # 1. Stable
    ranker.print_table(
        ranker.get_ranked_list(RankingMode.STABLE, min_b=32, max_b=90, top_n=20),
        "[STABLE] RANKING (32B - 90B)",
    )

    # 2. Trending
    ranker.print_table(
        ranker.get_ranked_list(RankingMode.TRENDING, min_b=0, max_b=2000, top_n=50),
        "[TRENDING] GLOBAL (ALL SIZES)",
    )

    # 3. Edge
    ranker.print_table(
        ranker.get_ranked_list(RankingMode.TRENDING, min_b=0, max_b=5.5, top_n=20),
        "[EDGE] / MOBILE TRENDING (< 5.5B)",
    )

    # 4. GGUF PROVIDERS (Специальный режим)
    print("\n[INFO] Фильтрация: Только известные GGUF провайдеры...")

    all_models = ranker.prepare_data()
    # Фильтруем
    gguf_only = [
        m for m in all_models if m.author.lower() in [k.lower() for k in GGUF_KINGS]
    ]
    # Сортируем
    gguf_only.sort(
        key=lambda m: ranker._score_model(m, RankingMode.STABLE), reverse=True
    )

    # Переназначаем ранги для красивого вывода
    for i, m in enumerate(gguf_only, 1):
        m.rank = i
        m.rank_delta = "new"
        m.accel = 0.0

    ranker.print_table(
        gguf_only[:20],
        "[PROVIDERS] TOP GGUF PROVIDERS (Unsloth, TheBloke, Bartowski...)",
    )

    # 5. Fuzzy Search Demo
    print("\n" + "=" * 80)
    print("[INFO] HYBRID SEARCH DEMO (local cache + HF API fallback)")
    print("=" * 80)

    search_queries = [
        ("qwen3", 10),
        ("Qwen2.5", 10),
        ("gpt-oss", 10),
        ("deepseek", 10),
        ("minimax", 10),
        ("Devstral", 10),
        ("Kimi K2", 10),
        ("GLM", 10),
        ("Coder", 10),
        ("Gemma", 10),
    ]

    for query, top_n in search_queries:
        results = ranker.search_models(query, mode=RankingMode.STABLE, top_n=top_n)
        ranker.print_table(results, f'[SEARCH] "{query}"')

    # 5. HF API with Author Filter Demo
    print("\n" + "=" * 80)
    print("[INFO] HF API + AUTHOR FILTER DEMO (guaranteed fresh & complete)")
    print("=" * 80)

    hf_api_searches = [
        ("deepseek", "unsloth", 10),
        ("qwen", "unsloth", 10),
        ("minimax", "unsloth", 10),
        ("Devstral", "unsloth", 10),
        ("gpt-oss", "unsloth", 10),
        ("Kimi K2", "unsloth", 10),
        ("GLM", "unsloth", 10),
        ("Qwen", "unsloth", 10),
        ("Coder", "unsloth", 10),
    ]

    for query, author, top_n in hf_api_searches:
        results = ranker.search_models(
            query,
            author=author,
            mode=RankingMode.STABLE,
            top_n=top_n,
        )
        ranker.print_table(results, f'[HF API] "{query}" @ {author}')

    # 6. Specialized Rankings
    print("\n" + "=" * 80)
    print("SPECIALIZED MODEL RANKINGS")
    print("=" * 80)

    spec_ranker = SpecializedRanker(ranker, ranker.history, default_author=None)

    print("\nFetching specialized categories from HF API...")
    spec_ranker.fetch_all(author=None, timeout_seconds=60, force_refresh=force_refresh)

    categories = [
        "VISION-LANGUAGE",
        "MULTIMODAL",
        "THINKING",
        "TOOLS",
        "CODE",
        "EMBEDDING",
    ]
    for category in categories:
        results = spec_ranker.get_ranking(category, top_n=15, author=None)
        ranker.print_table(results, f"{category} RANKING (Stable)")

    universal = spec_ranker.get_universal_models(
        min_categories=2, top_n=15, author=None
    )
    ranker.print_table(universal, "UNIVERSAL RANKING (3+ categories)")

    spec_ranker.close()

    # 7. Сохраняем Markdown
    ranker.save_markdown_report()


def get_dynamic_search_queries(models: List[ModelInfo], top_n: int = 15) -> List[str]:
    """
    Генерирует динамический список поисковых запросов на основе популярных моделей.
    """
    if not models:
        return [
            "qwen3",
            "Qwen2.5",
            "gpt-oss",
            "deepseek",
            "minimax",
            "Devstral",
            "Kimi K2",
            "GLM",
            "Coder",
            "Gemma",
        ]

    base_names = []
    for m in models:
        base = extract_base_model_name(m.id)
        if base and len(base) > 2:
            base_names.append(base)

    from collections import Counter

    counter = Counter(base_names)

    queries = []
    for name, count in counter.most_common(top_n):
        if count >= 1 and len(name) > 2:
            queries.append(name)

    defaults = [
        "qwen3",
        "Qwen2.5",
        "gpt-oss",
        "deepseek",
        "minimax",
        "Devstral",
        "Kimi K2",
        "GLM",
        "Coder",
        "Gemma",
    ]
    for default in defaults:
        if default.lower() not in [q.lower() for q in queries]:
            queries.append(default)
            if len(queries) >= top_n + 5:
                break

    return queries[: top_n + 5]


if __name__ == "__main__":
    import sys
    import os

    force_refresh = "--force-refresh" in sys.argv or "-f" in sys.argv
    use_emoji = "--no-emoji" not in sys.argv

    print("=" * 80)
    if force_refresh:
        print("[REFRESH] FORCE REFRESH MODE - Rankings reset, params cache preserved")
        ranker = GGUFModelRanker()
        if hasattr(ranker.fetcher, "cache"):
            ranker.fetcher.cache.close()
        if hasattr(ranker, "_params_cache"):
            ranker._params_cache.close()
        import gc

        gc.collect()
        ranker.history.reset_rankings()
        print("  [OK] Rankings reset, model_params_cache preserved")
    else:
        if use_emoji:
            print("[CACHE] MODE - Using cached data")
        else:
            print("[CACHE MODE] Using cached data")

    ranker = GGUFModelRanker()

    # Validate and cleanup params cache from invalid entries
    cleaned = ranker._params_cache.validate_and_cleanup_params_cache()
    if cleaned > 0:
        print(f"[CACHE] Cleaned {cleaned} invalid param entries")

    if force_refresh:
        ranker.fetcher.fetch_deep_scan(force_refresh=True)
    all_models = ranker.prepare_data()

    # Progressive enrichment of unknown parameters (max 5 batches = 250 models)
    print("\n[INFO] Progressive enrichment of model parameters...")
    unknown_models = [
        m for m in all_models if m.parsed_params_b == 0 or m.parsed_params_b is None
    ]
    unknown_models.sort(key=lambda x: (x.downloads, x.likes), reverse=True)

    batch_size = 50
    max_batches = 5
    total_enriched = 0

    for batch_num in range(1, max_batches + 1):
        if not unknown_models:
            break

        batch = unknown_models[:batch_size]
        remaining = len(unknown_models)

        print(
            f"  [ENRICH] Batch {batch_num}/{max_batches}: {len(batch)} models (remaining: {remaining})..."
        )

        enriched = asyncio.run(
            ranker.enrich_unknown_params(batch, max_concurrent=5, timeout_seconds=45.0)
        )

        total_enriched += enriched

        # Remove processed batch (regardless of result)
        unknown_models = unknown_models[batch_size:]

        if enriched == 0:
            print(f"  [ENRICH] No params fetched, skipping remaining batches")
            break

    print(f"  [ENRICH] Total enriched this run: {total_enriched} models")

    # === GGUF PROVIDERS (ГЛАВНАЯ ТАБЛИЦА) ===
    print("\n" + "=" * 80)
    print("[INFO] TOP GGUF MODELS FROM KNOWN PROVIDERS")
    print("=" * 80)

    gguf_only = [
        m for m in all_models if m.author.lower() in [k.lower() for k in GGUF_KINGS]
    ]

    # Ensure all GGUF provider models have parameters before ranking
    unknown_providers = [
        m for m in gguf_only if m.parsed_params_b == 0 or m.parsed_params_b is None
    ]

    if unknown_providers:
        print(
            f"\n[ENRICH] GGUF providers: enriching all {len(unknown_providers)} unknown models..."
        )
        enriched_total = 0
        batch_num = 0
        failed_models = []

        while unknown_providers and batch_num < 10:
            batch = unknown_providers[:50]
            batch_num += 1
            print(f"  [ENRICH] Providers batch {batch_num}: {len(batch)} models...")

            enriched = asyncio.run(
                ranker.enrich_unknown_params(
                    batch, max_concurrent=5, timeout_seconds=30.0
                )
            )
            enriched_total += enriched

            # Remove successfully enriched from list
            still_unknown = []
            for m in batch:
                if m.parsed_params_b and m.parsed_params_b > 0:
                    pass  # Successfully enriched
                else:
                    still_unknown.append(m)

            unknown_providers = still_unknown

            if not unknown_providers:
                print(f"  [ENRICH] All GGUF provider models enriched!")
                break

        print(
            f"  [ENRICH] GGUF providers enriched: {enriched_total}/{len(unknown_providers) + enriched_total}"
        )

    # Sort GGUF providers by score
    gguf_only.sort(
        key=lambda m: ranker._score_model(m, RankingMode.STABLE), reverse=True
    )

    for i, m in enumerate(gguf_only, 1):
        m.rank = i
        m.rank_delta = "new"
        m.accel = 0.0

    ranker.print_table(
        gguf_only[:30],
        "[PROVIDERS] TOP GGUF PROVIDERS (Unsloth, TheBloke, Bartowski...)",
    )

    # Сохраняем Markdown
    ranker.save_markdown_report()
