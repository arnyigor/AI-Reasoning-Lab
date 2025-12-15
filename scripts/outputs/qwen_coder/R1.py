def collect_view_ids(tree):
    result = []
    seen_nodes = set()  # для защиты от циклов по identity узла

    def dfs(node):
        if node is None:
            return

        # Проверяем, не посещали ли мы этот узел ранее (по identity)
        node_id = id(node)
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)

        # Добавляем ID, если он уникален для результата
        node_id_str = node.get('id')
        if node_id_str is not None and node_id_str not in result:
            result.append(node_id_str)

        # Рекурсивный обход дочерних узлов
        for child in node.get('children', []):
            dfs(child)

    dfs(tree)
    return result
