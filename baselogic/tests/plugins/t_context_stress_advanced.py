# plugins/t_context_stress_advanced.py

import os
import random
import re
import uuid
import datetime
from typing import Dict, Any, Tuple, List, Set

from dotenv import load_dotenv
import logging
import pymorphy2

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

# --- Инициализация ---
load_dotenv()
log = logging.getLogger(__name__)
morph = pymorphy2.MorphAnalyzer()

def normalize_word(word: str) -> str:
    parsed = morph.parse(word)[0]
    return parsed.normal_form

class AdvancedContextStressTestGenerator(AbstractTestGenerator):
    """
    Продвинутый генератор стресс-тестов (Needle in a Haystack).

    Отличия от базовой версии:
    1. Генерирует мультиформатный текст (нарратив, логи, email, json, таблицы).
    2. Использует сложные синтаксические конструкции.
    3. Добавляет высокий уровень энтропии (UUID, хеши, таймстемпы).
    """

    # --- Словари данных для генерации ---

    TECH_BUZZWORDS = [
        'асинхронный', 'деплоймент', 'кластеризация', 'рефакторинг', 'инкапсуляция',
        'полиморфизм', 'кэширование', 'балансировка', 'виртуализация', 'оркестрация',
        'квантование', 'инференс', 'промпт-инжиниринг', 'файн-тюнинг', 'дистилляция'
    ]

    CORPORATE_ROLES = [
        'Lead DevOps', 'Senior Backend Dev', 'CTO', 'Product Owner', 'QA Lead',
        'Data Scientist', 'Security Officer', 'Compliance Manager', 'HR Director'
    ]

    # Шаблоны сложных предложений
    COMPLEX_TEMPLATES = [
        "Несмотря на то, что {entity} пытался {action_inf}, результаты показали, что {obj} {state}.",
        "В то время как {entity} {action_past} {location}, система автоматически {action_past} {obj}.",
        "Учитывая, что {obj} {state}, {entity} принял решение {action_inf} немедленно.",
        "Анализ показал: если {entity} {action_fut}, то {obj} неизбежно будет {state}.",
        "Впрочем, ни {entity}, ни его коллеги не могли предвидеть, что {obj} окажется {location}."
    ]

    def __init__(self, test_id: str):
        super().__init__(test_id)

        lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "8,16,32")
        depths_str = os.getenv("CST_NEEDLE_DEPTH_PERCENTAGES", "10,50,90")

        self.context_lengths_k = [int(k.strip()) for k in lengths_str.split(',')]
        self.needle_depths = [int(d.strip()) for d in depths_str.split(',')]

        self.test_plan = self._create_test_plan()
        self.current_test_index = 0

        log.info(f"Advanced Context Stress: План создан, {len(self.test_plan)} кейсов.")

    def _create_test_plan(self):
        MAX_SAFE_TOKENS = 1024 * 1024 * 1024 # Лимит безопасности
        plan = []
        for context_k in self.context_lengths_k:
            if context_k * 1024 > MAX_SAFE_TOKENS: continue
            for depth_percent in self.needle_depths:
                plan.append({
                    'context_k': context_k,
                    'depth_percent': depth_percent,
                    'test_id': f"adv_stress_{context_k}k_{depth_percent}pct"
                })
        return plan

    # --- Генераторы контента разных форматов ---

    def _gen_narrative_block(self) -> str:
        """Генерирует связный художественный или публицистический текст."""
        entities = ['инженер', 'аналитик', 'система', 'алгоритм', 'сервер', 'протокол']
        actions_inf = ['оптимизировать', 'уничтожить', 'перезагрузить', 'исследовать', 'заблокировать']
        actions_past = ['обнаружил', 'скрыл', 'развернул', 'проигнорировал', 'скомпилировал']
        actions_fut = ['запустит', 'обновит', 'удалил', 'проверит']
        objects = ['базу данных', 'микросервис', 'отчет', 'ключ шифрования', 'патч безопасности']
        locations = ['в облаке', 'на локальном кластере', 'в песочнице', 'в продакшене']
        states = ['нестабилен', 'скомпрометирован', 'оптимизирован', 'недоступен', 'поврежден']

        sentences = []
        for _ in range(random.randint(3, 6)):
            tmpl = random.choice(self.COMPLEX_TEMPLATES)
            s = tmpl.format(
                entity=random.choice(entities),
                action_inf=random.choice(actions_inf),
                action_past=random.choice(actions_past),
                action_fut=random.choice(actions_fut),
                obj=random.choice(objects),
                location=random.choice(locations),
                state=random.choice(states)
            )
            sentences.append(s)

        return " ".join(sentences)

    def _gen_log_block(self) -> str:
        """Генерирует имитацию системных логов."""
        lines = []
        base_time = datetime.datetime.now()
        levels = ['INFO', 'DEBUG', 'WARN', 'ERROR', 'CRITICAL']
        components = ['AuthService', 'DataLake', 'K8sCluster', 'PaymentGateway', 'NeuralNet']

        lines.append("```system_log")
        for _ in range(random.randint(4, 8)):
            ts = base_time + datetime.timedelta(milliseconds=random.randint(1, 5000))
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            lvl = random.choice(levels)
            comp = random.choice(components)
            msg_id = str(uuid.uuid4())[:8]
            msg = f"Process {random.randint(1000,9999)}: {random.choice(self.TECH_BUZZWORDS)} failed for task {msg_id}"
            lines.append(f"[{ts_str}] [{lvl}] [{comp}] {msg}")
        lines.append("```")
        return "\n".join(lines)

    def _gen_email_block(self) -> str:
        """Генерирует корпоративное письмо."""
        sender = f"{random.choice(['alex', 'john', 'maria', 'sveta'])}@company.corp"
        role = random.choice(self.CORPORATE_ROLES)
        subject = f"Re: {random.choice(['Incident', 'Update', 'Meeting', 'Report'])} #{random.randint(1000,9999)}"

        body = self._gen_narrative_block()

        email = (
            f"\nFrom: {sender} ({role})\n"
            f"To: all@company.corp\n"
            f"Subject: {subject}\n"
            f"Date: {datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S')}\n\n"
            f"Коллеги,\n\n{body}\n\n"
            f"С уважением,\n{sender.split('@')[0].capitalize()}\n"
            f"{'-'*20}"
        )
        return email

    def _gen_json_block(self) -> str:
        """Генерирует JSON конфиг (мусорные данные)."""
        import json
        data = {
            "config_id": str(uuid.uuid4()),
            "params": {
                "timeout": random.randint(100, 5000),
                "retry_policy": random.choice(["linear", "exponential"]),
                "tags": random.sample(self.TECH_BUZZWORDS, 3)
            },
            "nodes": [random.randint(1, 100) for _ in range(5)],
            "active": random.choice([True, False])
        }
        return f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"

    def _generate_haystack(self, context_length_tokens: int) -> str:
        """Собирает контекст из разнородных блоков."""
        # Приблизительно 1 токен ~ 3-4 символа (очень грубо, для кириллицы + код может быть иначе)
        # Целимся в количество символов
        target_chars = context_length_tokens * 3

        blocks = []
        current_chars = 0

        generators = [
            self._gen_narrative_block,
            self._gen_narrative_block, # Нарратива чуть больше
            self._gen_log_block,
            self._gen_email_block,
            self._gen_json_block
        ]

        section_id = 1
        while current_chars < target_chars:
            gen_func = random.choice(generators)

            header = f"\n\n### SECTION {section_id}: {random.choice(self.TECH_BUZZWORDS).upper()}\n"
            content = gen_func()

            block = header + content
            blocks.append(block)

            current_chars += len(block)
            section_id += 1

        return "".join(blocks)

    # --- Генерация иголки (Фактов) ---

    def _generate_needle(self) -> Tuple[str, str, str]:
        """Генерирует сложные факты, которые трудно угадать."""

        needle_types = [
            {
                'id': 'secret_key',
                'template': "Критический API-ключ для доступа к ядру системы: '{key}'.",
                'question': "Какой API-ключ используется для доступа к ядру системы?",
                'answer': "{key}",
                'gen': lambda: f"sk-live-{uuid.uuid4().hex[:12]}"
            },
            {
                'id': 'hidden_person',
                'template': "Настоящим виновником инцидента #404 был скрытый сотрудник {name}, работающий из {city}.",
                'question': "Как звали сотрудника, виновного в инциденте #404?",
                'answer': "{name}",
                'gen': lambda: (random.choice(['Вениамин Кузнецов', 'Аркадий Райкин', 'Жанна Агузарова']), random.choice(['Омска', 'Твери', 'Риги']))
            },
            {
                'id': 'legacy_param',
                'template': "Внимание: параметр 'max_tokens' в конфиге legacy_v1 жестко задан значением {val} и не подлежит изменению.",
                'question': "Какое значение параметра max_tokens задано в конфиге legacy_v1?",
                'answer': "{val}",
                'gen': lambda: str(random.randint(1337, 99999))
            }
        ]

        chosen = random.choice(needle_types)

        if chosen['id'] == 'hidden_person':
            name, city = chosen['gen']()
            needle = chosen['template'].format(name=name, city=city)
            ans = chosen['answer'].format(name=name)
        else:
            val = chosen['gen']()
            needle = chosen['template'].format(key=val, val=val)
            ans = chosen['answer'].format(key=val, val=val)

        return needle, chosen['question'], ans

    def _add_smart_distractors(self, haystack: str, needle: str, question: str) -> str:
        """Добавляет 'ложные иголки' - похожие по структуре, но с другими данными."""

        distractors = []

        if "API-ключ" in needle:
            for _ in range(3):
                fake_key = f"sk-test-{uuid.uuid4().hex[:10]}"
                distractors.append(f"Старый неактивный API-ключ: '{fake_key}'.")
                distractors.append(f"Ключ для тестового окружения: '{fake_key}'.")

        if "инцидент" in needle:
            distractors.append("Подозрение на инцидент #403 пало на системного администратора Ивана, но он был оправдан.")
            distractors.append("В инциденте #500 виновных не обнаружено.")

        if "max_tokens" in needle:
            distractors.append("Параметр 'min_tokens' обычно равен 100.")
            distractors.append("В новой версии конфига параметр 'max_tokens' игнорируется.")

        # Вставка дистракторов
        parts = haystack.split('\n\n')
        for d in distractors:
            if parts:
                idx = random.randint(0, len(parts)-1)
                parts.insert(idx, f"Примечание: {d}")

        return "\n\n".join(parts)

    def _insert_needle(self, haystack: str, needle: str, depth_percent: int) -> str:
        """Вставляет иголку, маскируя её под формат окружающего текста."""
        lines = haystack.split('\n')
        target_line_idx = int(len(lines) * (depth_percent / 100))
        target_line_idx = max(0, min(target_line_idx, len(lines) - 1))

        # Определяем контекст места вставки для маскировки
        surrounding = "\n".join(lines[max(0, target_line_idx-5):min(len(lines), target_line_idx+5)])

        if "```json" in surrounding:
            # Вставляем как поле JSON
            masked_needle = f'  "_SECRET_INFO_": "{needle}",'
        elif "```system_log" in surrounding:
            # Вставляем как лог
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            masked_needle = f"[{ts}] [CRITICAL] [KernelAudit] {needle}"
        elif "From:" in surrounding:
            # Вставляем как P.S. в письме
            masked_needle = f"\nP.S. Важно: {needle}"
        else:
            # Обычный текст, но с маркером важности
            masked_needle = f"\n\n!!! ВНИМАНИЕ (CONFIDENTIAL): {needle} !!!\n\n"

        lines.insert(target_line_idx, masked_needle)
        return "\n".join(lines)

    def generate(self) -> Dict[str, Any]:
        if not self.test_plan:
            raise RuntimeError("План тестов исчерпан")

        config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1

        log.info(f"Generating Advanced Test: {config['test_id']}")

        # 1. Генерация иголки
        needle, question, answer = self._generate_needle()

        # 2. Генерация стога (мультиформатного)
        tokens_needed = config['context_k'] * 1024
        haystack = self._generate_haystack(tokens_needed)

        # 3. Добавление дистракторов
        haystack = self._add_smart_distractors(haystack, needle, question)

        # 4. Вставка иголки
        final_text = self._insert_needle(haystack, needle, config['depth_percent'])

        prompt = (
            f"Проанализируй предоставленные данные (логи, переписку, документацию) и ответь на вопрос.\n"
            f"Игнорируй тестовые и устаревшие данные. Найди актуальный факт.\n\n"
            f"{final_text}\n\n"
            f"ВОПРОС: {question}\n"
            f"ОТВЕТ:"
        )

        return {
            'prompt': prompt,
            'expected_output': answer,
            'test_name': config['test_id'],
            'metadata': {
                'context_k': config['context_k'],
                'depth_percent': config['depth_percent'],
                'complexity': 'high',
                'contains_code': True
            }
        }

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """Упрощенная, но строгая верификация для точных данных."""

        # Очистка от markdown и лишних символов
        clean_resp = llm_output.replace('`', '').strip()
        clean_exp = expected_output.strip()

        # Подготовка базового словаря деталей
        details_dict = {
            'expected': clean_exp,
            'received_snippet': clean_resp[:100], # Берем начало для лога
            'match_type': 'none'
        }

        # 1. Точное вхождение (для ключей и ID)
        if clean_exp in clean_resp:
            details_dict['match_type'] = 'Exact match'
            return {'is_correct': True, 'score': 1.0, 'details': details_dict}

        # 2. Проверка чисел
        nums_resp = re.findall(r'\d+', clean_resp)
        nums_exp = re.findall(r'\d+', clean_exp)
        if nums_exp and set(nums_exp).issubset(set(nums_resp)):
            details_dict['match_type'] = 'Numeric match'
            details_dict['found_numbers'] = nums_resp
            return {'is_correct': True, 'score': 1.0, 'details': details_dict}

        # 3. Проверка именованных сущностей (фамилий)
        # Если в ожидаемом ответе есть кириллица (имя человека)
        if re.search(r'[а-яА-Я]', clean_exp):
            exp_words = set(clean_exp.lower().split())
            resp_words = set(clean_resp.lower().split())

            # Если пересечение слов значительное (например фамилия найдена)
            common = exp_words.intersection(resp_words)
            if len(common) >= len(exp_words) * 0.5: # Хотя бы половина слов
                details_dict['match_type'] = 'Entity/Text match'
                details_dict['matched_words'] = list(common)
                return {'is_correct': True, 'score': 1.0, 'details': details_dict}

        # Если ничего не подошло
        details_dict['error'] = 'Not found in response'
        return {
            'is_correct': False,
            'score': 0.0,
            'details': details_dict
        }