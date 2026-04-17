from typing import Dict, Any
from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class DistributedConsensusReasoningTestGenerator(AbstractTestGenerator):
    def __init__(self, test_id: str) -> None:
        super().__init__(test_id)

    def generate(self) -> Dict[str, Any]:
        function_name = "consensusOutcome"
        expected_result = (
            "LEADER=N5(term=7);"
            "COMMITTED=[e1,e2,e3,e4];"
            "BYZANTINE=[];"
            "FALSE_POSITIVE=[N6_conflict_detection_between_N1_and_N5];"
            "MIN_TERM=7"
        )

        prompt = (
            "Return only Kotlin code.\n"
            "Do not use markdown fences.\n"
            "Do not print explanations, comments, reasoning, or extra text.\n"
            "Implement the exact Kotlin function:\n"
            f"fun {function_name}(): String\n"
            "Also implement main() that prints only the returned final string.\n\n"
            "You must analyze the scenario and compute the final answer.\n"
            "Do not hardcode unrelated text.\n"
            "The program must compile and run.\n\n"
            "Return the result exactly in this canonical format:\n"
            "LEADER=<node(term=x)>;COMMITTED=[comma-separated entries];BYZANTINE=[comma-separated nodes or empty];FALSE_POSITIVE=[description or empty];MIN_TERM=<number>\n\n"
            "Important semantic clarifications for this task:\n"
            "1) Connectivity statements are authoritative and directional from each datacenter's perspective.\n"
            "2) A datacenter is considered partitioned if, from its own perspective, it loses connection with more than 50% of the other datacenters.\n"
            "3) When the question asks what is guaranteed in the final state, use the strongest safe conclusion that holds across race conditions.\n"
            "4) Do not treat a node as actually Byzantine unless the rules force that conclusion.\n"
            "5) If conflicting same-term leadership/log claims require a new conflict-resolution election, account for the resulting higher term in the final stable state.\n\n"
            "Scenario:\n"
            "A distributed system of 13 nodes (N1-N13) uses modified Multi-Paxos.\n"
            "Datacenter A (US-East): N1, N2, N3, N4\n"
            "Datacenter B (US-West): N5, N6, N7, N8\n"
            "Datacenter C (EU): N9, N10, N11\n"
            "Datacenter D (Asia): N12, N13\n\n"
            "Rules:\n"
            "1) Quorum requirement: floor(n/2) + 1 = 7 nodes.\n"
            "2) Leader election: There can be at most 1 Leader. Higher term has priority. If candidates are otherwise tied, the node with the smaller number wins.\n"
            "3) Term increment: At each leader election, participating nodes increment term by 1.\n"
            "4) Byzantine tolerance: Up to floor((n-1)/3) = 4 Byzantine nodes.\n"
            "5) Network partition handling:\n"
            "   - If a datacenter loses connection with more than 50% of the other datacenters, it is partitioned.\n"
            "   - A partitioned datacenter enters read-only mode.\n"
            "6) Commit rule: A log entry is committed only if:\n"
            "   - It is written to a quorum of 7 nodes.\n"
            "   - The current-term Leader confirms commit in the next heartbeat.\n"
            "   - There is no Byzantine disagreement with more than one different value for the same log position.\n"
            "7) Clock skew between datacenters can be up to ±200ms.\n"
            "8) Byzantine detection rule: If a node observes conflicting messages from the same node with the same term, it marks that node as Byzantine.\n"
            "9) Recovery rule: A partitioned datacenter can return to active mode only if:\n"
            "   - Connectivity is restored with at least 50% of datacenters.\n"
            "   - It receives a snapshot from the current Leader.\n"
            "   - Its local term is less than or equal to the global term.\n\n"
            "Initial state T0:\n"
            "N1  A  term=5  Leader    [e1,e2,e3,e4] committed  Online\n"
            "N2  A  term=5  Follower  [e1,e2,e3,e4] committed  Online\n"
            "N3  A  term=5  Follower  [e1,e2,e3]              Online\n"
            "N4  A  term=4  Follower  [e1,e2]                 Online\n"
            "N5  B  term=5  Follower  [e1,e2,e3,e4] committed Online\n"
            "N6  B  term=5  Follower  [e1,e2,e3,e4] committed Online\n"
            "N7  B  term=5  Follower  [e1,e2,e3]              Online\n"
            "N8  B  term=5  Follower  [e1,e2,e3,e4] committed Online\n"
            "N9  C  term=5  Follower  [e1,e2,e3]              Online\n"
            "N10 C  term=5  Follower  [e1,e2,e3,e4] committed Online\n"
            "N11 C  term=4  Follower  [e1,e2]                 Offline\n"
            "N12 D  term=5  Follower  [e1,e2,e3]              Online\n"
            "N13 D  term=5  Follower  [e1,e2,e3,e4] committed Online\n"
            "N1 is the current Leader.\n\n"
            "Events:\n"
            "T1 (t=0ms): Massive network partition with authoritative directional visibility:\n"
            "- From A's perspective: A sees neither B nor C nor D.\n"
            "- From B's perspective: B sees A, C, D.\n"
            "- From C's perspective: C sees B, D, but not A.\n"
            "- From D's perspective: D sees B, C, but not A.\n\n"
            "T2 (t=+150ms):\n"
            "- N11 returns Online.\n"
            "- A client sends write request e5 to N5.\n\n"
            "T3 (t=+300ms):\n"
            "- N4 suddenly gets a connection to N9 through a backup satellite channel.\n"
            "- That A->C path has 600ms latency.\n"
            "- N4 starts leader election with term=5 because its local term was 4.\n\n"
            "T4 (t=+450ms):\n"
            "- N1, still isolated from A's perspective, receives internal heartbeat from N2 and N3.\n"
            "- N1 increments term to 6 and tries to commit e5 locally.\n\n"
            "T5 (t=+500ms):\n"
            "- N6 observes conflicting same-term leadership/log claims:\n"
            "  * From N1 via delayed path: term=6, log=[e1,e2,e3,e4,e5]\n"
            "  * From N5 as local new Leader: term=6, log=[e1,e2,e3,e4,e5']\n"
            "- N6 marks either N1 or N5 as Byzantine.\n\n"
            "T6 (t=+800ms): Partial recovery with authoritative directional visibility:\n"
            "- From A's perspective: A sees B and D, but not C.\n"
            "- From B's perspective: B sees A, C, D.\n"
            "- From C's perspective: C sees B and D, but not A.\n"
            "- From D's perspective: D sees A, B, C.\n\n"
            "Task:\n"
            "Compute the only correct final stable state after T6.\n"
            "You must determine:\n"
            "- the guaranteed final Leader and its term,\n"
            "- which entries are guaranteed committed,\n"
            "- actual Byzantine nodes if any,\n"
            "- whether N6's Byzantine mark is a false positive,\n"
            "- the minimum term in the final stable system after necessary conflict resolution.\n\n"
            "Return only Kotlin code.\n"
            "Print only the final canonical result string.\n"
        )

        return {
            "prompt": prompt,
            "expected_output": {
                "target_language": "kotlin",
                "function_name": function_name,
                "test_input": [],
                "expected_result": expected_result,
                "validation_type": "exact_match",
                "output_type": "str",
            },
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        language = expected_output.get("target_language", "kotlin")

        if language != "kotlin":
            return self._error_response(
                error_msg=f"Unsupported target language: {language}",
                method="unsupported_language",
                preview=llm_output,
            )

        success, code_to_exec, method = self._extract_kotlin_code(llm_output)
        if not success or not code_to_exec.strip():
            return self._error_response(
                error_msg="Failed to extract Kotlin code from model output.",
                method=method if method else "unknown",
                preview=llm_output,
            )

        function_name = expected_output.get("function_name", "")
        if function_name and f"fun {function_name}(" not in code_to_exec:
            return self._error_response(
                error_msg=f"Required function '{function_name}' was not found in the generated Kotlin code.",
                method=method,
                preview=code_to_exec,
            )

        if "fun main(" not in code_to_exec:
            return self._error_response(
                error_msg="Required entry point 'main' was not found in the generated Kotlin code.",
                method=method,
                preview=code_to_exec,
            )

        test_input = expected_output.get("test_input", [])
        if test_input == []:
            args = []
        elif isinstance(test_input, list) and all(isinstance(x, str) for x in test_input):
            args = test_input
        else:
            return self._error_response(
                error_msg="Invalid test_input format. Expected [] or list[str].",
                method=method,
                preview=code_to_exec,
            )

        try:
            exec_result = self.execute_kotlin_code(code_to_exec, args=args)
        except Exception as e:
            return self._error_response(
                error_msg="Exception while executing Kotlin code.",
                method=method,
                preview=code_to_exec,
                raw_err=str(e),
            )

        if not isinstance(exec_result, dict):
            return self._error_response(
                error_msg="Execution result has invalid format.",
                method=method,
                preview=code_to_exec,
                raw_err=str(exec_result),
            )

        if not exec_result.get("success", False):
            return self._error_response(
                error_msg="Kotlin execution failed.",
                method=method,
                preview=code_to_exec,
                raw_err=exec_result.get("error", ""),
            )

        output_str = exec_result.get("output", "").strip()
        last_line = output_str.split("\n")[-1].strip() if output_str else ""

        output_type = expected_output.get("output_type", "str")
        expected_val = expected_output.get("expected_result")

        try:
            if output_type == "int":
                actual_val = int(last_line)
            elif output_type == "float":
                actual_val = float(last_line)
            elif output_type == "bool":
                actual_val = last_line.lower() == "true"
            else:
                actual_val = last_line
        except Exception as e:
            return self._error_response(
                error_msg=f"Failed to cast execution output to {output_type}.",
                method=method,
                preview=code_to_exec,
                raw_err=str(e),
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

    def _error_response(self, error_msg: str, method: str, preview: str, raw_err: str = "") -> Dict[str, Any]:
        return {
            "is_correct": False,
            "details": {
                "error": error_msg,
                "extraction_method": method,
                "code_preview": preview[:300],
                "raw_error": raw_err,
            },
        }
