def tst1_score():
    caught = 0
    test_cases = [
        ([], []),
        ([1, 2, 3], [1, 2, 3]),
        ([1, 2, 3, 2, 4, 1], [1, 2, 3, 4]),
        ([1, 1, 1, 1], [1]),
        (['a', 'b', 'c', 'b', 'a'], ['a', 'b', 'c']),
        ([1, 'a', 2, 'a', 1], [1, 'a', 2]),
        ([None, 1, None, 2], [None, 1, 2]),
    ]

    for i, (input_seq, expected) in enumerate(test_cases):
        try:
            result = correct_dedupe(input_seq)
            assert result == expected, f"Test case {i} failed: got {result}, expected {expected}"
        except Exception:
            # Если корректная функция падает — это ошибка теста (не мутанта).
            raise AssertionError("Correct implementation is broken")

    for mutant in mutants:
        try:
            result = mutant([])
            assert result == [], "Empty list test failed"
        except Exception:
            continue  # Мутант не прошел первый тест, пропускаем

        try:
            # Проверяем все кейсы
            for input_seq, expected in test_cases:
                if input_seq == []:
                    continue  # Пропустим пустой список в этом цикле
                result = mutant(input_seq)
                assert result == expected, f"Mutant failed on {input_seq}: got {result}, expected {expected}"
            caught += 1
        except Exception:
            pass

    return caught
