import os
import random
import uuid
import logging
from typing import Dict, Any, Tuple, List
import re

from dotenv import load_dotenv

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

load_dotenv()
log = logging.getLogger(__name__)

class RussianAdvancedMultiHopContextGenerator(AbstractTestGenerator):
    """
    Русская версия RULER-style теста.
    Генерирует логические цепочки на русском языке, смешивая их с техническим шумом.
    """

    # Русские сущности для генерации
    ENTITIES = {
        'person': ['Алексей', 'Мария', 'Дмитрий', 'Светлана', 'Евгений', 'Ольга'],
        'project': ['Проект_Омега', 'Система_Зевс', 'Модуль_Ядро', 'Платформа_Восток'],
        'file': ['config.yaml', 'отчет_за_май.docx', 'secret_key.txt', 'main.py', 'база_клиентов.db'],
        'location': ['Сервер_Москва_1', 'Бэкап_Хранилище', 'Облако_Яндекс', 'Локальный_Диск_D'],
    }

    # Технический шум оставляем "айтишным" (смесь ру/енг), так как это реалистично
    NOISE_PHRASES = [
        "Ошибка сегментации в процессе {pid}",
        "Пользователь {pid} запросил доступ к {uuid}",
        "Сервис {word} перезагружен успешно",
        "Обнаружена высокая задержка в модуле {word}",
        "Выполнение задачи {uuid} приостановлено"
    ]

    BUZZWORDS = ['асинхронность', 'репликация', 'шардирование', 'дедлок', 'кэширование']

    def __init__(self, test_id: str):
        super().__init__(test_id)

        self.lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "8,16,32,64")
        self.context_lengths_k = [int(k.strip()) for k in self.lengths_str.split(',')]

        self.test_plan = []
        for ctx in self.context_lengths_k:
            # Сложность та же: от 3 до 15 шагов
            hops = max(3, min(15, int(ctx / 6) + 2))
            self.test_plan.append({
                'context_k': ctx,
                'hops': hops,
                'test_id': f"ru_multihop_{ctx}k_{hops}steps"
            })

        self.current_test_index = 0
        log.info(f"Russian Generator initialized: {len(self.test_plan)} scenarios.")

    def _generate_noise_block(self, size_chars: int) -> str:
        """Генерирует мусорный текст (имитация логов на русском/английском)."""
        buffer = []
        chars_count = 0
        while chars_count < size_chars:
            tpl = random.choice(self.NOISE_PHRASES)
            s = tpl.format(
                pid=random.randint(1000, 9999),
                word=random.choice(self.BUZZWORDS),
                uuid=str(uuid.uuid4())[:8]
            )
            buffer.append(s)
            chars_count += len(s) + 1
        return "\n".join(buffer)

    def _generate_chain(self, num_hops: int) -> Tuple[List[Dict], str, str]:
        """Генерирует цепочку связей на русском."""

        # Начальное звено
        start_obj = random.choice(self.ENTITIES['project']) + f"_{random.randint(10,99)}"
        chain = []
        current_obj = start_obj

        # (Текст связи, Тип связи)
        relations = [
            ("управляется сотрудником", "менеджер"),
            ("находится на сервере", "локация"),
            ("зависит от файла", "зависимость"),
            ("содержит внутри себя", "контейнер"),
            ("ссылается на объект", "ссылка")
        ]

        for i in range(num_hops):
            rel_text, rel_type = random.choice(relations)

            if i == num_hops - 1:
                # Финал - секретный код
                final_val = str(random.randint(10000, 99999))
                chain.append({'s': current_obj, 'p': rel_text, 'o': final_val, 'is_final': True})
                answer = final_val
            else:
                # Промежуточное звено
                # Выбираем случайное имя для следующего объекта
                next_category = random.choice(list(self.ENTITIES.keys()))
                next_obj = random.choice(self.ENTITIES[next_category]) + f"_{uuid.uuid4().hex[:4]}"

                chain.append({'s': current_obj, 'p': rel_text, 'o': next_obj, 'is_final': False})
                current_obj = next_obj

        question = f"Начиная с объекта '{start_obj}', проследи всю цепочку связей и найди финальное секретное число/код."
        return chain, question, answer

    def _format_clue(self, link: Dict) -> str:
        """Маскирует факты под разные форматы (Русский контекст)."""
        s, p, o = link['s'], link['p'], link['o']
        formats = [
            # Лог
            lambda: f"[ИНФО] [СистемаСвязей] Обновление карты: '{s}' -> {p} -> '{o}'",
            # JSON (ключи англ, значения ру - реалистично)
            lambda: f'{{ "source": "{s}", "relation_type": "{p}", "target_value": "{o}" }}',
            # Комментарий в коде
            lambda: f"# ВАЖНО: Связать {s} с {o} (причина: {p})",
            # Письмо
            lambda: f"Тема: Касательно {s}\nКоллеги, напоминаю, что {s} теперь {p} {o}.",
            # SQL
            lambda: f"INSERT INTO links (src, dst) VALUES ('{s}', '{o}'); -- {p}"
        ]
        return random.choice(formats)()

    def generate(self) -> Dict[str, Any]:
        if not self.test_plan:
            self.current_test_index = 0

        config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1

        chain, question, answer = self._generate_chain(config['hops'])

        # Увеличиваем объем символов, т.к. русские слова длиннее, а токены "дороже"
        total_chars = config['context_k'] * 1024 * 4
        avg_noise_size = int(total_chars / (len(chain) + 1))

        haystack_parts = []
        for link in chain:
            haystack_parts.append(self._generate_noise_block(avg_noise_size))
            haystack_parts.append(f"\n\n{self._format_clue(link)}\n\n")
        haystack_parts.append(self._generate_noise_block(avg_noise_size))

        full_text = "".join(haystack_parts)

        prompt = (
            f"Система: Ты системный аналитик, расследующий инцидент.\n"
            f"Задача: {question}\n"
            f"Требование: Напиши ТОЛЬКО финальное значение (число). Не давай пояснений, если не просят.\n\n"
            f"--- НАЧАЛО ДАННЫХ ---\n"
            f"{full_text}\n"
            f"--- КОНЕЦ ДАННЫХ ---\n\n"
            f"Вопрос: {question}\n"
            f"Ответ:"
        )

        return {
            'prompt': prompt,
            'expected_output': answer,
            'test_name': config['test_id'],
            'metadata': config
        }

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Усовершенствованная верификация для Chain-of-Thought ответов.
        Приоритет отдается последнему найденному числу, но учитываются и вхождения.
        """
        # 1. Базовая нормализация
        # Убираем лишние пробелы и знаки препинания по краям
        clean_resp = self._cleanup_llm_response(llm_output)
        clean_exp = expected_output.strip()

        # Приводим к нижнему регистру для текстового сравнения
        lower_resp = clean_resp.lower()
        lower_exp = clean_exp.lower()

        result = {
            'is_correct': False,
            'score': 0.0,
            'details': {
                'expected': clean_exp,
                'received_raw': llm_output[:100] + "..." if len(llm_output) > 100 else llm_output
            }
        }

        # 2. Стратегия "Exact Match" (Идеальное совпадение)
        if lower_resp == lower_exp:
            result.update({'is_correct': True, 'score': 1.0})
            result['details']['match_type'] = 'exact_full'
            return result

        # 3. Стратегия "Последнее число" (Самая надежная для CoT)
        # Ищем все последовательности цифр
        # \d+ ловит целые числа. Если нужны float, regex будет сложнее: r'-?\d+(?:\.\d+)?'
        all_nums = re.findall(r'\d+', clean_resp)

        if all_nums:
            last_num = all_nums[-1]
            if last_num == clean_exp:
                result.update({'is_correct': True, 'score': 1.0})
                result['details']['match_type'] = 'last_number_hit'
                result['details']['found_sequence'] = all_nums
                return result

            # Если ожидаемого числа нет в конце, но оно ЕСТЬ в списке найденных чисел
            if clean_exp in all_nums:
                # Это "частичный успех" или "грязный ответ".
                # Часто модель пишет: "I found 17846, so the answer is 17846." -> тут ок.
                # Но если: "Value 17846 is wrong, answer is 0." -> тут риск False Positive.
                # Поэтому даем score 1.0, но помечаем тип.
                result.update({'is_correct': True, 'score': 1.0})
                result['details']['match_type'] = 'contains_number'
                result['details']['found_sequence'] = all_nums
                return result

        # 4. Стратегия "Вхождение подстроки" (Fallback для текста)
        # Если ожидаем не число, а слово (например "yes" или "error")
        if lower_exp in lower_resp:
            # Проверяем, не является ли это частью другого слова (например "cat" в "catch")
            # Используем границы слова \b
            if re.search(r'\b' + re.escape(lower_exp) + r'\b', lower_resp):
                result.update({'is_correct': True, 'score': 1.0})
                result['details']['match_type'] = 'substring_word_boundary'
                return result

            # Если границы слов не сработали, но вхождение есть (грубый поиск)
            result.update({'is_correct': True, 'score': 1.0})
            result['details']['match_type'] = 'substring_loose'
            return result

        # 5. Попытка извлечь "Trace" (Цепочку) для логов
        # Если это Chain-of-Thought, полезно выцепить последние предложения
        # Разделяем по переносам строк или точкам
        sentences = re.split(r'[.\n]', llm_output)
        # Берем последние 2 непустых предложения как "вывод"
        meaningful_sentences = [s.strip() for s in sentences if s.strip()]
        trace_summary = " | ".join(meaningful_sentences[-2:]) if len(meaningful_sentences) >= 2 else llm_output[-200:]

        result['details']['trace_summary'] = trace_summary

        return result

