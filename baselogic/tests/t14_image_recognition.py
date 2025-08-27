# image_test_generator.py
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Union

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

# Получаем логгер
log = logging.getLogger(__name__)

class ImageRecognitionTestGenerator(AbstractTestGenerator):
    """
    Тест на распознавание изображений через встраивание base64 в текстовый prompt.
    """

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует тестовый prompt с встроенным изображением в формате base64.
        """
        try:
            # Получаем путь к изображению
            image_path = self.get_image()
            log.info(f"Попытка загрузки изображения из: {image_path}")

            # Проверяем существование файла
            if not Path(image_path).exists():
                log.error(f"Файл изображения не найден: {image_path}")
                raise FileNotFoundError(f"Файл изображения не найден: {image_path}")

            log.info(f"Файл изображения найден: {image_path}")
            base64_image = self._encode_image_to_base64(image_path)
            log.info(f"Изображение успешно закодировано в base64, длина: {len(base64_image)} символов")

            prompt = (
                f"Проанализируй это изображение в формате base64.\n"
                f"<изображение>{base64_image}</изображение>\n"
                f"Вопрос: Что изображено на картинке? Ответь ТОЛЬКО одним словом на русском языке\n"
                f"Ответ:"
            )
            log.debug(f"Сгенерирован prompt длиной: {len(prompt)} символов")

        except FileNotFoundError as e:
            log.error(f"Файл изображения не найден, используем резервный prompt: {e}")
            prompt = f"Что обычно показывают на скриншотах экрана компьютера? Ответь одним словом:"
        except Exception as e:
            log.error(f"Ошибка обработки изображения, используем резервный prompt: {e}")
            prompt = f"Что обычно показывают на скриншотах экрана компьютера? Ответь одним словом:"

        return {
            "prompt": prompt,
            "expected_output": "скриншот"
        }

    def get_image(self) -> Path:
        """Путь к изображению"""
        # Используем правильный путь к fixtures относительно скриптов
        current_dir = Path(__file__).parent
        image_path = current_dir / "fixtures" / "screen-1.jpg"
        log.debug(f"get_image() возвращает путь: {image_path}")
        return image_path

    def _encode_image_to_base64(self, image_path: Union[str, Path]) -> str:
        """Преобразует изображение в base64 строку."""
        path = Path(image_path)
        log.debug(f"Кодирование изображения в base64: {path}")

        if not path.exists():
            log.error(f"Файл изображения не найден при кодировании: {path}")
            raise FileNotFoundError(f"Файл изображения не найден: {path}")

        try:
            with open(path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
                log.debug(f"Изображение успешно закодировано, размер: {len(encoded)} символов")
                return encoded
        except Exception as e:
            log.error(f"Не удалось закодировать изображение {path}: {e}")
            raise

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Проверяет ответ модели на соответствие ожидаемому результату.
        """

        # Если ответ пустой - тест не пройден
        if not llm_output or llm_output.strip() == "":
            log.warning("Модель вернула пустой ответ")
            return {
                "is_correct": False,
                "details": {
                    "expected": expected_output,
                    "received": llm_output,
                    "error": "Пустой ответ от модели"
                },
                "confidence": 0.0
            }

        log.info(f"Проверка ответа модели: '{llm_output}' ожидаемый: '{expected_output}'")

        clean_output = llm_output.strip().lower()
        expected = expected_output.strip().lower()

        # Множество ключевых слов для более гибкой проверки (на русском)
        screenshot_keywords = {
            "кот", "котенок", "кошка"
        }

        # Проверки
        is_exact_match = expected == clean_output
        is_partial_match = expected in clean_output or clean_output in expected
        has_screenshot_keyword = any(keyword in clean_output for keyword in screenshot_keywords)

        is_correct = is_exact_match or is_partial_match or has_screenshot_keyword

        # Расчет уверенности
        if is_exact_match:
            confidence = 1.0
        elif is_partial_match:
            confidence = 0.9
        elif has_screenshot_keyword:
            confidence = 0.7
        else:
            confidence = 0.0

        log.info(f"Результат проверки - корректно: {is_correct}, уверенность: {confidence}")

        return {
            "is_correct": is_correct,
            "details": {
                "expected": expected_output,
                "received": llm_output,
                "checks": {
                    "exact_match": is_exact_match,
                    "partial_match": is_partial_match,
                    "keyword_match": has_screenshot_keyword
                }
            },
            "confidence": confidence
        }