import datetime
import logging
import os
import random
import re
import uuid
from typing import Dict, Any

# Попытка импорта из фреймворка пользователя, иначе заглушка для локального запуска
try:
    from baselogic.tests.abstract_test_generator import AbstractTestGenerator
except ImportError:
    # Заглушка, чтобы код работал автономно при проверке
    class AbstractTestGenerator:
        def __init__(self, test_id: str):
            self.test_id = test_id

        def generate(self) -> Dict[str, Any]: raise NotImplementedError

        def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]: raise NotImplementedError
from dotenv import load_dotenv

# Настройка логирования
log = logging.getLogger(__name__)
load_dotenv()  # Загружает .env файл

class AdvancedReasoningTestGenerator(AbstractTestGenerator):
    """
    Генератор тестов на сложные логические рассуждения (Reasoning).

    Проверяет способность модели:
    1. Multi-hop Reasoning: Связывать разрозненные факты (Fact A -> Fact B -> Answer).
    2. Temporal Resolution: Различать актуальные данные от устаревших по таймстемпам.
    3. Noise Resistance: Игнорировать правдоподобные дистракторы.
    """

    TECH_BUZZWORDS = [
        'асинхронный', 'деплоймент', 'шардирование', 'рефакторинг', 'сериализация',
        'дедлок', 'кэширование', 'балансировка', 'горутина', 'оркестрация',
        'квантование', 'инференс', 'бэкпропагейшн', 'токенизация', 'эмбеддинг'
    ]

    def __init__(self, test_id: str, seed: int = 42):
        super().__init__(test_id)
        self.rng = random.Random(seed)

        # Конфигурация через переменные окружения
        lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "1")
        scenarios_str = os.getenv("CST_SCENARIOS", "multi_hop, temporal")

        self.context_lengths = [int(k.strip()) for k in lengths_str.split(',')]
        self.scenarios = [s.strip() for s in scenarios_str.split(',')]
        self.current_idx = 0

        log.info(
            f"AdvancedReasoningTest initialized: {len(self.context_lengths)} context sizes, {len(self.scenarios)} scenarios")

    # --- Вспомогательные методы генерации (Private) ---

    def _gen_timestamp(self, relative_min: int = 0, relative_max: int = 10000) -> str:
        base = datetime.datetime.now() - datetime.timedelta(minutes=relative_max)
        ts = base + datetime.timedelta(minutes=self.rng.randint(0, relative_max - relative_min))
        return ts.strftime("%Y-%m-%d %H:%M:%S")

    def _gen_narrative_noise(self) -> str:
        """Генерирует правдоподобный технический текст."""
        templates = [
            "Инженер {name} пытался выполнить {action} на сервере {server}, но столкнулся с ошибкой {error}.",
            "После обновления {system} до версии {ver}, метрики {metric} показали {status} рост.",
            "Анализ инцидента {id} выявил, что {reason} привела к каскадному сбою в {module}.",
            "В документации по {topic} сказано, что метод {method} является устаревшим (deprecated)."
        ]
        return templates[self.rng.randint(0, len(templates) - 1)].format(
            name=self.rng.choice(['Алекс', 'Мария', 'Джон', 'Света']),
            action=self.rng.choice(['диплой', 'роллбек', 'комит', 'мердж']),
            server=f"srv-{self.rng.randint(10, 99)}",
            error=self.rng.choice(['Timeout', 'SegFault', 'OOM', '404']),
            system=self.rng.choice(['Kubernetes', 'Postgres', 'Redis']),
            ver=f"{self.rng.randint(1, 5)}.{self.rng.randint(0, 9)}",
            metric=self.rng.choice(['CPU', 'RAM', 'DiskIO']),
            status=self.rng.choice(['значительный', 'незначительный', 'критический']),
            id=self.rng.randint(1000, 9999),
            reason=self.rng.choice(['утечка памяти', 'сетевая задержка', 'битая память']),
            module=self.rng.choice(['Auth', 'Billing', 'Frontend']),
            topic=self.rng.choice(['API', 'SDK', 'CLI']),
            method=self.rng.choice(['getUsers', 'setCookie', 'initAuth'])
        )

    def _gen_log_noise(self) -> str:
        """
        Генерирует реалистичный блок системных логов.
        Включает HTTP-запросы, метрики ресурсов и имитацию стектрейсов ошибок.
        """
        lines = ["system_log"]

        components = ['ApiGateway', 'AuthService', 'DbShard-01', 'K8s-Ingress', 'PaymentWorker']
        levels = ['INFO', 'DEBUG', 'WARN', 'ERROR', 'CRITICAL']
        http_methods = ['GET', 'POST', 'PUT', 'DELETE']
        endpoints = ['/api/v1/users', '/auth/login', '/payment/process', '/health', '/graphql']
        status_codes = [200, 201, 204, 302, 304, 400, 401, 403, 404, 500, 502]

        # Генерируем от 6 до 12 строк логов за один блок
        for _ in range(self.rng.randint(6, 12)):
            ts = self._gen_timestamp()
            comp = self.rng.choice(components)
            lvl = self.rng.choice(levels)
            tid = uuid.uuid4().hex[:16]  # Trace ID для реализма

            # Генерация текста сообщения в зависимости от уровня
            if lvl in ['INFO', 'DEBUG']:
                method = self.rng.choice(http_methods)
                path = self.rng.choice(endpoints)
                # ВОТ ЗДЕСЬ БЫЛА ОШИБКА - добавлен аргумент status_codes
                code = self.rng.choice(status_codes)
                duration = self.rng.randint(5, 800)
                msg = f"[{tid}] Ingress: {method} {path} HTTP/1.1 {code} - {duration}ms"

            elif lvl == 'WARN':
                metric = self.rng.choice(['Memory', 'CPU', 'DiskIO', 'ThreadCount'])
                val = self.rng.randint(85, 98)
                msg = f"[{tid}] Threshold exceeded: {metric} usage at {val}% on node {comp}"

            else:  # ERROR, CRITICAL
                err_type = self.rng.choice(
                    ['ConnectionRefused', 'TimeoutError', 'NullPointerException', 'DeadlockDetected',
                     'SerializationError'])
                msg = f"[{tid}] Transaction failed: {err_type} while processing request"

                # С вероятностью 30% добавляем фейковый Stack Trace (сильный шум для LLM)
                if self.rng.random() > 0.7:
                    line_no = self.rng.randint(10, 200)
                    msg += f"\n\t at {comp}.core.handlers.process(handlers.py:{line_no})"
                    msg += f"\n\t at {comp}.db.session.execute(session.py:{line_no + 15})"

            lines.append(f"[{ts}] [{lvl}] [{comp}] {msg}")

        lines.append("```")
        return "\n".join(lines)

    def _build_haystack(self, tokens_k: int) -> str:
        """Собирает контекст (стог сена) заданного размера."""
        # 1000 токенов ~ 3000-4000 символов
        target_len = tokens_k * 3000
        blocks = []
        curr_len = 0
        generators = [self._gen_narrative_noise, self._gen_narrative_noise, self._gen_log_noise]

        i = 1
        while curr_len < target_len:
            gen = self.rng.choice(generators)
            header = f"\n\n## Part {i}: {self.rng.choice(self.TECH_BUZZWORDS).upper()}\n"
            content = gen()
            block = header + content
            blocks.append(block)
            curr_len += len(block)
            i += 1
        return "".join(blocks)

    def _create_logic_puzzle(self, scenario: str) -> Dict[str, Any]:
        """Создает логическую задачу (иголку)."""

        if scenario == 'multi_hop':
            # Задача: Найти переменную, потом найти её значение
            var_name = f"ENV_VAR_{self.rng.randint(100, 999)}"
            secret_value = f"secret_v{self.rng.randint(10, 99)}"

            part1 = f"ВАЖНО: Для доступа к API используйте значение переменной окружения {var_name}."
            part2 = f"```env\n# Server Config\n{var_name}={secret_value}\nDEBUG=False\n```"

            return {
                'parts': [part1, part2],
                'question': "Какое конкретное значение нужно использовать для доступа к API?",
                'answer': secret_value
            }

        elif scenario == 'temporal':
            # Задача: Найти последнее состояние объекта
            obj_id = f"Transaction-{self.rng.randint(1000, 9999)}"
            ts_old = self._gen_timestamp(relative_min=60, relative_max=120)
            ts_new = self._gen_timestamp(relative_min=1, relative_max=10)

            part1 = f"[{ts_old}] [INFO] {obj_id} status changed to PENDING."
            part2 = f"[{ts_new}] [WARN] {obj_id} failed with status REJECTED."

            return {
                'parts': [part1, part2],
                'question': f"Какой финальный статус у транзакции {obj_id}?",
                'answer': "REJECTED"
            }
        return {}

    def _insert_puzzle(self, haystack: str, puzzle: Dict[str, Any]) -> str:
        """Внедряет части пазла в текст скрытно (без явных маркеров)."""
        blocks = haystack.split('\n\n')
        parts = puzzle['parts']

        # Если контекст слишком мал, просто добавляем в конец
        if len(blocks) < len(parts):
            return haystack + "\n\n" + "\n\n".join(parts)

        # Случайная вставка в разные части текста
        indices = sorted(self.rng.sample(range(len(blocks)), len(parts)))
        for i, idx in enumerate(indices):
            blocks[idx] += f"\n{parts[i]}"

        return "\n\n".join(blocks)

    # --- Обязательные методы API (Override) ---

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует тестовый кейс.
        Returns:
            Dict с ключами 'prompt', 'expected_output', 'metadata'.
        """
        # Выбор параметров для текущей итерации
        k = self.context_lengths[self.current_idx % len(self.context_lengths)]
        scen = self.scenarios[self.current_idx % len(self.scenarios)]
        self.current_idx += 1

        # 1. Создаем контекст
        haystack = self._build_haystack(k)

        # 2. Создаем логическую задачу
        puzzle = self._create_logic_puzzle(scen)

        # 3. Внедряем задачу в контекст
        full_text = self._insert_puzzle(haystack, puzzle)

        prompt = (
            f"Проанализируй представленные ниже данные (логи и документацию).\n"
            f"Используй логическое мышление, чтобы найти верный ответ. Учитывай временные метки и связи между данными.\n\n"
            f"--- НАЧАЛО ДАННЫХ ---\n{full_text}\n--- КОНЕЦ ДАННЫХ ---\n\n"
            f"ВОПРОС: {puzzle['question']}\n"
            f"ОТВЕТ (только значение):"
        )

        return {
            'prompt': prompt,
            'expected_output': puzzle['answer'],
            'metadata': {
                'test_type': 'reasoning',
                'scenario': scen,
                'context_size_k': k
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет корректность ответа модели.

        Возвращаемый словарь содержит ключи:
            - is_correct (bool): True/False
            - score     (float): 0‑1
            - reason    (str) : краткое описание результата
            - details   (dict): вложенные данные для логирования

        Тесты в репортерах ожидают именно эти поля.
        """
        # 1️⃣ Очистка ответа от «think‑tags» и лишних пробелов
        cleaned = self._cleanup_llm_response(llm_output)
        if not cleaned:
            result = {
                "is_correct": False,
                "score": 0.0,
                "reason": "Empty response",
                "details": {"score": 0.0, "reason": "Empty response"}
            }
            return result

        # 2️⃣ Нормализация (удаляем пунктуацию, приводим к нижнему регистру)
        def _clean(text: str) -> str:
            t = text.strip().lower()
            return re.sub(r"[^a-z0-9]", "", t)

        resp_clean = _clean(cleaned)
        exp_clean  = _clean(str(expected_output))

        # 3️⃣ Точное совпадение
        if resp_clean == exp_clean:
            result = {
                "is_correct": True,
                "score": 1.0,
                "reason": "exact match",
                "details": {"score": 1.0, "reason": "exact match"}
            }
            return result

        # 4️⃣ Подстрочная проверка
        if exp_clean in resp_clean:
            score = 1.0 if len(resp_clean) <= len(exp_clean) * 3 else 0.8
            reason = "substring match"
            result = {
                "is_correct": True,
                "score": score,
                "reason": reason,
                "details": {"score": score, "reason": reason}
            }
            return result

        # 5️⃣ Нет совпадения
        result = {
            "is_correct": False,
            "score": 0.0,
            "reason": f"Expected '{expected_output}' not found in response.",
            "details": {"score": 0.0, "reason": f"Expected '{expected_output}' not found"}
        }
        return result


# --- Блок для локальной проверки (если запущен напрямую) ---
if __name__ == "__main__":
    gen = AdvancedReasoningTestGenerator("test_run_1")

    print("=== Test Generation ===")
    case = gen.generate()
    print(f"Scenario: {case['metadata']['scenario']}")
    print(f"Expected: {case['expected_output']}")

    # ВОТ ЭТО ДОБАВЬТЕ, чтобы увидеть весь промпт:
    print("\n=== FULL PROMPT ===")
    print(case['prompt'])
    print("\n=== END OF PROMPT ===")

    print("\n=== Verification Simulation ===")
    res_ok = gen.verify(f"Ответ: {case['expected_output']}", case['expected_output'])
    print(f"Correct check: {res_ok}")

    res_fail = gen.verify("Я не знаю.", case['expected_output'])
    print(f"Fail check: {res_fail}")
