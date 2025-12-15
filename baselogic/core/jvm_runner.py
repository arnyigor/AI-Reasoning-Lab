#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# -------------------------------------------------------------
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# 1️⃣ Загрузка .env (если установлен пакет python‑dotenv)
try:
    from dotenv import load_dotenv, find_dotenv
except ImportError:
    load_dotenv = None

# Глобальная загрузка .env (рядом со скриптом)
if load_dotenv:
    dotenv_path = find_dotenv(".env", raise_error_if_not_found=False)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
        logger.debug(f"Loaded .env from {dotenv_path}")

# -------------------------------------------------------------
class JVMRunnerError(RuntimeError):
    """Исключение, бросаемое при проблемах запуска JVM‑компилятора/вывода."""
    pass

# -------------------------------------------------------------
class JVMRunner:
    def __init__(
            self,
            java_home: Optional[str] = None,
            kotlin_home: Optional[str] = None,
    ) -> None:
        self.env = os.environ.copy()

        if not java_home:
            java_home = self.env.get("JAVA_HOME")

        if java_home:
            jh = Path(java_home).expanduser().resolve()
            bin_dir = jh / "bin"

            # Обновляем переменные для подпроцессов
            self.env["JAVA_HOME"] = str(jh)
            # Добавляем bin в начало PATH, чтобы subprocess видел правильную версию
            self.env["PATH"] = f"{str(bin_dir)}{os.pathsep}{self.env.get('PATH', '')}"

            logger.debug(f"Configured JAVA_HOME: {jh}")
        else:
            logger.warning("JAVA_HOME not set. Relying on system PATH.")

        # ── 4️⃣ Настройка KOTLIN_HOME -----------------------------------
        if kotlin_home is None:
            kotlin_home = self.env.get("KOTLIN_HOME")

        # Флаг для использования shell (нужен для .bat файлов на Windows)
        self.use_shell: bool = False

        # ── 5️⃣ Поиск исполняемых файлов ----------------------------------
        # Ищем kotlinc
        self.kotlinc_path = self._find_executable("kotlinc", kotlin_home)

        # Ищем java (ВАЖНО: передаем java_home явно, чтобы не зависеть только от which)
        self.java_path = self._find_executable("java", java_home)

        # Проверки
        if not self.kotlinc_path:
            raise JVMRunnerError(
                "Не найден kotlinc. Установите Kotlin SDK и укажите KOTLIN_HOME в .env"
            )
        if not self.java_path:
            raise JVMRunnerError(
                "Не найден java. Проверьте JAVA_HOME в .env"
            )

        logger.info(
            f"[+] JVM Environment configured.\n"
            f"    Java:   {self.java_path}\n"
            f"    Kotlin: {self.kotlinc_path}"
        )

    # -------------------------------------------------------------
    def _find_executable(self, name: str, home: Optional[str] = None) -> Path:
        """
        Ищет исполняемый файл. Приоритет:
        1. home/bin/{name}[.exe/.bat] (если home задан)
        2. PATH (через shutil.which)
        """
        candidates: list[Path] = []

        # 1. Если задан home, ищем строго там
        if home:
            base = Path(home).expanduser().resolve()
            bin_dir = base / "bin"

            # На Windows проверяем расширения
            if os.name == 'nt':
                for ext in [".exe", ".bat", ".cmd"]:
                    candidates.append(bin_dir / f"{name}{ext}")
            else:
                candidates.append(bin_dir / name)

        # 2. Проверяем кандидатов из home
        for candidate in candidates:
            if candidate.is_file():
                logger.debug(f"Found {name} in home: {candidate}")
                if candidate.suffix.lower() in (".bat", ".cmd"):
                    self.use_shell = True
                return candidate

        # 3. Если в home пусто, ищем в PATH (используя обновленный PATH из self.env)
        # Примечание: shutil.which по умолчанию смотрит os.environ, если path не передан.
        # Передаем явно self.env['PATH'], так как мы могли его изменить в __init__
        path_candidate = shutil.which(name, path=self.env.get("PATH"))

        if path_candidate:
            cand_path = Path(path_candidate)
            logger.debug(f"Found {name} in PATH: {cand_path}")
            # Проверка расширения для флага shell
            if cand_path.suffix.lower() in (".bat", ".cmd"):
                self.use_shell = True
            return cand_path

        msg = f"Executable '{name}' not found. (Checked home={home})"
        # Возвращаем None или вызываем ошибку, здесь оставим None для обработки выше,
        # но так как метод аннотирован как -> Path, лучше сразу вернуть ошибку или путь.
        # В текущей логике __init__ ожидает Path или падает позже?
        # Сейчас вернем None, а __init__ проверит. Но лучше сделаем raise.
        # Для совместимости с текущим кодом вернем None (но type hint ругается),
        # поэтому перепишем на явный поиск.

        # Если ничего не нашли - это ошибка уровня runner'а
        return None # type: ignore

    # -------------------------------------------------------------
    def run_kotlin_code(self, kotlin_source: str,
                        args: Optional[list[str]] = None) -> str:
        """
        Компилирует и запускает Kotlin‑код.
        """
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            src_file = tmp_dir / "Main.kt"
            jar_file = tmp_dir / "output.jar"

            try:
                src_file.write_text(kotlin_source, encoding="utf-8")
            except OSError as exc:
                return f"Error writing source file: {exc}"

            # ── Компиляция ───────────────────────────────────────────────
            compile_cmd = [
                str(self.kotlinc_path),
                "-include-runtime",
                "-d", str(jar_file),
                str(src_file),
            ]

            try:
                result_compile = subprocess.run(
                    compile_cmd,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=self.use_shell,
                )
                if result_compile.returncode != 0:
                    return f"Compilation Error:\n{result_compile.stderr.strip()}"

            except subprocess.TimeoutExpired:
                return "Compilation Timeout (30s)."
            except Exception as exc:
                return f"Compilation Failed: {exc}"

            # ── Запуск ───────────────────────────────────────────────────
            run_cmd = [str(self.java_path), "-jar", str(jar_file)] + (args or [])

            try:
                result_run = subprocess.run(
                    run_cmd,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=self.use_shell, # Важно для Windows если java вызвана через батник (редко, но бывает)
                )
                if result_run.returncode != 0:
                    return f"Runtime Error:\n{result_run.stderr.strip()}"

                return result_run.stdout.rstrip("\n")

            except subprocess.TimeoutExpired:
                return "Execution Timeout (10s)."
            except Exception as exc:
                return f"Execution Failed: {exc}"

# -------------------------------------------------------------
if __name__ == "__main__":
    # Включаем подробный лог для отладки
    logging.getLogger().setLevel(logging.DEBUG)

    # Исправленный Kotlin код: добавлено определение класса User
    kotlin_code = """
        data class User(val name: String)

        fun main() {
            val version = System.getProperty("java.version")
            println("Hello from Python! Running on JVM version: $version")

            val x = 10
            val y = 20
            val user = User("Mark")
            println("Result of calculation: ${x + y} with name: ${user.name}")
        }
    """

    print("--- Starting JVM Runner ---")
    try:
        runner = JVMRunner()
        output = runner.run_kotlin_code(kotlin_source=kotlin_code)
    except JVMRunnerError as exc:
        logger.error(f"Initialization Error: {exc}")
        output = str(exc)
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        output = str(e)

    print("\n--- Execution Output ---")
    print(output)
