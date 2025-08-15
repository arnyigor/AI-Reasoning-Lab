import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, Type
from ..tests.abstract_test_generator import AbstractTestGenerator

class PluginManager:
    """Управляет плагинами тестов"""
    
    def __init__(self, plugins_dir: Path = None):
        self.plugins_dir = plugins_dir or Path(__file__).parent.parent / "tests" / "plugins"
        self.plugins_dir.mkdir(exist_ok=True)
        self.loaded_plugins: Dict[str, Type[AbstractTestGenerator]] = {}
    
    def discover_plugins(self) -> Dict[str, Type[AbstractTestGenerator]]:
        """Обнаруживает все доступные плагины"""
        plugins = {}
        
        # Ищем файлы плагинов
        for plugin_file in self.plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                # Импортируем модуль
                module_name = f"baselogic.tests.plugins.{plugin_file.stem}"
                module = importlib.import_module(module_name)
                
                # Ищем классы, наследующие AbstractTestGenerator
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, AbstractTestGenerator) and 
                        obj != AbstractTestGenerator):
                        plugins[plugin_file.stem] = obj
                        
            except Exception as e:
                logging.warning(f"Не удалось загрузить плагин {plugin_file}: {e}")
        
        self.loaded_plugins = plugins
        return plugins
    
    def get_test_generator(self, test_name: str) -> Type[AbstractTestGenerator]:
        """Возвращает генератор теста по имени"""
        if test_name not in self.loaded_plugins:
            raise ValueError(f"Плагин {test_name} не найден")
        return self.loaded_plugins[test_name]