from typing import Dict, Any, List
import pandas as pd

class ReportFormatter:
    """Форматирует отчеты для лучшей читаемости"""
    
    @staticmethod
    def format_leaderboard_table(data: pd.DataFrame) -> str:
        """Форматирует таблицу лидеров с эмодзи и цветами"""
        formatted_data = data.copy()
        
        # Добавляем эмодзи для рангов
        formatted_data['Ранг'] = formatted_data['Score'].rank(ascending=False).astype(int)
        formatted_data['🏆'] = formatted_data['Ранг'].apply(
            lambda x: '🥇' if x == 1 else '🥈' if x == 2 else '🥉' if x == 3 else f'#{x}'
        )
        
        # Форматируем проценты
        formatted_data['Точность'] = formatted_data['Accuracy'].apply(
            lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
        )
        
        # Форматируем время
        formatted_data['Время'] = formatted_data['Avg_Time_ms'].apply(
            lambda x: f"{x/1000:.1f}с" if pd.notna(x) else "N/A"
        )
        
        # Создаем красивую таблицу
        table = formatted_data[['🏆', 'Модель', 'Точность', 'Время', 'Запусков']].to_string(
            index=False,
            justify='center'
        )
        
        return f"""
# 🏆 Таблица Лидеров

*Последнее обновление: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*

```
{table}
```

### Детальная статистика

{ReportFormatter._generate_detailed_stats(data)}
"""
    
    @staticmethod
    def _generate_detailed_stats(data: pd.DataFrame) -> str:
        """Генерирует детальную статистику"""
        stats = []
        
        # Лучшая модель
        best_model = data.loc[data['Score'].idxmax()]
        stats.append(f"**🏆 Лучшая модель:** {best_model['Модель']} (Score: {best_model['Score']:.3f})")
        
        # Средняя точность
        avg_accuracy = data['Accuracy'].mean()
        stats.append(f"**📊 Средняя точность:** {avg_accuracy:.1%}")
        
        # Количество протестированных моделей
        stats.append(f"**🔢 Протестировано моделей:** {len(data)}")
        
        return "\n".join(stats)