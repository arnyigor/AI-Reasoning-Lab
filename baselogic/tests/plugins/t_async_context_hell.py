import os
import re
import json
import uuid
import random
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Tuple

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


@dataclass
class RepoConfig:
    url: str
    ref: str
    local_dir: Path


# ----------------------------------------------------------------------
# INJECTION LOGIC (PRINCIPAL ARCHITECT LEVEL)
# ----------------------------------------------------------------------

def _inject_context_propagation_bug(src: str, bug_trace: str, ok_trace: str) -> Tuple[str, int]:
    """
    Injects a 'Context Propagation' bug.
    Issue: asyncio.loop.run_in_executor does NOT propagate ContextVars automatically.
    The code inside the executor will see empty context vars.
    """
    lines = src.splitlines()
    ins_at = 0

    # Imports
    lines = ["import asyncio", "import time", "from contextvars import ContextVar, copy_context", "from functools import partial"] + lines

    for i, line in enumerate(lines):
        if "def " in line:
            ins_at = len(lines)
            break

    # Setup ContextVar
    header = [
        "",
        "# Global Security Context for Audit Logging",
        "current_audit_user: ContextVar[str] = ContextVar('audit_user', default='SYSTEM')",
        ""
    ]
    lines[ins_at:ins_at] = header
    ins_at += len(header)

    # BUG: Lost Context in ThreadPool
    bug_block = [
        "",
        "class ReportGenerator:",
        "    def _heavy_sync_generation(self, report_id: str):",
        "        # SYNC CODE running in thread",
        "        user = current_audit_user.get()",
        "        print(f'Generating report {report_id} for {user}')",
        "        time.sleep(0.1) # Simulate CPU work",
        "        return f'PDF_DATA_{report_id}'",
        "",
        "    async def generate_user_report(self, rid: str, user: str):",
        "        token = current_audit_user.set(user)",
        "        try:",
        "            loop = asyncio.get_running_loop()",
        f"            # [Audit] Logic ID: {bug_trace}",
        "            # BUG: run_in_executor starts a new thread.",
        "            # ContextVars (like current_audit_user) are NOT copied to threads by default.",
        "            # inside _heavy_sync_generation, user will be 'SYSTEM' (default), not the actual user.",
        "            result = await loop.run_in_executor(",
        "                None, self._heavy_sync_generation, rid",
        "            )",
        "            return result",
        "        finally:",
        "            current_audit_user.reset(token)",
    ]

    # DISTRACTOR: Correct Context Propagation
    distractor_block = [
        "",
        "class LegacyDataExporter:",
        f"    # [Audit] Logic ID: {ok_trace}",
        "    async def export_data_safe(self, query: str):",
        "        ctx = copy_context()",
        "        loop = asyncio.get_running_loop()",
        "        # Correct: Using functools.partial to wrap the call,",
        "        # and ctx.run to execute it inside the captured context.",
        "        await loop.run_in_executor(",
        "            None, lambda: ctx.run(self._sync_export, query)",
        "        )",
        f"        # Trace: {ok_trace}",
        "        return True",
        "",
        "    def _sync_export(self, q): pass",
    ]

    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + ["", "# ---"] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + ["", "# ---"] + distractor_block

    return "\n".join(lines), ins_at + 1


def _inject_destructor_bug(src: str, bug_trace: str, ok_trace: str) -> Tuple[str, int]:
    """
    Injects a '__del__ Lifecycle' bug.
    Issue: Attempting to clean up async resources (close sockets/DBs) in __del__.
    __del__ is synchronous and called by GC at unpredictable times (even when loop is closed).
    """
    lines = src.splitlines()
    ins_at = 0

    lines = ["import weakref", "import asyncio"] + lines

    for i, line in enumerate(lines):
        if "class" in line:
            ins_at = len(lines)
            break

    # BUG: Sync Destructor cleaning Async Resource
    bug_block = [
        "",
        "class PostgresConnector:",
        "    def __init__(self, dsn):",
        "        self.dsn = dsn",
        "        self._pool = None",
        "",
        "    async def connect(self):",
        "        self._pool = await self._create_pool()",
        "",
        "    def __del__(self):",
        f"        # [Audit] Logic ID: {bug_trace}",
        "        # BUG: __del__ is a synchronous finalizer called by Garbage Collector.",
        "        # 1. We cannot await here.",
        "        # 2. Scheduling a task is dangerous: the event loop might be closed or closing.",
        "        # 3. This often causes 'RuntimeError: Event loop is closed' logs during shutdown.",
        "        if self._pool:",
        "            try:",
        "                # The naive attempt to 'be safe' causes the crash",
        "                loop = asyncio.get_event_loop()",
        "                if loop.is_running():",
        "                    loop.create_task(self._pool.close())",
        "            except Exception:",
        "                pass",
        "",
        "    async def _create_pool(self): return type('MockPool', (), {'close': lambda s: None})()",
    ]

    # DISTRACTOR: Correct Cleanup via Weakref Finalizer or Context Manager
    distractor_block = [
        "",
        "class RedisCache:",
        "    def __init__(self):",
        "        self._client = None",
        "        # Correct: Rely on Async Context Managers or weakref.finalize for non-async cleanup",
        "        # But for async connections, standard practice is 'async with' or explicit 'aclose'",
        "",
        f"    # [Audit] Logic ID: {ok_trace}",
        "    async def aclose(self):",
        "        if self._client:",
        "            await self._client.close()",
        f"            # Trace: {ok_trace}",
        "",
        "    async def __aenter__(self): return self",
        "    async def __aexit__(self, exc_type, exc, tb): await self.aclose()",
    ]

    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + ["", "# ---"] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + ["", "# ---"] + distractor_block

    return "\n".join(lines), ins_at + 1


# ----------------------------------------------------------------------
# Generator Class
# ----------------------------------------------------------------------

class AsyncContextHellBugHuntV7TestGenerator(AbstractTestGenerator):
    DEFAULT_REPO_URL = "https://github.com/tiangolo/fastapi.git"

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.repo = RepoConfig(
            url=os.getenv("FASTAPI_REPO_URL", self.DEFAULT_REPO_URL),
            ref=os.getenv("FASTAPI_REPO_REF", "HEAD"),
            local_dir=Path(os.getenv("FASTAPI_LOCAL_DIR", ".cache/fastapi_repo")).resolve(),
        )
        self.max_files = 15
        self.per_file_max_chars = 6000
        # Expert level context
        self.test_plan = [{"context_k": 96, "depth_percent": 100, "test_id": "v7_backend_architect"}]

    def _ensure_repo(self):
        self.repo.local_dir.parent.mkdir(parents=True, exist_ok=True)
        if not self.repo.local_dir.exists():
            subprocess.run(["git", "clone", "--depth", "1", self.repo.url, str(self.repo.local_dir)], check=True, stdout=subprocess.PIPE)

    def _iter_files(self, root, exts):
        out = []
        for p in root.rglob("*"):
            if p.is_file() and any(str(p).endswith(e) for e in exts):
                if not any(x in p.parts for x in [".git", "__pycache__", "docs", "tests"]):
                    out.append(p)
        return out

    def generate(self) -> Dict[str, Any]:
        self._ensure_repo()

        files = self._iter_files(self.repo.local_dir, (".py",))
        files = [f for f in files if f.stat().st_size > 1000]
        random.shuffle(files)
        chosen = files[:self.max_files]

        if len(chosen) < 2:
            chosen = [self.repo.local_dir / "service_a.py", self.repo.local_dir / "service_b.py"]

        file_ctx = chosen[0]
        file_lifecycle = chosen[1]

        t_ctx_bug = uuid.uuid4().hex[:8]
        t_ctx_ok = uuid.uuid4().hex[:8]
        t_life_bug = uuid.uuid4().hex[:8]
        t_life_ok = uuid.uuid4().hex[:8]

        blocks = []

        for p in chosen:
            try:
                if p.exists():
                    txt = p.read_text(encoding='utf-8', errors='ignore')[:self.per_file_max_chars]
                else:
                    txt = "# Placeholder"
            except: continue

            rel = str(p.relative_to(self.repo.local_dir)) if p.exists() else p.name

            if p == file_ctx:
                txt, _ = _inject_context_propagation_bug(txt, t_ctx_bug, t_ctx_ok)

            if p == file_lifecycle:
                txt, _ = _inject_destructor_bug(txt, t_life_bug, t_life_ok)

            blocks.append(f"# FILE: {rel}\n{txt}")

        haystack = "\n\n".join(blocks)

        system_prompt = (
            "You are a Distinguished Software Architect. You are auditing a critical Python AsyncIO backend. "
            "Your job is to find deep architectural flaws that standard developers miss. "
            "Focus on: Thread-boundary Context Propagation and Async Resource Lifecycle (Garbage Collection interaction)."
        )

        user_prompt = (
            "Analyze the codebase. I marked 4 blocks with `[Audit] Logic ID: ...`.\n"
            "We have two baffling production incidents:\n\n"
            "**Incident A (Security Audit Failure):**\n"
            "We use `ContextVars` to track the `User-ID` for every request. However, when we generate PDF reports (CPU-bound work offloaded to threads), "
            "the audit logs inside the PDF generator constantly show 'SYSTEM' (the default) instead of the actual user, "
            "even though the controller clearly calls `current_audit_user.set(user_id)` before calling the generator.\n\n"
            "**Incident B (The Shutdown Crash):**\n"
            "During service restarts or scaling down, we see a flood of `RuntimeError: Event loop is closed` and "
            "`Task was destroyed but it is pending` in the logs. This seems to happen when the Garbage Collector cleans up old connection objects.\n\n"
            "**Task:**\n"
            "Identify the TWO logic blocks responsible for these issues.\n"
            "Ignore valid patterns (distractors using `copy_context` or `__aexit__`).\n\n"
            "**Output JSON:**\n"
            "{\n"
            '  "findings": [\n'
            '    {"trace": "ID", "verdict": "Detailed explanation of the architectural flaw"}\n'
            '  ]\n'
            "}"
        )

        expected = {
            "bugs": [t_ctx_bug, t_life_bug],
            "distractors": [t_ctx_ok, t_life_ok],
            "bug_types": {
                t_ctx_bug: "ContextVar Propagation Failure (run_in_executor default behavior)",
                t_life_bug: "Async Cleanup in Sync Destructor (__del__ trap)"
            }
        }

        return {
            "prompt": f"{system_prompt}\n\n{haystack}\n\nQUESTION:\n{user_prompt}\n\nANSWER (JSON):",
            "system_prompt": system_prompt,
            "expected_output": json.dumps(expected),
            "test_name": "v7_backend_architect_hardcore",
            "metadata": {"complexity": "distinguished_architect", "domain": "async_context_lifecycle"}
        }

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        clean = re.sub(r'```(?:json)?\s*(.*?)```', r'\1', llm_raw_output, flags=re.DOTALL)
        clean = re.sub(r'<think>.*?</think>', '', clean, flags=re.DOTALL)
        clean = clean.strip()

        parsed_findings = []
        try:
            parsed_json = json.loads(clean)
            if 'findings' in parsed_json:
                parsed_findings = parsed_json['findings']
        except:
            trace_matches = re.findall(r'[\"\']trace[\"\']\s*:\s*[\"\']([a-zA-Z0-9]+)[\"\']', clean)
            parsed_findings = [{"trace": t, "verdict": "Extracted via regex"} for t in trace_matches]

        return {
            'answer': clean,
            'parsed_findings': parsed_findings
        }

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        parsed = self.parse_llm_output(llm_output)
        findings = parsed.get('parsed_findings', [])

        try: exp = json.loads(expected_output)
        except: return {"is_correct": False, "score": 0, "details": {"error": "Invalid expected output"}}

        if not isinstance(findings, list) or len(findings) != 2:
            return {"is_correct": False, "score": 0, "details": {"error": "Count mismatch"}}

        got = {str(f.get("trace", "")).strip() for f in findings}
        targets = set(exp["bugs"])

        # Strict checking
        is_correct = (got == targets)

        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0,
            "details": {
                "got_traces": list(got),
                "expected_bugs": list(targets),
                "false_positives": list(got - targets)
            }
        }