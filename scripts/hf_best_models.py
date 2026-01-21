import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from huggingface_hub import HfApi

HISTORY_FILE = "gguf_ranking_history.json"

class RankingMode(Enum):
    STABLE = "stable"
    TRENDING = "trending"

class RankingHistoryManager:
    def __init__(self, filepath=HISTORY_FILE, max_history=20, cleanup_days=30):
        self.filepath = filepath
        self.max_history = max_history
        self.cleanup_days = cleanup_days
        self.data = self._load_data()
        self._cleanup_old_configs()

    def _load_data(self):
        if not os.path.exists(self.filepath): return {}
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}

    def _save_data(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e: print(f"❌ Error: {e}")

    def _cleanup_old_configs(self):
        now = datetime.now(timezone.utc)
        keys_to_delete = [k for k, v in self.data.items() if not v.get("snapshots") or
                          (now - datetime.fromisoformat(v["snapshots"][-1]["timestamp"]).replace(tzinfo=timezone.utc)).days > self.cleanup_days]
        for k in keys_to_delete: del self.data[k]
        if keys_to_delete: self._save_data()

    def _generate_config_key(self, params: Dict[str, Any]) -> str:
        return hashlib.md5(json.dumps(params, sort_keys=True).encode('utf-8')).hexdigest()

    def process_ranking(self, current_models: List[Any], run_params: Dict[str, Any]):
        config_key = self._generate_config_key(run_params)
        if config_key not in self.data: self.data[config_key] = {"params": run_params, "snapshots": []}
        history = self.data[config_key]
        snapshots = history["snapshots"]

        # Карта последнего состояния для расчета Δ Rank и Δ Velocity
        last_state = {item['id']: item for item in snapshots[-1]['items']} if snapshots else {}

        now = datetime.now(timezone.utc)
        for idx, model in enumerate(current_models, 1):
            mid = getattr(model, 'id')
            dt = getattr(model, 'created_at', now)
            if isinstance(dt, str): dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            days = max(0.5, (now - dt.replace(tzinfo=timezone.utc)).days)

            # Текущая скорость
            v_curr = model.downloads / days
            model.velocity = v_curr

            if mid in last_state:
                model.rank_delta = last_state[mid]['rank'] - idx
                model.accel = v_curr - last_state[mid].get('v', v_curr)
            else:
                model.rank_delta = "new"
                model.accel = 0.0

        # Сохраняем новый снимок, если состав или данные изменились
        current_ids = [m.id for m in current_models]
        last_ids = [item['id'] for item in snapshots[-1]['items']] if snapshots else []

        if current_ids != last_ids or len(snapshots) == 0:
            new_record = {
                "timestamp": now.isoformat(),
                "items": [{"id": m.id, "rank": i, "v": m.velocity, "score": m.combined_score}
                          for i, m in enumerate(current_models, 1)]
            }
            snapshots.append(new_record)
            if len(snapshots) > self.max_history: snapshots.pop(0)
            self._save_data()

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
        match = re.search(r'(\d+(?:\.\d+)?)b', m.id.lower())
        return float(match.group(1)) if match else None

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
        run_params = {"mode": mode.value, "min": min_params, "max": max_params, "n": top_n}
        models = self.api.list_models(filter="gguf", sort="downloads", direction=-1, limit=10000, full=True)
        candidates = []
        for m in models:
            if "text-generation" not in (getattr(m, 'pipeline_tag', '') or '').lower(): continue
            p = self.extract_parameters(m)
            if (min_params and (p is None or p < min_params)) or (max_params and (p is None or p > max_params)): continue
            m.parsed_params = p
            m.combined_score = self._score_trending(m) if mode == RankingMode.TRENDING else self._score_stable(m)
            if m.combined_score > 0.001: candidates.append(m)
        candidates.sort(key=lambda x: x.combined_score, reverse=True)
        return self.history_manager.process_ranking(candidates[:top_n], run_params)

    def print_top_models(self, models, title="TOP"):
        print(f"\n{'='*180}\n{title:^180}\n{'='*180}")
        header = f"{'#':^3} | {'ΔR':^4} | {'MODEL ID':<60} | {'PARAMS':^8} | {'DLs':^8} | {'V (DL/D)':^9} | {'ACCEL':^9} | {'LIKES':^6} | {'SCORE':^6}"
        print(header)
        print("-" * 180)
        for i, m in enumerate(models, 1):
            d_r = "🆕" if m.rank_delta == "new" else (f"+{m.rank_delta}" if m.rank_delta > 0 else (f"{m.rank_delta}" if m.rank_delta < 0 else "—"))
            v_str = f"{m.velocity:.1f}" if m.velocity < 1000 else f"{m.velocity/1000:.1f}k"

            # Визуализация ускорения
            if abs(m.accel) < 0.1: a_str = "stable"
            else: a_str = f"{'+' if m.accel > 0 else ''}{m.accel:.1f}"

            p_str = f"{m.parsed_params:.1f}B" if m.parsed_params else "?"
            dl_str = f"{m.downloads/1000:.1f}k" if m.downloads > 1000 else str(m.downloads)

            print(f"{i:^3} | {d_r:^4} | {m.id[:58]:<60} | {p_str:^8} | {dl_str:>8} | {v_str:>9} | {a_str:>9} | {m.likes:>6} | {m.combined_score:.3f}")
        print("=" * 180)

if __name__ == "__main__":
    ranker = GGUFModelRanker()
    # Запуск для сбора первой точки истории или сравнения
    ranker.print_top_models(ranker.get_top_gguf_models(RankingMode.STABLE, 8, 35), "🏛️ STABLE RANKING")
    ranker.print_top_models(ranker.get_top_gguf_models(RankingMode.TRENDING, 8, 35), "🚀 TRENDING RANKING")