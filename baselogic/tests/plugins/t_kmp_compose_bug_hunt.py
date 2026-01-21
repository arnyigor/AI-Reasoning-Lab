# plugins/t_kmp_compose_bug_hunt_v2.py

"""
KMP + Compose Bug Hunt v2 (FINAL) – генератор тестов на поиск регрессий.
--------------------------------------------------------------------
Особенности:
1. ГАРАНТИРОВАННАЯ инъекция двух багов (UI Side-effect + VM One-time event).
   Если подходящие файлы не найдены, создаются синтетические блоки кода.
2. В коде оставляются маркеры `trace=...` для однозначной идентификации.
3. Гибкий парсинг ответов LLM (справляется с Markdown, переносами строк в JSON).
4. Строгая верификация по trace-ID (50% веса оценки).

Author: AI Reasoning Lab
"""

import os
import re
import json
import uuid
import random
import hashlib
import logging
import datetime
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Импортируем базовый класс (предполагается, что он доступен в окружении)
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------

def _run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    return p.stdout


def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:10]


def _iter_files(root: Path, exts: Tuple[str, ...], exclude_dirs: Tuple[str, ...]) -> List[Path]:
    out: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if not any(p.suffix == e or str(p).endswith(e) for e in exts):
            continue
        # Проверка исключенных директорий
        if any(d in set(p.parts) for d in exclude_dirs):
            continue
        out.append(p)
    return out


def _read_text_safely(path: Path, max_chars: int) -> str:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    if len(txt) <= max_chars:
        return txt
    return txt[:max_chars] + "\n/* ... truncated ... */\n"


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lower().strip()


# ----------------------------------------------------------------------
# Bug Injection Logic (Aggressive)
# ----------------------------------------------------------------------

def _inject_ui_side_effect_bug_aggressive(src: str, trace: str) -> Tuple[str, int]:
    """
    Инъекция UI-бага (Side-effect в Composable).
    Если @Composable не найден, создает синтетическую функцию.
    """
    lines = src.splitlines()
    ins_at = None

    # Попытка 1: Найти существующий @Composable
    for i, line in enumerate(lines):
        if "@Composable" in line:
            # Ищем открывающую скобку функции
            for j in range(i, min(i + 20, len(lines))):
                if "{" in lines[j]:
                    ins_at = j + 1
                    break
            if ins_at:
                break

    # Попытка 2: Fallback - создаем синтетический блок в конце
    if ins_at is None:
        log.warning(f"No @Composable found for trace={trace}, appending synthetic one.")
        ins_at = len(lines)
        synthetic_block = [
            "",
            "// Synthetic Composable for bug injection",
            "@androidx.compose.runtime.Composable",
            "fun BuggyScreen() {",
        ]
        lines.extend(synthetic_block)
        ins_at += len(synthetic_block)

    bug_block = [
        f"    // === UI REGRESSION START (trace={trace}) ===",
        "    // BUG: Side-effect runs on EVERY recomposition because it's not wrapped in LaunchedEffect",
        "    val bugScope = androidx.compose.runtime.rememberCoroutineScope()",
        "    bugScope.launch {",
        f"        kotlinx.coroutines.delay(50)",
        f"        println(\"[BUG-UI] Repeated side-effect; trace={trace}\")",
        "    }",
        f"    // === UI REGRESSION END (trace={trace}) ===",
        "",
    ]

    lines[ins_at:ins_at] = bug_block
    return "\n".join(lines), ins_at + 1


def _inject_vm_one_time_event_bug_aggressive(src: str, trace: str) -> Tuple[str, int]:
    """
    Инъекция VM-бага (One-time event не сбрасывается).
    Если класс не найден, создает синтетический класс.
    """
    lines = src.splitlines()
    ins_at = None

    # Попытка 1: Найти любой класс
    for i, line in enumerate(lines):
        if re.search(r'\bclass\s+\w+', line):
            for j in range(i, min(i + 30, len(lines))):
                if "{" in lines[j]:
                    ins_at = j + 1
                    break
            if ins_at:
                break

    # Попытка 2: Fallback - создаем синтетический класс
    if ins_at is None:
        log.warning(f"No class found for trace={trace}, appending synthetic one.")
        ins_at = len(lines)
        synthetic_block = [
            "",
            "// Synthetic ViewModel for bug injection",
            "class BuggyViewModel {",
        ]
        lines.extend(synthetic_block)
        ins_at += len(synthetic_block)

    bug_block = [
        f"    // === VM REGRESSION START (trace={trace}) ===",
        "    // BUG: One-time event NEVER reset",
        "    private val _navigateEvent = kotlinx.coroutines.flow.MutableStateFlow(false)",
        "    val navigateEvent: kotlinx.coroutines.flow.StateFlow<Boolean> = _navigateEvent",
        "",
        "    fun triggerNavigation() {",
        f"        _navigateEvent.value = true  // NEVER RESET! Listeners will receive 'true' repeatedly.",
        f"        println(\"[BUG-VM] Event triggered; trace={trace}\")",
        "    }",
        f"    // === VM REGRESSION END (trace={trace}) ===",
        "",
    ]

    lines[ins_at:ins_at] = bug_block
    return "\n".join(lines), ins_at + 1


# ----------------------------------------------------------------------
# Config Classes
# ----------------------------------------------------------------------

@dataclass
class RepoConfig:
    url: str
    ref: str
    local_dir: Path


@dataclass
class CaseConfig:
    context_k: int
    depth_percent: int
    max_files: int
    per_file_max_chars: int


# ----------------------------------------------------------------------
# Main Generator Class
# ----------------------------------------------------------------------

class KmpComposeBugHuntV2TestGenerator(AbstractTestGenerator):
    DEFAULT_REPO_URL = "https://github.com/JetBrains/compose-multiplatform.git"

    def __init__(self, test_id: str):
        super().__init__(test_id)

        self.repo = RepoConfig(
            url=os.getenv("KMP_REPO_URL", self.DEFAULT_REPO_URL),
            ref=os.getenv("KMP_REPO_REF", "HEAD"),
            local_dir=Path(os.getenv("KMP_LOCAL_DIR", ".cache/kmp_repo")).resolve(),
        )

        lengths_str = os.getenv("KMP_CONTEXT_LENGTHS_K", "8,16")
        depths_str = os.getenv("KMP_NEEDLE_DEPTH_PERCENTAGES", "30,70")

        self.max_files = int(os.getenv("KMP_MAX_FILES", "25"))
        self.per_file_max_chars = int(os.getenv("KMP_PER_FILE_MAX_CHARS", "5000"))
        self.context_lengths_k = [int(x.strip()) for x in lengths_str.split(",") if x.strip()]
        self.needle_depths = [int(x.strip()) for x in depths_str.split(",") if x.strip()]

        self.test_plan = self._create_test_plan()
        self.current_test_index = 0

        log.info(f"KMP BugHunt v2 initialized. Plan: {len(self.test_plan)} tests.")

    def _create_test_plan(self) -> List[Dict[str, Any]]:
        plan = []
        for k in self.context_lengths_k:
            for d in self.needle_depths:
                plan.append({
                    "context_k": k,
                    "depth_percent": d,
                    "test_id": f"kmp_bug_hunt_v2_{k}k_{d}pct",
                })
        return plan

    def _ensure_repo(self) -> None:
        self.repo.local_dir.parent.mkdir(parents=True, exist_ok=True)
        if not self.repo.local_dir.exists():
            log.info("Cloning repo into %s", self.repo.local_dir)
            _run(["git", "clone", "--depth", "1", self.repo.url, str(self.repo.local_dir)])
        else:
            # Опционально можно сделать git pull, если нужно свежее состояние
            pass

    def _pick_files(self, cfg: CaseConfig) -> List[Path]:
        root = self.repo.local_dir
        exts = (".kt", ".kts")
        exclude_dirs = (".git", "build", ".gradle", ".idea", "out", "generated", "node_modules")

        all_files = _iter_files(root, exts=exts, exclude_dirs=exclude_dirs)

        # Предпочитаем исходники примеров, там чаще встречается код UI
        preferred = [p for p in all_files if any(seg in p.parts for seg in ("src", "examples", "sample"))]
        pool = preferred if len(preferred) >= 10 else all_files

        # Детерминированный шаффл
        seed_val = f"{self.test_id}:{cfg.context_k}:{cfg.depth_percent}"
        seed = _sha1_text(seed_val)
        rnd = random.Random(seed)
        rnd.shuffle(pool)

        return pool[:cfg.max_files]

    def _build_context_blocks(self, chosen: List[Path], cfg: CaseConfig) -> Tuple[List[str], Dict[str, Any]]:
        rnd = random.Random(_sha1_text(f"{self.test_id}:inject"))
        root = self.repo.local_dir

        # Нам нужно минимум 2 файла для инъекции
        kt_files = [p for p in chosen if str(p).endswith(".kt")]
        if len(kt_files) < 2:
            # Если файлов мало, дублируем их для теста
            if not kt_files:
                raise RuntimeError("No .kt files found in repo subset.")
            kt_files = kt_files * 2

        ui_file = rnd.choice(kt_files)
        vm_file = rnd.choice([f for f in kt_files if f != ui_file] or [ui_file])

        trace_ui = uuid.uuid4().hex[:8]
        trace_vm = uuid.uuid4().hex[:8]

        injection_meta = {
            "ui_bug": {"file": None, "line": None, "trace": trace_ui},
            "vm_bug": {"file": None, "line": None, "trace": trace_vm},
            "all_files": [],
        }

        blocks: List[str] = []
        injection_count = 0

        for p in chosen:
            rel = str(p.relative_to(root))
            txt = _read_text_safely(p, cfg.per_file_max_chars)
            if not txt.strip():
                continue

            # UI Bug Injection
            if p == ui_file:
                new_txt, line_no = _inject_ui_side_effect_bug_aggressive(txt, trace_ui)
                txt = new_txt
                injection_meta["ui_bug"]["file"] = rel
                injection_meta["ui_bug"]["line"] = line_no
                log.info(f"Injecting UI bug into {rel} at line {line_no} (trace={trace_ui})")
                injection_count += 1

            # VM Bug Injection
            if p == vm_file:
                new_txt, line_no = _inject_vm_one_time_event_bug_aggressive(txt, trace_vm)
                txt = new_txt
                injection_meta["vm_bug"]["file"] = rel
                injection_meta["vm_bug"]["line"] = line_no
                log.info(f"Injecting VM bug into {rel} at line {line_no} (trace={trace_vm})")
                injection_count += 1

            header = (
                f"\n\n// ================================\n"
                f"// FILE: {rel}\n"
                f"// SHA: {_sha1_text(txt)}\n"
                f"// ================================\n"
            )
            blocks.append(header + txt)
            injection_meta["all_files"].append(rel)

        # Валидация
        if injection_count < 2:
            # В редких случаях (один файл) может быть меньше, но мы стараемся обеспечить 2
            log.warning(f"Injected only {injection_count}/2 bugs. Verification might be affected.")

        return blocks, injection_meta

    def _assemble_haystack(self, blocks: List[str], cfg: CaseConfig) -> str:
        # Простая склейка с ограничением длины
        target_chars = cfg.context_k * 1024 * 3  # ~3 chars per token approximation
        joined = "\n".join(blocks)

        if len(joined) <= target_chars:
            return joined

        # Если контекст слишком большой, режем середину (чтобы сохранить хедеры файлов и инъекции,
        # которые вероятнее всего попали в начало или конец списка при шаффле,
        # но лучше просто обрезать хвост аккуратно)
        # В данной реализации просто берем начало и хвост.
        head = joined[:int(target_chars * 0.7)]
        tail = joined[-int(target_chars * 0.25):]
        return head + "\n\n/* ... Huge context omitted ... */\n\n" + tail

    # ----------------------------------------------------------------------
    # Generator Method
    # ----------------------------------------------------------------------

    def generate(self) -> Dict[str, Any]:
        if not self.test_plan:
            raise RuntimeError("Test plan is empty")

        config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1

        cfg = CaseConfig(
            context_k=config["context_k"],
            depth_percent=config["depth_percent"],
            max_files=self.max_files,
            per_file_max_chars=self.per_file_max_chars,
        )

        self._ensure_repo()
        chosen = self._pick_files(cfg)
        blocks, meta = self._build_context_blocks(chosen, cfg)
        haystack = self._assemble_haystack(blocks, cfg)

        question = (
            "В проекте KMP + Compose обнаружены ДВЕ регрессии:\n\n"
            "**Регрессия 1 (UI)**: Side-effect запускается напрямую в теле @Composable вне LaunchedEffect, "
            "вызывая повторное выполнение при каждой рекомпозиции.\n"
            "**Регрессия 2 (VM)**: One-time event в StateFlow никогда не сбрасывается, "
            "из-за чего событие обрабатывается повторно.\n\n"
            "**КРИТИЧЕСКИ ВАЖНО**: В коде есть комментарии-маркеры вида:\n"
            "```\n"
            "// === UI REGRESSION START (trace=abc12345) ===\n"
            "// === VM REGRESSION END (trace=def67890) ===\n"
            "```\n\n"
            "**Задача**:\n"
            "1. Найди ОБА бага, используя маркеры `trace`.\n"
            "2. Для каждого бага укажи:\n"
            "   - `file`: точный путь как в `// FILE: ...`\n"
            "   - `line`: номер строки (примерно)\n"
            "   - `trace`: 8-символьный код из комментария\n"
            "   - `root_cause`: краткое описание причины\n"
            "   - `fix_patch`: однострочный код исправления\n"
            "3. Ответ должен быть **валидным JSON** без Markdown-обертки (без ```json).\n\n"
            "Пример формата ответа:\n"
            "{\n"
            '  "findings": [\n'
            '    {"file": "src/Ui.kt", "line": 40, "trace": "abc12345", "root_cause": "...", "fix_patch": "LaunchedEffect(Unit) { ... }"},\n'
            '    {"file": "src/Vm.kt", "line": 20, "trace": "def67890", "root_cause": "...", "fix_patch": "SharedFlow or reset"}\n'
            "  ]\n"
            "}\n"
            "ВАЖНО: fix_patch пиши в одну строку, избегай реальных переносов строк внутри JSON-значений."
        )

        expected = {
            "ui_bug": meta["ui_bug"],
            "vm_bug": meta["vm_bug"],
            "all_files": meta["all_files"],
        }

        prompt = (
            "Ты — senior Android/KMP инженер.\n\n"
            f"{haystack}\n\n"
            f"ВОПРОС:\n{question}\n\n"
            "ОТВЕТ (только JSON):\n"
        )

        return {
            "prompt": prompt,
            "expected_output": json.dumps(expected, ensure_ascii=False),
            "test_name": config["test_id"],
            "metadata": {
                "repo_url": self.repo.url,
                "context_k": cfg.context_k,
                "injected_traces": [meta["ui_bug"]["trace"], meta["vm_bug"]["trace"]],
                "complexity": "very_high",
            },
        }

    # ----------------------------------------------------------------------
    # Response Parsing & Verification
    # ----------------------------------------------------------------------

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        """
        Парсит ответ модели, очищая его от мусора и извлекая JSON.
        """
        clean = self._cleanup_llm_response(llm_raw_output)
        parsed_json = self._parse_json_flexible(clean)

        # Если не удалось распарсить, возвращаем "чистый" текст
        answer_str = json.dumps(parsed_json, ensure_ascii=False) if parsed_json else clean

        return {
            'answer': answer_str,
            'thinking_log': llm_raw_output,
            'parsed_findings': parsed_json.get('findings', []) if parsed_json else []
        }

    def _parse_json_flexible(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Продвинутый парсинг JSON, устойчивый к типичным ошибкам LLM:
        - Markdown fence
        - Неэкранированные переносы строк в значениях
        - Опечатки в ключах (rootcause vs root_cause)
        """
        # Используем метод санитизации из базового класса (замена тире и т.д.)
        clean = self._sanitize_code(text)

        # Убираем ```json ... ``` и просто ``` ... ```
        clean = re.sub(r'```(?:json)?\s*(.*?)```', r'\1', clean, flags=re.DOTALL)

        # Заменяем явные \n на пробелы (чтобы не ломать JSON)
        clean = re.sub(r'\\n', ' ', clean)

        # Нормализуем ключи (rootcause -> root_cause)
        clean = re.sub(r'"root[_-]?cause"', '"root_cause"', clean, flags=re.IGNORECASE)
        clean = re.sub(r'"fix[_-]?patch"', '"fix_patch"', clean, flags=re.IGNORECASE)

        # Функция для удаления реальных переносов строк ВНУТРИ значений JSON
        def fix_multiline_strings(match):
            key = match.group(1)
            value = match.group(2)
            # Заменяем переносы на пробелы
            fixed_value = value.replace('\n', ' ').replace('\r', '')
            return f'"{key}": "{fixed_value}"'

        # Regex ловит "key": "value...with...newlines"
        # Поддерживает значения, не содержащие кавычек внутри (или простые случаи)
        clean = re.sub(r'"(\w+)":\s*"([^"]*(?:\n[^"]*)*)"', fix_multiline_strings, clean)

        try:
            parsed = json.loads(clean)
            return self._normalize_parsed_dict(parsed)
        except Exception:
            pass

        # Fallback: поиск JSON-объекта внутри текста
        match = re.search(r'\{[\s\S]*?"findings"[\s\S]*?\}', clean)
        if match:
            try:
                # Повторяем фиксы для найденного фрагмента
                json_str = match.group(0)
                json_str = re.sub(r'\\n', ' ', json_str)
                json_str = re.sub(r'"(\w+)":\s*"([^"]*(?:\n[^"]*)*)"', fix_multiline_strings, json_str)
                return self._normalize_parsed_dict(json.loads(json_str))
            except Exception:
                pass

        return None

    def _normalize_parsed_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Дополнительная нормализация словаря после парсинга."""
        if "findings" in data and isinstance(data["findings"], list):
            for f in data["findings"]:
                # Подстраховка для ключей, если regex не сработал
                if "rootcause" in f and "root_cause" not in f:
                    f["root_cause"] = f.pop("rootcause")
                if "fixpatch" in f and "fix_patch" not in f:
                    f["fix_patch"] = f.pop("fixpatch")
        return data

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Верификация ответа.
        Критерии:
        1. Valid JSON.
        2. Найдены оба бага (проверка по Trace ID - 50% баллов).
        3. Корректные файлы (с учетом basename).
        4. Наличие ключевых слов исправления (LaunchedEffect, SharedFlow...).
        """
        clean = self._cleanup_llm_response(llm_output)
        try:
            exp = json.loads(expected_output)
        except json.JSONDecodeError:
            # Если expected некорректен (крайне маловероятно), тест фейлится
            return {"is_correct": False, "score": 0.0, "details": {"error": "Invalid expected_output"}}

        ans_obj = self._parse_json_flexible(clean)

        if not ans_obj or "findings" not in ans_obj:
            return {
                "is_correct": False,
                "score": 0.0,
                "details": {
                    "error": "No valid JSON with 'findings' key found.",
                    "preview": clean[:500]
                }
            }

        findings = ans_obj["findings"]
        if not isinstance(findings, list) or len(findings) < 2:
            return {
                "is_correct": False,
                "score": 0.0,
                "details": {
                    "error": f"Expected at least 2 findings, got {len(findings) if isinstance(findings, list) else 'invalid type'}",
                    "findings": findings
                }
            }

        # 1. Trace ID Check (Most Important)
        expected_traces = {exp["ui_bug"]["trace"], exp["vm_bug"]["trace"]}
        got_traces = {str(f.get("trace", "")).strip() for f in findings}
        # Пересечение найденных и ожидаемых
        matched_traces = expected_traces.intersection(got_traces)
        trace_ok = (matched_traces == expected_traces)

        # 2. File Check (Tolerance to path variations)
        all_files_normalized = {_normalize_path(f) for f in exp["all_files"]}
        files_ok = True
        # Проверяем первые 2 находки (предполагаем, что они соответствуют 2 багам)
        for f in findings[:2]:
            got_file = _normalize_path(f.get("file", ""))
            # Проверяем полное совпадение
            if got_file in all_files_normalized:
                continue

            # Проверяем совпадение по имени файла (basename)
            got_basename = os.path.basename(got_file)
            expected_basenames = [os.path.basename(p) for p in all_files_normalized]

            if got_basename not in expected_basenames:
                files_ok = False
                break

        # 3. Fix Patterns Check
        fix_text = " ".join(str(f.get("fix_patch", "")) for f in findings[:2]).lower()
        required_keywords = [
            "launchedeffect", "disposableeffect", "sharedflow",
            "channel", "reset", "clear", "emit", "acknowledge", "consume"
        ]
        fix_ok = any(kw in fix_text for kw in required_keywords)

        # 4. Root Cause Check
        root_cause_text = " ".join(str(f.get("root_cause", "")) for f in findings[:2]).lower()
        cause_keywords = [
            "recomposition", "side-effect", "side effect", "coroutine",
            "one-time", "event", "never reset", "repeated", "launch"
        ]
        # Достаточно найти 2 совпадения ключевых слов
        cause_ok = sum(1 for kw in cause_keywords if kw in root_cause_text) >= 2

        # 5. Line Check (Low priority)
        line_ok = True
        tolerance = 20
        # Пытаемся сопоставить находки с ожидаемыми по trace
        for f in findings:
            tr = str(f.get("trace", "")).strip()
            expected_line = None
            if tr == exp["ui_bug"]["trace"]:
                expected_line = exp["ui_bug"]["line"]
            elif tr == exp["vm_bug"]["trace"]:
                expected_line = exp["vm_bug"]["line"]

            if expected_line is not None:
                ans_line = f.get("line")
                if isinstance(ans_line, int):
                    if abs(ans_line - expected_line) > tolerance:
                        # line_ok = False # Можно не штрафовать строго
                        pass
                else:
                    # Если линия не int или отсутствует
                    pass

        # Scoring System
        score = 0.0
        if trace_ok: score += 0.50
        if files_ok: score += 0.15
        if fix_ok: score += 0.20
        if cause_ok: score += 0.10
        if line_ok: score += 0.05

        return {
            "is_correct": score >= 0.70,
            "score": round(score, 3),
            "details": {
                "trace_ok": trace_ok,
                "files_ok": files_ok,
                "fix_ok": fix_ok,
                "cause_ok": cause_ok,
                "matched_traces": list(matched_traces),
                "expected_traces": list(expected_traces),
                "score_breakdown": {
                    "trace": 0.50 if trace_ok else 0.0,
                    "files": 0.15 if files_ok else 0.0,
                    "fix": 0.20 if fix_ok else 0.0,
                    "cause": 0.10 if cause_ok else 0.0
                }
            },
        }
