def choose_prefetch(items, max_bytes):
    items.sort(key=lambda x: x['id'])

    n = len(items)
    if n == 0 or max_bytes < 0:
        return []

    dp = [-1] * (max_bytes + 1)
    parent = [None] * (max_bytes + 1)
    best_path = [[] for _ in range(max_bytes + 1)]

    dp[0] = 0

    for i, item in enumerate(items):
        id_, bytes_, value_ = item['id'], item['bytes'], item['value']

        # Обратный проход по байтам
        for j in range(max_bytes, bytes_ - 1, -1):
            if dp[j - bytes_] != -1:
                new_value = dp[j - bytes_] + value_
                old_value = dp[j]

                if new_value > old_value or (new_value == old_value and best_path[j] is not None):
                    # Выбираем лучший путь: по значению, потом лексикографически
                    dp[j] = new_value
                    parent[j] = i

    path = []
    current_weight = max_bytes
    while current_weight >= 0:
        idx = parent[current_weight]
        if idx is not None:
            path.append(items[idx]['id'])
            current_weight -= items[idx]['bytes']
        else:
            break

    return sorted(path)
