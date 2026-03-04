# ============================================================================
# LLM BENCHMARK VIEWER - С СОРТИРОВКОЙ И ИЗМЕНЕНИЕМ ШИРИНЫ КОЛОНОК
# ============================================================================

import sys, json, os, re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from functools import partial

# --- GUI & Data ---
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QMessageBox, QDialog, QSplitter, QAbstractItemView, QHeaderView,
    QComboBox
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QFont, QColor, QBrush, QIcon

# --- Data Processing ---
import pandas as pd
import numpy as np
from scipy.stats import binomtest

# --- Matplotlib ---
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Wilson score interval."""
    if trials == 0:
        return (0.0, 0.0)
    phat = successes / trials
    z = 1.96
    denominator = 1 + z**2/trials
    centre_adj = phat + z**2/(2*trials)
    adj_std = np.sqrt((phat*(1-phat) + z**2/(4*trials))/trials)
    lower = max(0, (centre_adj - z * adj_std) / denominator)
    upper = min(1, (centre_adj + z * adj_std) / denominator)
    return (lower, upper)


def extract_thinking_length(llm_response: str, thinking_response: str) -> int:
    total_thinking = str(thinking_response)
    think_blocks = re.findall(r'<think>(.*?)</think>', str(llm_response), re.DOTALL | re.IGNORECASE)
    for block in think_blocks:
        total_thinking += block
    return len(total_thinking)


def extract_answer_length(llm_response: str) -> int:
    clean_answer = re.sub(r'<think>.*?</think>', '', str(llm_response), flags=re.DOTALL | re.IGNORECASE)
    return len(clean_answer.strip())


# ============================================================================
# SORTABLE TABLE WIDGET
# ============================================================================

class SortableTableWidget(QTableWidget):
    """Таблица с сортировкой по клику на заголовок и изменением ширины колонок."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sort_column = -1
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.data = []
        self.column_types = []  # 'text', 'number', 'percent'

        # Настройка header для изменения ширины
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Можно менять ширину
        header.setStretchLastSection(True)  # Последняя колонка растягивается
        header.setSectionsClickable(True)  # Клик по заголовку
        header.setHighlightSections(True)  # Подсветка активной колонки

        # Подключение сортировки
        header.sectionClicked.connect(self.on_header_clicked)

        # Стиль
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(False)  # Отключаем встроенную, используем свою

    def set_column_types(self, types: List[str]):
        """Устанавливает типы колонок для правильной сортировки."""
        self.column_types = types

    def on_header_clicked(self, logical_index: int):
        """Обработка клика по заголовку колонки."""
        if logical_index == self.sort_column:
            # Переключение направления
            self.sort_order = (
                Qt.SortOrder.DescendingOrder
                if self.sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            # Новая колонка - по умолчанию ascending
            self.sort_column = logical_index
            self.sort_order = Qt.SortOrder.AscendingOrder

        self._sort_table()
        self._update_header_icons()

    def _sort_table(self):
        """Сортировка данных таблицы."""
        if self.sort_column < 0 or self.sort_column >= self.columnCount():
            return

        if not self.data:
            return

        # Сортируем данные
        col_type = self.column_types[self.sort_column] if self.sort_column < len(self.column_types) else 'text'

        def get_sort_key(row_data):
            value = row_data[self.sort_column]
            if col_type == 'number':
                try:
                    return float(str(value).replace(',', '').replace(' ', '').replace(' мс', ''))
                except:
                    return 0
            elif col_type == 'percent':
                try:
                    return float(str(value).replace('%', ''))
                except:
                    return 0
            else:
                return str(value).lower()

        self.data.sort(key=get_sort_key, reverse=(self.sort_order == Qt.SortOrder.DescendingOrder))
        self._refresh_table()

    def _update_header_icons(self):
        """Обновление иконок сортировки в заголовке."""
        header = self.horizontalHeader()

        for i in range(self.columnCount()):
            item = self.horizontalHeaderItem(i)
            if item:
                text = item.text()
                # Удаляем старые иконки
                text = re.sub(r'\s*[▲▼]$', '', text)

                if i == self.sort_column:
                    icon = '▲' if self.sort_order == Qt.SortOrder.AscendingOrder else '▼'
                    text += f' {icon}'

                item.setText(text)

    def set_data(self, data: List[List[str]], headers: List[str], column_types: List[str] = None):
        """Установка данных в таблицу."""
        self.data = [row[:] for row in data]  # Копия данных
        self.column_types = column_types or ['text'] * len(headers)

        self.setRowCount(len(data))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        self._refresh_table()
        self._update_header_icons()

    def _refresh_table(self):
        """Обновление отображения таблицы."""
        self.setRowCount(len(self.data))

        for row, row_data in enumerate(self.data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))

                # Выравнивание для числовых колонок
                if col < len(self.column_types) and self.column_types[col] in ['number', 'percent']:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                self.setItem(row, col, item)

        self.resizeColumnsToContents()


# ============================================================================
# DATA MODEL
# ============================================================================

@dataclass
class TestResult:
    test_id: str
    model_name: str
    category: str
    is_correct: bool
    execution_time_ms: float
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    verification_details: Dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    llm_response: str = ""
    thinking_response: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TestResult":
        return cls(
            test_id=d.get("test_id", ""),
            model_name=d.get("model_name", "unknown"),
            category=d.get("category", "uncategorized"),
            is_correct=bool(d.get("is_correct", False)),
            execution_time_ms=float(d.get("execution_time_ms", 0.0)),
            performance_metrics=d.get("performance_metrics", {}),
            verification_details=d.get("verification_details", {}),
            prompt=d.get("prompt", ""),
            llm_response=d.get("llm_response", ""),
            thinking_response=d.get("thinking_response", "")
        )


# ============================================================================
# LEADERBOARD CALCULATOR
# ============================================================================

class LeaderboardCalculator:
    def __init__(self, df: pd.DataFrame, all_results: List[TestResult] = None):
        self.df = df.copy()
        self.all_results = all_results or []
        self.all_df = pd.DataFrame([
            {
                'model_name': r.model_name,
                'category': r.category,
                'is_correct': r.is_correct,
                'execution_time_ms': r.execution_time_ms,
                'llm_response': r.llm_response,
                'thinking_response': r.thinking_response
            }
            for r in self.all_results
        ]) if self.all_results else df.copy()

    def _calculate_verbosity(self, df: pd.DataFrame) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float, name='Verbosity_Index')

        df_work = df.copy()

        for col in ['llm_response', 'thinking_response']:
            if col not in df_work.columns:
                df_work[col] = ""

        df_work['llm_response'] = df_work['llm_response'].fillna("")
        df_work['thinking_response'] = df_work['thinking_response'].fillna("")

        df_work['thinking_len'] = df_work.apply(
            lambda row: extract_thinking_length(row['llm_response'], row['thinking_response']), axis=1
        )
        df_work['answer_len'] = df_work.apply(
            lambda row: extract_answer_length(row['llm_response']), axis=1
        )
        df_work['total_len'] = df_work['thinking_len'] + df_work['answer_len']

        model_stats = df_work.groupby('model_name')[['thinking_len', 'total_len']].sum()
        verbosity = pd.Series(0.0, index=model_stats.index, name='Verbosity_Index')

        for model in model_stats.index:
            total = model_stats.loc[model, 'total_len']
            if total > 0:
                verbosity[model] = model_stats.loc[model, 'thinking_len'] / total

        return verbosity

    def _calculate_comprehensiveness(self, df: pd.DataFrame) -> pd.Series:
        if 'category' not in df.columns or df['category'].nunique() == 0:
            return pd.Series(0.0, index=df['model_name'].unique(), name="Comprehensiveness")

        total_unique_categories = self.all_df['category'].nunique() if not self.all_df.empty else df['category'].nunique()
        all_models_coverage = self.all_df.groupby('model_name')['category'].nunique() if not self.all_df.empty else df.groupby('model_name')['category'].nunique()
        filtered_models = df['model_name'].unique()

        comprehensiveness_index = pd.Series(0.0, index=filtered_models, name="Comprehensiveness")

        for model in filtered_models:
            if model in all_models_coverage.index:
                comprehensiveness_index[model] = all_models_coverage[model] / total_unique_categories
            else:
                comprehensiveness_index[model] = 0.0

        return comprehensiveness_index

    def calculate(self) -> pd.DataFrame:
        if self.df.empty:
            return pd.DataFrame()

        metrics = self.df.groupby('model_name').agg(
            Successes=('is_correct', 'sum'),
            Total_Runs=('is_correct', 'count'),
            Avg_Time_ms=('execution_time_ms', 'mean')
        )

        verbosity = self._calculate_verbosity(self.df)
        comprehensiveness = self._calculate_comprehensiveness(self.df)

        metrics = metrics.join(verbosity, how='left').join(comprehensiveness, how='left')
        metrics['Verbosity_Index'] = metrics['Verbosity_Index'].fillna(0.0)
        metrics['Comprehensiveness'] = metrics['Comprehensiveness'].fillna(0.0)

        metrics['Accuracy'] = (metrics['Successes'] / metrics['Total_Runs']).fillna(0)
        metrics['Trust_Score'] = metrics.apply(
            lambda row: wilson_score_interval(int(row['Successes']), int(row['Total_Runs']))[0],
            axis=1
        )

        metrics.sort_values(by='Trust_Score', ascending=False, inplace=True)
        metrics.reset_index(inplace=True)
        metrics.insert(0, 'Rank', range(1, len(metrics) + 1))
        metrics.set_index('model_name', inplace=True)

        leaderboard_df = pd.DataFrame()
        leaderboard_df['Ранг'] = metrics['Rank']
        leaderboard_df['Модель'] = metrics.index
        leaderboard_df['Trust Score'] = metrics['Trust_Score'].map(lambda x: f"{x:.3f}")
        leaderboard_df['Accuracy'] = metrics['Accuracy'].map(lambda x: f"{x:.1%}")
        leaderboard_df['Coverage'] = metrics['Comprehensiveness'].map(lambda x: f"{x:.0%}")
        leaderboard_df['Verbosity'] = metrics['Verbosity_Index'].map(lambda x: f"{x:.1%}")
        leaderboard_df['Avg Time'] = metrics['Avg_Time_ms'].map(lambda x: f"{x:,.0f} мс")
        leaderboard_df['Runs'] = metrics['Total_Runs'].astype(int)

        leaderboard_df.set_index('Ранг', inplace=True)
        return leaderboard_df


# ============================================================================
# CATEGORY METRICS TABLE
# ============================================================================

class CategoryMetricsCalculator:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def calculate(self) -> pd.DataFrame:
        if self.df.empty:
            return pd.DataFrame()

        metrics = self.df.groupby(['model_name', 'category']).agg(
            Попыток=('is_correct', 'count'),
            Успешно=('is_correct', 'sum'),
            Avg_Time_ms=('execution_time_ms', 'mean')
        ).reset_index()

        metrics['Accuracy'] = (metrics['Успешно'] / metrics['Попыток']).fillna(0)
        metrics['Accuracy_str'] = metrics['Accuracy'].map(lambda x: f"{x:.0%}")

        return metrics


# ============================================================================
# MATPLOTLIB CANVAS
# ============================================================================

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        # Создаём оси заранее
        self.ax_time = fig.add_subplot(211)  # Гистограмма времени
        self.ax_accuracy = fig.add_subplot(212)  # Accuracy по категориям
        super(MplCanvas, self).__init__(fig)


# ============================================================================
# MAIN WINDOW
# ============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM Benchmark Viewer")
        self.resize(1600, 1000)

        self.all_results: List[TestResult] = []
        self.df: pd.DataFrame = pd.DataFrame()
        self.filtered_df: pd.DataFrame = pd.DataFrame()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)

        # Tabs
        self.tabs = QTabWidget()
        self._setup_tabs()
        main_layout.addWidget(self.tabs)

        self._connect_signals()

    def _create_toolbar(self) -> QHBoxLayout:
        toolbar = QHBoxLayout()

        self.filter_model = QLineEdit()
        self.filter_model.setPlaceholderText("Фильтр по модели...")
        self.filter_category = QComboBox()
        self.filter_category.addItem("Все категории")
        self.filter_category.setEditable(True)

        self.btn_load = QPushButton("📂 Загрузить папку")
        self.btn_compare = QPushButton("⚖️ Сравнить")
        self.btn_leaderboard = QPushButton("🏆 Лидерборд")
        self.btn_category_metrics = QPushButton("📊 По категориям")
        self.btn_export = QPushButton("💾 Экспорт CSV")
        self.btn_refresh_charts = QPushButton("🔄 Обновить графики")
        toolbar.addWidget(self.btn_refresh_charts)


        toolbar.addWidget(QLabel("Модель:"))
        toolbar.addWidget(self.filter_model, 1)
        toolbar.addWidget(QLabel("Категория:"))
        toolbar.addWidget(self.filter_category, 1)
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_category_metrics)
        toolbar.addWidget(self.btn_leaderboard)
        toolbar.addWidget(self.btn_compare)
        toolbar.addWidget(self.btn_export)

        return toolbar

    def _setup_tabs(self):
        # Tab 1: Таблица результатов (SORTABLE!)
        self.table_widget = SortableTableWidget()
        self.table_widget.set_column_types(['text', 'text', 'text', 'text', 'number', 'number'])
        self.tabs.addTab(self.table_widget, "📋 Все результаты")

        # Tab 2: Детальный просмотр
        self.detail_view = QWidget()
        detail_layout = QVBoxLayout(self.detail_view)

        detail_splitter = QSplitter(Qt.Orientation.Horizontal)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Поле", "Значение"])
        self.tree_widget.setColumnWidth(0, 200)
        tree_layout.addWidget(self.tree_widget)

        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)

        self.prompt_view = QTextEdit()
        self.prompt_view.setReadOnly(True)
        self.prompt_view.setPlaceholderText("Prompt будет отображен здесь")

        self.response_view = QTextEdit()
        self.response_view.setReadOnly(True)
        self.response_view.setPlaceholderText("Ответ LLM будет отображен здесь")

        text_layout.addWidget(QLabel("<b>Prompt:</b>"))
        text_layout.addWidget(self.prompt_view, 1)
        text_layout.addWidget(QLabel("<b>Ответ LLM:</b>"))
        text_layout.addWidget(self.response_view, 2)

        detail_splitter.addWidget(tree_container)
        detail_splitter.addWidget(text_container)
        detail_splitter.setStretchFactor(0, 1)
        detail_splitter.setStretchFactor(1, 2)

        detail_layout.addWidget(detail_splitter)
        self.tabs.addTab(self.detail_view, "🔍 Подробно")

        # Tab 3: Метрики по категориям (SORTABLE!)
        self.category_table = SortableTableWidget()
        self.category_table.set_column_types(['text', 'text', 'number', 'number', 'percent', 'number'])
        self.tabs.addTab(self.category_table, "📊 Метрики по категориям")

        # Tab 4: Графики
        self.chart_tab = QWidget()
        chart_layout = QVBoxLayout(self.chart_tab)
        self.canvas = MplCanvas(self)
        chart_layout.addWidget(self.canvas)
        self.tabs.addTab(self.chart_tab, "📈 Визуализация")

    def _connect_signals(self):
        self.btn_load.clicked.connect(self.load_folder)
        self.filter_model.textChanged.connect(self.apply_filters)
        self.filter_category.currentTextChanged.connect(self.apply_filters)
        self.btn_leaderboard.clicked.connect(self.show_leaderboard)
        self.btn_compare.clicked.connect(self.show_comparison)
        self.btn_category_metrics.clicked.connect(self.show_category_metrics)
        self.btn_export.clicked.connect(self.export_csv)
        self.table_widget.itemSelectionChanged.connect(self.on_row_selected)
        self.btn_refresh_charts.clicked.connect(lambda: self.update_charts() if self.tabs.currentIndex() == 3 else None)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int):
        """Авто-обновление графиков при переходе на вкладку."""
        if index == 3:  # Вкладка с графиками
            self.update_charts()

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с JSON-файлами")
        if not folder:
            return

        json_files = list(Path(folder).glob("*.json"))
        if not json_files:
            QMessageBox.warning(self, "Ошибка", "В папке нет JSON-файлов.")
            return

        self.all_results.clear()
        loaded_count = 0

        for f in json_files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        for item in data:
                            self.all_results.append(TestResult.from_dict(item))
                            loaded_count += 1
                    else:
                        self.all_results.append(TestResult.from_dict(data))
                        loaded_count += 1
            except Exception as e:
                print(f"Ошибка загрузки {f.name}: {e}")

        if self.all_results:
            self._build_dataframe()
            self._update_category_filter()
            self.apply_filters()
            QMessageBox.information(self, "Успех", f"Загружено {loaded_count} записей из {len(json_files)} файлов.")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить данные.")

    def _build_dataframe(self):
        records = [
            {
                'test_id': r.test_id,
                'model_name': r.model_name,
                'category': r.category,
                'is_correct': r.is_correct,
                'execution_time_ms': r.execution_time_ms,
                'llm_response': r.llm_response,
                'thinking_response': r.thinking_response,
                'prompt': r.prompt
            }
            for r in self.all_results
        ]
        self.df = pd.DataFrame(records)

    def _update_category_filter(self):
        self.filter_category.clear()
        self.filter_category.addItem("Все категории")
        if not self.df.empty:
            categories = sorted(self.df['category'].unique())
            self.filter_category.addItems(categories)

    def apply_filters(self):
        if self.df.empty:
            return

        mask = pd.Series([True] * len(self.df))
        model_filter = self.filter_model.text().strip()
        category_filter = self.filter_category.currentText().strip()

        if model_filter and category_filter != "Все категории":
            mask &= self.df['model_name'].str.contains(model_filter, case=False, na=False)
            mask &= self.df['category'] == category_filter
        elif model_filter:
            mask &= self.df['model_name'].str.contains(model_filter, case=False, na=False)
        elif category_filter and category_filter != "Все категории":
            mask &= self.df['category'] == category_filter

        self.filtered_df = self.df[mask].copy()
        self.update_table()

        if self.tabs.currentIndex() == 3:
            self.update_charts()

    def update_table(self):
        df = self.filtered_df if not self.filtered_df.empty else self.df

        headers = ["ID", "Модель", "Категория", "Результат", "Время (мс)", "Trust Score"]
        column_types = ['text', 'text', 'text', 'text', 'number', 'number']

        data = []
        for _, rec in df.iterrows():
            trust = wilson_score_interval(1 if rec['is_correct'] else 0, 1)[0]
            row = [
                rec['test_id'],
                rec['model_name'],
                rec['category'],
                "✅" if rec['is_correct'] else "❌",
                f"{rec['execution_time_ms']:.0f}",
                f"{trust:.3f}"
            ]
            data.append(row)

        self.table_widget.set_data(data, headers, column_types)

    def on_row_selected(self):
        selected_rows = self.table_widget.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        test_id = self.table_widget.item(row, 0).text()
        result = next((r for r in self.all_results if r.test_id == test_id), None)

        if not result:
            return

        self.tree_widget.clear()

        def add_to_tree(parent, key, value):
            if isinstance(value, dict):
                item = QTreeWidgetItem([str(key), "{...}"])
                for k, v in value.items():
                    add_to_tree(item, k, v)
                if parent is None:
                    self.tree_widget.addTopLevelItem(item)
                else:
                    parent.addChild(item)
            elif isinstance(value, list):
                item = QTreeWidgetItem([str(key), f"[{len(value)} items]"])
                if parent is None:
                    self.tree_widget.addTopLevelItem(item)
                else:
                    parent.addChild(item)
            else:
                val_str = str(value)
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                item = QTreeWidgetItem([str(key), val_str])
                if parent is None:
                    self.tree_widget.addTopLevelItem(item)
                else:
                    parent.addChild(item)
            return item

        root_data = {
            "Model": result.model_name,
            "Category": result.category,
            "Test ID": result.test_id,
            "Correct": result.is_correct,
            "Time (ms)": result.execution_time_ms,
            "Metrics": result.performance_metrics,
            "Verification": result.verification_details
        }

        for k, v in root_data.items():
            add_to_tree(None, k, v)

        self.tree_widget.expandAll()
        self.tree_widget.resizeColumnToContents(0)

        self.prompt_view.setPlainText(result.prompt[:5000] + ("..." if len(result.prompt) > 5000 else ""))
        self.response_view.setPlainText(result.llm_response[:5000] + ("..." if len(result.llm_response) > 5000 else ""))

    def show_leaderboard(self):
        if self.df.empty:
            QMessageBox.information(self, "Ошибка", "Нет данных для лидерборда.")
            return

        calc = LeaderboardCalculator(self.filtered_df if not self.filtered_df.empty else self.df, self.all_results)
        leaderboard_df = calc.calculate()

        if leaderboard_df.empty:
            QMessageBox.warning(self, "Ошибка", "Не удалось рассчитать лидерборд.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("🏆 Лидерборд моделей")
        dialog.resize(1000, 600)
        layout = QVBoxLayout(dialog)

        # Сортируемая таблица для лидерборда
        table = SortableTableWidget()
        table.set_column_types(['number', 'text', 'number', 'percent', 'percent', 'percent', 'number', 'number'])

        data = []
        for _, row in leaderboard_df.iterrows():
            data.append([str(v) for v in row])

        table.set_data(data, list(leaderboard_df.columns), table.column_types)
        table.setAlternatingRowColors(True)

        layout.addWidget(table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def show_category_metrics(self):
        if self.df.empty:
            QMessageBox.information(self, "Ошибка", "Нет данных для метрик по категориям.")
            return

        df = self.filtered_df if not self.filtered_df.empty else self.df
        calc = CategoryMetricsCalculator(df)
        metrics_df = calc.calculate()

        if metrics_df.empty:
            QMessageBox.warning(self, "Ошибка", "Не удалось рассчитать метрики.")
            return

        self.tabs.setCurrentIndex(2)

        headers = ["Модель", "Категория", "Попыток", "Успешно", "Accuracy", "Ср. время (мс)"]
        column_types = ['text', 'text', 'number', 'number', 'percent', 'number']

        data = []
        for _, rec in metrics_df.iterrows():
            row = [
                rec['model_name'],
                rec['category'],
                str(rec['Попыток']),
                str(rec['Успешно']),
                rec['Accuracy_str'],
                f"{rec['Avg_Time_ms']:.0f}"
            ]
            data.append(row)

        self.category_table.set_data(data, headers, column_types)

    def show_comparison(self):
        selected_items = self.table_widget.selectedItems()
        rows = set(item.row() for item in selected_items)

        if len(rows) < 2:
            QMessageBox.information(self, "Ошибка", "Выберите минимум 2 записи для сравнения.")
            return

        selected_rows = sorted(list(rows))[:4]
        results = []

        for r in selected_rows:
            test_id = self.table_widget.item(r, 0).text()
            res = next((x for x in self.all_results if x.test_id == test_id), None)
            if res:
                results.append(res)

        if len(results) < 2:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("⚖️ Сравнение записей")
        dialog.resize(1400, 900)
        layout = QHBoxLayout(dialog)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        for result in results:
            widget = QWidget()
            vlayout = QVBoxLayout(widget)

            header = QLabel(f"<h3>{result.model_name}</h3>")
            header.setStyleSheet("background-color: #e0e0e0; padding: 10px; border-radius: 5px;")
            vlayout.addWidget(header)

            info = QLabel(
                f"<b>Категория:</b> {result.category}<br>"
                f"<b>Результат:</b> {'✅ Correct' if result.is_correct else '❌ Incorrect'}<br>"
                f"<b>Время:</b> {result.execution_time_ms:.0f} мс"
            )
            vlayout.addWidget(info)

            vlayout.addWidget(QLabel("<b>Prompt:</b>"))
            prompt_edit = QTextEdit()
            prompt_edit.setReadOnly(True)
            prompt_edit.setPlainText(result.prompt[:2000] + ("..." if len(result.prompt) > 2000 else ""))
            prompt_edit.setMaximumHeight(200)
            vlayout.addWidget(prompt_edit)

            vlayout.addWidget(QLabel("<b>Ответ LLM:</b>"))
            response_edit = QTextEdit()
            response_edit.setReadOnly(True)
            response_edit.setPlainText(result.llm_response[:2000] + ("..." if len(result.llm_response) > 2000 else ""))
            vlayout.addWidget(response_edit)

            status_label = QLabel(f"{'✅ Correct' if result.is_correct else '❌ Incorrect'}")
            status_label.setStyleSheet(
                "color: green; font-weight: bold; font-size: 14px;" if result.is_correct
                else "color: red; font-weight: bold; font-size: 14px;"
            )
            vlayout.addWidget(status_label)

            splitter.addWidget(widget)

        layout.addWidget(splitter)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def update_charts(self):
        """Обновление графиков с правильной очисткой осей."""
        df = self.filtered_df if not self.filtered_df.empty else self.df

        if df.empty:
            return

        # Очищаем оси ПЕРЕД перерисовкой (не fig.clear()!)
        self.canvas.ax_time.clear()
        self.canvas.ax_accuracy.clear()

        # === График 1: Гистограмма времени ответа ===
        times = df['execution_time_ms'].dropna()
        if not times.empty:
            self.canvas.ax_time.hist(times, bins=30, alpha=0.7, color='steelblue', edgecolor='black')
            self.canvas.ax_time.set_title("📊 Распределение времени ответа", fontsize=12, fontweight='bold')
            self.canvas.ax_time.set_xlabel("Время (мс)")
            self.canvas.ax_time.set_ylabel("Количество запусков")
            self.canvas.ax_time.grid(True, alpha=0.3, linestyle='--')
            # Добавляем среднее и медиану линиями
            mean_val = times.mean()
            median_val = times.median()
            self.canvas.ax_time.axvline(mean_val, color='red', linestyle='--', label=f'Среднее: {mean_val:.0f} мс')
            self.canvas.ax_time.axvline(median_val, color='green', linestyle=':', label=f'Медиана: {median_val:.0f} мс')
            self.canvas.ax_time.legend(fontsize=8)

        # === График 2: Accuracy по категориям ===
        if 'category' in df.columns and df['category'].nunique() > 0:
            acc_by_cat = df.groupby('category')['is_correct'].mean().sort_values(ascending=True)
            if not acc_by_cat.empty:
                # Цветовая кодировка
                colors = ['#2ecc71' if x >= 0.9 else '#f39c12' if x >= 0.7 else '#e74c3c' for x in acc_by_cat]
                bars = self.canvas.ax_accuracy.barh(acc_by_cat.index, acc_by_cat.values, color=colors, alpha=0.8, edgecolor='black')
                self.canvas.ax_accuracy.set_title("🎯 Точность по категориям", fontsize=12, fontweight='bold')
                self.canvas.ax_accuracy.set_xlabel("Accuracy")
                self.canvas.ax_accuracy.set_xlim(0, 1.1)
                self.canvas.ax_accuracy.grid(True, axis='x', alpha=0.3, linestyle='--')

                # Добавляем значения на столбцы
                for i, (cat, acc) in enumerate(acc_by_cat.items()):
                    self.canvas.ax_accuracy.text(acc + 0.02, i, f'{acc:.0%}', va='center', fontsize=9, fontweight='bold')

                # Подпись оси Y, если категорий много
                if len(acc_by_cat) > 10:
                    self.canvas.ax_accuracy.tick_params(axis='y', labelsize=8)

        # Финальная компоновка и отрисовка
        self.canvas.figure.tight_layout(pad=3.0)
        self.canvas.draw()

    def export_csv(self):
        if self.df.empty:
            QMessageBox.information(self, "Ошибка", "Нет данных для экспорта.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт CSV", "benchmark_results.csv", "CSV Files (*.csv)"
        )

        if file_path:
            try:
                df = self.filtered_df if not self.filtered_df.empty else self.df
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "Успех", f"Данные экспортированы в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())