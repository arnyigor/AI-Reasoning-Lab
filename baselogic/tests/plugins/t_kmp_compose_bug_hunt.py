# plugins/t_kmp_compose_bug_hunt_v4.py

"""
KMP + Compose Bug Hunt v4 (International Hardcore).
--------------------------------------------------------------------
Scenario:
A mixed-language project (English docs, Russian comments).
The model must act as a Principal Architect detecting subtle logic bugs.

Traps:
1. "Zombie State": derivedStateOf reads a plain 'var'.
   Symptom: UI stuck.
2. "Lifecycle Leak": LaunchedEffect subscribes but never unsubscribes.
   Symptom: OOM / Leaks.

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

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


@dataclass
class RepoConfig:
    url: str
    ref: str
    local_dir: Path


# ----------------------------------------------------------------------
# INJECTION LOGIC
# ----------------------------------------------------------------------

def _inject_zombie_state_bug(src: str, bug_trace: str, ok_trace: str) -> Tuple[str, int]:
    """
    Injects:
    1. Distractor (Correct usage of derivedStateOf with State)
    2. Bug (Incorrect usage with plain var)
    """
    lines = src.splitlines()
    ins_at = None

    # Try to find a Composable to look natural
    for i, line in enumerate(lines):
        if "@Composable" in line and "fun" in line:
            for j in range(i, min(i+20, len(lines))):
                if "{" in lines[j]:
                    ins_at = j + 1
                    break
            if ins_at: break

    # Fallback: create new component
    if ins_at is None:
        lines.extend(["", "// Компонент фильтрации данных", "@androidx.compose.runtime.Composable", "fun DataFilterEngine() {"])
        ins_at = len(lines)

    # DISTRACTOR (Correct)
    distractor_block = [
        f"    // [Audit] Logic ID: {ok_trace}",
        "    val searchQuery = androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(\"\") }",
        "    val filteredResults by androidx.compose.runtime.remember {",
        "        androidx.compose.runtime.derivedStateOf {",
        f"            // Correct: Reading State object inside. Trace: {ok_trace}",
        "            // (Пересчет списка при изменении query)",
        "            performSearch(searchQuery.value)",
        "        }",
        "    }",
    ]

    # BUG (Incorrect: Plain var)
    bug_block = [
        "",
        f"    // [Audit] Logic ID: {bug_trace}",
        "    // Оптимизация: кешируем конфиг, чтобы не пересоздавать лишний раз",
        "    var rawFilterConfig = \"default_config\" // Plain var!",
        "    val configHash by androidx.compose.runtime.remember {",
        "        androidx.compose.runtime.derivedStateOf {",
        f"            // Trace: {bug_trace}",
        "            // ОШИБКА: derivedStateOf не видит изменений обычной переменной rawFilterConfig",
        "            rawFilterConfig.hashCode()",
        "        }",
        "    }",
    ]

    # Randomize order
    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + [""] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + [""] + distractor_block

    return "\n".join(lines), ins_at + 1


def _inject_lifecycle_leak_bug(src: str, bug_trace: str, ok_trace: str) -> Tuple[str, int]:
    """
    Injects:
    1. Distractor (Correct DisposableEffect)
    2. Bug (Leaking LaunchedEffect)
    """
    lines = src.splitlines()
    ins_at = None

    for i, line in enumerate(lines):
        if "@Composable" in line and "fun" in line:
            for j in range(i, min(i+20, len(lines))):
                if "{" in lines[j]:
                    ins_at = j + 1
                    break
            if ins_at: break

    if ins_at is None:
        lines.extend(["", "// Экран дашборда", "@androidx.compose.runtime.Composable", "fun DashboardScreen() {"])
        ins_at = len(lines)

    # BUG (Leak)
    bug_block = [
        f"    // [Audit] Setup analytics: {bug_trace}",
        "    // Безопасный скоуп для подписки на события аналитики",
        "    androidx.compose.runtime.LaunchedEffect(Unit) {",
        "        // BUG: Registering without unregistering -> Memory Leak",
        "        AnalyticsManager.getInstance().registerCallback { event ->",
        f"            println(\"Event: $event (ID: {bug_trace})\")",
        "        }",
        "    }",
    ]

    # DISTRACTOR (Correct)
    distractor_block = [
        "",
        f"    // [Audit] Setup sensor: {ok_trace}",
        "    androidx.compose.runtime.DisposableEffect(Unit) {",
        "        val listener = SensorListener { data ->",
        f"            println(\"Sensor: $data (ID: {ok_trace})\")",
        "        }",
        "        // Корректная подписка с очисткой",
        "        SensorManager.register(listener)",
        "        onDispose {",
        "            SensorManager.unregister(listener)",
        "        }",
        "    }",
    ]

    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + [""] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + [""] + distractor_block

    return "\n".join(lines), ins_at + 1


# ----------------------------------------------------------------------
# Generator Class
# ----------------------------------------------------------------------

class KmpComposeBugHuntV4TestGenerator(AbstractTestGenerator):
    DEFAULT_REPO_URL = "https://github.com/JetBrains/compose-multiplatform.git"

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.repo = RepoConfig(
            url=os.getenv("KMP_REPO_URL", self.DEFAULT_REPO_URL),
            ref=os.getenv("KMP_REPO_REF", "HEAD"),
            local_dir=Path(os.getenv("KMP_LOCAL_DIR", ".cache/kmp_repo")).resolve(),
        )
        self.max_files = 20
        self.per_file_max_chars = 6000
        self.test_plan = [{"context_k": 32, "depth_percent": 50, "test_id": "v4_international_hardcore"}]
        self.current_test_index = 0

    def _ensure_repo(self):
        self.repo.local_dir.parent.mkdir(parents=True, exist_ok=True)
        if not self.repo.local_dir.exists():
            subprocess.run(["git", "clone", "--depth", "1", self.repo.url, str(self.repo.local_dir)], check=True, stdout=subprocess.PIPE)

    def _iter_files(self, root, exts):
        out = []
        for p in root.rglob("*"):
            if p.is_file() and any(str(p).endswith(e) for e in exts):
                if not any(x in p.parts for x in [".git", "build", "generated"]):
                    out.append(p)
        return out

    def generate(self) -> Dict[str, Any]:
        self._ensure_repo()

        files = self._iter_files(self.repo.local_dir, (".kt",))
        # Prefer "src" files that are substantial enough
        files = [f for f in files if "src" in f.parts and f.stat().st_size > 500]
        random.shuffle(files)
        chosen = files[:self.max_files]

        if len(chosen) < 2: chosen = chosen * 2
        file_state = chosen[0]
        file_cycle = chosen[1]

        t_zombie_bug = uuid.uuid4().hex[:8]
        t_zombie_ok = uuid.uuid4().hex[:8]
        t_leak_bug = uuid.uuid4().hex[:8]
        t_leak_ok = uuid.uuid4().hex[:8]

        blocks = []

        for p in chosen:
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore')[:self.per_file_max_chars]
            except: continue

            rel = str(p.relative_to(self.repo.local_dir))

            if p == file_state:
                txt, _ = _inject_zombie_state_bug(txt, t_zombie_bug, t_zombie_ok)

            if p == file_cycle:
                txt, _ = _inject_lifecycle_leak_bug(txt, t_leak_bug, t_leak_ok)

            blocks.append(f"// FILE: {rel}\n{txt}")

        haystack = "\n\n".join(blocks)

        system_prompt = (
            "You are a Principal Android Architect at a top-tier tech company. "
            "You are reviewing code submitted by a Junior developer. "
            "The code contains comments in Russian, but you must output your analysis in JSON format."
        )

        user_prompt = (
            "Review the provided KMP/Compose code. There are 4 marked blocks with IDs `[Audit] ...`.\n"
            "Two of these blocks contain CRITICAL architectural bugs causing production issues.\n\n"
            "**Reported Symptoms:**\n"
            "1. **Bug A (UI Freeze):** Users report that changing filter settings does NOT update the results on screen, even though logs show the variable changing.\n"
            "2. **Bug B (OOM Crash):** The app crashes with `OutOfMemoryError` after the user repeatedly opens and closes the Dashboard screen.\n\n"
            "**Your Task:**\n"
            "1. Locate all 4 Audit IDs.\n"
            "2. Analyze the code: Distinguish between correct patterns (Distractors) and broken logic (Bugs).\n"
            "3. Return a valid JSON object containing exactly TWO findings corresponding to the symptoms above.\n\n"
            "**Output Format (Strict JSON):**\n"
            "{\n"
            '  "findings": [\n'
            '    {"trace": "TRACE_ID_1", "verdict": "BUG: Brief technical explanation..."},\n'
            '    {"trace": "TRACE_ID_2", "verdict": "BUG: Brief technical explanation..."}\n'
            "  ]\n"
            "}"
        )

        expected = {
            "bugs": [t_zombie_bug, t_leak_bug],
            "distractors": [t_zombie_ok, t_leak_ok],
        }

        return {
            "prompt": f"{system_prompt}\n\n{haystack}\n\nQUESTION:\n{user_prompt}\n\nANSWER (JSON):",
            "system_prompt": system_prompt,
            "expected_output": json.dumps(expected),
            "test_name": "v4_international_hardcore",
            "metadata": {"complexity": "impossible"}
        }

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        # Clean markdown
        clean = re.sub(r'```(?:json)?\s*(.*?)```', r'\1', llm_raw_output, flags=re.DOTALL)
        clean = re.sub(r'<think>.*?</think>', '', clean, flags=re.DOTALL)
        clean = clean.strip()

        parsed = None
        try:
            parsed = json.loads(clean)
        except:
            # Fallback regex
            m = re.search(r'\{[\s\S]*?"findings"[\s\S]*?\}', clean)
            if m:
                try: parsed = json.loads(m.group(0))
                except: pass

        return {'answer': json.dumps(parsed) if parsed else clean, 'parsed_findings': parsed.get('findings', []) if parsed else []}

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        parsed = self.parse_llm_output(llm_output)
        findings = parsed.get('parsed_findings', [])

        try: exp = json.loads(expected_output)
        except: return {"is_correct": False, "score": 0, "details": {"error": "Invalid expected output"}}

        if len(findings) != 2:
            return {"is_correct": False, "score": 0, "details": {"error": f"Expected exactly 2 bugs, found {len(findings)}"}}

        got = {str(f.get("trace", "")).strip() for f in findings}
        targets = set(exp["bugs"])
        distractors = set(exp["distractors"])

        correct = len(got.intersection(targets))
        wrong = len(got.intersection(distractors))

        # Strict scoring: All or nothing for "Impossible" mode
        is_correct = (correct == 2) and (wrong == 0)

        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0,
            "details": {
                "got_traces": list(got),
                "expected_bugs": list(targets),
                "distractors_picked": list(got.intersection(distractors)),
                "verdicts": [f.get("verdict") for f in findings]
            }
        }
