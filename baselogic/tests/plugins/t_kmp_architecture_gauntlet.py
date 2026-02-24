# plugins/t_kmp_architecture_gauntlet.py

"""
KMP Architecture Gauntlet (Hardcore Code Generation Test).
--------------------------------------------------------------------
Scenario:
The LLM acts as a Principal KMP Architect. It must generate commonMain,
androidMain, and iosMain code for SecureStorage and Biometry.

Traps (Automated Regex Checks):
1. "Expect/Actual Inheritance": Fails if LLM uses `expect class` and tries to inherit from it with `:`. (Syntax Error in KMP)
2. "Context Crash": Fails if `BiometricPrompt` is instantiated with a raw `Context` instead of `FragmentActivity`.
3. "iOS Main Thread Freeze": Fails if iOS implementation uses `Thread.sleep`.
4. "Uncancellable Coroutine": Fails if iOS FaceID doesn't handle `invokeOnCancellation`.
5. "JVM Hallucinations": Fails if Retrofit, Room (legacy), or Exposed are imported.

Author: AI Reasoning Lab
"""

import re
import json
import logging
from typing import Dict, Any, List

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class KmpArchitectureGauntletTestGenerator(AbstractTestGenerator):

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.test_plan = [{"context_k": 0, "depth_percent": 0, "test_id": "kmp_architect_gauntlet"}]

    def generate(self) -> Dict[str, Any]:
        system_prompt = (
            "You are a Principal Kotlin Multiplatform (KMP) Architect at a top-tier fintech company. "
            "You write mathematically proven, memory-safe, and idiomatic KMP code. "
            "You perfectly understand the Kotlin compiler's rules for expect/actual and c-interop."
        )

        user_prompt = (
            "Project: 'FinTrack' (Android, iOS). UI is Compose Multiplatform.\n\n"
            "Task: Write the core platform-specific integrations for:\n"
            "1. `SecureStorage` (Save/Get encrypted strings).\n"
            "2. `BiometryManager` (Authenticate user via FaceID/BiometricPrompt).\n"
            "3. The `AppModule` using Koin DI to provide these instances to `commonMain` ViewModels.\n\n"
            "Requirements:\n"
            "- Provide code for `commonMain`, `androidMain`, and `iosMain`.\n"
            "- Integrate Koin safely.\n"
            "- Ensure coroutines are cancellable and thread-safe (especially on iOS).\n"
            "- Android's `BiometricPrompt` must not crash due to invalid Context casting.\n\n"
            "Output your code in standard Markdown blocks (```kotlin). Add brief comments explaining your architectural choices."
        )

        return {
            "prompt": f"{system_prompt}\n\nQUESTION:\n{user_prompt}\n\nANSWER:",
            "system_prompt": system_prompt,
            "expected_output": "Architectural constraints validation via Regex AST",
            "test_name": "kmp_architect_gauntlet",
            "metadata": {"complexity": "hardcore", "domain": "kmp"}
        }

    def _extract_all_kotlin_code(self, llm_output: str) -> str:
        """Извлекает весь Kotlin код из Markdown блоков для сплошного анализа."""
        code_blocks = re.findall(r'```(?:kotlin|kt)\s*(.*?)```', llm_output, flags=re.DOTALL | re.IGNORECASE)
        if not code_blocks:
            # Fallback, если модель забыла теги
            return llm_output
        return "\n\n".join(code_blocks)

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        full_code = self._extract_all_kotlin_code(llm_output)

        penalties = []
        bonuses = []
        is_fatal = False

        # ------------------------------------------------------------------
        # TRAP 1: Expect/Actual Syntax vs Dependency Inversion
        # ------------------------------------------------------------------
        if re.search(r'expect\s+class\s+\w+', full_code):
            if re.search(r'class\s+\w+\s*:\s*(?:SecureStorage|BiometryManager)', full_code):
                penalties.append("FATAL: Syntax error. Inheriting from an 'expect class' as if it were an interface.")
                is_fatal = True
            else:
                penalties.append("WARNING: Used 'expect class' for dependencies instead of standard 'interface' (DIP violation).")

        if re.search(r'interface\s+(?:SecureStorage|BiometryManager)', full_code):
            bonuses.append("GOOD: Used interfaces for abstractions (Clean Architecture DIP).")

        # ------------------------------------------------------------------
        # TRAP 2: Android BiometricPrompt Context Cast Crash
        # Исправлено: Захватываем любое выражение до первой запятой
        # ------------------------------------------------------------------
        biometric_prompt_match = re.search(r'BiometricPrompt\s*\(\s*([^,]+)\s*,', full_code)
        if biometric_prompt_match:
            ctx_var = biometric_prompt_match.group(1).strip()
            # Проверяем, упоминается ли FragmentActivity вообще в коде
            if not re.search(r'FragmentActivity', full_code) and not re.search(r'as\s+FragmentActivity', full_code):
                penalties.append(f"FATAL: Android BiometricPrompt instantiated with raw '{ctx_var}'. Missing FragmentActivity. Will crash with IllegalArgumentException.")
                is_fatal = True
            else:
                bonuses.append("GOOD: Correctly identified FragmentActivity requirement for BiometricPrompt.")
        else:
            penalties.append("FATAL: BiometricPrompt implementation not found or syntactically invalid.")
            is_fatal = True

        # ------------------------------------------------------------------
        # TRAP 3 & 4: iOS Coroutines and Thread Safety
        # ------------------------------------------------------------------
        if re.search(r'Thread\.sleep', full_code):
            penalties.append("FATAL: Used Thread.sleep on iOS. Will trigger Watchdog crash (0x8badf00d).")
            is_fatal = True

        if re.search(r'suspendCoroutine\s*\{', full_code) and not re.search(r'suspendCancellableCoroutine', full_code):
            penalties.append("WARNING: Used non-cancellable coroutine for iOS biometry. Can leak if ViewModel is cleared.")

        if re.search(r'suspendCancellableCoroutine', full_code):
            bonuses.append("GOOD: Used suspendCancellableCoroutine for Native interop.")
            if not re.search(r'invokeOnCancellation', full_code):
                penalties.append("FATAL: Used suspendCancellableCoroutine but forgot invokeOnCancellation to invalidate LAContext.")
                is_fatal = True
            else:
                bonuses.append("GOOD: Properly handled iOS FaceID cancellation via invokeOnCancellation.")

        # ------------------------------------------------------------------
        # TRAP 5: JVM Hallucinations in KMP
        # ------------------------------------------------------------------
        forbidden_imports = re.findall(r'import\s+(retrofit2\.|org\.jetbrains\.exposed\.|androidx\.room\.(?!.*multiplatform))', full_code)
        if forbidden_imports:
            penalties.append(f"FATAL: Hallucinated JVM-only libraries in KMP: {set(forbidden_imports)}")
            is_fatal = True

        # ------------------------------------------------------------------
        # TRAP 6: Koin Context Injection
        # ------------------------------------------------------------------
        # Ищем случаи, когда модель делает `single { AndroidSecureStorage() }`,
        # но класс `AndroidSecureStorage` объявлен как `class AndroidSecureStorage(context: Context)`.
        # Захватываем имя класса в Koin модуле:
        koin_instantiations = re.findall(r'single\s*<\s*\w+\s*>\s*\{\s*([A-Z]\w+)\(\)\s*\}|single\s*\{\s*([A-Z]\w+)\(\)\s*\}', full_code)

        for match in koin_instantiations:
            class_name = match[0] or match[1] # Берем имя класса, которое инстанцируется с ()
            if class_name:
                # Проверяем, требует ли именно этот класс Context в своем конструкторе
                class_def_pattern = rf'class\s+{class_name}\s*\([^)]*Context[^)]*\)'
                if re.search(class_def_pattern, full_code):
                    penalties.append(f"FATAL: Koin module directly instantiates '{class_name}()' without passing required Context parameter.")
                    is_fatal = True

        # ------------------------------------------------------------------
        # TRAP 7: Swift/C Syntax Hallucinations in Kotlin (НОВАЯ ЛОВУШКА)
        # ------------------------------------------------------------------
        swift_hallucinations = re.findall(r'(&error|let\s+[a-zA-Z_]+\s*=|->\s*Void)', full_code)
        if swift_hallucinations:
            penalties.append(f"FATAL: Hallucinated Swift/C syntax inside Kotlin iOS file: {set(swift_hallucinations)}")
            is_fatal = True

        # ------------------------------------------------------------------
        # SCORING LOGIC
        # ------------------------------------------------------------------
        is_correct = not is_fatal and len(penalties) <= 1

        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0,
            "details": {
                "verdict": "PASS" if is_correct else "FAIL",
                "is_fatal": is_fatal,
                "bonuses": bonuses,
                "penalties": penalties,
                "extracted_code_length": len(full_code)
            }
        }