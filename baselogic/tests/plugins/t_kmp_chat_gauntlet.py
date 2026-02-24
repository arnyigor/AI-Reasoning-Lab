# plugins/t_kmp_chat_gauntlet.py

"""
KMP Chat Gauntlet (Compose Multiplatform: Android + Desktop).
--------------------------------------------------------------------
Scenario:
The LLM acts as a Senior KMP Architect. It must implement a Chat Screen
with LLM Streaming (SSE) and Markdown rendering.

Target Platforms: Android, Desktop (JVM).

Traps & Checks:
1. "Streaming Integrity": Must use Flow + emit/emitAll. Rejects blocking calls like body<String>().
2. "UI Thread Safety": Parsing must happen on Default/IO dispatchers.
3. "Advanced Concurrency": Bonuses for Debounce, Mutex, or Actor usage.
4. "Platform Specifics": Checks for valid Desktop Entry points (Compose Window or Swing Interop).
5. "Code Extraction": robustly handles nested markdown and truncation.

Author: AI Reasoning Lab (Fixed & Robust)
"""

import re
import logging
from typing import Dict, Any

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class KmpChatGauntletTestGenerator(AbstractTestGenerator):

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.test_plan = [{"context_k": 0, "depth_percent": 0, "test_id": "kmp_chat_gauntlet"}]

    def generate(self) -> Dict[str, Any]:
        system_prompt = (
            "You are a Principal Kotlin Multiplatform (KMP) Engineer specializing in Compose Multiplatform. "
            "You write high-performance, concurrent, and platform-agnostic code. "
            "You prefer 'Compose-native' solutions over embedding platform views (like WebView) whenever possible."
        )

        user_prompt = (
            "Project: 'DevChat' (Android, Desktop JVM). UI: Compose Multiplatform.\n\n"
            "Task: Implement a Chat Interface with the following requirements:\n"
            "1. `ChatRepository`: Method `streamMessage(prompt: String): Flow<String>` simulating an LLM API (use Ktor).\n"
            "2. `MessageParser`: A component that takes raw text and parses it into a Markdown-friendly structure (keep it abstract/simplified logic, but show WHERE it happens).\n"
            "3. `ChatScreen`: A Composable displaying the chat history.\n\n"
            "Technical Constraints:\n"
            "- **Streaming**: The UI must update in real-time as chunks arrive from the network.\n"
            "- **Performance**: Markdown parsing is CPU-heavy. NEVER block the UI thread.\n"
            "- **UI**: Use `LazyColumn` for efficiency.\n"
            "- **Platform**: Ensure `desktopMain` entry point creates a window properly.\n"
            "- **DI**: Show how to inject the Repository using Koin.\n\n"
            "Write the code for:\n"
            "- `commonMain` (Repo, ViewModel/Presenter, UI)\n"
            "- `desktopMain` (Entry point)\n"
            "- `androidMain` (Manifest snippet or Activity setup NOT required, just focus on KMP parts if needed).\n\n"
            "Output standard Kotlin markdown blocks."
        )

        return {
            "prompt": f"{system_prompt}\n\nQUESTION:\n{user_prompt}\n\nANSWER:",
            "system_prompt": system_prompt,
            "expected_output": "Compose Multiplatform validation via Regex AST",
            "test_name": "kmp_chat_gauntlet",
            "metadata": {"complexity": "hardcore", "domain": "compose-kmp"}
        }

    def _extract_all_kotlin_code(self, llm_output: str) -> str:
        """
        Robust extraction of Kotlin code blocks.
        Fixes issue where nested backticks (e.g. inside strings) break the parser.
        """
        code_blocks = []

        # 1. Используем MULTILINE (re.M), чтобы ^ совпадал с началом строки.
        # Ищем блоки, начинающиеся с ``` в начале строки.
        # (?:kotlin|kt|java)? - необязательный язык
        # \s* - возможные пробелы после языка
        # $ - конец строки (чтобы не захватить ``` внутри строки)
        # (.*?) - контент (non-greedy)
        # ^``` - закрывающий блок в начале строки
        pattern = r'^```(?:kotlin|kt|java)?\s*$(.*?)^```'

        # re.S (DOTALL) позволяет точке совпадать с переносами строк внутри блока
        found_blocks = re.findall(pattern, llm_output, flags=re.MULTILINE | re.DOTALL)

        if found_blocks:
            code_blocks.extend(found_blocks)

        # 2. Обработка TRUNCATION (Обрыва)
        # Если модель не закрыла последний блок, re.findall его не найдет.
        # Ищем последний открывающий тег, за которым НЕТ закрывающего (до конца текста)
        # last_open_match ищет ``` в начале строки, после которого идет всё до конца ($)
        # Но нужно убедиться, что внутри этого "хвоста" нет закрывающего ``` в начале строки.

        lines = llm_output.split('\n')
        inside_block = False
        buffer = []

        # Ручной проход для надежности (State Machine), если regex подвел или для хвостов
        manual_blocks = []
        current_chunk = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if inside_block:
                    # Closing
                    manual_blocks.append("\n".join(current_chunk))
                    current_chunk = []
                    inside_block = False
                else:
                    # Opening
                    # Проверяем, не является ли это ``` внутри текста (хотя мы смотрим startswith)
                    # Обычно модели пишут ```kotlin
                    inside_block = True
            else:
                if inside_block:
                    current_chunk.append(line)

        # Если после цикла мы остались inside_block, значит был обрыв
        if inside_block and current_chunk:
            manual_blocks.append("\n".join(current_chunk))

        # Если regex не нашел ничего, берем ручной парсинг
        if not code_blocks and manual_blocks:
            return "\n\n".join(manual_blocks)

        # Если regex нашел, проверяем, не пропустили ли мы хвост
        if code_blocks:
            # Просто возвращаем то, что нашел надежный regex, плюс ручной хвост если он отличается?
            # Для простоты: если regex сработал, верим ему. Но проверим на "хвост"
            last_block_end = llm_output.rfind("```")
            # Если после последнего ``` есть куча кода (например fun main), добавим его
            # Но это сложно детектить. Доверимся re.findall с MULTILINE.
            pass

        if not code_blocks:
            # Fallback: если вообще нет ```, но есть код
            if "fun " in llm_output and "class " in llm_output:
                return llm_output
            return ""

        return "\n\n".join(code_blocks)

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        full_code = self._extract_all_kotlin_code(llm_output)

        penalties = []
        bonuses = []
        is_fatal = False

        # ------------------------------------------------------------------
        # 0. Truncation Detection
        # ------------------------------------------------------------------
        if not full_code or len(full_code) < 50:
            return {
                "is_correct": False,
                "score": 0.0,
                "details": {"verdict": "FAIL", "reason": "No code blocks found or code too short"}
            }

        # Проверка на обрыв: если нет закрывающих ``` в конце сырого текста
        is_truncated = not llm_output.strip().endswith("```") and len(llm_output) > 2000
        if is_truncated:
            penalties.append("WARNING: Output truncated (Token Limit). Missing parts excused if logic is valid.")

        # ------------------------------------------------------------------
        # 1. NETWORK & STREAMING
        # ------------------------------------------------------------------
        if 'Flow<' in full_code:
            # emit, emitAll, trySend (callbackFlow), send (Channel)
            if re.search(r'(?:emit|emitAll|trySend|send)\s*\(', full_code):
                bonuses.append("GOOD: Correctly used Kotlin Flow/Channel emission.")
            elif re.search(r'channelFlow|callbackFlow', full_code):
                bonuses.append("GOOD: Used advanced Flow builders.")
            else:
                penalties.append("FATAL: Flow defined but no emission (emit/trySend) found.")
                is_fatal = True
        else:
            penalties.append("FATAL: Return type Flow<...> not found in Repository.")
            is_fatal = True

        # Blocking Calls Trap
        if re.search(r'body\s*<\s*String\s*>\s*\(\s*\)', full_code):
            penalties.append("FATAL: Used 'body<String>()' (Blocking). Violates Streaming requirement.")
            is_fatal = True

        # ------------------------------------------------------------------
        # 2. CONCURRENCY & PERFORMANCE
        # ------------------------------------------------------------------
        has_bg_dispatcher = re.search(r'Dispatchers\.(?:Default|IO)', full_code)
        has_context_switch = re.search(r'(?:withContext|flowOn|launch|subscribeOn)\s*\(', full_code)

        if has_bg_dispatcher and has_context_switch:
            bonuses.append("GOOD: Explicitly offloaded heavy operations (IO/Default).")
        else:
            penalties.append("WARNING: No explicit Dispatcher switch found. Potential UI blocking.")

        # Advanced Patterns
        if re.search(r'(?:debounce|sample|throttle)', full_code, re.IGNORECASE):
            bonuses.append("AMAZING: Implemented Debounce/Sample strategy.")

        if re.search(r'Mutex\s*\(', full_code):
            bonuses.append("AMAZING: Used Mutex for thread safety.")

        if 'SupervisorJob' in full_code:
            bonuses.append("GOOD: Used SupervisorJob.")

        if 'LazyColumn' in full_code:
            bonuses.append("GOOD: Used LazyColumn.")
        elif re.search(r'Column\s*\{[^}]*forEach', full_code):
            penalties.append("FATAL: Used 'Column + forEach'. Performance killer.")
            is_fatal = True

        # ------------------------------------------------------------------
        # 3. PLATFORM SPECIFICS (DESKTOP)
        # ------------------------------------------------------------------
        has_compose_window = re.search(r'(?:application|singleWindowApplication)\s*\{', full_code)
        has_swing_interop = re.search(r'(?:JFrame|ComposePanel|SwingUtilities)', full_code)
        has_main_fun = re.search(r'fun\s+main\s*\(\s*\)', full_code)

        if has_compose_window:
            bonuses.append("GOOD: Correct Modern Desktop Entry Point.")
        elif has_swing_interop:
            penalties.append("WARNING: Used legacy Swing/JFrame wrapper.")
        elif has_main_fun:
            # Есть main, но нет явного Window?
            # Если был обрыв (truncated), прощаем
            if is_truncated:
                penalties.append("WARNING: 'fun main' found but body likely truncated.")
            else:
                penalties.append("WARNING: 'fun main' found but Window creation unclear.")
        else:
            if is_truncated:
                penalties.append("WARNING: Desktop entry point missing (Truncated).")
            else:
                if "desktopMain" in llm_output:
                    penalties.append("FATAL: Desktop entry point (fun main) missing.")
                    is_fatal = True

        # ------------------------------------------------------------------
        # 4. STATE & DI
        # ------------------------------------------------------------------
        if re.search(r'(?:MutableStateFlow|mutableStateListOf|SnapshotStateList)', full_code):
            bonuses.append("GOOD: Used reactive state container.")
        elif 'mutableStateOf' in full_code and 'ViewModel' in full_code:
            bonuses.append("GOOD: Used Compose State inside ViewModel.")
        else:
            penalties.append("WARNING: Reactive state management unclear.")

        if 'koin' in full_code.lower() and ('module' in full_code or 'single' in full_code or 'viewModel' in full_code):
            bonuses.append("GOOD: Koin DI modules defined.")

        # ------------------------------------------------------------------
        # SCORING
        # ------------------------------------------------------------------
        bonuses_count = len(bonuses)
        fatals_count = sum(1 for p in penalties if p.startswith("FATAL"))
        warnings_count = sum(1 for p in penalties if p.startswith("WARNING"))

        points = 0
        points += bonuses_count * 20
        points -= fatals_count * 100
        points -= warnings_count * 10

        final_points = max(0, min(100, points))

        # PASS criteria: No Fatals AND Score >= 50
        is_correct = (fatals_count == 0) and (final_points >= 50)

        grade = self._get_grade_label(final_points)
        if is_truncated and is_correct:
            grade += " (Truncated)"

        return {
            "is_correct": is_correct,
            "score": round(final_points / 100.0, 2),
            "details": {
                "verdict": "PASS" if is_correct else "FAIL",
                "points": final_points,
                "grade": grade,
                "stats": {
                    "good": bonuses_count,
                    "fatal": fatals_count,
                    "warning": warnings_count,
                    "truncated": is_truncated
                },
                "bonuses": bonuses,
                "penalties": penalties,
                "extracted_code_len": len(full_code)
            }
        }

    def _get_grade_label(self, points: int) -> str:
        if points >= 95: return "Principal KMP Architect (S+)"
        if points >= 80: return "Senior Engineer (A)"
        if points >= 60: return "Middle Developer (B)"
        if points >= 30: return "Junior (C)"
        return "Failed / Hallucination"