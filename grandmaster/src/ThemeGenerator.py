def generate_theme_prompt(theme_idea: str) -> str:
    """
    Создает детализированный промпт для LLM для генерации новой темы.

    Args:
        theme_idea: Краткая идея для темы, например, "Загадка в магической академии".

    Returns:
        Готовый к использованию промпт.
    """
    prompt = f"""
    Пожалуйста, создай новую тему для логической головоломки в стиле "Загадка Эйнштейна".
    Тема должна быть основана на идее: "{theme_idea}".

    Требования к результату:
    1.  Придумай яркое и запоминающееся название для темы.
    2.  Придумай ровно 9 названия для категорий. Названия должны быть в единственном числе.
    3.  Для каждой из 9 категорий придумай ровно 9 уникальных, интересных и тематических названий/имен.
    4.  Отформатируй результат в виде готового к копированию кода на Python — одного словаря.

    Пример идеального результата для темы "Стимпанк-Алхимия":
    {{
        "Стимпанк-Алхимия": {{
            "Изобретатель": ["Alastair", "Isadora", "Bartholomew", "Genevieve", "Percival", "Seraphina", "Thaddeus", "Odette"],
            "Гильдия": ["Artificers", "Clockwork", "Alchemists", "Aethernauts", "Iron-Wrights", "Illuminators", "Cartographers", "Innovators"],
            "Автоматон": ["Cogsworth", "Steam-Golem", "Brass-Scarab", "Chrono-Spider", "Aether-Wisp", "The Oraculum", "The Geographer", "The Archivist"],
            "Эликсир": ["Philosopher's Dew", "Liquid-Luck", "Elixir of Vigor", "Draught of Genius", "Quicksilver-Tonic", "Sun-Stone-Solution", "Aether-in-a-Bottle", "Glimmer-Mist"]
        }}
    }}

    Теперь, пожалуйста, сгенерируй новый словарь для темы "{theme_idea}".
    """
    return prompt.strip()

my_idea = "Тайна в заброшенной Школе"
prompt_for_llm = generate_theme_prompt(my_idea)
print(prompt_for_llm)