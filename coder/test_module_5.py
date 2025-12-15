# --- СЮДА ВСТАВИТЬ КОД МОДЕЛИ ---
import json
from typing import Iterable, Any, Generator, Tuple, Optional


def robust_process_data(
        stream: Iterable[Any], config: dict
) -> Generator[Tuple[Any, Optional[str]], None, None]:
    """
    Process a stream of items with a three‑step pipeline.

    :param stream: An iterable containing arbitrary objects.
    :param config: Configuration dictionary (expects at least 'rate').
    :return: A generator yielding tuples (result, error_msg).
             On success: (result, None)
             On failure: (None, "<ErrorType>: <message>")
    """
    # Use a sensible default if no rate is supplied
    rate = config.get("rate", 1.0)

    for item in stream:
        try:
            # ---------- Step 1: Validate & Normalize ----------
            if not isinstance(item, str):
                raise TypeError("Expected string")
            cleaned = item.strip().lower()

            # ---------- Step 2: Parse ----------
            if cleaned.startswith("{"):
                try:
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError as exc:
                    # Per the requirement – report as ValueError
                    raise ValueError("Invalid JSON") from exc
            else:
                parsed = cleaned

            # ---------- Step 3: Enrich ----------
            if isinstance(parsed, dict) and "amount" in parsed:
                try:
                    amount_val = float(parsed["amount"])
                except Exception as exc:
                    raise ValueError("Cannot convert 'amount' to float") from exc
                parsed["amount"] = amount_val * rate

            yield (parsed, None)

        except Exception as e:
            # Return a string that always starts with the exception name.
            # This also captures the ValueError raised above for bad JSON.
            yield (None, f"{type(e).__name__}: {e}")


# --- ВАЛИДАТОР ---
import unittest

class TestAIReasoningLab_Module5(unittest.TestCase):
    def test_pipeline(self):
        data = [
            "  Test String  ",           # 0. OK -> "test string"
            123,                        # 1. Fail -> TypeError
            '{"amount": "10"}',         # 2. OK -> dict, amount=15.0 (rate 1.5)
            '{"amount": "bad"}',        # 3. Fail -> ValueError (float conv)
            '{broken_json',             # 4. Fail -> ValueError (json)
            '{"other": 1}',             # 5. OK -> dict no change
        ]
        config = {'rate': 1.5}

        results = list(robust_process_data(data, config))

        # 0. String normal
        self.assertEqual(results[0], ("test string", None))

        # 1. TypeError
        val, err = results[1]
        self.assertIsNone(val)
        self.assertIn("TypeError", err)

        # 2. JSON amount
        val, err = results[2]
        self.assertEqual(val['amount'], 15.0)
        self.assertIsNone(err)

        # 3. Bad amount
        val, err = results[3]
        self.assertIsNone(val)
        self.assertIn("ValueError", err)

        # 4. Broken JSON
        val, err = results[4]
        self.assertIsNone(val)
        self.assertIn("ValueError", err)

if __name__ == '__main__':
    print("\n🚀 ЗАПУСК МОДУЛЯ 5: ROBUSTNESS")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
