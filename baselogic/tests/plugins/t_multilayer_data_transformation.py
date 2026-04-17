from typing import Dict, Any
from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class MultiLayerDataTransformationTestGenerator(AbstractTestGenerator):
    def __init__(self, test_id: str) -> None:
        super().__init__(test_id)

    def generate(self) -> Dict[str, Any]:
        function_name = "transformStringsByLength"
        source_items = ["cat", "dog", "rat", "bee", "ant", "cat", "xyz", "bee"]
        expected_result = "{3=[rat, dog, cat, bee, ant]}"

        prompt = (
            "Return only Kotlin code. "
            f"Implement a function {function_name}(items: List<String>): Map<Int, List<String>>. "
            "The function must build a map where keys are string lengths and values are lists of strings of that length. "
            "Keep only strings that contain at least one vowel from aeiouAEIOU. "
            "Remove duplicates. "
            "Sort each list in reverse alphabetical order. "
            f"In main, use this exact input: {source_items}. "
            "Call the function with this input and print only the final result using println. "
            "Do not print explanations, labels, debug text, or anything except the final result. "
            "Return only Kotlin code."
        )

        return {
            "prompt": prompt,
            "expected_output": {
                "function_name": function_name,
                "test_input": [],
                "expected_result": expected_result,
                "validation_type": "exact_match",
                "output_type": "str",
            },
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        success, code_to_exec, method = self._extract_kotlin_code(llm_output)

        if not success:
            return self._error_response("Блок кода Kotlin не найден", method, code_to_exec)

        try:
            exec_result = self.execute_kotlin_code(code_to_exec, args=[])
        except Exception as e:
            return self._error_response(
                f"Ошибка вызова execute_kotlin_code: {e}",
                method,
                code_to_exec
            )

        if not exec_result.get("success", False):
            return self._error_response(
                "Ошибка выполнения/компиляции Kotlin-кода",
                method,
                code_to_exec,
                exec_result.get("error", "") or exec_result.get("stderr", "")
            )

        output_str = exec_result.get("output", "").strip()
        last_line = output_str.split("\n")[-1].strip() if output_str else ""

        expected_val = expected_output["expected_result"]
        out_type = expected_output.get("output_type", "str")

        try:
            if out_type == "int":
                actual_val = int(last_line)
            elif out_type == "float":
                actual_val = float(last_line)
            elif out_type == "bool":
                actual_val = last_line.lower() == "true"
            else:
                actual_val = last_line
        except Exception as e:
            return self._error_response(
                "Ошибка преобразования вывода",
                method,
                output_str,
                str(e),
            )

        is_correct = actual_val == expected_val

        return {
            "is_correct": is_correct,
            "details": {
                "actual": actual_val,
                "expected": expected_val,
                "extraction_method": method,
                "status": "✓ OK" if is_correct else "✗ Mismatch",
            },
        }

    def _error_response(
            self,
            error_msg: str,
            method: str,
            preview: str,
            raw_err: str = ""
    ) -> Dict[str, Any]:
        return {
            "is_correct": False,
            "details": {
                "error": error_msg,
                "extraction_method": method,
                "code_preview": preview[:300],
                "raw_error": raw_err,
            },
        }