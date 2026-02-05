# plugins/t_async_race_bug_hunt_v5.py

"""
Asyncio + DB Consistency Bug Hunt v5 (Backend Hardcore).
--------------------------------------------------------------------
Scenario:
A High-Load Python Backend (FastAPI/SQLAlchemy context).
The model must act as a Lead Backend Engineer detecting concurrency flaws.

Traps:
1. "Lost Update" (Race Condition): Reading a value, modifying logic in app memory,
   then saving back without DB locks or atomic queries.
   Symptom: Data corruption under concurrent load (e.g., inventory count mismatch).

2. "Loop Blocking" (Sync in Async): Calling a blocking synchronous function
   (heavy calculation or sync I/O) directly inside an async route.
   Symptom: Service latency spikes, heartbeats fail, "Server is unresponsive".

Author: AI Reasoning Lab
"""

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

# Assuming this imports exist in your environment structure
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

def _inject_race_condition_bug(src: str, bug_trace: str, ok_trace: str) -> Tuple[str, int]:
    """
    Injects:
    1. Distractor (Correct Atomic Update / Row Locking)
    2. Bug (Check-Then-Act Race Condition)
    """
    lines = src.splitlines()
    ins_at = None

    # Find a place to inject a Service method
    for i, line in enumerate(lines):
        if "class" in line or "def " in line:
            # Insert logic slightly deeper or at end of imports
            ins_at = len(lines) - 2 if len(lines) > 10 else len(lines)
            break

    if ins_at is None: ins_at = len(lines)

    # DISTRACTOR (Correct: Atomic DB Operation)
    distractor_block = [
        "",
        "class WalletService:",
        f"    # [Audit] Logic ID: {ok_trace}",
        "    async def deduct_balance_atomic(self, user_id: int, amount: Decimal):",
        "        # Correct: Executing update directly in DB to prevent race conditions",
        "        query = (",
        "            update(users_table)",
        "            .where(users_table.c.id == user_id)",
        "            .where(users_table.c.balance >= amount)",
        "            .values(balance=users_table.c.balance - amount)",
        "            .returning(users_table.c.id)",
        "        )",
        f"        # Trace ID: {ok_trace}",
        "        result = await self.database.execute(query)",
        "        if not result: raise InsufficientFundsError()",
    ]

    # BUG (Incorrect: Read-Modify-Write Race)
    bug_block = [
        "",
        "class InventoryService:",
        f"    # [Audit] Logic ID: {bug_trace}",
        "    async def reserve_item_unsafe(self, item_id: str, count: int):",
        "        # OIRM (Object-In-Ram-Mapping) approach",
        "        item = await self.repo.get_by_id(item_id)",
        "        ",
        "        # BUG: Race Condition window starts here.",
        "        # Under concurrency, multiple requests read the same 'stock' value.",
        "        if item.stock >= count:",
        "            # Processing payment (simulation)...",
        "            await asyncio.sleep(0.01)",
        "            item.stock -= count",
        f"            # Trace ID: {bug_trace}",
        "            # Writing back the stale state, overwriting other transactions",
        "            await self.repo.save(item)",
        "            return True",
        "        return False",
    ]

    # Randomize order
    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + [""] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + [""] + distractor_block

    return "\n".join(lines), ins_at + 1


def _inject_blocking_loop_bug(src: str, bug_trace: str, ok_trace: str) -> Tuple[str, int]:
    """
    Injects:
    1. Distractor (Correct usage of run_in_executor/to_thread)
    2. Bug (Blocking CPU bound task in async def)
    """
    lines = src.splitlines()
    ins_at = None

    # Find valid insertion point
    for i, line in enumerate(lines):
        if "import" in line:
            continue
        ins_at = len(lines)
        break

    if ins_at is None: ins_at = 0

    # Imports needed for logic
    extra_imports = ["import time", "import hashlib", "import asyncio"]
    lines = extra_imports + lines

    # BUG (Blocking the Loop)
    bug_block = [
        "",
        f"    # [Audit] Logic ID: {bug_trace}",
        "    async def generate_report_preview(self, data: dict):",
        "        # BUG: This looks like a simple function, but it's CPU bound",
        "        # and executed synchronously inside the event loop.",
        "        log.info('Starting heavy calculation...')",
        "        ",
        "        # Heavy blocking operation simulation",
        "        # In real world: image processing, huge json parsing, pd.DataFrame ops",
        f"        result = 0",
        "        for i in range(10_000_000):",
        f"             result += hashlib.sha256(str(i).encode()).digest()[0] # Trace: {bug_trace}",
        "        ",
        "        return result",
    ]

    # DISTRACTOR (Correct: Offloading)
    distractor_block = [
        "",
        f"    # [Audit] Logic ID: {ok_trace}",
        "    async def hash_password_secure(self, raw_password: str) -> str:",
        "        # Correct: Offloading CPU-bound work to a thread pool",
        "        # to avoid blocking the main asyncio event loop.",
        "        loop = asyncio.get_running_loop()",
        "        hashed = await loop.run_in_executor(",
        "            None, ",
        "            lambda: bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt())",
        "        )",
        f"        # Trace: {ok_trace}",
        "        return hashed.decode()",
    ]

    if random.random() > 0.5:
        lines[ins_at:ins_at] = distractor_block + [""] + bug_block
    else:
        lines[ins_at:ins_at] = bug_block + [""] + distractor_block

    return "\n".join(lines), ins_at + 1


# ----------------------------------------------------------------------
# Generator Class
# ----------------------------------------------------------------------

class AsyncRaceConditionBugHuntV5TestGenerator(AbstractTestGenerator):
    # Using FastAPI as base because it's the standard for modern Python Async backends
    DEFAULT_REPO_URL = "https://github.com/tiangolo/fastapi.git"

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.repo = RepoConfig(
            url=os.getenv("FASTAPI_REPO_URL", self.DEFAULT_REPO_URL),
            ref=os.getenv("FASTAPI_REPO_REF", "HEAD"),
            local_dir=Path(os.getenv("FASTAPI_LOCAL_DIR", ".cache/fastapi_repo")).resolve(),
        )
        self.max_files = 15
        self.per_file_max_chars = 5000
        # "Context_k: 32" simulates a Senior Dev needing to hold larger architectural context
        self.test_plan = [{"context_k": 32, "depth_percent": 60, "test_id": "v5_backend_concurrency"}]
        self.current_test_index = 0

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
        # Select substantial source files
        files = [f for f in files if f.stat().st_size > 800]
        random.shuffle(files)
        chosen = files[:self.max_files]

        if len(chosen) < 2:
            # Fallback if repo is empty or filtered out
            chosen = [self.repo.local_dir / "mock_a.py", self.repo.local_dir / "mock_b.py"]

        file_race = chosen[0]
        file_blocking = chosen[1]

        t_race_bug = uuid.uuid4().hex[:8]
        t_race_ok = uuid.uuid4().hex[:8]
        t_block_bug = uuid.uuid4().hex[:8]
        t_block_ok = uuid.uuid4().hex[:8]

        blocks = []

        for p in chosen:
            try:
                if p.exists():
                    txt = p.read_text(encoding='utf-8', errors='ignore')[:self.per_file_max_chars]
                else:
                    txt = "# Placeholder file"
            except: continue

            rel = str(p.relative_to(self.repo.local_dir)) if p.exists() else p.name

            if p == file_race:
                txt, _ = _inject_race_condition_bug(txt, t_race_bug, t_race_ok)

            if p == file_blocking:
                txt, _ = _inject_blocking_loop_bug(txt, t_block_bug, t_block_ok)

            blocks.append(f"# FILE: {rel}\n{txt}")

        haystack = "\n\n".join(blocks)

        system_prompt = (
            "You are a Lead Backend Engineer (Python/Asyncio expert). "
            "You are conducting a code review for a high-load financial service. "
            "The code contains English documentation and Python logic. "
            "You must identify critical architectural flaws."
        )

        user_prompt = (
            "Review the provided Python code snippets. There are 4 marked blocks with IDs `[Audit] ...`.\n"
            "Two of these blocks contain CRITICAL concurrency bugs causing data corruption or downtime.\n\n"
            "**Reported Production Incidents:**\n"
            "1. **Bug A (Inventory Drift):** During flash sales, we sell more items than we have in stock. The database shows negative values or lost writes.\n"
            "2. **Bug B (System Freeze):** The health-check endpoint times out (503 Service Unavailable) randomly when users generate PDF reports, blocking all other requests.\n\n"
            "**Your Task:**\n"
            "1. Locate all 4 Audit IDs.\n"
            "2. Analyze the code: Distinguish between robust concurrency patterns and dangerous anti-patterns.\n"
            "3. Return a valid JSON object containing exactly TWO findings corresponding to the incidents above.\n\n"
            "**Output Format (Strict JSON):**\n"
            "{\n"
            '  "findings": [\n'
            '    {"trace": "TRACE_ID_1", "verdict": "BUG: Technical explanation (Race/Blocking)..."},\n'
            '    {"trace": "TRACE_ID_2", "verdict": "BUG: Technical explanation (Race/Blocking)..."}\n'
            "  ]\n"
            "}"
        )

        expected = {
            "bugs": [t_race_bug, t_block_bug],
            "distractors": [t_race_ok, t_block_ok],
            "bug_types": {
                t_race_bug: "Race Condition (Check-Then-Act)",
                t_block_bug: "Event Loop Blocking (Sync call in Async)"
            }
        }

        return {
            "prompt": f"{system_prompt}\n\n{haystack}\n\nQUESTION:\n{user_prompt}\n\nANSWER (JSON):",
            "system_prompt": system_prompt,
            "expected_output": json.dumps(expected),
            "test_name": "v5_backend_concurrency",
            "metadata": {"complexity": "expert", "domain": "backend_async"}
        }

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        # Clean markdown
        clean = re.sub(r'```(?:json)?\s*(.*?)```', r'\1', llm_raw_output, flags=re.DOTALL)
        clean = re.sub(r'<think>.*?</think>', '', clean, flags=re.DOTALL) # Remove CoT if present
        clean = clean.strip()

        parsed = None
        try:
            parsed = json.loads(clean)
        except:
            # Fallback regex to find the JSON object
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

        if not isinstance(findings, list) or len(findings) != 2:
            return {
                "is_correct": False,
                "score": 0,
                "details": {
                    "error": f"Expected exactly 2 bugs, found {len(findings) if isinstance(findings, list) else 0}",
                    "raw_output": llm_output
                }
            }

        got = {str(f.get("trace", "")).strip() for f in findings}
        targets = set(exp["bugs"])
        distractors = set(exp["distractors"])

        correct = len(got.intersection(targets))
        wrong = len(got.intersection(distractors))

        # Strict scoring: Logic must be flawless
        is_correct = (correct == 2) and (wrong == 0)

        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0,
            "details": {
                "got_traces": list(got),
                "expected_bugs": list(targets),
                "missed": list(targets - got),
                "false_positives": list(got.intersection(distractors)),
                "verdicts": [f.get("verdict") for f in findings]
            }
        }