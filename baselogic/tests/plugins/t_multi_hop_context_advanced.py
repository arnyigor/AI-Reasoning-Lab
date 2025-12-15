import logging
import os
import random
import re
import uuid
from typing import Dict, Any, Tuple, List

from dotenv import load_dotenv

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


# Если AbstractTestGenerator импортируется из другого места, раскомментируйте импорт
# from baselogic.tests.abstract_test_generator import AbstractTestGenerator
load_dotenv()
log = logging.getLogger(__name__)

class AdvancedMultiHopContextGenerator(AbstractTestGenerator):
    """
    Генератор стресс-тестов RULER-style (Multi-Hop Tracing).
    Реализует динамическую сложность цепочки рассуждений в зависимости от размера контекста.
    """

    ENTITIES = {
        'microservice': ['AuthService', 'PaymentGateway', 'DataLake', 'NotificationService', 'UserGraph'],
        'person': ['Alex', 'Maria', 'John', 'Svetlana', 'Dmitry', 'Yoshua'],
        'artifact': ['config.yaml', 'database_schema', 'API Key', 'Deploy Manifest', 'Incident Report'],
        'location': ['AWS us-east-1', 'On-Premise Server #4', 'GCP Frankfurt', 'Azure Blob', 'Localhost'],
        'action': ['migrated to', 'failed at', 'referenced by', 'deprecated in', 'hidden inside']
    }

    NOISE_BUZZWORDS = [
        'refactoring', 'latency', 'throughput', 'async', 'deadlock', 'mutex',
        'garbage collection', 'serialization', 'handshake', 'backpressure'
    ]

    def __init__(self, test_id: str):
        super().__init__(test_id)

        self.lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "8,16,32,64")
        self.context_lengths_k = [int(k.strip()) for k in self.lengths_str.split(',')]

        self.test_plan = []
        for ctx in self.context_lengths_k:
            # Адаптивная сложность: чем больше контекст, тем длиннее цепочка.
            # 8k -> 3 hops, 64k -> ~12 hops.
            hops = max(3, min(15, int(ctx / 6) + 2))

            self.test_plan.append({
                'context_k': ctx,
                'hops': hops,
                'test_id': f"multi_hop_{ctx}k_{hops}steps"
            })

        self.current_test_index = 0
        log.info(f"MultiHop Generator initialized: {len(self.test_plan)} scenarios loaded.")

    def _generate_noise_block(self, size_chars: int) -> str:
        """Генерирует технический шум (имитация логов и кода)."""
        noise_templates = [
            "Process {pid} {word} status: {status}.",
            "def {word}_{pid}(): return '{uuid}'",
            "// TODO: Fix {word} in module {pid}",
            "User {pid} requested access to {uuid}."
        ]

        buffer = []
        chars_count = 0
        while chars_count < size_chars:
            tpl = random.choice(noise_templates)
            s = tpl.format(
                pid=random.randint(1000, 9999),
                word=random.choice(self.NOISE_BUZZWORDS),
                status=random.choice(['OK', 'FAIL', 'PENDING']),
                uuid=str(uuid.uuid4())[:8]
            )
            buffer.append(s)
            chars_count += len(s) + 1
        return "\n".join(buffer)

    def _generate_chain(self, num_hops: int) -> Tuple[List[Dict], str, str]:
        """Генерирует логическую цепочку связей."""
        start_obj = f"Project_{uuid.uuid4().hex[:4].upper()}"
        chain = []
        current_obj = start_obj

        relations = [
            ("managed by", "manager"), ("located in", "location"),
            ("depends on", "dependency"), ("stored inside", "container"),
            ("referenced in", "reference")
        ]

        for i in range(num_hops):
            rel_text, rel_type = random.choice(relations)

            if i == num_hops - 1:
                # Финальное значение (Ответ)
                final_val = str(random.randint(10000, 99999))
                chain.append({'s': current_obj, 'p': rel_text, 'o': final_val, 'is_final': True})
                answer = final_val
            else:
                # Промежуточное звено
                next_obj = f"Entity_{uuid.uuid4().hex[:6]}"
                chain.append({'s': current_obj, 'p': rel_text, 'o': next_obj, 'is_final': False})
                current_obj = next_obj

        question = f"Starting from '{start_obj}', trace the relationships to find the final secret value/code."
        return chain, question, answer

    def _format_clue(self, link: Dict) -> str:
        """Маскирует факт под разные форматы (JSON, SQL, Email)."""
        s, p, o = link['s'], link['p'], link['o']
        formats = [
            lambda: f"[INFO] [DependencyTree] Mapping update: '{s}' -> {p} -> '{o}'",
            lambda: f'{{ "source": "{s}", "relation": "{p}", "target": "{o}" }}',
            lambda: f"# TODO: Link {s} with {o} (reason: {p})",
            lambda: f"Subject: Update on {s}\nJust a reminder that {s} is {p} {o} now.",
            lambda: f"INSERT INTO relations (from_node, to_node) VALUES ('{s}', '{o}'); -- {p}"
        ]
        return random.choice(formats)()

    def generate(self) -> Dict[str, Any]:
        if not self.test_plan:
            self.current_test_index = 0

        config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1

        chain, question, answer = self._generate_chain(config['hops'])

        # Расчет размера шума
        total_chars = config['context_k'] * 1024 * 3
        avg_noise_size = int(total_chars / (len(chain) + 1))

        haystack_parts = []
        for link in chain:
            haystack_parts.append(self._generate_noise_block(avg_noise_size))
            haystack_parts.append(f"\n\n{self._format_clue(link)}\n\n")
        haystack_parts.append(self._generate_noise_block(avg_noise_size))

        prompt = (
            f"System: You are a forensic data analyst. Analyze the provided chaotic logs and code snippets.\n"
            f"Task: {question}\n"
            f"Constraint: Provide ONLY the final value. Do not explain unless asked.\n\n"
            f"--- BEGIN DATA DUMP ---\n"
            f"{''.join(haystack_parts)}\n"
            f"--- END DATA DUMP ---\n\n"
            f"Question: {question}\n"
            f"Final Answer:"
        )

        return {
            'prompt': prompt,
            'expected_output': answer,
            'test_name': config['test_id'],
            'metadata': config
        }

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        clean_output = self._cleanup_llm_response(llm_output)
        clean_resp = clean_output.strip().lower()
        clean_exp = expected_output.strip().lower()

        if clean_exp in clean_resp:
            return {'is_correct': True, 'score': 1.0, 'details': {'match': 'exact', 'expected': clean_exp}}

        found_nums = re.findall(r'\d+', clean_resp)
        if clean_exp in found_nums:
            return {'is_correct': True, 'score': 1.0, 'details': {'match': 'numeric', 'found': found_nums}}

        return {'is_correct': False, 'score': 0.0, 'details': {'expected': clean_exp, 'received': clean_resp[:50]}}
