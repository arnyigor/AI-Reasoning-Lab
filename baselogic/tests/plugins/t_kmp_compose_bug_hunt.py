# plugins/t_kmp_compose_bug_hunt.py
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

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


# -----------------------------
# Utilities
# -----------------------------
def _run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    """Run a command and return stdout; raises on error."""
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
        if p.suffix not in exts and not any(str(p).endswith(e) for e in exts):
            continue
        parts = set(p.parts)
        if any(d in parts for d in exclude_dirs):
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


def _find_first_composable_function(src: str) -> Optional[int]:
    """Returns line index (0-based) where @Composable function body starts."""
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if "@Composable" in line:
            for j in range(i, min(i + 30, len(lines))):
                if "fun " in lines[j] and "{" in lines[j]:
                    return j
                if "{" in lines[j] and ("fun " in "\n".join(lines[i:j + 1])):
                    return j
    return None


def _insert_bug_into_composable(src: str) -> Tuple[str, int]:
    """
    Insert realistic Compose regression: launching coroutine in composable body.
    Returns (new_src, inserted_line_number_1_based).
    """
    lines = src.splitlines()
    ins_at = _find_first_composable_function(src)

    if ins_at is None:
        ins_at = 0
        for i, line in enumerate(lines[:200]):
            if line.strip().startswith("import "):
                ins_at = i + 1

    insert_idx = ins_at + 1
    trace = uuid.uuid4().hex[:8]
    bug_block = [
        "    // --- Regression (introduced recently) ---",
        "    // The screen 'works', but recompositions will trigger this again and again.",
        "    val _bugScope = androidx.compose.runtime.rememberCoroutineScope()",
        "    _bugScope.launch {",
        f"        kotlinx.coroutines.delay(25) // simulate IO; trace={trace}",
        f"        println(\"[BUG] repeated side-effect; trace={trace}\")",
        "    }",
        "    // --- End regression ---",
        "",
    ]

    lines[insert_idx:insert_idx] = bug_block
    inserted_line = insert_idx + 1  # 1-based
    return "\n".join(lines), inserted_line


def _normalize_path(path: str) -> str:
    """Normalize path separators for cross-platform comparison."""
    return path.replace("\\", "/").lower().strip()


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


# -----------------------------
# Generator
# -----------------------------
class KmpComposeBugHuntTestGenerator(AbstractTestGenerator):
    """
    Realistic "bug hunt" for a large KMP + Compose codebase.

    Improvements:
    - Cross-platform path normalization
    - Line number tolerance (±10 lines)
    - Better JSON parsing with fallback
    - More forgiving verification logic
    """

    DEFAULT_REPO_URL = "https://github.com/JetBrains/compose-multiplatform.git"

    def __init__(self, test_id: str):
        super().__init__(test_id)

        self.repo = RepoConfig(
            url=os.getenv("KMP_REPO_URL", self.DEFAULT_REPO_URL),
            ref=os.getenv("KMP_REPO_REF", "HEAD"),
            local_dir=Path(os.getenv("KMP_LOCAL_DIR", ".cache/kmp_repo")).resolve(),
        )

        lengths_str = os.getenv("KMP_CONTEXT_LENGTHS_K", "8,16,32")
        depths_str = os.getenv("KMP_NEEDLE_DEPTH_PERCENTAGES", "10,50,90")
        max_files = int(os.getenv("KMP_MAX_FILES", "40"))
        per_file_max_chars = int(os.getenv("KMP_PER_FILE_MAX_CHARS", "8000"))

        self.context_lengths_k = [int(x.strip()) for x in lengths_str.split(",") if x.strip()]
        self.needle_depths = [int(x.strip()) for x in depths_str.split(",") if x.strip()]
        self.max_files = max_files
        self.per_file_max_chars = per_file_max_chars

        self.test_plan = self._create_test_plan()
        self.current_test_index = 0

        log.info("KMP Compose BugHunt: plan=%d cases", len(self.test_plan))

    def _create_test_plan(self) -> List[Dict[str, Any]]:
        plan = []
        for k in self.context_lengths_k:
            for d in self.needle_depths:
                plan.append(
                    {
                        "context_k": k,
                        "depth_percent": d,
                        "test_id": f"kmp_compose_bug_hunt_{k}k_{d}pct",
                    }
                )
        return plan

    def _ensure_repo(self) -> None:
        self.repo.local_dir.parent.mkdir(parents=True, exist_ok=True)

        if not self.repo.local_dir.exists():
            log.info("Cloning repo into %s", self.repo.local_dir)
            _run(["git", "clone", "--depth", "1", self.repo.url, str(self.repo.local_dir)])
        else:
            try:
                _run(["git", "fetch", "--all", "--prune"], cwd=self.repo.local_dir)
            except Exception as e:
                log.warning("git fetch failed: %s", e)

        if self.repo.ref and self.repo.ref != "HEAD":
            try:
                _run(["git", "checkout", self.repo.ref], cwd=self.repo.local_dir)
            except Exception as e:
                log.warning("git checkout %s failed: %s", self.repo.ref, e)

    def _pick_files(self, cfg: CaseConfig) -> List[Path]:
        root = self.repo.local_dir
        exts = (".kt", ".kts", ".gradle.kts", ".md")
        exclude_dirs = (
            ".git",
            "build",
            ".gradle",
            ".idea",
            "out",
            "node_modules",
            "Pods",
            "DerivedData",
            "generated",
        )

        files = _iter_files(root, exts=exts, exclude_dirs=exclude_dirs)
        preferred = [p for p in files if any(seg in p.parts for seg in ("src", "examples", "sample", "samples"))]
        pool = preferred if len(preferred) >= 20 else files

        seed = _sha1_text(f"{self.test_id}:{cfg.context_k}:{cfg.depth_percent}:{len(pool)}")
        rnd = random.Random(seed)
        rnd.shuffle(pool)

        return pool[: cfg.max_files]

    def _build_context_blocks(self, chosen: List[Path], cfg: CaseConfig) -> Tuple[List[str], Dict[str, Any]]:
        """Returns list of text blocks and an injection metadata dict."""
        rnd = random.Random(_sha1_text(f"{self.test_id}:{cfg.context_k}:{cfg.depth_percent}:target"))
        kt_files = [p for p in chosen if str(p).endswith(".kt")]
        target_file = rnd.choice(kt_files) if kt_files else rnd.choice(chosen)

        root = self.repo.local_dir
        rel_target = str(target_file.relative_to(root))

        blocks: List[str] = []
        injection_meta: Dict[str, Any] = {
            "target_file": rel_target,
            "inserted_line": None,
            "trace": None,
        }

        for p in chosen:
            rel = str(p.relative_to(root))
            txt = _read_text_safely(p, max_chars=cfg.per_file_max_chars)
            if not txt.strip():
                continue

            if p == target_file and str(p).endswith(".kt"):
                new_txt, line_no = _insert_bug_into_composable(txt)
                txt = new_txt
                injection_meta["inserted_line"] = line_no

            header = (
                f"\n\n// ================================\n"
                f"// FILE: {rel}\n"
                f"// SNAPSHOT_SHA1: {_sha1_text(txt)}\n"
                f"// ================================\n"
            )
            blocks.append(header + txt)

        return blocks, injection_meta

    def _assemble_haystack(self, blocks: List[str], cfg: CaseConfig) -> str:
        """Assemble context with target size."""
        target_chars = cfg.context_k * 1024 * 3
        joined = "\n".join(blocks)

        if len(joined) <= target_chars:
            return joined

        head = joined[: int(target_chars * 0.6)]
        tail = joined[-int(target_chars * 0.35) :]
        noise = (
            "\n\n/* --- build logs excerpt ---\n"
            f"[{datetime.datetime.now().isoformat()}] WARN: Gradle configuration cache reused\n"
            f"[{datetime.datetime.now().isoformat()}] INFO: KMP targets: android/ios/desktop\n"
            f"[{datetime.datetime.now().isoformat()}] DEBUG: taskId={uuid.uuid4().hex[:12]}\n"
            "--- end logs --- */\n\n"
        )
        return head + noise + tail

    def generate(self) -> Dict[str, Any]:
        if not self.test_plan:
            raise RuntimeError("Test plan is empty")

        config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1

        cfg = CaseConfig(
            context_k=int(config["context_k"]),
            depth_percent=int(config["depth_percent"]),
            max_files=self.max_files,
            per_file_max_chars=self.per_file_max_chars,
        )

        self._ensure_repo()

        chosen = self._pick_files(cfg)
        blocks, meta = self._build_context_blocks(chosen, cfg)

        # Depth control: move target file block
        target_file = meta["target_file"]
        target_idx = None
        for i, b in enumerate(blocks):
            if f"// FILE: {target_file}" in b:
                target_idx = i
                break

        if target_idx is not None:
            b = blocks.pop(target_idx)
            insert_at = int(len(blocks) * (cfg.depth_percent / 100.0))
            insert_at = max(0, min(insert_at, len(blocks)))
            blocks.insert(insert_at, b)

        haystack = self._assemble_haystack(blocks, cfg)

        question = (
            "В проекте KMP + Compose появилась регрессия: при открытии экрана/компонента "
            "наблюдается повторяющийся side-effect (например, множатся запросы/логи) при рекомпозициях.\n\n"
            "Задача:\n"
            "1) Найди точное место в коде, которое запускает side-effect на каждой рекомпозиции.\n"
            "2) Укажи путь к файлу и примерную строку.\n"
            "3) Предложи исправление: перенести запуск в LaunchedEffect(...) или другой корректный механизм side-effects.\n\n"
            "Ответ верни в JSON с полями: file, line, root_cause, fix_patch."
        )

        expected = {
            "file": meta["target_file"],
            "line": meta["inserted_line"],
            "must_contain": ["LaunchedEffect", "DisposableEffect", "SideEffect"],
            "root_cause_keywords": ["recomposition", "side-effect", "scope.launch", "repeated"],
        }

        prompt = (
            "Ты — senior Android/KMP инженер. Проведи расследование по коду ниже.\n"
            "Игнорируй любые 'тестовые ключи' и нерелевантные логи; ищи причину именно в Compose-коде.\n\n"
            f"{haystack}\n\n"
            f"ВОПРОС:\n{question}\n\n"
            "ОТВЕТ:\n"
        )

        return {
            "prompt": prompt,
            "expected_output": json.dumps(expected, ensure_ascii=False),
            "test_name": config["test_id"],
            "metadata": {
                "repo_url": self.repo.url,
                "repo_ref": self.repo.ref,
                "context_k": cfg.context_k,
                "depth_percent": cfg.depth_percent,
                "max_files": cfg.max_files,
                "per_file_max_chars": cfg.per_file_max_chars,
                "complexity": "high",
                "contains_code": True,
                "bug_pattern": "coroutine launch in @Composable body (recomposition repeats side-effect)",
            },
        }

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Improved verification with:
        - Cross-platform path normalization
        - Line number tolerance (±10)
        - Multiple fix patterns
        - Better JSON extraction
        """
        clean = self._cleanup_llm_response(llm_output).strip()
        exp = json.loads(expected_output)

        details = {
            "expected_file": exp.get("file"),
            "expected_line": exp.get("line"),
            "received_snippet": clean[:300],
            "match_file": False,
            "match_fix": False,
            "match_root_cause": False,
            "match_line": False,
        }

        # Extract JSON from response
        ans_obj = None
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', clean, re.DOTALL)
        if json_match:
            try:
                ans_obj = json.loads(json_match.group(1))
            except:
                pass

        if ans_obj is None:
            try:
                ans_obj = json.loads(clean)
            except:
                pass

        # Normalize expected file path
        expected_file = _normalize_path(exp.get("file", ""))
        expected_line = exp.get("line")

        # File check (cross-platform)
        file_ok = False
        if expected_file:
            # Check in raw text
            if expected_file in _normalize_path(clean):
                file_ok = True
            # Check in parsed JSON
            if isinstance(ans_obj, dict):
                ans_file = _normalize_path(str(ans_obj.get("file", "")))
                if expected_file in ans_file or ans_file in expected_file:
                    file_ok = True

        # Line check (with tolerance)
        line_ok = False
        if expected_line and isinstance(ans_obj, dict):
            ans_line = ans_obj.get("line")
            if ans_line and isinstance(ans_line, (int, float)):
                if abs(int(ans_line) - expected_line) <= 10:
                    line_ok = True

        # Fix check (multiple patterns)
        fix_ok = False
        must_patterns = exp.get("must_contain", [])
        fix_patterns = [
            r'LaunchedEffect',
            r'DisposableEffect',
            r'SideEffect',
            r'rememberUpdatedState',
        ]

        combined_check = clean
        if isinstance(ans_obj, dict):
            combined_check += " " + str(ans_obj.get("fix_patch", ""))
            combined_check += " " + str(ans_obj.get("root_cause", ""))

        if any(re.search(p, combined_check, re.IGNORECASE) for p in fix_patterns):
            fix_ok = True

        # Root cause check
        cause_ok = False
        cause_keys = exp.get("root_cause_keywords", [])
        hits = sum(1 for k in cause_keys if k.lower() in combined_check.lower())
        if hits >= max(1, len(cause_keys) // 2):
            cause_ok = True

        details["match_file"] = file_ok
        details["match_line"] = line_ok
        details["match_fix"] = fix_ok
        details["match_root_cause"] = cause_ok

        # Scoring
        score = 0.0
        if file_ok:
            score += 0.4
        if line_ok:
            score += 0.1
        if fix_ok:
            score += 0.4
        if cause_ok:
            score += 0.1

        return {
            "is_correct": score >= 0.8,  # Более мягкий порог
            "score": round(score, 3),
            "details": details,
        }
