"""
Семантический анализатор для улучшенной системы валидации.

Предоставляет продвинутые возможности семантического анализа:
- Векторное сравнение ответов с использованием embeddings
- Извлечение и анализ ключевых концепций
- Оценка логической связности текста
- Анализ полноты и релевантности ответов
"""

from typing import Dict, Any, List, Tuple, Optional, Set
import re
import logging
from collections import Counter, defaultdict
import math

from ..tests.expert_calibration_dataset import TestType

log = logging.getLogger(__name__)


class SemanticSimilarityScorer:
    """
    Оценщик семантического сходства на основе векторных представлений.

    Использует различные подходы к сравнению текстов:
    - Косинусное сходство embeddings
    - Jaccard similarity для множеств слов
    - BM25 для релевантности
    """

    def __init__(self):
        self.embedder = None  # Будет инициализирован с sentence-transformers
        self.stop_words = self._load_stop_words()

    def _load_stop_words(self) -> Set[str]:
        """Загрузка стоп-слов для русского языка"""
        return {
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то',
            'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за',
            'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще',
            'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли',
            'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь',
            'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей',
            'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя',
            'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже',
            'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому',
            'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти',
            'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех',
            'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть',
            'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего',
            'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо',
            'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя',
            'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между'
        }

    def calculate_similarity(self, text1: str, text2: str) -> Dict[str, float]:
        """
        Вычислить семантическое сходство между двумя текстами.

        Returns:
            Dict с различными метриками сходства
        """
        # Предварительная обработка
        clean1 = self._preprocess_text(text1)
        clean2 = self._preprocess_text(text2)

        similarities = {}

        # 1. Jaccard similarity для множеств слов
        similarities['jaccard'] = self._jaccard_similarity(clean1, clean2)

        # 2. Cosine similarity для TF-IDF векторов
        similarities['cosine_tfidf'] = self._cosine_similarity_tfidf(clean1, clean2)

        # 3. BM25 similarity
        similarities['bm25'] = self._bm25_similarity(clean1, clean2)

        # 4. Combined similarity (взвешенная комбинация)
        similarities['combined'] = (
            similarities['jaccard'] * 0.2 +
            similarities['cosine_tfidf'] * 0.5 +
            similarities['bm25'] * 0.3
        )

        return similarities

    def _preprocess_text(self, text: str) -> List[str]:
        """Предварительная обработка текста"""
        # Приведение к нижнему регистру
        text = text.lower()

        # Удаление пунктуации
        text = re.sub(r'[^\w\s]', ' ', text)

        # Токенизация
        tokens = text.split()

        # Удаление стоп-слов и коротких слов
        tokens = [token for token in tokens
                 if token not in self.stop_words and len(token) > 2]

        return tokens

    def _jaccard_similarity(self, tokens1: List[str], tokens2: List[str]) -> float:
        """Jaccard similarity для множеств слов"""
        set1 = set(tokens1)
        set2 = set(tokens2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _cosine_similarity_tfidf(self, tokens1: List[str], tokens2: List[str]) -> float:
        """Cosine similarity для TF-IDF векторов"""
        # Создание словаря всех слов
        all_words = list(set(tokens1 + tokens2))

        # Вычисление TF для каждого документа
        tf1 = Counter(tokens1)
        tf2 = Counter(tokens2)

        # Вычисление IDF
        idf = {}
        for word in all_words:
            df = (1 if word in tf1 else 0) + (1 if word in tf2 else 0)
            idf[word] = math.log(2 / df) if df > 0 else 0

        # Создание TF-IDF векторов
        vector1 = [tf1.get(word, 0) * idf[word] for word in all_words]
        vector2 = [tf2.get(word, 0) * idf[word] for word in all_words]

        return self._cosine_similarity(vector1, vector2)

    def _cosine_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """Вычисление косинусного сходства"""
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        norm1 = math.sqrt(sum(a * a for a in vector1))
        norm2 = math.sqrt(sum(b * b for b in vector2))

        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

    def _bm25_similarity(self, tokens1: List[str], tokens2: List[str]) -> float:
        """BM25 similarity"""
        # Упрощенная реализация BM25
        query = tokens1
        document = tokens2

        k1 = 1.5  # параметр насыщения
        b = 0.75  # параметр нормализации длины

        # Статистики документа
        doc_len = len(document)
        avg_doc_len = (len(tokens1) + len(tokens2)) / 2

        score = 0
        doc_freq = Counter(document)

        for term in query:
            if term in doc_freq:
                tf = doc_freq[term]
                idf = math.log(2 / 1)  # упрощение для двух документов

                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * doc_len / avg_doc_len)

                score += idf * numerator / denominator

        # Нормализация
        max_possible_score = len(query) * math.log(2)
        return score / max_possible_score if max_possible_score > 0 else 0.0


class ConceptExtractor:
    """
    Извлекатель ключевых концепций из текста.

    Использует различные подходы:
    - TF-IDF для важных терминов
    - Синтаксический анализ для именных групп
    - Статистические методы для ключевых слов
    """

    def __init__(self):
        self.tfidf_vectorizer = None
        self.nlp_model = None  # spaCy или Natasha

    def extract_concepts(self, text: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Извлечь ключевые концепции из текста.

        Returns:
            List of (concept, score) tuples
        """
        # Предварительная обработка
        tokens = self._preprocess_text(text)

        # 1. TF-IDF based extraction
        tfidf_concepts = self._extract_tfidf_concepts(tokens, top_n)

        # 2. Statistical extraction (word frequency + position)
        statistical_concepts = self._extract_statistical_concepts(tokens, top_n)

        # 3. Syntactic extraction (noun phrases)
        syntactic_concepts = self._extract_syntactic_concepts(text, top_n)

        # Комбинирование результатов
        combined_concepts = self._combine_concept_scores(
            tfidf_concepts, statistical_concepts, syntactic_concepts
        )

        return combined_concepts[:top_n]

    def _preprocess_text(self, text: str) -> List[str]:
        """Предварительная обработка текста"""
        # Приведение к нижнему регистру
        text = text.lower()

        # Удаление пунктуации
        text = re.sub(r'[^\w\s]', ' ', text)

        # Токенизация
        tokens = text.split()

        # Фильтрация
        stop_words = {'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а'}
        tokens = [token for token in tokens
                 if token not in stop_words and len(token) > 2]

        return tokens

    def _extract_tfidf_concepts(self, tokens: List[str], top_n: int) -> List[Tuple[str, float]]:
        """Извлечение концепций на основе TF-IDF"""
        if len(tokens) < 2:
            return []

        # Простая TF-IDF реализация
        word_freq = Counter(tokens)
        total_words = len(tokens)

        # Для простоты используем только TF (поскольку у нас один документ)
        concepts = [(word, freq / total_words) for word, freq in word_freq.most_common(top_n)]

        return concepts

    def _extract_statistical_concepts(self, tokens: List[str], top_n: int) -> List[Tuple[str, float]]:
        """Статистическое извлечение концепций"""
        word_freq = Counter(tokens)
        total_words = len(tokens)

        concepts = []
        for word, freq in word_freq.most_common(top_n):
            # Учет позиции слова (слова в начале более важны)
            position_bonus = 1.0
            if word in tokens[:10]:  # первые 10 слов
                position_bonus = 1.2

            score = (freq / total_words) * position_bonus
            concepts.append((word, score))

        return concepts

    def _extract_syntactic_concepts(self, text: str, top_n: int) -> List[Tuple[str, float]]:
        """Синтаксическое извлечение концепций (именньх групп)"""
        # Заглушка - будет реализована с spaCy/Natasha
        # Пока возвращаем простые существительные
        tokens = self._preprocess_text(text)

        # Простая эвристика: слова длиннее 5 символов считаем концепциями
        concepts = [(word, 1.0) for word in tokens if len(word) > 5]
        concepts = list(set(concepts))  # удаление дубликатов

        return concepts[:top_n]

    def _combine_concept_scores(self, *concept_lists) -> List[Tuple[str, float]]:
        """Комбинирование оценок из разных методов"""
        combined_scores = defaultdict(float)

        for concept_list in concept_lists:
            for concept, score in concept_list:
                combined_scores[concept] += score

        # Сортировка по комбинированной оценке
        sorted_concepts = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_concepts


class LogicalCoherenceAnalyzer:
    """
    Анализатор логической связности текста.

    Оценивает:
    - Наличие логических связок
    - Последовательность аргументации
    - Структуру рассуждений
    """

    def __init__(self):
        self.logical_connectors = {
            'causal': ['потому что', 'поэтому', 'следовательно', 'вызывает', 'приводит к'],
            'temporal': ['сначала', 'затем', 'после', 'перед', 'во время'],
            'contrastive': ['однако', 'но', 'несмотря на', 'в то время как', 'напротив'],
            'additive': ['кроме того', 'также', 'более того', 'вдобавок', 'еще'],
            'explanatory': ['то есть', 'иными словами', 'например', 'в частности']
        }

    def analyze_coherence(self, text: str) -> Dict[str, float]:
        """
        Анализ логической связности текста.

        Returns:
            Dict с метриками связности
        """
        # Предварительная обработка
        clean_text = text.lower()

        coherence_scores = {}

        # 1. Плотность логических связок
        coherence_scores['connector_density'] = self._calculate_connector_density(clean_text)

        # 2. Разнообразие связок
        coherence_scores['connector_diversity'] = self._calculate_connector_diversity(clean_text)

        # 3. Структурная связность
        coherence_scores['structural_coherence'] = self._analyze_structural_coherence(clean_text)

        # 4. Аргументативная последовательность
        coherence_scores['argumentative_flow'] = self._analyze_argumentative_flow(clean_text)

        # 5. Общая оценка связности
        coherence_scores['overall_coherence'] = (
            coherence_scores['connector_density'] * 0.3 +
            coherence_scores['connector_diversity'] * 0.2 +
            coherence_scores['structural_coherence'] * 0.3 +
            coherence_scores['argumentative_flow'] * 0.2
        )

        return coherence_scores

    def _calculate_connector_density(self, text: str) -> float:
        """Расчет плотности логических связок"""
        words = text.split()
        total_words = len(words)

        if total_words == 0:
            return 0.0

        connector_count = 0
        for connector_type, connectors in self.logical_connectors.items():
            for connector in connectors:
                connector_count += text.count(connector)

        return connector_count / total_words

    def _calculate_connector_diversity(self, text: str) -> float:
        """Расчет разнообразия логических связок"""
        used_connector_types = set()

        for connector_type, connectors in self.logical_connectors.items():
            for connector in connectors:
                if connector in text:
                    used_connector_types.add(connector_type)
                    break

        return len(used_connector_types) / len(self.logical_connectors)

    def _analyze_structural_coherence(self, text: str) -> float:
        """Анализ структурной связности"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 2:
            return 0.5

        # Анализ переходов между предложениями
        transition_score = 0
        for i in range(len(sentences) - 1):
            current_sentence = sentences[i].lower()
            next_sentence = sentences[i + 1].lower()

            # Проверка наличия связок между предложениями
            has_transition = any(
                connector in current_sentence or connector in next_sentence
                for connectors in self.logical_connectors.values()
                for connector in connectors
            )

            if has_transition:
                transition_score += 1

        return transition_score / (len(sentences) - 1)

    def _analyze_argumentative_flow(self, text: str) -> float:
        """Анализ аргументативной последовательности"""
        # Простая эвристика: наличие последовательности слов
        flow_indicators = [
            'во-первых', 'во-вторых', 'в-третьих', 'итак', 'таким образом',
            'следовательно', 'в заключение', 'наконец'
        ]

        found_indicators = sum(1 for indicator in flow_indicators if indicator in text.lower())

        return min(found_indicators / 3, 1.0)  # нормировка


class CompletenessAnalyzer:
    """
    Анализатор полноты ответа.

    Оценивает:
    - Покрытие требуемых аспектов
    - Глубину анализа
    - Наличие примеров и объяснений
    """

    def __init__(self):
        self.completeness_indicators = {
            'examples': ['например', 'пример', 'скажем', 'допустим', 'предположим'],
            'explanations': ['потому что', 'поскольку', 'объясняется', 'заключается в'],
            'analysis': ['анализируя', 'рассматривая', 'исследуя', 'изучая'],
            'conclusions': ['следовательно', 'таким образом', 'в итоге', 'в заключение']
        }

    def analyze_completeness(self, response: str, reference: Dict[str, Any], test_type: TestType) -> Dict[str, float]:
        """
        Анализ полноты ответа относительно требований.
        """
        completeness_scores = {}

        # 1. Покрытие ключевых аспектов
        completeness_scores['aspect_coverage'] = self._calculate_aspect_coverage(response, reference, test_type)

        # 2. Глубина анализа
        completeness_scores['depth_score'] = self._calculate_depth_score(response)

        # 3. Качество объяснений
        completeness_scores['explanation_quality'] = self._calculate_explanation_quality(response)

        # 4. Структурная полнота
        completeness_scores['structural_completeness'] = self._calculate_structural_completeness(response)

        # 5. Общая оценка полноты
        completeness_scores['overall_completeness'] = (
            completeness_scores['aspect_coverage'] * 0.4 +
            completeness_scores['depth_score'] * 0.3 +
            completeness_scores['explanation_quality'] * 0.2 +
            completeness_scores['structural_completeness'] * 0.1
        )

        return completeness_scores

    def _calculate_aspect_coverage(self, response: str, reference: Dict[str, Any], test_type: TestType) -> float:
        """Расчет покрытия ключевых аспектов"""
        if test_type == TestType.MULTI_HOP_REASONING:
            key_steps = reference.get('key_steps', [])
            covered_steps = sum(1 for step in key_steps if step.lower() in response.lower())
            return covered_steps / len(key_steps) if key_steps else 0.0

        elif test_type == TestType.CONSTRAINED_OPTIMIZATION:
            constraints = reference.get('expected_considerations', [])
            covered_constraints = sum(1 for constraint in constraints
                                    if any(word in response.lower() for word in constraint.lower().split()))
            return covered_constraints / len(constraints) if constraints else 0.0

        # Для других типов тестов
        return 0.5

    def _calculate_depth_score(self, response: str) -> float:
        """Оценка глубины анализа"""
        depth_indicators = [
            'подробно', 'детально', 'глубоко', 'всесторонне',
            'комплексно', 'многоаспектно', 'многогранно'
        ]

        found_indicators = sum(1 for indicator in depth_indicators if indicator in response.lower())

        # Учет длины ответа как индикатора глубины
        length_score = min(len(response.split()) / 100, 1.0)

        return min((found_indicators + length_score) / 2, 1.0)

    def _calculate_explanation_quality(self, response: str) -> float:
        """Оценка качества объяснений"""
        explanation_score = 0

        for category, indicators in self.completeness_indicators.items():
            found_indicators = sum(1 for indicator in indicators if indicator in response.lower())
            explanation_score += min(found_indicators / 2, 1.0)  # нормировка для каждой категории

        return explanation_score / len(self.completeness_indicators)

    def _calculate_structural_completeness(self, response: str) -> float:
        """Оценка структурной полноты"""
        # Проверка наличия введения, основной части и заключения
        has_introduction = any(word in response.lower() for word in ['рассмотрим', 'анализируем', 'изучим'])
        has_conclusion = any(word in response.lower() for word in ['итог', 'вывод', 'заключение', 'таким образом'])

        structural_score = (has_introduction + has_conclusion) / 2

        return structural_score


class EnhancedSemanticAnalyzer:
    """
    Улучшенный семантический анализатор.

    Интегрирует все компоненты семантического анализа для комплексной оценки.
    """

    def __init__(self):
        self.similarity_scorer = SemanticSimilarityScorer()
        self.concept_extractor = ConceptExtractor()
        self.coherence_analyzer = LogicalCoherenceAnalyzer()
        self.completeness_analyzer = CompletenessAnalyzer()

    def analyze(self, response: str, reference: Dict[str, Any], test_type: TestType) -> Dict[str, Any]:
        """
        Комплексный семантический анализ ответа.

        Returns:
            Dict с результатами всех видов анализа
        """
        analysis_results = {}

        # 1. Семантическое сходство
        if 'expected_answer' in reference:
            analysis_results['similarity'] = self.similarity_scorer.calculate_similarity(
                response, reference['expected_answer']
            )

        # 2. Извлечение концепций
        analysis_results['concepts'] = self.concept_extractor.extract_concepts(response, top_n=5)

        # 3. Логическая связность
        analysis_results['coherence'] = self.coherence_analyzer.analyze_coherence(response)

        # 4. Полнота ответа
        analysis_results['completeness'] = self.completeness_analyzer.analyze_completeness(
            response, reference, test_type
        )

        # 5. Интегральные метрики
        analysis_results['integrated_scores'] = self._calculate_integrated_scores(analysis_results)

        return analysis_results

    def _calculate_integrated_scores(self, analysis_results: Dict[str, Any]) -> Dict[str, float]:
        """Расчет интегральных оценок"""
        integrated = {}

        # Семантическая оценка (основана на сходстве)
        similarity = analysis_results.get('similarity', {})
        integrated['semantic_score'] = similarity.get('combined', 0.5)

        # Оценка концептуального покрытия
        concepts = analysis_results.get('concepts', [])
        integrated['concept_coverage'] = len(concepts) / 5 if concepts else 0.0

        # Оценка логической связности
        coherence = analysis_results.get('coherence', {})
        integrated['logical_coherence'] = coherence.get('overall_coherence', 0.5)

        # Оценка полноты
        completeness = analysis_results.get('completeness', {})
        integrated['semantic_completeness'] = completeness.get('overall_completeness', 0.5)

        # Общая семантическая оценка
        integrated['overall_semantic_score'] = (
            integrated['semantic_score'] * 0.4 +
            integrated['concept_coverage'] * 0.2 +
            integrated['logical_coherence'] * 0.2 +
            integrated['semantic_completeness'] * 0.2
        )

        return integrated

    def get_analysis_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Генерация текстового summary анализа"""
        integrated = analysis_results.get('integrated_scores', {})

        summary_parts = []

        semantic_score = integrated.get('semantic_score', 0.5)
        if semantic_score > 0.8:
            summary_parts.append("Высокое семантическое сходство с ожидаемым ответом")
        elif semantic_score > 0.6:
            summary_parts.append("Умеренное семантическое сходство")
        else:
            summary_parts.append("Низкое семантическое сходство")

        coherence_score = integrated.get('logical_coherence', 0.5)
        if coherence_score > 0.7:
            summary_parts.append("Хорошая логическая связность")
        elif coherence_score > 0.4:
            summary_parts.append("Приемлемая логическая связность")
        else:
            summary_parts.append("Слабая логическая связность")

        completeness_score = integrated.get('semantic_completeness', 0.5)
        if completeness_score > 0.7:
            summary_parts.append("Высокая полнота ответа")
        elif completeness_score > 0.4:
            summary_parts.append("Достаточная полнота ответа")
        else:
            summary_parts.append("Недостаточная полнота ответа")

        return ". ".join(summary_parts)


# Глобальный экземпляр семантического анализатора
semantic_analyzer = EnhancedSemanticAnalyzer()


if __name__ == "__main__":
    # Тестирование семантического анализатора
    test_response = """
    Повышение процентной ставки ЦБ на 2% повлияет на ВВП через цепную реакцию,
    начинающуюся с уменьшения инвестиций в новые проекты. Увеличение стоимости
    кредитов для бизнеса приводит к снижению инвестиционной активности.
    """

    test_reference = {
        'expected_answer': 'замедление роста ВВП',
        'key_steps': ['снижение инвестиций', 'замедление роста', 'рост безработицы']
    }

    analyzer = EnhancedSemanticAnalyzer()
    results = analyzer.analyze(test_response, test_reference, TestType.MULTI_HOP_REASONING)

    print("=== Результаты семантического анализа ===")
    print(f"Семантическое сходство: {results['integrated_scores']['semantic_score']:.3f}")
    print(f"Логическая связность: {results['integrated_scores']['logical_coherence']:.3f}")
    print(f"Полнота ответа: {results['integrated_scores']['semantic_completeness']:.3f}")
    print(f"Общая оценка: {results['integrated_scores']['overall_semantic_score']:.3f}")
    print(f"Summary: {analyzer.get_analysis_summary(results)}")