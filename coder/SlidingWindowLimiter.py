#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Production‑grade асинхронный Rate Limiter и Retry decorator.
Только стандартная библиотека (Python 3.10+).
"""

from __future__ import annotations

import asyncio
import collections
import functools
import random
import time
from typing import Any, Awaitable, Callable, Deque

# --------------------------------------------------------------------------- #
#                            SlidingWindowLimiter
# --------------------------------------------------------------------------- #

class SlidingWindowLimiter:
    """
    Асинхронный лимитер «скользящего окна».

    Параметры
    ---------
    capacity : int
        Максимальное число запросов, разрешённых за один период.
    period : float
        Длина периода в секундах.  Запросы старше `period` секунд считаются
        неактивными и удаляются из окна.

    Поведение
    ---------
    * Используется как ``async with limiter:``.
    * Если лимит исчерпан, контекстный менеджер делает паузу до момента,
      когда в окне появится свободное место.
    * Работает корректно при конкурентных вызовах (с помощью asyncio.Lock).

    Ограничения
    ------------
    * `capacity` и `period` должны быть положительными целыми/числами с плавающей точкой.
    """

    def __init__(self, *, capacity: int, period: float) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if period <= 0.0:
            raise ValueError("period must be a positive number")

        self.capacity: int = capacity
        self.period: float = period

        # Храним метки времени в порядке возрастания (дек из collections)
        self._timestamps: Deque[float] = collections.deque()

        # Lock нужен, чтобы атомарно обрабатывать состояние лимитера.
        self._lock: asyncio.Lock = asyncio.Lock()

    async def __aenter__(self) -> "SlidingWindowLimiter":
        """
        При входе в контекст проверяем текущее состояние окна и,
        при необходимости, делаем паузу до освобождения места.
        Возвращает сам объект лимитера.
        """
        while True:
            # 1️⃣ Захватываем lock, чтобы безопасно изменить очередь
            async with self._lock:
                now = time.monotonic()

                # Удаляем устаревшие метки (старше `period`)
                while self._timestamps and self._timestamps[0] <= now - self.period:
                    self._timestamps.popleft()

                if len(self._timestamps) < self.capacity:
                    # Есть свободное место – записываем текущую метку
                    self._timestamps.append(now)
                    return self

                # 2️⃣ Нет места, запоминаем время старейшего запроса
                oldest_timestamp = self._timestamps[0]

            # 3️⃣ Считаем сколько нужно ждать до освобождения окна.
            # После выхода из lock другие задачи могут добавить свои метки,
            # но мы всё равно будем делать корректную паузу и затем пробуем снова.
            wait_time = max(0.0, (oldest_timestamp + self.period) - time.monotonic())
            await asyncio.sleep(wait_time)

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        При выходе из контекста ничего не делаем – метка времени уже
        была сохранена при входе. Метод нужен только для поддержки протокола.
        """
        # No-op: запись timestamp уже выполнена в __aenter__
        pass

# --------------------------------------------------------------------------- #
#                          with_retry_and_limit decorator
# --------------------------------------------------------------------------- #

def with_retry_and_limit(
        limiter: SlidingWindowLimiter,
        *,
        retries: int = 3,
        backoff_base: float = 0.5,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Декоратор, который оборачивает асинхронную функцию в лимитер и
    при возникновении исключения (кроме KeyboardInterrupt) выполняет
    повторные попытки с экспоненциальной задержкой.

    Параметры
    ---------
    limiter : SlidingWindowLimiter
        Экземпляр, через который будет проходить каждый вызов.
    retries : int
        Максимальное число дополнительных попыток (не считая первой).
    backoff_base : float
        Базовая величина для экспоненциального back‑off.
    """
    if retries < 0:
        raise ValueError("retries must be non‑negative")

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while True:
                try:
                    async with limiter:
                        return await fn(*args, **kwargs)
                except KeyboardInterrupt:
                    # Не надо перехватывать сигнал прерывания.
                    raise
                except Exception as exc:          # pylint: disable=broad-except
                    if attempt >= retries:
                        raise  # Проброс последнего исключения

                    attempt += 1
                    delay = backoff_base * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        return wrapper

    return decorator

# --------------------------------------------------------------------------- #
#                               Демонстрационный пример
# --------------------------------------------------------------------------- #

async def mock_request(id: int) -> str:
    """
    Имитация сетевого запроса. С 50 % вероятностью бросает ошибку.
    """
    await asyncio.sleep(0.1)                       # Небольшая задержка сети
    if random.random() < 0.5:
        raise RuntimeError(f"Network error for id {id}")
    return f"Success: id={id}"

# Конфигурация лимитера (3 запроса в секунду)
limiter = SlidingWindowLimiter(capacity=3, period=1.0)

@with_retry_and_limit(limiter, retries=2)           # 1 + 2 попытки
async def limited_request(id: int) -> str:
    return await mock_request(id)

async def main() -> None:
    ids = range(10)
    tasks = [limited_request(i) for i in ids]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Выводим результаты
    for idx, result in zip(ids, results):
        if isinstance(result, Exception):
            print(f"[{idx}] FAILED: {result}")
        else:
            print(f"[{idx}] OK   : {result}")

if __name__ == "__main__":
    asyncio.run(main())
