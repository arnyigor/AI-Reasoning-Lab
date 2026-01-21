# plugins/t_kmp_compose_bug_hunt_v3.py

"""
KMP + Compose Bug Hunt v3 (HARDCORE) – Stealth Mode & Distractors.
--------------------------------------------------------------------
Версия для проверки глубокого решёнинга (Reasoning).

Усложнения:
1. "Stealth Traces": Trace-ID спрятаны в обычных логах или комментариях аудита.
2. "Distractors" (Дистракторы): Рядом с багом генерируется ПРАВИЛЬНЫЙ код
   с другим trace-ID. Модель должна отличить баг от фичи.
3. Отсутствие явных маркеров "REGRESSION START".

Author: AI Reasoning Lab
"""

import os
import re
import json
import uuid
import random
import hashlib
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Предполагается, что базовый класс доступен в python path
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Data Classes (Defined at module level to fix unresolved reference)
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
# Utilities
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
# STEALTH Bug Injection Logic
# ----------------------------------------------------------------------

def _inject_ui_stealth_bug_with_distractor(src: str, bug_trace: str, distractor_trace: str) -> Tuple[str, int]:
    """
    Вставляет ДВА блока в UI код:
    1. Правильный код (Distractor) - LaunchedEffect с корректным ключом.
    2. Баг (Bug) - Side-effect (launch) прямо в теле Composable.

    Модель должна понять, что первый trace - это норма, а второй - баг.
    """
    lines = src.splitlines()
    ins_at = None

    # Пытаемся найти существующий Composable
    for i, line in enumerate(lines):
        if "@Composable" in line:
            for j in range(i, min(i + 20, len(lines))):
                if "{" in lines[j]:
                    ins_at = j + 1
                    break
            if ins_at: break

    # Fallback: создаем синтетический Composable
    if ins_at is None:
        lines.extend([
            "",
            "// Analytics Screen Component",
            "@androidx.compose.runtime.Composable",
            "fun AnalyticsDashboard() {"
        ])
        ins_at = len(lines)

    # --- Генерация блоков ---

    # DISTRACTOR (Правильный паттерн)
    distractor_block = [
        f"    // [Audit] View tracking event {distractor_trace}",
        "    val scope = androidx.compose.runtime.rememberCoroutineScope()",
        "    // Correct: Side-effect wrapped in LaunchedEffect",
        "    androidx.compose.runtime.LaunchedEffect(Unit) {",
        f"        println(\"Analytics: View opened (id={distractor_trace})\")",
        "    }",
    ]

    # BUG (Неправильный паттерн)
    bug_block = [
        "",
        f"    // [Audit] Refresh tracking event {bug_trace}",
        "    // FIXME: Check why this logs too many times during scroll?",
        "    // Incorrect: Launching directly in composition",
        "    scope.launch {",
        f"        println(\"Analytics: Refresh trigger (id={bug_trace})\")",
        "        kotlinx.coroutines.delay(500)",
        "    }",
    ]

    # Случайный порядок, чтобы модель не запоминала "первый всегда баг"
    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + [""] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + [""] + distractor_block

    return "\n".join(lines), ins_at + 1


def _inject_vm_stealth_bug_with_distractor(src: str, bug_trace: str, distractor_trace: str) -> Tuple[str, int]:
    """
    Вставляет ДВА блока в ViewModel:
    1. Правильный код (Distractor) - Channel или SharedFlow.
    2. Баг (Bug) - MutableStateFlow для one-shot события без сброса.
    """
    lines = src.splitlines()
    ins_at = None

    # Ищем класс
    for i, line in enumerate(lines):
        if re.search(r'\bclass\s+\w+', line) and "{" in line:
            ins_at = i + 1
            break

    # Fallback
    if ins_at is None:
        lines.extend([
            "",
            "// User Profile ViewModel",
            "class UserProfileViewModel {"
        ])
        ins_at = len(lines)

    # DISTRACTOR (Правильный паттерн)
    distractor_block = [
        f"    // Operation ID: {distractor_trace}",
        "    private val _toastChannel = kotlinx.coroutines.channels.Channel<String>()",
        "    val toastFlow = _toastChannel.receiveAsFlow()",
        "    fun showToast(msg: String) {",
        f"        _toastChannel.trySend(msg) // Safe one-shot event {distractor_trace}",
        "    }",
    ]

    # BUG (Неправильный паттерн)
    bug_block = [
        "",
        f"    // Operation ID: {bug_trace}",
        "    private val _navEvent = kotlinx.coroutines.flow.MutableStateFlow<Boolean>(false)",
        "    val navEvent: kotlinx.coroutines.flow.StateFlow<Boolean> = _navEvent",
        "    fun navigateToSettings() {",
        f"        _navEvent.value = true // Logic for op {bug_trace} (Never reset!)",
        "    }",
    ]

    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + [""] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + [""] + distractor_block

    return "\n".join(lines), ins_at + 1


# ----------------------------------------------------------------------
# Main Generator Class v3
# ----------------------------------------------------------------------

class KmpComposeBugHuntV3TestGenerator(AbstractTestGenerator):
    DEFAULT_REPO_URL = "https://github.com/JetBrains/compose-multiplatform.git"

    def __init__(self, test_id: str):
        super().__init__(test_id)

        self.repo = RepoConfig(
            url=os.getenv("KMP_REPO_URL", self.DEFAULT_REPO_URL),
            ref=os.getenv("KMP_REPO_REF", "HEAD"),
            local_dir=Path(os.getenv("KMP_LOCAL_DIR", ".cache/kmp_repo")).resolve(),
        )

        # Конфигурация по умолчанию
        self.max_files = 20
        self.per_file_max_chars = 4000

        # План тестов
        self.test_plan = [
            {"context_k": 16, "depth_percent": 50, "test_id": "v3_stealth_distractors_16k"},
            {"context_k": 32, "depth_percent": 80, "test_id": "v3_stealth_distractors_32k"},
        ]
        self.current_test_index = 0

        log.info(f"KMP BugHunt v3 (Hardcore) initialized. Plan: {len(self.test_plan)} tests.")

    def _ensure_repo(self):
        self.repo.local_dir.parent.mkdir(parents=True, exist_ok=True)
        if not self.repo.local_dir.exists():
            log.info("Cloning repo...")
            _run(["git", "clone", "--depth", "1", self.repo.url, str(self.repo.local_dir)])

    def _pick_files(self) -> List[Path]:
        root = self.repo.local_dir
        exts = (".kt", ".kts")
        exclude_dirs = (".git", "build", "generated", "node_modules", ".idea")

        all_files = _iter_files(root, exts, exclude_dirs)

        # Предпочитаем файлы исходного кода
        preferred = [p for p in all_files if "src" in p.parts]
        pool = preferred if len(preferred) >= 5 else all_files

        seed_val = f"{self.test_id}:{self.current_test_index}"
        rnd = random.Random(_sha1_text(seed_val))
        rnd.shuffle(pool)

        return pool[:self.max_files]

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        """
        Парсинг ответа. Использует базовые методы очистки.
        """
        clean = self._sanitize_code(llm_raw_output)
        clean = self._cleanup_llm_response(clean)

        # Убираем markdown и переносы строк в JSON
        clean = re.sub(r'```(?:json)?\s*(.*?)```', r'\1', clean, flags=re.DOTALL)
        clean = re.sub(r'\\n', ' ', clean)

        parsed = None
        try:
            parsed = json.loads(clean)
        except:
            # Fallback
            match = re.search(r'\{[\s\S]*?"findings"[\s\S]*?\}', clean)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except:
                    pass

        return {
            'answer': json.dumps(parsed, ensure_ascii=False) if parsed else clean,
            'thinking_log': llm_raw_output,
            'parsed_findings': parsed.get('findings', []) if parsed else []
        }

    def generate(self) -> Dict[str, Any]:
        if not self.test_plan:
            raise RuntimeError("Test plan empty")

        config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1

        self._ensure_repo()
        files = self._pick_files()

        # Гарантируем 2 разных файла для UI и VM
        kt_files = [f for f in files if str(f).endswith(".kt")]
        if len(kt_files) < 2:
            kt_files = kt_files * 2

        ui_file = kt_files[0]
        vm_file = kt_files[1]

        # Генерируем 4 уникальных trace ID
        # 2 БАГА + 2 ДИСТРАКТОРА (Правильных кода)
        trace_ui_bug = uuid.uuid4().hex[:8]
        trace_ui_ok = uuid.uuid4().hex[:8]

        trace_vm_bug = uuid.uuid4().hex[:8]
        trace_vm_ok = uuid.uuid4().hex[:8]

        blocks = []
        meta = {
            "ui": {
                "file": str(ui_file.relative_to(self.repo.local_dir)),
                "bug_trace": trace_ui_bug,
                "ok_trace": trace_ui_ok
            },
            "vm": {
                "file": str(vm_file.relative_to(self.repo.local_dir)),
                "bug_trace": trace_vm_bug,
                "ok_trace": trace_vm_ok
            },
        }

        # Сборка контекста с инъекциями
        for p in files:
            txt = _read_text_safely(p, self.per_file_max_chars)
            rel = str(p.relative_to(self.repo.local_dir))

            # Инъекция UI (баг + дистрактор)
            if p == ui_file:
                txt, _ = _inject_ui_stealth_bug_with_distractor(txt, trace_ui_bug, trace_ui_ok)
                log.info(f"UI Injection in {rel}: BUG={trace_ui_bug}, OK={trace_ui_ok}")

            # Инъекция VM (баг + дистрактор)
            if p == vm_file:
                txt, _ = _inject_vm_stealth_bug_with_distractor(txt, trace_vm_bug, trace_vm_ok)
                log.info(f"VM Injection in {rel}: BUG={trace_vm_bug}, OK={trace_vm_ok}")

            blocks.append(f"// FILE: {rel}\n{txt}")

        haystack = "\n\n".join(blocks)

        question = (
            "Ты — ведущий инженер по качеству (QA Automation Lead). Проведи глубокий аудит кода.\n"
            "В логах системы фигурируют ID операций (trace ID), которые можно найти в коде (в комментариях [Audit], FIXME или Operation ID).\n\n"
            "**Ситуация**:\n"
            "1. В UI-слое есть две операции отслеживания. Одна реализована корректно через `LaunchedEffect`, другая вызывает **утечку side-effect'ов** (прямой запуск `scope.launch` при рекомпозиции).\n"
            "2. В ViewModel есть два события навигации. Одно использует безопасный `Channel`/`trySend`, другое использует **StateFlow для one-shot событий** без сброса (баг).\n\n"
            "**Твоя задача (Reasoning)**:\n"
            "1. Найди ВСЕ 4 trace ID в коде.\n"
            "2. Проанализируй код рядом с каждым ID: является ли он багом или корректной реализацией?\n"
            "3. Отфильтруй корректный код (дистракторы).\n"
            "4. Верни JSON только с **двумя реальными багами**.\n\n"
            "Формат JSON (строго):\n"
            "{\n"
            '  "findings": [\n'
            '    {"file": "path/to/file.kt", "trace": "BAD_TRACE_ID_1", "verdict": "BUG: описание..."},\n'
            '    {"file": "path/to/file.kt", "trace": "BAD_TRACE_ID_2", "verdict": "BUG: описание..."}\n'
            "  ]\n"
            "}"
        )

        return {
            "prompt": f"{haystack}\n\nВОПРОС:\n{question}\n\nОТВЕТ (JSON):",
            "expected_output": json.dumps(meta, ensure_ascii=False),
            "test_name": config["test_id"],
            "metadata": {
                "complexity": "hardcore",
                "distractors": True,
                "context_k": config["context_k"]
            }
        }

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Верификация с проверкой на дистракторы.
        """
        parsed_res = self.parse_llm_output(llm_output)
        findings = parsed_res.get('parsed_findings', [])

        try:
            exp = json.loads(expected_output)
        except:
            return {"is_correct": False, "score": 0, "details": {"error": "Invalid expected output"}}

        if len(findings) != 2:
            return {
                "is_correct": False,
                "score": 0,
                "details": {
                    "error": f"Found {len(findings)} items, expected exactly 2 bugs",
                    "preview": findings
                }
            }

        got_traces = {str(f.get("trace", "")).strip() for f in findings}

        # Целевые (багованные) трейсы
        target_traces = {exp["ui"]["bug_trace"], exp["vm"]["bug_trace"]}
        # Дистракторы (правильные) трейсы - если модель выбрала их, это провал Reasoning
        distractor_traces = {exp["ui"]["ok_trace"], exp["vm"]["ok_trace"]}

        # Оценка
        correct_picks = len(got_traces.intersection(target_traces))
        wrong_picks = len(got_traces.intersection(distractor_traces))

        # Идеальный результат: нашел оба бага, не выбрал ни одного дистрактора
        is_perfect = (correct_picks == 2) and (wrong_picks == 0)

        score = 0.0
        if is_perfect:
            score = 1.0
        elif correct_picks == 1 and wrong_picks == 0:
            score = 0.5  # Нашел 1 баг, но уверенно (не выбрал дистрактор)
        elif correct_picks == 1 and wrong_picks == 1:
            score = 0.25 # Угадал 50/50
        elif correct_picks == 2 and wrong_picks > 0:
            score = 0.5  # Нашел все, но прихватил лишнее (если бы формат позволял >2)

        return {
            "is_correct": score >= 0.5, # Засчитываем, если хотя бы один баг найден чисто
            "score": score,
            "details": {
                "got_traces": list(got_traces),
                "expected_bugs": list(target_traces),
                "distractors": list(distractor_traces),
                "wrong_picks_count": wrong_picks,
                "correct_picks_count": correct_picks
            }
        }
