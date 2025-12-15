import re
from typing import Any, List, Tuple


# --------------------------------------------------------------------------- #
#   Tokenisation
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r'[()]|-[0-9]+|\d+|[A-Za-z]+')


def _tokenise(expr: str) -> List[str]:
    """Return a list of tokens for the given S‑expression."""
    return _TOKEN_RE.findall(expr)


# --------------------------------------------------------------------------- #
#   Parsing
# --------------------------------------------------------------------------- #

class _ParseError(ValueError):
    pass


def _parse_expr(tokens: List[str], i: int) -> Tuple[Any, int]:
    """
    Parse an expression starting at position `i` in `tokens`.
    Returns a tuple (node, next_index).
    node is either:
        - bool/int
        - tuple(op_name:str, args:list)
    """
    if i >= len(tokens):
        raise _ParseError('Unexpected end of input')

    token = tokens[i]

    # Opening parenthesis → an operator expression
    if token == '(':
        if i + 1 >= len(tokens):
            raise _ParseError('Missing operator after "("')
        op_name = tokens[i + 1].upper()
        args: List[Any] = []
        j = i + 2

        while True:
            if j >= len(tokens):
                raise _ParseError(f'Unclosed parenthesis for operator {op_name}')
            if tokens[j] == ')':
                return (op_name, args), j + 1
            subnode, next_j = _parse_expr(tokens, j)
            args.append(subnode)
            j = next_j

    # Closing parenthesis without matching '(' – syntax error
    if token == ')':
        raise _ParseError('Unexpected ")"')

    # Literal value: boolean or integer
    low = token.lower()
    if low == 'true':
        return True, i + 1
    if low == 'false':
        return False, i + 1

    # Try to parse an integer
    try:
        val = int(token)
        return val, i + 1
    except ValueError as exc:
        raise _ParseError(f'Unknown token: {token}') from exc


def _parse(tokens: List[str]) -> Any:
    """
    Parse a list of tokens into an AST.
    The top‑level expression may be just a value or an operator application.
    """
    node, next_i = _parse_expr(tokens, 0)
    if next_i != len(tokens):
        raise ValueError('Extra tokens after parsing complete')
    return node


# --------------------------------------------------------------------------- #
#   Evaluation
# --------------------------------------------------------------------------- #

class _EvalError(ValueError):
    pass


def _evaluate(node: Any) -> Any:
    """
    Recursively evaluate an AST node.
    Returns bool or int according to the semantics of the expression.
    """
    # Leaf nodes – already have concrete values
    if isinstance(node, (bool, int)):
        return node

    op_name, args = node  # type: ignore[misc]

    # Evaluate all arguments first
    evaluated_args = [_evaluate(arg) for arg in args]

    # Helpers to enforce argument types
    def _require_bools(args_list):
        if not all(isinstance(v, bool) for v in args_list):
            raise TypeError(f'{op_name} expects boolean arguments')

    def _require_ints(args_list):
        # In Python `bool` is a subclass of int, so we explicitly reject it.
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in args_list):
            raise TypeError(f'{op_name} expects integer arguments')

    # Logical operators
    if op_name == 'AND':
        if len(evaluated_args) < 2:
            raise ValueError('AND requires at least 2 arguments')
        _require_bools(evaluated_args)
        return all(evaluated_args)

    if op_name == 'OR':
        if len(evaluated_args) < 2:
            raise ValueError('OR requires at least 2 arguments')
        _require_bools(evaluated_args)
        return any(evaluated_args)

    if op_name == 'XOR':
        if len(evaluated_args) != 2:
            raise ValueError('XOR requires exactly 2 arguments')
        _require_bools(evaluated_args)
        return evaluated_args[0] ^ evaluated_args[1]

    if op_name == 'NOT':
        if len(evaluated_args) != 1:
            raise ValueError('NOT requires exactly 1 argument')
        _require_bools(evaluated_args)
        return not evaluated_args[0]

    # Comparison operators – result is boolean
    if op_name in ('GT', 'LT', 'EQ'):
        if len(evaluated_args) != 2:
            raise ValueError(f'{op_name} requires exactly 2 arguments')
        _require_ints(evaluated_args)
        a, b = evaluated_args
        if op_name == 'GT':
            return a > b
        if op_name == 'LT':
            return a < b
        # EQ
        return a == b

    raise ValueError(f'Unknown operator: {op_name}')


# --------------------------------------------------------------------------- #
#   Public API
# --------------------------------------------------------------------------- #

def evaluate_logic(expression: str) -> bool:
    """
    Evaluate an S‑style logical expression and return the boolean result.

    Parameters
    ----------
    expression : str
        The input string containing a single S‑expression.  Whitespace is ignored.
        Supported elements:
            * Integers (e.g., "42", "-5")
            * Booleans ("true"/"false", case‑insensitive)
            * Operators: AND, OR, XOR, NOT, GT, LT, EQ

    Returns
    -------
    bool
        The evaluated boolean value.

    Raises
    ------
    ValueError
        If the syntax is invalid or an operator receives the wrong number of arguments.
    TypeError
        If operand types do not match the expectations of an operator.
    """
    tokens = _tokenise(expression)
    if not tokens:
        raise ValueError('Empty expression')
    ast = _parse(tokens)
    result = _evaluate(ast)

    if isinstance(result, bool):
        return result

    # The top‑level node could be a number – that is an error per the spec
    raise TypeError(f'Expression does not evaluate to boolean: {result}')



# --- НИЖЕ КОД ВАЛИДАТОРА (НЕ МЕНЯТЬ) ---
import unittest

class TestAIReasoningLab_Module1(unittest.TestCase):
    def test_basic_literals(self):
        """Тест простых литералов"""
        self.assertTrue(evaluate_logic("true"))
        self.assertFalse(evaluate_logic("FALSE"))
        # Числа сами по себе не являются валидным логическим результатом для всей функции,
        # но парсер должен уметь их читать внутри выражений.
        # Однако по условию evaluate_logic возвращает bool.

    def test_arithmetic_ops(self):
        """Тест операторов сравнения чисел"""
        self.assertTrue(evaluate_logic("(GT 10 5)"))
        self.assertFalse(evaluate_logic("(LT 10 5)"))
        self.assertTrue(evaluate_logic("(EQ 55 55)"))
        self.assertFalse(evaluate_logic("(EQ 55 56)"))

    def test_logic_ops(self):
        """Тест логических операторов"""
        self.assertTrue(evaluate_logic("(AND true true true)"))
        self.assertFalse(evaluate_logic("(AND true false true)"))
        self.assertTrue(evaluate_logic("(OR false false true)"))
        self.assertTrue(evaluate_logic("(XOR true false)"))
        self.assertFalse(evaluate_logic("(XOR true true)"))
        self.assertFalse(evaluate_logic("(NOT true)"))

    def test_deep_recursion(self):
        """Тест глубокой вложенности и смешанных типов"""
        # (5 > 3) AND (10 == 10) -> True AND True -> True
        # NOT True -> False
        # True OR False -> True
        expr = "(OR (AND (GT 5 3) (EQ 10 10)) (NOT true))"
        self.assertTrue(evaluate_logic(expr))

        # Сложный кейс: ((1 < 5) XOR (5 > 10)) -> (True XOR False) -> True
        expr2 = "(XOR (LT 1 5) (GT 5 10))"
        self.assertTrue(evaluate_logic(expr2))

    def test_whitespace_robustness(self):
        """Тест устойчивости к пробелам"""
        expr = "  (  AND   ( GT   10 5 )    true )  "
        self.assertTrue(evaluate_logic(expr))

    def test_error_handling_args_count(self):
        """Проверка валидации количества аргументов"""
        with self.assertRaises(ValueError):
            evaluate_logic("(NOT true false)") # NOT принимает только 1 аргумент
        with self.assertRaises(ValueError):
            evaluate_logic("(GT 5)") # GT принимает 2 аргумента

    def test_error_handling_types(self):
        """Проверка валидации типов"""
        # GT ждет int, получает bool
        try:
            evaluate_logic("(GT true false)")
        except (TypeError, ValueError):
            pass # ОК, ошибка поймана
        else:
            self.fail("Должен был упасть с ошибкой типов при (GT true false)")

        # AND ждет bool, получает int
        try:
            evaluate_logic("(AND 1 2)")
        except (TypeError, ValueError):
            pass # ОК
        else:
            self.fail("Должен был упасть с ошибкой типов при (AND 1 2)")

if __name__ == '__main__':
    print("\n🚀 ЗАПУСК МОДУЛЯ 1: RECURSION & PARSING")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
