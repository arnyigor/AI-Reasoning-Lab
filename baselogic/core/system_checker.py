import platform
import subprocess
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import psutil

# Безопасный импорт библиотек для работы с GPU
NVML_AVAILABLE = False
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except ImportError:
    pass
except Exception as e:
    logging.warning(f"pynvml доступен, но инициализация не удалась: {e}")

GPUTIL_AVAILABLE = False
try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    pass

log = logging.getLogger(__name__)

class SystemProfiler:
    """
    Универсальный сборщик информации о системе с поддержкой Windows, macOS и Linux.
    """

    def __init__(self):
        self.system_info = {}
        self.platform = platform.system()

    def get_system_info(self) -> Dict[str, Any]:
        """Собирает полную информацию о системе безопасно."""
        info = {}

        try:
            # Базовая информация об ОС
            info['os'] = self._get_os_info()

            # Процессор
            info['cpu'] = self._get_cpu_info()

            # Память
            info['memory'] = self._get_memory_info()

            # GPU информация
            info['gpus'] = self._get_gpu_info()

            # Платформо-специфичные детали
            if self.platform == 'Darwin':
                info['macos_details'] = self._get_macos_system_details()
            elif self.platform == 'Windows':
                info['windows_details'] = self._get_windows_system_details()
            elif self.platform == 'Linux':
                info['linux_details'] = self._get_linux_system_details()

            # Дополнительная системная информация
            info['system'] = self._get_additional_system_info()

            # Версии критических библиотек (БЕЗОПАСНО)
            info['environment'] = self._get_environment_info_safe()

        except Exception as e:
            log.error(f"Ошибка при сборе системной информации: {e}")
            info['error'] = str(e)

        return info

    def _get_os_info(self) -> Dict[str, str]:
        """Информация об операционной системе."""
        try:
            info = {
                'platform': self.platform,
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'hostname': platform.node(),
                'processor': platform.processor(),
                'python_executable': sys.executable
            }

            # Дополнительная информация для Windows
            if self.platform == 'Windows':
                try:
                    info['windows_edition'] = platform.win32_edition()
                    info['windows_version'] = platform.win32_ver()
                except:
                    pass

            return info
        except Exception as e:
            log.warning(f"Ошибка получения информации об ОС: {e}")
            return {'error': str(e)}

    def _get_cpu_info(self) -> Dict[str, Any]:
        """Подробная информация о процессоре с учетом ОС."""
        try:
            info = {
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'processor_name': platform.processor()
            }

            # Безопасное получение частоты
            try:
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    info['max_frequency_mhz'] = cpu_freq.max
                    info['current_frequency_mhz'] = cpu_freq.current
            except:
                info['frequency'] = 'unavailable'

            # Дополнительная информация по платформам
            if self.platform == 'Linux':
                info.update(self._get_linux_cpu_info())
            elif self.platform == 'Darwin':
                info.update(self._get_macos_cpu_info())
            elif self.platform == 'Windows':
                info.update(self._get_windows_cpu_info())

            return info
        except Exception as e:
            log.warning(f"Ошибка получения информации о CPU: {e}")
            return {'error': str(e)}

    def _get_linux_cpu_info(self) -> Dict[str, Any]:
        """Дополнительная информация о CPU для Linux."""
        info = {}
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()

            for line in cpuinfo.split('\n'):
                if 'model name' in line:
                    info['model_name'] = line.split(':')[1].strip()
                    break
                elif 'cpu family' in line:
                    info['cpu_family'] = line.split(':')[1].strip()
                elif 'cpu MHz' in line:
                    info['cpu_mhz'] = float(line.split(':')[1].strip())
        except:
            pass
        return info

    def _get_macos_cpu_info(self) -> Dict[str, Any]:
        """Дополнительная информация о CPU для macOS."""
        info = {}
        try:
            # Реальная архитектура
            result = subprocess.run(['uname', '-m'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['real_architecture'] = result.stdout.strip()

            # Информация о чипе через sysctl
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info['cpu_brand'] = result.stdout.strip()

            # Частота CPU
            result = subprocess.run(['sysctl', '-n', 'hw.cpufrequency'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                try:
                    info['cpu_frequency_hz'] = int(result.stdout.strip())
                except:
                    pass
        except Exception as e:
            log.warning(f"Ошибка получения macOS CPU информации: {e}")
        return info

    def _get_windows_cpu_info(self) -> Dict[str, Any]:
        """Дополнительная информация о CPU для Windows."""
        info = {}
        try:
            # Используем wmic для получения детальной информации
            result = subprocess.run(['wmic', 'cpu', 'get', 'name', '/format:value'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Name='):
                        info['cpu_model'] = line.split('=')[1].strip()
                        break
        except Exception as e:
            log.warning(f"Ошибка получения Windows CPU информации: {e}")
        return info

    def _get_memory_info(self) -> Dict[str, Any]:
        """Информация о памяти."""
        try:
            mem = psutil.virtual_memory()

            info = {
                'total_ram_gb': round(mem.total / (1024**3), 2),
                'available_ram_gb': round(mem.available / (1024**3), 2),
                'used_ram_gb': round(mem.used / (1024**3), 2),
                'ram_percentage': round(mem.percent, 1)
            }

            # Безопасное получение информации о swap
            try:
                swap = psutil.swap_memory()
                info['total_swap_gb'] = round(swap.total / (1024**3), 2) if swap.total > 0 else 0
                info['swap_percentage'] = round(swap.percent, 1) if swap.total > 0 else 0
            except:
                info['swap_info'] = 'unavailable'

            return info
        except Exception as e:
            log.warning(f"Ошибка получения информации о памяти: {e}")
            return {'error': str(e)}

    def _get_gpu_info(self) -> List[Dict[str, Any]]:
        """Комплексная информация о GPU для всех платформ."""
        gpus = []

        # NVIDIA GPU через pynvml
        try:
            nvidia_gpus = self._get_nvidia_gpu_info()
            if nvidia_gpus:
                gpus.extend(nvidia_gpus)
        except Exception as e:
            log.warning(f"Ошибка получения NVIDIA GPU информации: {e}")

        # AMD GPU
        try:
            amd_gpus = self._get_amd_gpu_info()
            if amd_gpus:
                gpus.extend(amd_gpus)
        except Exception as e:
            log.warning(f"Ошибка получения AMD GPU информации: {e}")

        # Intel GPU
        try:
            intel_gpus = self._get_intel_gpu_info()
            if intel_gpus:
                gpus.extend(intel_gpus)
        except Exception as e:
            log.warning(f"Ошибка получения Intel GPU информации: {e}")

        # Apple Silicon GPU
        try:
            apple_gpu = self._get_apple_gpu_info()
            if apple_gpu:
                gpus.append(apple_gpu)
        except Exception as e:
            log.warning(f"Ошибка получения Apple GPU информации: {e}")

        # Windows integrated GPU через wmic
        if self.platform == 'Windows' and not gpus:
            try:
                windows_gpus = self._get_windows_gpu_info()
                if windows_gpus:
                    gpus.extend(windows_gpus)
            except Exception as e:
                log.warning(f"Ошибка получения Windows GPU информации: {e}")

        return gpus

    def _get_nvidia_gpu_info(self) -> List[Dict[str, Any]]:
        """Информация о NVIDIA GPU."""
        if not NVML_AVAILABLE:
            return []

        try:
            gpus = []
            count = pynvml.nvmlDeviceGetCount()

            for idx in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')

                # Память
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_memory_gb = round(mem_info.total / (1024**3), 2)

                gpu_info = {
                    'vendor': 'NVIDIA',
                    'name': name,
                    'index': idx,
                    'memory_total_gb': total_memory_gb,
                    'memory_used_gb': round(mem_info.used / (1024**3), 2),
                    'memory_free_gb': round(mem_info.free / (1024**3), 2),
                    'type': 'discrete'
                }

                # Дополнительная информация
                try:
                    driver_version = pynvml.nvmlSystemGetDriverVersion()
                    if isinstance(driver_version, bytes):
                        driver_version = driver_version.decode('utf-8')
                    gpu_info['driver_version'] = driver_version
                except:
                    gpu_info['driver_version'] = 'unknown'

                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    gpu_info['temperature_c'] = temp
                except:
                    pass

                gpus.append(gpu_info)

            pynvml.nvmlShutdown()
            return gpus

        except Exception as e:
            log.warning(f"Ошибка получения информации о NVIDIA GPU: {e}")
            return []

    def _get_amd_gpu_info(self) -> List[Dict[str, Any]]:
        """Информация о AMD GPU через rocm-smi."""
        try:
            result = subprocess.run(['rocm-smi', '--showid', '--showmeminfo', 'vram', '--json'],
                                    capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                gpus = []

                for gpu_id, gpu_data in data.items():
                    if gpu_id.startswith('card'):
                        gpu_info = {
                            'vendor': 'AMD',
                            'name': gpu_data.get('Card series', 'Unknown AMD GPU'),
                            'index': int(gpu_id.replace('card', '')),
                            'memory_total_gb': round(int(gpu_data.get('VRAM Total Memory (B)', 0)) / (1024**3), 2),
                            'memory_used_gb': round(int(gpu_data.get('VRAM Total Used Memory (B)', 0)) / (1024**3), 2),
                            'type': 'discrete'
                        }
                        gpus.append(gpu_info)

                return gpus
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            pass

        return []

    def _get_intel_gpu_info(self) -> List[Dict[str, Any]]:
        """Информация о Intel GPU."""
        gpus = []

        # Linux: intel_gpu_top
        if self.platform == 'Linux':
            try:
                result = subprocess.run(['intel_gpu_top', '-l'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and 'Intel' in result.stdout:
                    gpus.append({
                        'vendor': 'Intel',
                        'name': 'Intel Integrated Graphics',
                        'index': 0,
                        'type': 'integrated'
                    })
            except:
                pass

        # Windows: DirectX через dxdiag (если доступно)
        elif self.platform == 'Windows':
            try:
                # Проверяем через wmic наличие Intel GPU
                result = subprocess.run(['wmic', 'path', 'win32_videocontroller', 'get', 'name'],
                                        capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Intel' in line and 'Graphics' in line:
                            gpus.append({
                                'vendor': 'Intel',
                                'name': line.strip(),
                                'index': len(gpus),
                                'type': 'integrated'
                            })
                            break
            except:
                pass

        return gpus

    def _get_apple_gpu_info(self) -> Optional[Dict[str, Any]]:
        """Информация о Apple Silicon GPU."""
        if self.platform != 'Darwin':
            return None

        try:
            # Определяем чип Apple
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                    capture_output=True, text=True, timeout=5)

            if 'Apple' in result.stdout:
                chip_name = result.stdout.strip()

                # Получаем информацию о памяти (unified memory)
                try:
                    mem_result = subprocess.run(['sysctl', '-n', 'hw.memsize'],
                                                capture_output=True, text=True, timeout=5)
                    total_memory = int(mem_result.stdout.strip()) if mem_result.returncode == 0 else 0
                except:
                    total_memory = 0

                return {
                    'vendor': 'Apple',
                    'name': f'{chip_name} GPU',
                    'index': 0,
                    'type': 'unified_memory',
                    'memory_total_gb': round(total_memory / (1024**3), 2),
                    'chip': chip_name,
                    'architecture': 'apple_silicon'
                }
        except Exception as e:
            log.warning(f"Ошибка получения Apple GPU информации: {e}")

        return None

    def _get_windows_gpu_info(self) -> List[Dict[str, Any]]:
        """Информация о GPU для Windows через wmic."""
        gpus = []
        try:
            result = subprocess.run([
                'wmic', 'path', 'win32_videocontroller', 'get',
                'name,adapterram,driverversion', '/format:csv'
            ], capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                lines = result.stdout.split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip() and ',' in line:
                        parts = line.split(',')
                        if len(parts) >= 4:
                            try:
                                name = parts[2].strip() if len(parts) > 2 else 'Unknown GPU'
                                ram_bytes = int(parts[1]) if parts[1].strip().isdigit() else 0
                                driver_version = parts[3].strip() if len(parts) > 3 else 'Unknown'

                                if name and name != 'Name':
                                    gpu_info = {
                                        'vendor': self._detect_gpu_vendor(name),
                                        'name': name,
                                        'index': len(gpus),
                                        'driver_version': driver_version,
                                        'type': 'discrete' if ram_bytes > 1024*1024*1024 else 'integrated'
                                    }

                                    if ram_bytes > 0:
                                        gpu_info['memory_total_gb'] = round(ram_bytes / (1024**3), 2)

                                    gpus.append(gpu_info)
                            except (ValueError, IndexError):
                                continue
        except Exception as e:
            log.warning(f"Ошибка получения Windows GPU информации: {e}")

        return gpus

    def _detect_gpu_vendor(self, gpu_name: str) -> str:
        """Определяет производителя GPU по названию."""
        name_lower = gpu_name.lower()
        if 'nvidia' in name_lower or 'geforce' in name_lower or 'rtx' in name_lower or 'gtx' in name_lower:
            return 'NVIDIA'
        elif 'amd' in name_lower or 'radeon' in name_lower or 'rx ' in name_lower:
            return 'AMD'
        elif 'intel' in name_lower:
            return 'Intel'
        elif 'apple' in name_lower:
            return 'Apple'
        else:
            return 'Unknown'

    def _get_macos_system_details(self) -> Dict[str, Any]:
        """Дополнительная информация для macOS."""
        details = {}
        try:
            # Версия macOS
            result = subprocess.run(['sw_vers', '-productVersion'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                details['macos_version'] = result.stdout.strip()

            # Build version
            result = subprocess.run(['sw_vers', '-buildVersion'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                details['build_version'] = result.stdout.strip()

            # Реальная архитектура
            result = subprocess.run(['uname', '-m'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                details['real_architecture'] = result.stdout.strip()

        except Exception as e:
            log.warning(f"Ошибка получения macOS деталей: {e}")

        return details

    def _get_windows_system_details(self) -> Dict[str, Any]:
        """Дополнительная информация для Windows."""
        details = {}
        try:
            # Windows version
            details['windows_version'] = platform.win32_ver()

            # System info через systeminfo
            result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Total Physical Memory:' in line:
                        details['total_physical_memory'] = line.split(':')[1].strip()
                    elif 'System Type:' in line:
                        details['system_type'] = line.split(':')[1].strip()

        except Exception as e:
            log.warning(f"Ошибка получения Windows деталей: {e}")

        return details

    def _get_linux_system_details(self) -> Dict[str, Any]:
        """Дополнительная информация для Linux."""
        details = {}
        try:
            # Kernel version
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                details['kernel_version'] = result.stdout.strip()

            # Distribution info
            try:
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('NAME='):
                            details['distribution'] = line.split('=')[1].strip().strip('"')
                        elif line.startswith('VERSION='):
                            details['distribution_version'] = line.split('=')[1].strip().strip('"')
            except:
                pass

        except Exception as e:
            log.warning(f"Ошибка получения Linux деталей: {e}")

        return details

    def _get_additional_system_info(self) -> Dict[str, Any]:
        """Дополнительная системная информация."""
        try:
            info = {
                'python_version': platform.python_version(),
                'python_implementation': platform.python_implementation(),
                'python_executable': sys.executable
            }

            # Информация о диске
            try:
                disk_usage = psutil.disk_usage('/')
                info['disk_total_gb'] = round(disk_usage.total / (1024**3), 2)
                info['disk_free_gb'] = round(disk_usage.free / (1024**3), 2)
                info['disk_used_gb'] = round(disk_usage.used / (1024**3), 2)
            except:
                pass

            return info
        except Exception as e:
            log.warning(f"Ошибка получения дополнительной системной информации: {e}")
            return {'error': str(e)}

    def _get_environment_info_safe(self) -> Dict[str, Any]:
        """ИСПРАВЛЕННОЕ безопасное получение версий библиотек."""
        env_info = {}

        # Список безопасных библиотек (прямой импорт)
        safe_libraries = ['pandas', 'numpy', 'requests', 'psutil', 'json', 'os', 'sys']

        for lib in safe_libraries:
            try:
                if lib in ['json', 'os', 'sys']:
                    # Встроенные модули
                    module = __import__(lib)
                    env_info[lib] = getattr(module, '__version__', 'built-in')
                else:
                    module = __import__(lib)
                    version = getattr(module, '__version__', 'unknown')
                    env_info[lib] = version
                    log.debug(f"✅ {lib}: {version}")
            except ImportError:
                env_info[lib] = 'not_installed'
            except Exception as e:
                env_info[lib] = f'error: {str(e)}'
                log.warning(f"Ошибка при импорте {lib}: {e}")

        # ИСПРАВЛЕНИЕ: Проблемные библиотеки проверяем через sys.executable
        problematic_libraries = ['torch', 'tensorflow', 'transformers', 'ollama', 'pynvml']

        for lib in problematic_libraries:
            env_info[lib] = self._get_library_version_safe(lib)

        return env_info

    def _get_library_version_safe(self, lib_name: str) -> str:
        """ИСПРАВЛЕННОЕ получение версии библиотеки через текущий Python интерпретатор."""
        try:
            # ИСПРАВЛЕНИЕ: Используем sys.executable вместо 'python'
            result = subprocess.run(
                [sys.executable, "-c", f"import {lib_name}; print({lib_name}.__version__)"],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                log.debug(f"✅ {lib_name}: {version}")
                return version
            else:
                stderr_msg = result.stderr.strip() if result.stderr else "unknown error"
                log.debug(f"⚠️ {lib_name}: import failed ({stderr_msg})")
                return "import_failed"

        except subprocess.TimeoutExpired:
            log.warning(f"⏱️ {lib_name}: timeout")
            return "timeout"
        except subprocess.CalledProcessError as e:
            log.warning(f"❌ {lib_name}: process error ({e})")
            return "process_error"
        except Exception as e:
            log.error(f"💥 {lib_name}: unexpected error ({e})")
            return f"error: {str(e)}"

    def save_system_profile(self, filepath: Path) -> None:
        """Сохраняет профиль системы в JSON файл."""
        system_info = self.get_system_info()

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(system_info, f, indent=2, default=str)
            log.info(f"✅ Профиль системы сохранен: {filepath}")
        except Exception as e:
            log.error(f"❌ Ошибка сохранения профиля системы: {e}")

# Вспомогательные функции
def log_system_info(results_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Добавляет информацию о системе к результатам benchmark'а."""
    profiler = SystemProfiler()
    system_info = profiler.get_system_info()

    results_dict['system_info'] = system_info
    results_dict['benchmark_timestamp'] = psutil.boot_time()

    return results_dict

def get_hardware_tier(system_info: Dict[str, Any]) -> str:
    """УЛУЧШЕННОЕ определение уровня оборудования с поддержкой всех платформ."""
    gpus = system_info.get('gpus', [])
    total_ram = system_info.get('memory', {}).get('total_ram_gb', 0)
    os_platform = system_info.get('os', {}).get('platform', '')

    # Специальная обработка для macOS
    if os_platform == 'Darwin':
        for gpu in gpus:
            if gpu.get('vendor') == 'Apple':
                chip_name = gpu.get('chip', '').lower()
                if any(x in chip_name for x in ['m1 ultra', 'm2 ultra', 'm3 ultra', 'm4 ultra']):
                    return 'workstation_mac'
                elif any(x in chip_name for x in ['m1 max', 'm2 max', 'm3 max', 'm4 max']):
                    return 'high_end_mac'
                elif any(x in chip_name for x in ['m1 pro', 'm2 pro', 'm3 pro', 'm4 pro']):
                    return 'mid_range_mac'
                elif any(x in chip_name for x in ['m1', 'm2', 'm3', 'm4']):
                    return 'entry_mac'

        # Для Intel Mac определяем по RAM
        if total_ram >= 64:
            return 'workstation_mac'
        elif total_ram >= 32:
            return 'desktop_mac'
        else:
            return 'mobile_mac'

    # Определяем по GPU для других систем (Windows/Linux)
    for gpu in gpus:
        vram = gpu.get('memory_total_gb', 0)
        gpu_name = gpu.get('name', '').lower()

        # Enterprise level
        if any(x in gpu_name for x in ['h100', 'a100', 'v100', 'a6000', 'a5000']) or vram >= 40:
            return 'enterprise'
        # High-end consumer/professional
        elif any(x in gpu_name for x in ['4090', '4080', '3090', '3080 ti', 'rtx a4000']) or vram >= 16:
            return 'high_end'
            # Mid-range
        elif any(x in gpu_name for x in ['4070', '4060', '3080', '3070', '3060 ti']) or vram >= 8:
            return 'mid_range'
        # Entry level
        elif any(x in gpu_name for x in ['4050', '3060', '3050', '1660']) or vram >= 4:
            return 'entry_level'
        # Integrated graphics
        elif any(x in gpu_name for x in ['integrated', 'intel', 'iris']) and vram == 0:
            return 'integrated_gpu'

    # Если GPU нет, определяем по RAM и типу процессора
    if total_ram >= 128:
        return 'workstation_cpu'
    elif total_ram >= 64:
        return 'high_end_cpu'
    elif total_ram >= 32:
        return 'desktop_cpu'
    elif total_ram >= 16:
        return 'mid_range_cpu'
    else:
        return 'mobile_cpu'

def generate_hardware_compatibility_matrix() -> Dict[str, Dict[str, Any]]:
    """Генерирует матрицу совместимости моделей и оборудования."""
    return {
        'enterprise': {
            'recommended_models': [
                'llama-3.1-70b', 'qwen2.5-72b', 'deepseek-v3',
                'mixtral-8x22b', 'claude-3-opus'
            ],
            'performance_expectation': 'optimal',
            'notes': 'Все модели работают на полной скорости'
        },

        'high_end': {
            'recommended_models': [
                'llama-3.1-8b', 'qwen2.5-14b', 'mistral-7b',
                'deepseek-coder-v2-16b', 'gemma-2-9b'
            ],
            'with_quantization': [
                'llama-3.1-70b-q4', 'qwen2.5-72b-q4'
            ],
            'performance_expectation': 'high'
        },

        'workstation_mac': {
            'recommended_models': [
                'llama-3.1-8b', 'qwen2.5-14b', 'llama-3.1-70b-q4'
            ],
            'performance_expectation': 'very_good',
            'notes': 'Отличная производительность благодаря unified memory'
        },

        'high_end_mac': {
            'recommended_models': [
                'llama-3.1-8b', 'qwen2.5-7b', 'mistral-7b'
            ],
            'performance_expectation': 'good',
            'notes': 'Хорошая производительность для professional задач'
        },

        'mid_range': {
            'recommended_models': [
                'llama-3.1-8b-q4', 'qwen2.5-7b', 'phi-3.5-mini'
            ],
            'performance_expectation': 'acceptable'
        },

        'entry_level': {
            'recommended_models': [
                'phi-3.5-mini', 'qwen2.5-1.5b', 'tinyllama-1.1b'
            ],
            'performance_expectation': 'limited'
        },

        'mobile_cpu': {
            'recommended_models': [
                'phi-3.5-mini', 'tinyllama-1.1b', 'qwen2.5-0.5b'
            ],
            'performance_expectation': 'slow',
            'notes': 'CPU-only inference, подходит для простых задач'
        }
    }

def main():
    """ИСПРАВЛЕННАЯ основная функция для тестирования системного профилера."""
    try:
        profiler = SystemProfiler()

        print("🔍 Сбор информации о системе...")
        system_info = profiler.get_system_info()
        # Определяем уровень оборудования
        tier = get_hardware_tier(system_info)

        print(f"✅ Уровень оборудования: {tier}")
        print(f"💻 ОС: {system_info['os']['platform']} {system_info['os']['platform_release']}")

        # ИСПРАВЛЕНИЕ: Умное определение наилучшего названия CPU
        cpu_info = system_info['cpu']
        cpu_name = _get_best_cpu_name(cpu_info, system_info['os']['platform'])
        print(f"🧠 CPU: {cpu_name}")

        # ИСПРАВЛЕНИЕ: Показ частоты процессора
        cpu_frequency = _get_best_cpu_frequency(cpu_info)
        if cpu_frequency:
            print(f"⚡ Частота CPU: {cpu_frequency}")

        print(f"💾 RAM: {system_info['memory']['total_ram_gb']} GB")

        for i, gpu in enumerate(system_info['gpus']):
            vram = gpu.get('memory_total_gb', 'N/A')
            gpu_type = gpu.get('type', 'unknown')
            print(f"🎮 GPU {i}: {gpu['vendor']} {gpu['name']} ({vram} GB VRAM, {gpu_type})")

        if not system_info['gpus']:
            print("🎮 GPU: Не обнаружено дискретных GPU")

        print("📦 Установленные библиотеки:")
        for lib, version in system_info['environment'].items():
            status_icon = "✅" if version not in ['not_installed', 'import_failed', 'timeout', 'error'] else "❌"
            print(f"  {status_icon} {lib}: {version}")

        # Сохраняем профиль
        profiler.save_system_profile(Path('system_profile.json'))
        print("💾 Системный профиль сохранен в system_profile.json")

        # Показываем рекомендации
        compatibility = generate_hardware_compatibility_matrix()
        if tier in compatibility:
            recommendations = compatibility[tier]
            print(f"\n🎯 Рекомендации для уровня '{tier}':")
            print(f"📈 Ожидаемая производительность: {recommendations['performance_expectation']}")
            print("🤖 Рекомендуемые модели:")
            for model in recommendations['recommended_models']:
                print(f"  - {model}")
            if 'notes' in recommendations:
                print(f"📝 Заметки: {recommendations['notes']}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        log.error(f"Критическая ошибка в main(): {e}", exc_info=True)

def _get_best_cpu_name(cpu_info: Dict[str, Any], platform: str) -> str:
    """Выбирает наиболее информативное название процессора в зависимости от платформы."""

    # Приоритет полей по информативности
    if platform == 'Darwin':  # macOS
        fields_priority = ['cpu_brand', 'model_name', 'processor_name']
    elif platform == 'Linux':
        fields_priority = ['model_name', 'processor_name', 'cpu_brand']
    elif platform == 'Windows':
        fields_priority = ['cpu_model', 'processor_name', 'model_name']
    else:
        fields_priority = ['processor_name']

    # Ищем первое доступное и информативное поле
    for field in fields_priority:
        value = cpu_info.get(field, '').strip()
        if value and value not in ['i386', 'x86_64', 'Unknown', '']:
            return value

    # Fallback к базовой информации
    cores = cpu_info.get('physical_cores', 'Unknown')
    threads = cpu_info.get('logical_cores', 'Unknown')
    arch = cpu_info.get('real_architecture', cpu_info.get('processor_name', 'Unknown'))

    return f"Unknown CPU ({cores} cores, {threads} threads, {arch})"

def _get_best_cpu_frequency(cpu_info: Dict[str, Any]) -> Optional[str]:
    """Форматирует частоту процессора для отображения."""

    # Проверяем разные источники частоты
    if 'cpu_frequency_hz' in cpu_info:
        freq_hz = cpu_info['cpu_frequency_hz']
        if freq_hz > 1000000000:  # GHz
            return f"{freq_hz / 1000000000:.2f} GHz"
        elif freq_hz > 1000000:  # MHz
            return f"{freq_hz / 1000000:.0f} MHz"

    if 'max_frequency_mhz' in cpu_info and cpu_info['max_frequency_mhz']:
        freq_mhz = cpu_info['max_frequency_mhz']
        if freq_mhz >= 1000:
            return f"{freq_mhz / 1000:.2f} GHz (макс.)"
        else:
            return f"{freq_mhz:.0f} MHz (макс.)"

    if 'current_frequency_mhz' in cpu_info and cpu_info['current_frequency_mhz']:
        freq_mhz = cpu_info['current_frequency_mhz']
        if freq_mhz >= 1000:
            return f"{freq_mhz / 1000:.2f} GHz (текущая)"
        else:
            return f"{freq_mhz:.0f} MHz (текущая)"

    if 'cpu_mhz' in cpu_info:
        freq_mhz = cpu_info['cpu_mhz']
        if freq_mhz >= 1000:
            return f"{freq_mhz / 1000:.2f} GHz"
        else:
            return f"{freq_mhz:.0f} MHz"

    return None

if __name__ == "__main__":
    main()
