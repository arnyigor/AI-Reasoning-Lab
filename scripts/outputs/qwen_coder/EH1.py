def normalize_android_path(path: str) -> str:
    if path is None or path == "":
        raise ValueError("Path must not be null or empty")

    # Разбиваем путь по "/"
    segments = path.split('/')

    # Стек для хранения нормализованных сегментов
    stack = []

    # Определяем, абсолютный ли это путь
    is_absolute = path.startswith('/')

    for segment in segments:
        if segment == '' or segment == '.':
            continue  # Пустой или текущий каталог — игнорируем

        elif segment == '..':
            if stack and stack[-1] != '..':
                # Удаляем предыдущий сегмент (если не относительный "..")
                stack.pop()
            elif not is_absolute:
                # Для относительных путей сохраняем ".."
                stack.append('..')
            # Если абсолютный путь и стек пуст — игнорируем

        else:
            stack.append(segment)

    # Собираем результат
    result = '/'.join(stack)
    if is_absolute:
        return '/' + result
    else:
        return result
