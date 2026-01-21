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
        Компилирует и запускает Kotlin-код.

        Автоматическая обработка:
        1. Если в коде нет 'fun main', метод сам создает функцию main(args: Array<String>).
        2. Импорты (строки с 'import'/'package') выносятся в начало файла.
        3. Остальной код помещается внутрь main, поэтому переменная 'args' доступна сразу.
        """

        # ── 1️⃣ Smart Wrapping (Авто-обертка) ──────────────────────────
        # Проверяем, определил ли пользователь main сам. Если нет — генерируем обертку.
        if "fun main" not in kotlin_source:
            lines = kotlin_source.splitlines()
            header_lines = []  # imports, package
            body_lines = []    # логика

            for line in lines:
                s = line.strip()
                # Выносим импорты и пакеты наверх
                if s.startswith("package ") or s.startswith("import "):
                    header_lines.append(line)
                else:
                    body_lines.append(line)

            # Собираем новый исходник
            # args доступен внутри благодаря сигнатуре main
            wrapped_source = (
                    "\n".join(header_lines) + "\n\n"
                                              "fun main(args: Array<String>) {\n" +
                    "\n".join(body_lines) +
                    "\n}"
            )

            logger.debug("Auto-wrapped Kotlin source into 'fun main(args)'")
            final_source = wrapped_source
        else:
            final_source = kotlin_source

        # ── 2️⃣ Стандартный процесс компиляции и запуска ───────────────
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            src_file = tmp_dir / "Main.kt"
            jar_file = tmp_dir / "output.jar"

            try:
                src_file.write_text(final_source, encoding="utf-8")
            except OSError as exc:
                return f"Error writing source file: {exc}"

            # Компиляция
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

            # Запуск (передаем args в subprocess)
            run_cmd = [str(self.java_path), "-jar", str(jar_file)] + (args or [])

            try:
                result_run = subprocess.run(
                    run_cmd,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=self.use_shell,
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
    runner = JVMRunner()

    # ПРИМЕР: Просто логика + импорты. Без fun main!
    # Мы обращаемся к 'args' напрямую, как будто это скрипт.
    script_body = """
    import java.io.File
    
    val name = if (args.isNotEmpty()) args[0] else "Unknown"
    println("Hello, $name!")
    
    // Можно даже определять локальные классы/функции
    data class Status(val code: Int)
    println(Status(200))
    """

    print("--- Auto-wrapped Execution ---")
    # Передаем аргумент "Developer" в Python, он попадает в args[0] в Kotlin
    output = runner.run_kotlin_code(script_body, args=["Developer"])
    print(output)
