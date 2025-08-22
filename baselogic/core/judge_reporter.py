import json
import logging
import time
from pathlib import Path

import pandas as pd

from baselogic.core.reporter import Reporter

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
def _safe_test_type(obj) -> str:
    """Вернуть verification_details.test_type или '' (при NaN/None)."""
    return obj.get("test_type", "") if isinstance(obj, dict) else ""


def _extract_score(parsed_json: str) -> float:
    """
    parsed_answer хранит строку вида
        {"reasoning": "...", "score": 4}
    Возвращаем числовой score или 0.
    """
    try:
        return float(json.loads(parsed_json).get("score", 0))
    except Exception:
        return 0.0
# ──────────────────────────────────────────────────────────────────────────


class JudgeReporter(Reporter):
    """
    Специализированный Reporter для LLM-судей.
    Считает Accuracy, Stability, Verbosity/Positional resistance и др.
    """

    # ──────────────────────────────────────────────────────────────
    def __init__(self, results_dir: Path):
        super().__init__(results_dir)
        self.judge_results = self._filter_judge_results()

    # ──────────────────────────────────────────────────────────────
    def _filter_judge_results(self) -> pd.DataFrame:
        """
        Подготавливает DataFrame с обязательными полями:
        category, test_type, score.
        """
        df = self.all_results.copy()
        if df.empty:
            return pd.DataFrame()

        # -------- category ------------------------------------------------
        def _infer_category(row) -> str:
            tid = row["test_id"]
            if tid.startswith("t08_accuracy"):
                return "accuracy_test"

            ttype = _safe_test_type(row["verification_details"])
            if ttype in {"ideal", "flawed"}:
                return "accuracy_test"
            if ttype == "verbose":
                return "verbosity_bias_test"
            if ttype in {"run_A", "run_B"}:
                return "positional_bias_test"
            return "other"

        df["category"] = df.apply(_infer_category, axis=1)

        # -------- test_type ----------------------------------------------
        df["test_type"] = df["verification_details"].apply(_safe_test_type)

        # -------- score ---------------------------------------------------
        df["score"] = df["parsed_answer"].apply(_extract_score)

        # -------- итоговый отбор ------------------------------------------
        judge_df = df[df["category"].isin(
            ["accuracy_test", "verbosity_bias_test", "positional_bias_test"]
        )].copy()

        log.info("Найдено %d записей для оценки судей", len(judge_df))
        return judge_df

    # ───── Accuracy ───────────────────────────────────────────────────────
    def _calculate_accuracy_score(self, df: pd.DataFrame) -> pd.Series:
        acc = {}
        for model, g in df.groupby("model_name"):
            ideal = g[g["test_type"] == "ideal"]["score"]
            flawed = g[g["test_type"] == "flawed"]["score"]
            acc[model] = max(0, (ideal.mean() - flawed.mean()) / 4.0) \
                if not ideal.empty and not flawed.empty else 0.0
        return pd.Series(acc, name="Accuracy_Score")

    # ───── Stability ──────────────────────────────────────────────────────
    def _calculate_stability_score(self, df: pd.DataFrame) -> pd.Series:
        stab = {}
        for model, g in df.groupby("model_name"):
            ideal = g[g["test_type"] == "ideal"]["score"]
            flawed = g[g["test_type"] == "flawed"]["score"]
            if len(ideal) > 1 and len(flawed) > 1:
                stab[model] = max(0, 1 - ((ideal.std() + flawed.std()) / 2) / 4.0)
            else:
                stab[model] = 0.0
        return pd.Series(stab, name="Stability_Score")

    # ───── Positional bias ────────────────────────────────────────────────
    def _calculate_positional_resistance(self, df: pd.DataFrame) -> pd.Series:
        pos_scores, pos_df = {}, df[df["category"] == "positional_bias_test"]
        for model, g in pos_df.groupby("model_name"):
            a = g[g["test_type"] == "run_A"]["choice"].tolist()
            b = g[g["test_type"] == "run_B"]["choice"].tolist()
            pairs = min(len(a), len(b))
            correct = sum(
                (ca == "A" and cb == "B") or (ca == "B" and cb == "A")
                for ca, cb in zip(a, b)
            )
            pos_scores[model] = correct / pairs if pairs else 0.0
        return pd.Series(pos_scores, name="Positional_Resistance")

    # ───── Verbosity bias ────────────────────────────────────────────────
    def _calculate_verbosity_resistance(self, df: pd.DataFrame) -> pd.Series:
        verb = {}
        for model, g in df.groupby("model_name"):
            ideal = g[g["test_type"] == "ideal"]["score"]
            verbose = g[g["test_type"] == "verbose"]["score"]
            if not ideal.empty and not verbose.empty:
                verb[model] = max(0, 1 - abs(ideal.mean() - verbose.mean()) / 4.0)
            else:
                verb[model] = 0.0
        return pd.Series(verb, name="Verbosity_Resistance")

    # ───── Format adherence ───────────────────────────────────────────────
    def _calculate_format_adherence(self, df: pd.DataFrame) -> pd.Series:
        fmt = {}
        for model, g in df.groupby("model_name"):
            total = len(g)
            valid = g["json_valid"].sum() if "json_valid" in g.columns else total
            fmt[model] = valid / total if total else 0.0
        return pd.Series(fmt, name="Format_Adherence")

    # ───── Итоговый рейтинг ───────────────────────────────────────────────
    def _calculate_judge_rating(self, metrics: pd.DataFrame) -> pd.DataFrame:
        weights = {
            "Accuracy_Score":    0.35,
            "Stability_Score":   0.25,
            "Positional_Resistance": 0.15,
            "Verbosity_Resistance":  0.10,
            "Format_Adherence":  0.15,
        }
        metrics["Judge_Rating"] = sum(metrics[c] * w for c, w in weights.items())
        metrics.sort_values("Judge_Rating", ascending=False, inplace=True)
        metrics.insert(0, "Rank", range(1, len(metrics) + 1))
        return metrics

    # ───── Публичный метод ────────────────────────────────────────────────
    def generate_judge_leaderboard(self) -> str:
        if self.judge_results.empty:
            return "# 🏛️ Рейтинг LLM-Судей\n\nНе найдено данных для оценки судей."

        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        acc  = self._calculate_accuracy_score(self.judge_results)
        stab = self._calculate_stability_score(self.judge_results)
        pos  = self._calculate_positional_resistance(self.judge_results)
        verb = self._calculate_verbosity_resistance(self.judge_results)
        fmt  = self._calculate_format_adherence(self.judge_results)

        metrics = pd.DataFrame({
            "Model": acc.index,
            "Accuracy_Score": acc.values,
            "Stability_Score": stab.reindex(acc.index, fill_value=0).values,
            "Positional_Resistance": pos.reindex(acc.index, fill_value=0).values,
            "Verbosity_Resistance": verb.reindex(acc.index, fill_value=0).values,
            "Format_Adherence": fmt.reindex(acc.index, fill_value=0).values,
        }).set_index("Model")

        final = self._calculate_judge_rating(metrics)

        # ─ Markdown-отчёт --------------------------------------------------
        tbl = self._to_markdown_table(
            final.assign(
                **{c: final[c].map(lambda x: f"{x:.3f}") for c in [
                    "Judge_Rating", "Accuracy_Score", "Stability_Score",
                    "Positional_Resistance", "Verbosity_Resistance"]},
                Format_Adherence=final["Format_Adherence"].map(lambda x: f"{x:.1%}")
            )[["Rank", "Judge_Rating",
               "Accuracy_Score", "Stability_Score",
               "Positional_Resistance", "Verbosity_Resistance",
               "Format_Adherence"]]
        )

        md = (
                "# 🏛️ Рейтинг LLM-Судей: кто объективнее?\n\n"
                f"*Последнее обновление: {ts}*\n\n"
                "## 🏆 Таблица лидеров\n\n" + tbl +
                "\n\n---\n*Этот рейтинг помогает выбрать надёжную модель-арбитр.*"
        )
        return md
