# grandmaster/src/LinguisticEngine.py

import inspect  # Импортируем модуль inspect
import pymorphy2
from typing import List, Dict

# --- БЛОК СОВМЕСТИМОСТИ v2.0 (АДАПТЕР) ---
# Эта версия не просто подменяет функцию, а создает полноценный адаптер,
# который имитирует поведение старой функции getargspec, используя новую.
if not hasattr(inspect, 'getargspec'):
    def getargspec_shim(func):
        """
        Обертка, которая вызывает новую функцию getfullargspec,
        но возвращает результат в старом 4-элементном формате,
        который ожидает pymorphy2 v0.9.1.
        """
        spec = inspect.getfullargspec(func)
        # Старый формат: (args, varargs, keywords, defaults)
        # Новый формат: (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations)
        # Мы просто берем первые 4 элемента из нового результата.
        return spec[:4]

    # Присваиваем нашу обертку имени старой функции
    inspect.getargspec = getargspec_shim
# --- КОНЕЦ БЛОКА СОВМЕСТИМОСТИ ---


class LinguisticEngine:
    """
    Отвечает за генерацию грамматически корректных форм слов
    для названий категорий, используя библиотеку pymorphy2.
    """
    def __init__(self):
        """
        Инициализирует морфологический анализатор.
        """
        self.morph = pymorphy2.MorphAnalyzer()

    def generate_dictionary(self, categories: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Создает словарь падежей для списка категорий.

        Args:
            categories (List[str]): Список названий категорий.

        Returns:
            Dict[str, Dict[str, str]]: Словарь в формате для linguistics.json.
        """
        dictionary = {}
        for category_name in categories:
            parsed_word = self.morph.parse(category_name)[0]

            try:
                nominative = parsed_word.inflect({'nomn'}).word
            except AttributeError:
                nominative = category_name

            try:
                genitive = parsed_word.inflect({'gent'}).word
            except AttributeError:
                genitive = category_name

            try:
                ablative = parsed_word.inflect({'ablt'}).word
            except AttributeError:
                ablative = category_name

            dictionary[category_name] = {
                "именительный": nominative,
                "родительный_ед": genitive,
                "творительный": ablative
            }
        return dictionary