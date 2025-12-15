#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Reasoning Lab — автономный набор тестов для сравнения LLM на задачах,
похожих на Android-разработку, но проверяемых в Python (stdlib only).

Требования:
- Python 3.9+
- Без внешних зависимостей
- Каждый тест: условие, вход/выход, эталон, reasoning checklist, критерий прохождения
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ----------------------------
# Utilities (safe-ish exec)
# ----------------------------

class CandidateError(Exception):
    pass


def _exec_candidate(code: str) -> Dict[str, Any]:
    """
    Executes candidate code in a fresh namespace.
    """
    ns: Dict[str, Any] = {}

    # Полный список, необходимый для работы классов и импортов
    safe_builtins = {
        # Exceptions
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AssertionError": AssertionError,
        "ImportError": ImportError,
        "NameError": NameError,
        "AttributeError": AttributeError,
        "NotImplementedError": NotImplementedError,

        # IO / Basic
        "print": print,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "id": id,
        "hash": hash,
        "__import__": __import__,      # Импорты
        "__build_class__": __build_class__, # Создание классов

        # Math / Logic
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "all": all,
        "any": any,
        "zip": zip,
        "sorted": sorted,
        "reversed": reversed,

        # Types
        "set": set,
        "dict": dict,
        "list": list,
        "tuple": tuple,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "isinstance": isinstance,
        "object": object,
        "super": super,
        "type": type,
    }
    ns["__builtins__"] = safe_builtins
    try:
        exec(code, ns, ns)
    except Exception as e:
        raise CandidateError(f"Exec failed: {e}\n{traceback.format_exc()}") from e
    return ns



def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _format_fail(msg: str) -> str:
    return f"FAIL: {msg}"


def _format_pass(msg: str) -> str:
    return f"PASS: {msg}"


# ----------------------------
# Test definitions
# ----------------------------

@dataclass
class TestCase:
    name: str
    func: Callable[..., Any]
    args: Tuple[Any, ...]
    expected: Any


@dataclass
class LabTest:
    test_id: str
    category: str
    android_analogy: str
    prompt: str
    reasoning_checklist: List[str]
    expected_output_desc: str
    required_symbols: List[str]
    tests: List[TestCase]
    reference_solution: str  # as text; used for documentation / debugging

    def grade(self, candidate_code: str, timeout_s: float = 2.0) -> Tuple[bool, str]:
        # Basic symbol check to avoid hardcoding print-only answers
        for sym in self.required_symbols:
            if re.search(rf"\b{re.escape(sym)}\b", candidate_code) is None:
                return False, _format_fail(f"Missing required symbol: {sym}")

        start = time.perf_counter()
        try:
            ns = _exec_candidate(candidate_code)
        except CandidateError as e:
            return False, _format_fail(str(e))

        elapsed = time.perf_counter() - start
        if elapsed > timeout_s:
            return False, _format_fail(f"Timeout during exec (> {timeout_s}s)")

        # Run test cases
        for tc in self.tests:
            if tc.name not in ns:
                return False, _format_fail(f"Function '{tc.name}' not found")
            fn = ns[tc.name]
            try:
                got = fn(*tc.args)
            except Exception as e:
                return False, _format_fail(f"{tc.name}{tc.args} raised {type(e).__name__}: {e}")
            if got != tc.expected:
                return False, _format_fail(
                    f"{tc.name}{tc.args} => {got!r}, expected {tc.expected!r}"
                )
        return True, _format_pass("All tests passed")


# ----------------------------
# Reference solutions (kept short, not for training; for human inspection)
# ----------------------------

REF_R1 = r'''
def collect_view_ids(tree):
    # tree: dict with keys {"id": str|None, "children": list[tree]} or None
    # Return unique IDs in DFS pre-order. Handle cycles by object identity.
    out = []
    seen_ids = set()
    seen_nodes = set()

    def dfs(node):
        if node is None:
            return
        nid = id(node)
        if nid in seen_nodes:
            return
        seen_nodes.add(nid)
        vid = node.get("id")
        if vid is not None and vid not in seen_ids:
            seen_ids.add(vid)
            out.append(vid)
        for ch in node.get("children", []):
            dfs(ch)

    dfs(tree)
    return out
'''

REF_DP1 = r'''
def choose_prefetch(items, max_bytes):
    # items: list[{"id": str, "bytes": int, "value": int}]
    # return sorted list of ids of chosen items maximizing total value, tie-break: min bytes, then lexicographic ids
    n = len(items)
    # dp[b] = (value, chosen_ids_tuple, used_bytes)
    dp = [(-1, (), 0) for _ in range(max_bytes + 1)]
    dp[0] = (0, (), 0)

    for it in items:
        w = it["bytes"]
        v = it["value"]
        iid = it["id"]
        for b in range(max_bytes, w - 1, -1):
            prev_val, prev_ids, _ = dp[b - w]
            if prev_val < 0:
                continue
            cand_ids = tuple(sorted(prev_ids + (iid,)))
            cand_val = prev_val + v
            cur_val, cur_ids, _ = dp[b]
            better = False
            if cand_val > cur_val:
                better = True
            elif cand_val == cur_val and cur_val >= 0:
                # tie-break: fewer bytes, then lexicographic ids
                # At fixed b it's same bytes, so only ids tie-break.
                if cand_ids < cur_ids:
                    better = True
            if better:
                dp[b] = (cand_val, cand_ids, b)

    best = max(dp, key=lambda x: x[0])
    return list(best[1])
'''

REF_DS1 = r'''
class LRUCacheTTL:
    def __init__(self, capacity, ttl_seconds):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.capacity = capacity
        self.ttl = ttl_seconds
        self._data = {}  # key -> (value, expires_at)
        self._order = []  # MRU at end; store keys

    def _purge_expired(self, now):
        # remove expired keys
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            self._data.pop(k, None)
        if expired:
            self._order = [k for k in self._order if k in self._data]

    def get(self, key, now):
        self._purge_expired(now)
        if key not in self._data:
            return None
        val, exp = self._data[key]
        # touch
        self._order = [k for k in self._order if k != key] + [key]
        return val

    def put(self, key, value, now):
        self._purge_expired(now)
        expires = now + self.ttl
        if key in self._data:
            self._data[key] = (value, expires)
            self._order = [k for k in self._order if k != key] + [key]
            return
        # evict if full
        if len(self._data) >= self.capacity:
            # evict LRU
            lru = self._order.pop(0)
            self._data.pop(lru, None)
        self._data[key] = (value, expires)
        self._order.append(key)
'''

REF_LC1 = r'''
def reduce_lifecycle(events):
    # Simplified states: CREATED, STARTED, RESUMED, PAUSED, STOPPED, DESTROYED
    # rotate => onPause,onStop,onDestroy,onCreate,onStart,onResume
    state = "INIT"
    for e in events:
        if e == "rotate":
            for sub in ["onPause", "onStop", "onDestroy", "onCreate", "onStart", "onResume"]:
                state = _apply(state, sub)
        else:
            state = _apply(state, e)
    can_access_ui = (state == "RESUMED")
    return (state, can_access_ui)

def _apply(state, e):
    # permissive but deterministic reducer
    if e == "onCreate":
        return "CREATED"
    if e == "onStart":
        return "STARTED" if state in ("CREATED", "STOPPED") else "STARTED"
    if e == "onResume":
        return "RESUMED" if state in ("STARTED", "PAUSED") else "RESUMED"
    if e == "onPause":
        return "PAUSED" if state == "RESUMED" else "PAUSED"
    if e == "onStop":
        return "STOPPED" if state in ("PAUSED", "STARTED") else "STOPPED"
    if e == "onDestroy":
        return "DESTROYED"
    raise ValueError("Unknown event")
'''

REF_EH1 = r'''
def normalize_android_path(path):
    # Similar to normalizing a file path: collapse //, resolve . and .., keep leading /
    # Raise ValueError on None or empty
    if path is None or path == "":
        raise ValueError("path required")
    is_abs = path.startswith("/")
    parts = [p for p in path.split("/") if p not in ("", ".")]
    stack = []
    for p in parts:
        if p == "..":
            if stack:
                stack.pop()
            else:
                # do not go above root for abs; for relative keep ".."
                if not is_abs:
                    stack.append("..")
        else:
            stack.append(p)
    out = "/".join(stack)
    return "/" + out if is_abs else out
'''


# ----------------------------
# Build tests (inputs + expected outputs)
# ----------------------------

def build_tests() -> List[LabTest]:
    tests: List[LabTest] = []

    # R1 — recursion (tree with cycles)
    # Build a small cyclic structure
    a = {"id": "root", "children": []}
    b = {"id": "btn_login", "children": []}
    c = {"id": "txt_title", "children": []}
    a["children"] = [b, c]
    b["children"] = [a]  # cycle back

    tests.append(LabTest(
        test_id="R1",
        category="recursion",
        android_analogy="DFS обход дерева layout/view с защитой от циклов (например, include/compose-дерево с ссылками).",
        prompt=(
            "Напиши функцию Python `collect_view_ids(tree)`.\n"
            "Вход: `tree` — узел (dict) формата {'id': str|None, 'children': list[узлов]} или None.\n"
            "Нужно вернуть список уникальных `id` в DFS pre-order.\n"
            "Требования:\n"
            "- Игнорировать None.\n"
            "- Уникальность по значению id (строке), но защита от циклов по identity узлов.\n"
            "- Порядок: как при обычном DFS pre-order, но повторяющиеся id не добавлять.\n"
        ),
        reasoning_checklist=[
            "Определить обход DFS pre-order.",
            "Сделать защиту от циклов по identity узлов (id(node)).",
            "Сделать уникальность результата по строковому id.",
            "Проверить поведение на None, пустых children, повторяющихся id."
        ],
        expected_output_desc="Список строк (id) в DFS pre-order без повторов.",
        required_symbols=["collect_view_ids"],
        tests=[
            TestCase(name="collect_view_ids", func=None, args=(a,), expected=["root", "btn_login", "txt_title"]),
            TestCase(name="collect_view_ids", func=None, args=(None,), expected=[]),
            TestCase(name="collect_view_ids", func=None,
                     args=({"id": None, "children": [{"id": "x", "children": []}]},), expected=["x"]),
        ],
        reference_solution=REF_R1
    ))

    # DP1 — knapsack-like prefetch selection
    items = [
        {"id": "img_a", "bytes": 4, "value": 7},
        {"id": "img_b", "bytes": 3, "value": 6},
        {"id": "img_c", "bytes": 2, "value": 4},
        {"id": "img_d", "bytes": 5, "value": 9},
    ]
    tests.append(LabTest(
        test_id="DP1",
        category="dynamic_programming",
        android_analogy="Выбор набора ресурсов для prefetch в ограниченный cache (0/1 knapsack).",
        prompt=(
            "Напиши функцию Python `choose_prefetch(items, max_bytes)`.\n"
            "items — список dict: {'id': str, 'bytes': int, 'value': int}.\n"
            "Нужно выбрать подмножество с суммарными bytes <= max_bytes и максимальным суммарным value.\n"
            "Вернуть список выбранных id, отсортированный лексикографически.\n"
            "Tie-break:\n"
            "- При одинаковом суммарном value выбрать лексикографически меньший список id.\n"
            "Ограничения: решение должно быть не хуже O(n*max_bytes) для средних размеров.\n"
        ),
        reasoning_checklist=[
            "Распознать задачу как 0/1 knapsack.",
            "Сделать DP по весу (max_bytes).",
            "Аккуратно реализовать tie-break для равной ценности.",
            "Вернуть id отсортированными."
        ],
        expected_output_desc="Список id выбранных элементов (лексикографически отсортирован).",
        required_symbols=["choose_prefetch"],
        tests=[
            TestCase(name="choose_prefetch", func=None, args=(items, 5), expected=["img_b", "img_c"]),  # value=10
            TestCase(name="choose_prefetch", func=None, args=(items, 7), expected=["img_a", "img_b"]),  # value=13
            TestCase(name="choose_prefetch", func=None, args=([], 10), expected=[]),
        ],
        reference_solution=REF_DP1
    ))

    # DS1 — LRU + TTL with deterministic time
    tests.append(LabTest(
        test_id="DS1",
        category="data_structures",
        android_analogy="LRU кэш (например, images) + TTL, с детерминированным временем (now параметр).",
        prompt=(
            "Реализуй класс Python `LRUCacheTTL`.\n"
            "Конструктор: `LRUCacheTTL(capacity: int, ttl_seconds: int)`.\n"
            "Методы:\n"
            "- `put(key, value, now)` сохраняет значение, истекающее в now+ttl_seconds.\n"
            "- `get(key, now)` возвращает value или None; доступ обновляет LRU-порядок.\n"
            "Правила:\n"
            "- При переполнении capacity выкидывать LRU (наименее недавно использованный).\n"
            "- Истёкшие записи считать отсутствующими (purge при get/put).\n"
            "- capacity и ttl_seconds должны быть > 0, иначе ValueError.\n"
        ),
        reasoning_checklist=[
            "Понять инварианты LRU (touch на get/put).",
            "Сделать purge истёкших по now при операциях.",
            "Сделать корректное вытеснение при capacity.",
            "Не использовать реальное время; только параметр now."
        ],
        expected_output_desc="Корректная работа LRU+TTL по тестам.",
        required_symbols=["LRUCacheTTL"],
        tests=[
            TestCase(name="_ds1_scenario", func=None, args=(), expected=True),
        ],
        reference_solution=REF_DS1
    ))

    # We'll inject DS1 scenario into candidate namespace requirement via helper name
    # Candidate must define class; we define scenario checker as a required function name in tests
    # but the actual function will be looked up from candidate ns, so we handle it differently:
    # We'll instead require candidate defines LRUCacheTTL and also define a function _ds1_scenario
    # that we won't require (simplify): override DS1 tests to call a local wrapper by executing candidate ns.
    # To keep framework simple, we encode DS1 as explicit functional tests via an adapter test.
    # We'll rebuild DS1 in a custom subclass-like way by wrapping with a synthetic function expected to exist:
    # -> easiest: require candidate defines `ds1_check()` returning True when internal checks pass.
    # Let's do that to keep grading uniform.

    tests.pop()  # remove DS1 above; re-add as ds1_check
    tests.append(LabTest(
        test_id="DS1",
        category="data_structures",
        android_analogy="LRU кэш (например, images) + TTL, с детерминированным временем (now параметр).",
        prompt=(
            "Реализуй класс Python `LRUCacheTTL` и функцию `ds1_check()`.\n"
            "Класс:\n"
            "- `LRUCacheTTL(capacity: int, ttl_seconds: int)`\n"
            "- `put(key, value, now)`\n"
            "- `get(key, now)` -> value|None\n"
            "Правила:\n"
            "- capacity и ttl_seconds > 0, иначе ValueError.\n"
            "- purge истёкших при get/put.\n"
            "- LRU вытеснение при переполнении.\n"
            "Функция `ds1_check()` должна создать кэш и вернуть True, если базовые сценарии проходят:\n"
            "1) put a@t=0, get a@t=1 == value\n"
            "2) get a@t=ttl == None (expired when now >= expires)\n"
            "3) LRU eviction: capacity=2, добавить 3 ключа, выкинуть LRU.\n"
        ),
        reasoning_checklist=[
            "Реализовать LRU структуру с 'touch'.",
            "Сделать TTL сравнение now >= expires.",
            "Проверить базовые сценарии в ds1_check без флейков."
        ],
        expected_output_desc="ds1_check() возвращает True, а поведение соответствует контракту.",
        required_symbols=["LRUCacheTTL", "ds1_check"],
        tests=[
            TestCase(name="ds1_check", func=None, args=(), expected=True),
        ],
        reference_solution=REF_DS1
    ))

    # LC1 — lifecycle reducer
    tests.append(LabTest(
        test_id="LC1",
        category="logical_chains",
        android_analogy="Lifecycle reducer для принятия решений (можно ли трогать UI).",
        prompt=(
            "Напиши функцию Python `reduce_lifecycle(events)`.\n"
            "events — список строк: onCreate,onStart,onResume,onPause,onStop,onDestroy,rotate.\n"
            "rotate разворачивается в: onPause,onStop,onDestroy,onCreate,onStart,onResume.\n"
            "Нужно вернуть tuple (final_state, can_access_ui).\n"
            "final_state ∈ {CREATED, STARTED, RESUMED, PAUSED, STOPPED, DESTROYED}.\n"
            "Правило can_access_ui: True только в RESUMED.\n"
            "Если событие неизвестно — ValueError.\n"
            "Допущение: reducer должен быть детерминированным и устойчивым к 'неидеальным' последовательностям.\n"
        ),
        reasoning_checklist=[
            "Развернуть rotate в фиксированную подпоследовательность.",
            "Реализовать детерминированный reducer по событиям.",
            "can_access_ui = (state == RESUMED).",
            "ValueError на неизвестные события."
        ],
        expected_output_desc="Кортеж (state, bool).",
        required_symbols=["reduce_lifecycle"],
        tests=[
            TestCase(name="reduce_lifecycle", func=None, args=(["onCreate", "onStart", "onResume"],),
                     expected=("RESUMED", True)),
            TestCase(name="reduce_lifecycle", func=None, args=(["onCreate", "onStart", "rotate"],),
                     expected=("RESUMED", True)),
            TestCase(name="reduce_lifecycle", func=None, args=(["onCreate", "onDestroy"],),
                     expected=("DESTROYED", False)),
        ],
        reference_solution=REF_LC1
    ))

    # EH1 — error handling + edge cases
    tests.append(LabTest(
        test_id="EH1",
        category="error_handling",
        android_analogy="Нормализация путей (похоже на работу с file paths/URI path segments) и корректные ошибки.",
        prompt=(
            "Напиши функцию Python `normalize_android_path(path)`.\n"
            "Поведение:\n"
            "- path — строка, абсолютная (начинается с '/') или относительная.\n"
            "- Убрать повторные '/', сегменты '.'\n"
            "- Разрешить '..' (подняться на уровень вверх)\n"
            "- Для абсолютных путей '..' выше корня игнорировать.\n"
            "- Для относительных путей '..' в начале сохранять (например '..', '../a').\n"
            "- На None или '' бросать ValueError.\n"
            "Примеры:\n"
            "/a//b/./c -> /a/b/c\n"
            "/../a -> /a\n"
            "../../a/./b -> ../../a/b\n"
        ),
        reasoning_checklist=[
            "Разделить путь на сегменты, нормализовать '.' и пустые.",
            "Корректно обработать '..' для abs/rel.",
            "Сохранить абсолютность (leading '/').",
            "ValueError на None/пустую строку."
        ],
        expected_output_desc="Нормализованный путь (строка) или ValueError.",
        required_symbols=["normalize_android_path"],
        tests=[
            TestCase(name="normalize_android_path", func=None, args=("/a//b/./c",), expected="/a/b/c"),
            TestCase(name="normalize_android_path", func=None, args=("/../a",), expected="/a"),
            TestCase(name="normalize_android_path", func=None, args=("../../a/./b",), expected="../../a/b"),
        ],
        reference_solution=REF_EH1
    ))

    # TST1 — complex tests: candidate writes unit tests that catch mutants
    # We grade by requiring candidate to implement function `tst1_score()` returning integer caught mutants count.
    tests.append(LabTest(
        test_id="TST1",
        category="testing",
        android_analogy="Написание тестов, которые ловят регрессии (mutation-like), как при проверке бизнес-логики use-case.",
        prompt=(
            "Напиши функцию `tst1_score()`.\n"
            "Внутри неё нужно:\n"
            "1) Определить набор assert-проверок (можно без unittest), которые проверяют поведение функции dedupe_preserve_order(seq).\n"
            "2) Тесты должны проходить на корректной реализации и падать на максимальном числе 'мутантов' (ошибочных реализаций).\n"
            "Контракт dedupe_preserve_order:\n"
            "- Вход: список hashable элементов.\n"
            "- Выход: список, где сохраняется ПЕРВОЕ вхождение каждого элемента и исходный порядок первых вхождений.\n"
            "Оценка:\n"
            "- В окружении уже будут доступны: correct_dedupe и список mutants.\n"
            "- Вернуть число мутантов, которых тесты 'поймали' (то есть тесты упали на мутанте).\n"
            "Ограничение: тесты должны проходить на correct_dedupe.\n"
        ),
        reasoning_checklist=[
            "Понять контракт 'первое вхождение + порядок'.",
            "Подобрать кейсы: повторы, все уникальные, все одинаковые, чередование, пустой список.",
            "Проверить, что тесты НЕ падают на correct и падают на мутантах.",
            "Вернуть счёт пойманных мутантов."
        ],
        expected_output_desc="Целое число (сколько мутантов поймано).",
        required_symbols=["tst1_score"],
        tests=[
            TestCase(name="tst1_score", func=None, args=(), expected=5),
            # we expect to catch all 5 mutants with good tests
        ],
        reference_solution="(reference is dynamic; see harness inside grader for mutants)"
    ))

    return tests


# ----------------------------
# Custom grading hook for TST1: inject correct + mutants into candidate namespace
# ----------------------------

def _inject_tst1_environment(candidate_code: str) -> str:
    """
    Wrap candidate code by injecting correct_dedupe and mutants into its globals.
    Candidate's tst1_score() will use them.
    """
    env = r'''
def correct_dedupe(seq):
    out = []
    seen = set()
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _m1(seq):  # loses order (uses set)
    return list(set(seq))

def _m2(seq):  # keeps last occurrence instead of first
    out = []
    seen = set()
    for x in reversed(seq):
        if x not in seen:
            seen.add(x)
            out.append(x)
    return list(reversed(out))

def _m3(seq):  # duplicates not removed
    return list(seq)

def _m4(seq):  # removes too much: only unique elements, but also sorts
    return sorted({x for x in seq})

def _m5(seq):  # off-by-one: skips first element always
    if not seq:
        return []
    return correct_dedupe(seq[1:])

mutants = [_m1, _m2, _m3, _m4, _m5]
'''
    return env + "\n" + candidate_code


# ----------------------------
# Runner
# ----------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-prompts", action="store_true", help="Print prompts for all tests to stdout.")
    parser.add_argument("--save-json", type=str, help="Save prompts to a JSON file (forces UTF-8).")
    parser.add_argument("--dir", type=str, default=None, help="Directory containing candidate outputs: <TEST_ID>.py")
    parser.add_argument("--label", type=str, default="model", help="Label for report")
    parser.add_argument("--timeout", type=float, default=2.0, help="Timeout for exec+tests per task (soft).")
    args = parser.parse_args()

    tests = build_tests()

    # Сценарий 1: Генерация промптов
    if args.print_prompts or args.save_json:
        pack = []
        for t in tests:
            pack.append({
                "test_id": t.test_id,
                "category": t.category,
                "android_analogy": t.android_analogy,
                "prompt": t.prompt,
                "expected_output": t.expected_output_desc,
                "reasoning_checklist": t.reasoning_checklist,
                "pass_criteria": "Все автотесты проходят (PASS).",
            })

        # Если указан файл — пишем в него напрямую с UTF-8
        if args.save_json:
            try:
                with open(args.save_json, "w", encoding="utf-8") as f:
                    json.dump(pack, f, ensure_ascii=False, indent=2)
                print(f"Successfully saved prompts to {args.save_json}")
            except Exception as e:
                print(f"Error saving file: {e}", file=sys.stderr)
                return 1

        # Если запрошен вывод в консоль
        if args.print_prompts:
            print(json.dumps(pack, ensure_ascii=False, indent=2))

        return 0

    # Сценарий 2: Проверка решений
    if not args.dir:
        print("Provide --dir with model outputs, or use --save-json / --print-prompts", file=sys.stderr)
        return 2

    results = []
    passed = 0

    for t in tests:
        path = os.path.join(args.dir, f"{t.test_id}.py")
        if not os.path.exists(path):
            results.append((t.test_id, False, _format_fail(f"Missing file: {path}")))
            continue

        code = _read_text(path)
        if t.test_id == "TST1":
            code = _inject_tst1_environment(code)

        ok, msg = t.grade(code, timeout_s=args.timeout)
        results.append((t.test_id, ok, msg))
        passed += 1 if ok else 0

    # Report
    print(f"== AI Reasoning Lab report: {args.label} ==")
    for tid, ok, msg in results:
        print(f"{tid}: {msg}")
    print(f"TOTAL: {passed}/{len(tests)} passed")

    return 0 if passed == len(tests) else 1



if __name__ == "__main__":
    raise SystemExit(main())

