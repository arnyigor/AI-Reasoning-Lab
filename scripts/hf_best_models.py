import sqlite3
import math
import os
import re

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
        self._init_cache()
        self._last_deep_scan = None

    def _init_cache(self):
        import sqlite3

        self._cache_conn = sqlite3.connect(
            "hf_deep_scan_cache.db", check_same_thread=False
        )
        cursor = self._cache_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deep_scan_cache (
                key TEXT PRIMARY KEY,
                data TEXT,
                timestamp TEXT,
                config_hash TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                key TEXT PRIMARY KEY,
                data TEXT,
                timestamp TEXT,
                ttl_seconds INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS specialized_cache (
                key TEXT PRIMARY KEY,
                data TEXT,
                timestamp TEXT,
                ttl_seconds INTEGER
            )
        """)
        self._cache_conn.commit()

    def _get_cache_key(self) -> str:
        strategies = ["trending", "lastModified", "downloads", "likes"]
        return f"deep_scan_{len(strategies)}_{PAGES_TO_FETCH}"

    def _is_cache_valid(self) -> bool:
        cursor = self._cache_conn.cursor()
        cursor.execute(
            "SELECT timestamp FROM deep_scan_cache WHERE key = ?",
            (self._get_cache_key(),),
        )
        row = cursor.fetchone()
        if not row:
            return False
        cached_time = datetime.fromisoformat(row[0])
        now = datetime.now(timezone.utc)
        elapsed = (now - cached_time).total_seconds()
        return elapsed < DEEP_SCAN_CACHE_TTL

    def _save_cache(self, data: List[ModelInfo], config_hash: str):
        cursor = self._cache_conn.cursor()
        import json

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
        cursor.execute(
            "REPLACE INTO deep_scan_cache (key, data, timestamp, config_hash) VALUES (?, ?, ?, ?)",
            (
                self._get_cache_key(),
                json.dumps(models_data),
                datetime.now(timezone.utc).isoformat(),
                config_hash,
            ),
        )
        self._cache_conn.commit()

    def _load_cache(self) -> Optional[List[ModelInfo]]:
        cursor = self._cache_conn.cursor()
        cursor.execute(
            "SELECT data FROM deep_scan_cache WHERE key = ?", (self._get_cache_key(),)
        )
        row = cursor.fetchone()
        if not row:
            return None
        import json

        models_data = json.loads(row[0])
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

    def _get_query_cache_key(
        self, query: str, author: str = None, limit: int = SEARCH_LIMIT
    ) -> str:
        import hashlib

        key_str = f"query_{query}_{author}_{limit}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_query_cache_ttl(self) -> int:
        return 1800  # 30 minutes for queries

    def _is_query_cache_valid(self, key: str, ttl: int = None) -> bool:
        if ttl is None:
            ttl = self._get_query_cache_ttl()
        cursor = self._cache_conn.cursor()
        cursor.execute("SELECT timestamp FROM query_cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return False
        cached_time = datetime.fromisoformat(row[0])
        elapsed = (datetime.now(timezone.utc) - cached_time).total_seconds()
        return elapsed < ttl

    def _save_query_cache(self, key: str, data: List[Dict]):
        cursor = self._cache_conn.cursor()
        import json

        cursor.execute(
            "REPLACE INTO query_cache (key, data, timestamp, ttl_seconds) VALUES (?, ?, ?, ?)",
            (
                key,
                json.dumps(data),
                datetime.now(timezone.utc).isoformat(),
                self._get_query_cache_ttl(),
            ),
        )
        self._cache_conn.commit()

    def _load_query_cache(self, key: str) -> Optional[List[Dict]]:
        cursor = self._cache_conn.cursor()
        cursor.execute("SELECT data FROM query_cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return None
        import json

        return json.loads(row[0])

    def _get_specialized_cache_key(
        self,
        query: str = "",
        author: str = None,
        limit: int = 1000,
        tags: List[str] = None,
    ) -> str:
        import hashlib

        tags_str = ",".join(tags) if tags else ""
        key_str = f"spec_{query}_{author}_{limit}_{tags_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_specialized_cache_ttl(self) -> int:
        return 3600  # 1 hour for specialized

    def _is_specialized_cache_valid(self, key: str) -> bool:
        cursor = self._cache_conn.cursor()
        cursor.execute("SELECT timestamp FROM specialized_cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return False
        cached_time = datetime.fromisoformat(row[0])
        elapsed = (datetime.now(timezone.utc) - cached_time).total_seconds()
        return elapsed < self._get_specialized_cache_ttl()

    def _save_specialized_cache(self, key: str, data: List[Dict]):
        cursor = self._cache_conn.cursor()
        import json

        cursor.execute(
            "REPLACE INTO specialized_cache (key, data, timestamp, ttl_seconds) VALUES (?, ?, ?, ?)",
            (
                key,
                json.dumps(data),
                datetime.now(timezone.utc).isoformat(),
                self._get_specialized_cache_ttl(),
            ),
        )
        self._cache_conn.commit()

    def _load_specialized_cache(self, key: str) -> Optional[List[Dict]]:
        cursor = self._cache_conn.cursor()
        cursor.execute("SELECT data FROM specialized_cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        if not row:
            return None
        import json

        return json.loads(row[0])

    def _fetch_stream(self, strategy: Dict, max_pages: int) -> List[Dict]:
        results = []
        for p in range(max_pages):
            time.sleep(random.uniform(0.3, 0.8))
            params = strategy.copy()
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
        cache_key = self._get_query_cache_key(query, author, limit)

        if use_cache and self._is_query_cache_valid(cache_key):
            cached = self._load_query_cache(cache_key)
            if cached is not None:
                print(
                    f'  [CACHE] query="{query}" author={author} ({len(cached)} results)'
                )
                return cached
            else:
                print(
                    f'  [CACHE MISS] query="{query}" - empty or invalid, fetching from API'
                )

        params = {
            "search": query,
            "filter": "gguf",
            "pipeline_tag": pipeline_tag,
            "limit": limit,
            "full": "true",
        }

        if author:
            params["author"] = author

        try:
            time.sleep(0.3)
            resp = self.session.get(HF_API, params=params, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                print(f'  [API] query="{query}" author={author} ({len(data)} results)')
                if use_cache:
                    self._save_query_cache(cache_key, data)
                return data
            elif resp.status_code == 429:
                print("  [WARN] HF API rate limited, waiting...")
                time.sleep(5)
                return self.fetch_by_query(
                    query, author, limit, pipeline_tag, use_cache
                )
            else:
                print(f"  [ERROR] HF API error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"  [ERROR] HF API request failed: {e}")
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
        cache_key = self._get_specialized_cache_key(query, author, limit, tags)

        if use_cache and self._is_specialized_cache_valid(cache_key):
            cached = self._load_specialized_cache(cache_key)
            if cached is not None:
                tags_str = ",".join(tags) if tags else "all"
                print(f"  [CACHE] tags={tags_str} ({len(cached)} results)")
                return cached
            else:
                tags_str = ",".join(tags) if tags else "all"
                print(
                    f"  [CACHE MISS] tags={tags_str} - empty or invalid, fetching from API"
                )

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

        try:
            time.sleep(0.3)
            resp = self.session.get(HF_API, params=params, timeout=20)

            if resp.status_code == 200:
                data = resp.json()
                tags_str = ",".join(tags) if tags else "all"
                print(f"  [API] tags={tags_str} ({len(data)} results)")
                if use_cache:
                    self._save_specialized_cache(cache_key, data)
                return data
            elif resp.status_code == 429:
                print("  [WARN] HF API rate limited")
                time.sleep(5)
                return self.fetch_specialized(query, author, limit, tags, use_cache)
            else:
                print(f"  [ERROR] HF API error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"  [ERROR] HF API request failed: {e}")
            return []

    def fetch_deep_scan(self, force_refresh: bool = False) -> List[ModelInfo]:
        strategies = [
            {"sort": "trending", "filter": "gguf"},
            {"sort": "lastModified", "filter": "gguf"},
            {"sort": "downloads", "filter": "gguf"},
            {"sort": "likes", "filter": "gguf"},
        ]

        if not force_refresh and self._is_cache_valid():
            cached = self._load_cache()
            if cached:
                print(
                    f"[CACHE] Deep scan (less than {DEEP_SCAN_CACHE_TTL // 60} min old, {len(cached)} models)"
                )
                self._last_deep_scan = cached
                return cached
            else:
                print(f"📡 [CACHE MISS] Empty or invalid cache, fetching from API")

        print(f"[NETWORK] SCANNING HF ({len(strategies)} x {PAGES_TO_FETCH} pages)...")
        unique_models: Dict[str, ModelInfo] = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_strat = {
                executor.submit(self._fetch_stream, s, PAGES_TO_FETCH): s["sort"]
                for s in strategies
            }
            for future in as_completed(future_to_strat):
                data = future.result()
                for item in data:
                    mid = item.get("id")
                    if mid in unique_models:
                        continue

                    if any(bad in mid.lower() for bad in BLACKLIST_KEYWORDS):
                        continue
                    pipeline = item.get("pipeline_tag", "")
                    if pipeline and pipeline not in [
                        "text-generation",
                        "text-generation-inference",
                        "conversational",
                        "fill-mask",
                    ]:
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
                    unique_models[mid] = model

        result = list(unique_models.values())
        print(
            f"📡 [SAVED] {len(result)} models cached for {DEEP_SCAN_CACHE_TTL // 60} minutes"
        )
        self._save_cache(result, self._get_cache_key())
        self._last_deep_scan = result
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
            if not item:
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
        self._search_cache[cache_key] = result
        return result

    def extract_size_billions(self, m: ModelInfo) -> float | None:
        if m.size_bytes:
            return round(m.size_bytes / 1_000_000_000, 1)
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
            if re.match(r"^\d+(?:\.\d+)?b$", tag.lower()):
                return float(tag[:-1])
        return None

    def prepare_data(self):
        if not self._cache:
            self._cache = self.fetcher.fetch_deep_scan()
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
        self._spec_conn = sqlite3.connect("specialized_models.db")
        self._init_spec_db()

    def _init_spec_db(self):
        cursor = self._spec_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spec_cache (
                category TEXT,
                model_id TEXT,
                data TEXT,
                fetched_at TEXT,
                PRIMARY KEY (category, model_id)
            )
        """)
        self._spec_conn.commit()

    def _save_to_cache(self, category: str, models: List[ModelInfo]):
        cursor = self._spec_conn.cursor()
        for m in models:
            data_str = f"{m.downloads},{m.likes},{m.parsed_params_b}"
            timestamp_str = m.timestamp.isoformat()
            cursor.execute(
                "REPLACE INTO spec_cache (category, model_id, data, author, fetched_at) VALUES (?, ?, ?, ?, ?)",
                (
                    category,
                    m.id,
                    data_str,
                    m.author,
                    timestamp_str,
                ),
            )
        self._spec_conn.commit()

    def _load_from_cache(self, category: str) -> List[ModelInfo]:
        cursor = self._spec_conn.cursor()
        cursor.execute(
            "SELECT model_id, data, fetched_at FROM spec_cache WHERE category = ?",
            (category,),
        )
        models = []
        for row in cursor.fetchall():
            downloads, likes, size_b = map(float, row[1].split(","))
            timestamp = (
                datetime.fromisoformat(row[2]) if row[2] else datetime.now(timezone.utc)
            )
            m = ModelInfo(
                id=row[0],
                downloads=int(downloads),
                likes=int(likes),
                timestamp=timestamp,
                tags=[],
                pipeline_tag="text-generation",
                size_bytes=size_b * 1_000_000_000 if size_b > 0 else None,
            )
            m.parsed_params_b = size_b
            models.append(m)
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
        self._spec_conn.close()


if __name__ == "__main__":
    import sys
    import os

    force_refresh = "--force-refresh" in sys.argv or "-f" in sys.argv
    use_emoji = "--no-emoji" not in sys.argv

    print("=" * 80)
    if force_refresh:
        print("[REFRESH] FORCE REFRESH MODE - Cache will be ignored")
        # Clear all caches
        for db_file in ["hf_deep_scan_cache.db", "specialized_models.db"]:
            if os.path.exists(db_file):
                os.remove(db_file)
                print(f"  Cleared {db_file}")
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
        ("qwen", 15),
        ("gpt", 15),
        ("deepseek", 15),
        ("nemot", 15),
        ("Chimera", 15),
    ]

    for query, top_n in search_queries:
        results = ranker.search_models(query, mode=RankingMode.STABLE, top_n=top_n)
        ranker.print_table(results, f'[SEARCH] "{query}"')

    # 5. HF API with Author Filter Demo
    print("\n" + "=" * 80)
    print("[INFO] HF API + AUTHOR FILTER DEMO (guaranteed fresh & complete)")
    print("=" * 80)

    hf_api_searches = [
        ("llama", "unsloth", 10),
        ("mistral", "bartowski", 10),
        ("deepseek", "unsloth", 10),
        ("qwen", "unsloth", 10),
        ("nemot", "unsloth", 10),
        ("Chimera", "unsloth", 10),
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
()
