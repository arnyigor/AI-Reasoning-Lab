import difflib
import logging
import os
import random
import re
import subprocess
import sys
import tempfile
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


@dataclass
class CodeTask:
    """Структура боевой задачи для code agent."""
    task_id: str
    language: str
    mode: str  # "agent_edit", "bug_fix", "feature_add", "refactor"
    description: str
    original_code: str
    user_request: str  # Что просит пользователь (как в реальном чате)

    # Валидация
    expected_changes: List[str] = field(default_factory=list)  # Что должно появиться
    forbidden_patterns: List[str] = field(default_factory=list)  # Что должно исчезнуть
    structural_requirements: Dict[str, Any] = field(default_factory=dict)

    # Функциональные тесты
    test_code: str = ""
    expected_output: Optional[str] = None

    # Внешние зависимости (для мокирования)
    external_dependencies: List[str] = field(default_factory=list)

    # Режим тестирования
    test_mode: str = "execute"  # "execute", "ast_only", "compile_only"

    # Для diff_apply
    unified_diff: str = ""
    expected_result: str = ""


class CombatCodeAgentTestGenerator(AbstractTestGenerator):
    """
    Combat-level тест для code agent.

    Симулирует реальные сценарии:
    1. Пользователь вставляет код и просит внести правки
    2. Agent должен понять контекст и применить изменения
    3. Код должен остаться рабочим

    Улучшения v2:
    - Автоматическое мокирование внешних зависимостей
    - Трехуровневая верификация (syntax → structure → execution)
    - Более детальные сообщения об ошибках
    - Поддержка partial success (структура OK, но runtime fail)
    """

    def __init__(self, test_id: str = "combat_code_agent"):
        super().__init__(test_id)
        self.tasks = self._init_combat_tasks()

    def _init_combat_tasks(self) -> List[CodeTask]:
        """Боевые задачи из реальной практики."""
        return [
            # ══════════════════════════════════════════════════════════════
            # 1. KOTLIN: Добавить обработку ошибок в suspend функцию
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_add_error_handling",
                language="kotlin",
                mode="feature_add",
                description="Добавление обработки ошибок в корутину",
                original_code='''
class UserRepository(private val api: UserApi) {
    
    suspend fun getUser(userId: String): User {
        val response = api.fetchUser(userId)
        return response.toUser()
    }
    
    suspend fun updateUser(user: User): Boolean {
        val response = api.updateUser(user.toRequest())
        return response.isSuccessful
    }
}
'''.strip(),
                user_request="""
Добавь обработку ошибок в оба метода:
1. Оберни в try-catch
2. Логируй ошибки через Log.e с тегом "UserRepository"  
3. В getUser возвращай null при ошибке (измени тип на User?)
4. В updateUser возвращай false при ошибке
""",
                expected_changes=[
                    "try",
                    "catch",
                    "Log.e",
                    "UserRepository",
                    "User?",
                    "null"
                ],
                structural_requirements={
                    "must_contain_all": ["try {", "catch (", "Log.e("],
                    "return_type_change": ("User", "User?")
                },
                test_code='''
import kotlinx.coroutines.runBlocking

// Mock классы для теста
interface UserApi {
    suspend fun fetchUser(id: String): UserResponse
    suspend fun updateUser(req: UserRequest): UpdateResponse
}
data class UserResponse(val id: String, val name: String) {
    fun toUser() = User(id, name)
}
data class User(val id: String, val name: String) {
    fun toRequest() = UserRequest(id, name)
}
data class UserRequest(val id: String, val name: String)
data class UpdateResponse(val isSuccessful: Boolean)

// Mock Android Log
object Log {
    fun e(tag: String, msg: String, ex: Throwable? = null) {
        println("ERROR[$tag]: $msg")
    }
}

// Тест
fun main() {
    val mockApi = object : UserApi {
        override suspend fun fetchUser(id: String) = UserResponse(id, "Test")
        override suspend fun updateUser(req: UserRequest) = UpdateResponse(true)
    }
    
    val repo = UserRepository(mockApi)
    
    // Проверяем что тип возврата nullable
    val result: User? = runBlocking { repo.getUser("1") }
    assert(result != null) { "getUser should return User" }
    
    val updated = runBlocking { repo.updateUser(User("1", "New")) }
    assert(updated) { "updateUser should return true" }
    
    println("TYPE_CHECK_PASSED")
}
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 2. PYTHON: Рефакторинг - вынести конфиг в отдельный класс
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_extract_config",
                language="python",
                mode="refactor",
                description="Извлечение конфигурации в отдельный класс",
                original_code='''
import os
import redis

class CacheService:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.password = os.getenv("REDIS_PASSWORD")
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password
        )
    
    def get(self, key: str) -> str | None:
        return self.client.get(key)
    
    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        return self.client.setex(key, ttl, value)
'''.strip(),
                user_request="""
Отрефактори:
1. Вынеси конфигурацию в dataclass RedisConfig
2. Используй @dataclass с frozen=True
3. Добавь classmethod from_env() для создания из переменных окружения
4. CacheService должен принимать RedisConfig в __init__
""",
                expected_changes=[
                    "@dataclass",
                    "frozen=True",
                    "RedisConfig",
                    "from_env",
                    "@classmethod"
                ],
                forbidden_patterns=[
                    # Запрещаем os.getenv ВНУТРИ CacheService.__init__
                    # Используем контекстную проверку
                ],
                structural_requirements={
                    "classes": ["RedisConfig", "CacheService"],
                    "dataclass_frozen": True,
                    "no_env_in_cache_init": True  # Специальная проверка
                },
                external_dependencies=["redis"],  # Требует мокирования
                test_code='''
# Mock redis перед импортом
import sys
from unittest.mock import MagicMock
sys.modules['redis'] = MagicMock()

# Теперь безопасно выполнять код
import dataclasses
import os

# RedisConfig должен быть dataclass
assert dataclasses.is_dataclass(RedisConfig), "RedisConfig must be a dataclass"

# Проверяем frozen
try:
    cfg = RedisConfig(host="localhost", port=6379, db=0, password=None)
    cfg.host = "other"  # Должно упасть
    assert False, "Should be frozen"
except dataclasses.FrozenInstanceError:
    pass

# Проверяем from_env
assert hasattr(RedisConfig, 'from_env'), "Missing from_env method"
assert callable(getattr(RedisConfig, 'from_env')), "from_env must be callable"

# Проверяем что это classmethod
import inspect
from_env_method = getattr(RedisConfig, 'from_env')
# У classmethod первый аргумент - cls, не self
assert inspect.ismethod(from_env_method), "from_env should be a method"

# CacheService принимает config
sig = inspect.signature(CacheService.__init__)
params = list(sig.parameters.keys())
assert 'config' in params or 'redis_config' in params, f"CacheService.__init__ должен принимать config. Params: {params}"

# Проверяем что CacheService больше не читает env напрямую
import ast
import inspect

# Получаем исходный код CacheService.__init__
source = inspect.getsource(CacheService.__init__)
tree = ast.parse(source)

# Ищем вызовы os.getenv в __init__
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'getenv':
                raise AssertionError("CacheService.__init__ не должен вызывать os.getenv напрямую")

print("ALL_STRUCTURE_TESTS_PASSED")
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 3. TYPESCRIPT: Добавить типизацию к legacy JS коду
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="ts_add_types",
                language="typescript",
                mode="feature_add",
                description="Добавление строгой типизации",
                original_code='''
// @ts-nocheck
export function processOrder(order, user, options) {
    const discount = options?.discount || 0;
    const items = order.items.map(item => ({
        ...item,
        finalPrice: item.price * (1 - discount)
    }));
    
    return {
        orderId: order.id,
        userId: user.id,
        items,
        total: items.reduce((sum, i) => sum + i.finalPrice, 0),
        processedAt: new Date()
    };
}

export function validateOrder(order) {
    if (!order.items || order.items.length === 0) {
        return { valid: false, error: "No items" };
    }
    if (order.items.some(i => i.price < 0)) {
        return { valid: false, error: "Invalid price" };
    }
    return { valid: true };
}
'''.strip(),
                user_request="""
Добавь полную типизацию:
1. Убери @ts-nocheck
2. Создай интерфейсы: Order, OrderItem, User, ProcessOptions, ProcessedOrder, ValidationResult
3. Типизируй все функции и их параметры
4. Используй strict типы (не any)
""",
                expected_changes=[
                    "interface Order",
                    "interface OrderItem",
                    "interface User",
                    "interface ProcessOptions",
                    "interface ProcessedOrder",
                    "interface ValidationResult",
                    ": Order",
                    ": User"
                ],
                forbidden_patterns=[
                    "@ts-nocheck",
                    ": any",
                    "as any"
                ],
                structural_requirements={
                    "interfaces_count": 6,
                    "no_implicit_any": True
                },
                test_mode="compile_only"  # Только компиляция TypeScript
            ),

            # ══════════════════════════════════════════════════════════════
            # 4. KOTLIN: Миграция с callback на Flow
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_callback_to_flow",
                language="kotlin",
                mode="refactor",
                description="Миграция callback API на Kotlin Flow",
                original_code='''
interface LocationCallback {
    fun onLocationUpdate(lat: Double, lng: Double)
    fun onError(error: Throwable)
}

class LocationService(private val client: FusedLocationClient) {
    
    private var callback: LocationCallback? = null
    
    fun startUpdates(callback: LocationCallback) {
        this.callback = callback
        client.requestLocationUpdates(object : LocationListener {
            override fun onLocationChanged(location: Location) {
                callback.onLocationUpdate(location.latitude, location.longitude)
            }
        })
    }
    
    fun stopUpdates() {
        client.removeLocationUpdates()
        callback = null
    }
}
'''.strip(),
                user_request="""
Перепиши на Kotlin Flow:
1. Убери интерфейс LocationCallback
2. Метод locationUpdates() должен возвращать Flow<LatLng>
3. Используй callbackFlow для обертки callback API
4. Добавь awaitClose для корректной очистки
5. Создай data class LatLng(val lat: Double, val lng: Double)
""",
                expected_changes=[
                    "Flow<LatLng>",
                    "callbackFlow",
                    "awaitClose",
                    "data class LatLng",
                    "trySend",  # или offer/emit
                ],
                forbidden_patterns=[
                    "interface LocationCallback",
                    "var callback:",
                    "callback.onLocationUpdate"
                ],
                structural_requirements={
                    "must_import": ["kotlinx.coroutines.flow"],
                    "data_class": "LatLng"
                },
                test_code='''
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.runBlocking

// Mock классы
data class Location(val latitude: Double, val longitude: Double)
interface LocationListener {
    fun onLocationChanged(location: Location)
}
class FusedLocationClient {
    private var listener: LocationListener? = null
    fun requestLocationUpdates(l: LocationListener) { listener = l }
    fun removeLocationUpdates() { listener = null }
    fun simulateUpdate(lat: Double, lng: Double) {
        listener?.onLocationChanged(Location(lat, lng))
    }
}

// Тест
fun main() = runBlocking {
    val mockClient = FusedLocationClient()
    val service = LocationService(mockClient)
    
    val flow = service.locationUpdates()
    
    // Проверяем что это Flow
    assert(flow is Flow<*>) { "locationUpdates should return Flow" }
    
    println("FLOW_MIGRATION_PASSED")
}
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 5. PYTHON: Исправить race condition в async коде
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_fix_race_condition",
                language="python",
                mode="bug_fix",
                description="Исправление race condition",
                original_code='''
import asyncio
from typing import Dict, Any

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: Dict[str, list] = {}
    
    async def is_allowed(self, client_id: str) -> bool:
        now = asyncio.get_event_loop().time()
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Очищаем старые запросы
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < self.window
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(now)
        return True
'''.strip(),
                user_request="""
В этом коде race condition при конкурентных вызовах is_allowed.
Исправь:
1. Добавь asyncio.Lock для защиты shared state
2. Lock должен быть per-client (не глобальный)
3. Используй async with для захвата lock
""",
                expected_changes=[
                    "asyncio.Lock",
                    "async with",
                    "_locks"  # словарь локов
                ],
                structural_requirements={
                    "lock_per_client": True,
                    "uses_async_with": True
                },
                test_code='''
import asyncio
from typing import Dict

# Тест на race condition
async def stress_test():
    limiter = RateLimiter(max_requests=5, window_seconds=1)
    
    async def hammer(client_id: str, n: int):
        results = await asyncio.gather(*[
            limiter.is_allowed(client_id) for _ in range(n)
        ])
        return sum(results)
    
    # 100 конкурентных запросов, должно пройти ровно 5
    allowed = await hammer("test_client", 100)
    
    # С race condition может пройти больше 5
    assert allowed == 5, f"Race condition detected! Allowed {allowed} requests instead of 5"
    print("RACE_CONDITION_FIXED")

asyncio.run(stress_test())
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 6. KOTLIN: Code Review правки (BigDecimal + validation)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_code_review_fixes",
                language="kotlin",
                mode="agent_edit",
                description="Применение правок из code review",
                original_code='''
class PaymentProcessor(
    private val gateway: PaymentGateway,
    private val logger: Logger
) {
    fun processPayment(amount: Double, cardToken: String): PaymentResult {
        logger.info("Processing payment: $amount")
        
        val response = gateway.charge(amount, cardToken)
        
        if (response.success) {
            logger.info("Payment successful")
            return PaymentResult.Success(response.transactionId)
        } else {
            logger.error("Payment failed: ${response.error}")
            return PaymentResult.Failure(response.error)
        }
    }
}
'''.strip(),
                user_request="""
Code review comments:
1. Line 5: amount должен быть BigDecimal, не Double (финансы!)
2. Line 6: Добавь валидацию amount > 0 перед обработкой
3. Line 8: gateway.charge может бросить исключение - оберни в try-catch
4. Line 11: Залогируй transactionId в success case
5. Общее: Сделай функцию suspend (gateway.charge должен быть suspend)
""",
                expected_changes=[
                    "BigDecimal",
                    "suspend fun",
                    "try",
                    "catch",
                    "transactionId"
                ],
                forbidden_patterns=[
                    "amount: Double"  # должен быть BigDecimal
                ],
                structural_requirements={
                    "suspend_function": True,
                    "has_validation": True,
                    "has_error_handling": True
                },
                test_code='''
import kotlinx.coroutines.runBlocking
import java.math.BigDecimal

// Mock классы
interface PaymentGateway {
    suspend fun charge(amount: BigDecimal, token: String): ChargeResponse
}
data class ChargeResponse(val success: Boolean, val transactionId: String?, val error: String?)
sealed class PaymentResult {
    data class Success(val transactionId: String) : PaymentResult()
    data class Failure(val error: String) : PaymentResult()
}
class Logger {
    fun info(msg: String) = println("INFO: $msg")
    fun error(msg: String) = println("ERROR: $msg")
}

// Тест
fun main() = runBlocking {
    val mockGateway = object : PaymentGateway {
        override suspend fun charge(amount: BigDecimal, token: String) =
            ChargeResponse(true, "TXN123", null)
    }
    
    val processor = PaymentProcessor(mockGateway, Logger())
    
    // Проверяем что принимает BigDecimal
    val result = processor.processPayment(BigDecimal("100.00"), "tok_test")
    
    assert(result is PaymentResult.Success) { "Should succeed" }
    
    println("PAYMENT_PROCESSOR_FIXED")
}
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 7. PYTHON: Async context manager для database transactions
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_async_context_manager",
                language="python",
                mode="feature_add",
                description="Добавление async context manager",
                original_code='''
class DatabaseConnection:
    def __init__(self, url: str):
        self.url = url
        self.connection = None
    
    async def connect(self):
        # Simulate connection
        self.connection = f"Connected to {self.url}"
        print(self.connection)
    
    async def disconnect(self):
        print("Disconnecting...")
        self.connection = None
    
    async def execute(self, query: str):
        if not self.connection:
            raise RuntimeError("Not connected")
        return f"Executed: {query}"
'''.strip(),
                user_request="""
Преврати класс в async context manager:
1. Добавь методы __aenter__ и __aexit__
2. __aenter__ должен вызывать connect() и возвращать self
3. __aexit__ должен вызывать disconnect() даже при ошибке
4. Используй typing для аннотации типов (Self или 'DatabaseConnection')
""",
                expected_changes=[
                    "__aenter__",
                    "__aexit__",
                    "async def __aenter__",
                    "async def __aexit__",
                    "return self"
                ],
                structural_requirements={
                    "has_aenter": True,
                    "has_aexit": True
                },
                test_code='''
import asyncio

# Тест async context manager
async def test_context_manager():
    async with DatabaseConnection("postgresql://localhost") as db:
        result = await db.execute("SELECT 1")
        assert "Executed" in result
    
    # После выхода из контекста должно быть disconnect
    assert db.connection is None, "Connection should be closed"
    
    print("ASYNC_CONTEXT_MANAGER_OK")

asyncio.run(test_context_manager())
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 8. JAVASCRIPT: Промисификация callback API
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="js_promisify_callbacks",
                language="javascript",
                mode="refactor",
                description="Конвертация callbacks в Promises",
                original_code='''
function fetchUserData(userId, callback) {
    setTimeout(() => {
        if (userId < 0) {
            callback(new Error("Invalid user ID"), null);
        } else {
            callback(null, { id: userId, name: `User${userId}` });
        }
    }, 100);
}

function saveUserData(userData, callback) {
    setTimeout(() => {
        if (!userData.name) {
            callback(new Error("Name is required"), null);
        } else {
            callback(null, { success: true, id: userData.id });
        }
    }, 100);
}
'''.strip(),
                user_request="""
Перепиши функции на Promises:
1. Переименуй в fetchUserDataAsync и saveUserDataAsync
2. Убери параметр callback
3. Возвращай Promise
4. Используй resolve/reject вместо callback(err, data)
5. Добавь JSDoc с типами
""",
                expected_changes=[
                    "fetchUserDataAsync",
                    "saveUserDataAsync",
                    "return new Promise",
                    "resolve(",
                    "reject("
                ],
                forbidden_patterns=[
                    "callback("
                ],
                structural_requirements={
                    "returns_promise": True,
                    "has_jsdoc": True
                },
                test_code='''
// Тест промисификации
async function test() {
    // Положительный сценарий
    const user = await fetchUserDataAsync(1);
    if (user.id !== 1) throw new Error("Wrong user ID");
    
    // Негативный сценарий
    try {
        await fetchUserDataAsync(-1);
        throw new Error("Should reject");
    } catch (err) {
        if (!err.message.includes("Invalid")) throw err;
    }
    
    // Save test
    const result = await saveUserDataAsync({ id: 1, name: "Test" });
    if (!result.success) throw new Error("Save failed");
    
    console.log("PROMISIFY_OK");
}

test().catch(console.error);
''',
                test_mode="execute"
            ),
        ]

    # ══════════════════════════════════════════════════════════════════════
    # ГЕНЕРАЦИЯ
    # ══════════════════════════════════════════════════════════════════════

    def generate(self) -> Dict[str, Any]:
        task = random.choice(self.tasks)
        prompt = self._build_agent_prompt(task)

        return {
            'prompt': prompt,
            'expected_output': {
                'type': 'combat_code_agent',
                'task': task
            }
        }

    def _build_agent_prompt(self, task: CodeTask) -> str:
        """Промпт в стиле реального code agent."""

        return f"""Ты — AI code assistant. Пользователь предоставляет код и просит внести изменения.

**Твоя задача:**
1. Внимательно прочитай исходный код
2. Примени ВСЕ запрошенные изменения
3. Верни ПОЛНЫЙ обновленный код (не diff, не фрагменты)
4. Код должен компилироваться/работать

---

**Исходный код ({task.language}):**

```{task.language}
{task.original_code}
```

---

**Запрос пользователя:**

{task.user_request}

---

**Требования к ответу:**
- Выведи ТОЛЬКО обновленный код в markdown блоке
- Без объяснений до или после кода
- Сохрани форматирование и стиль оригинала где возможно
"""

    # ══════════════════════════════════════════════════════════════════════
    # ВЕРИФИКАЦИЯ (ТРЕХУРОВНЕВАЯ)
    # ══════════════════════════════════════════════════════════════════════

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        task: CodeTask = expected_output["task"]

        # LEVEL 1: Извлечение и синтаксис
        code = self._extract_code(llm_output, task.language)
        if not code:
            return {
                "is_correct": False,
                "details": {
                    "level": "extraction",
                    "error": "Код не найден в ответе",
                    "raw_preview": llm_output[:300]
                }
            }

        # Проверка синтаксиса
        syntax_check = self._check_syntax(code, task.language)
        if not syntax_check["valid"]:
            return {
                "is_correct": False,
                "details": {
                    "level": "syntax",
                    "error": syntax_check["error"],
                    "code_preview": code[:500]
                }
            }

        # LEVEL 2: Структурная верификация
        errors = []
        warnings = []

        # 2.1: Проверяем expected_changes
        for change in task.expected_changes:
            if not self._flexible_search(code, change):
                errors.append(f"Не найдено ожидаемое изменение: '{change}'")

        # 2.2: Проверяем forbidden_patterns
        for pattern in task.forbidden_patterns:
            if self._flexible_search(code, pattern):
                errors.append(f"Найден запрещенный паттерн: '{pattern}'")

        # 2.3: Структурные требования
        struct_errors = self._verify_structure(code, task)
        errors.extend(struct_errors)

        # Если структура неверна - сразу fail
        if errors:
            return {
                "is_correct": False,
                "details": {
                    "level": "structure",
                    "task_id": task.task_id,
                    "mode": task.mode,
                    "language": task.language,
                    "errors": errors,
                    "warnings": warnings,
                    "code_preview": code[:500]
                }
            }

        # LEVEL 3: Функциональные тесты (если есть)
        if task.test_code:
            func_result = self._run_functional_test(code, task)
            if not func_result["success"]:
                # Структура OK, но тест упал
                return {
                    "is_correct": False,
                    "details": {
                        "level": "execution",
                        "task_id": task.task_id,
                        "mode": task.mode,
                        "language": task.language,
                        "errors": [f"Функциональный тест: {func_result['error']}"],
                        "warnings": warnings,
                        "structure_ok": True,  # Важно!
                        "code_preview": "OK (structure)"
                    }
                }

        # ✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ
        return {
            "is_correct": True,
            "details": {
                "level": "full_success",
                "task_id": task.task_id,
                "mode": task.mode,
                "language": task.language,
                "errors": [],
                "warnings": warnings,
                "code_preview": "OK"
            }
        }

    def _check_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Проверка синтаксиса кода."""
        try:
            if language == "python":
                compile(code, "<test>", "exec")
            elif language == "kotlin":
                # Базовая проверка через regex (полная требует kotlinc)
                if not re.search(r'\bfun\s+\w+|class\s+\w+', code):
                    return {"valid": False, "error": "No functions or classes found"}
            elif language in ("javascript", "typescript"):
                # Проверяем базовые паттерны
                if code.count('{') != code.count('}'):
                    return {"valid": False, "error": "Unbalanced braces"}

            return {"valid": True}
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {e}"}

    def _flexible_search(self, code: str, pattern: str) -> bool:
        """Гибкий поиск паттерна с учетом вариаций форматирования."""
        # Нормализуем пробелы
        normalized_code = re.sub(r'\s+', ' ', code)
        normalized_pattern = re.sub(r'\s+', ' ', pattern)

        # Прямой поиск
        if pattern in code:
            return True

        # Поиск без учета пробелов
        if normalized_pattern in normalized_code:
            return True

        # Regex с гибкими пробелами
        regex_pattern = re.sub(r'\s+', r'\\s*', re.escape(pattern))
        if re.search(regex_pattern, code):
            return True

        return False

    def _verify_structure(self, code: str, task: CodeTask) -> List[str]:
        """Проверка структурных требований с расширенной логикой."""
        errors = []
        reqs = task.structural_requirements

        # Проверка классов
        for cls in reqs.get("classes", []):
            if not re.search(rf'\bclass\s+{cls}\b', code):
                errors.append(f"Не найден класс: {cls}")

        # Проверка data class
        if "data_class" in reqs:
            cls_name = reqs["data_class"]
            if not re.search(rf'data\s+class\s+{cls_name}\b', code):
                errors.append(f"Не найден data class: {cls_name}")

        # Проверка suspend function
        if reqs.get("suspend_function"):
            if "suspend fun" not in code:
                errors.append("Функция должна быть suspend")

        # Проверка frozen dataclass
        if reqs.get("dataclass_frozen"):
            if not re.search(r'@dataclass\s*\(\s*frozen\s*=\s*True', code):
                errors.append("dataclass должен быть frozen=True")

        # Специальная проверка: os.getenv НЕ в CacheService.__init__
        if reqs.get("no_env_in_cache_init"):
            # Ищем определение CacheService.__init__
            init_match = re.search(
                r'class\s+CacheService.*?def\s+__init__\s*\([^)]*\)\s*:\s*(.*?)(?=\n    def|\nclass|\Z)',
                code,
                re.DOTALL
            )
            if init_match:
                init_body = init_match.group(1)
                if 'os.getenv' in init_body:
                    errors.append("CacheService.__init__ не должен вызывать os.getenv напрямую")

        # Обязательные элементы
        for item in reqs.get("must_contain_all", []):
            if not self._flexible_search(code, item):
                errors.append(f"Не найден обязательный элемент: {item}")

        # Проверка импортов
        for imp in reqs.get("must_import", []):
            if imp not in code:
                errors.append(f"Не найден импорт: {imp}")

        # Проверка async context manager
        if reqs.get("has_aenter"):
            if "async def __aenter__" not in code:
                errors.append("Отсутствует async def __aenter__")

        if reqs.get("has_aexit"):
            if "async def __aexit__" not in code:
                errors.append("Отсутствует async def __aexit__")

        # Проверка использования async with
        if reqs.get("uses_async_with"):
            if "async with" not in code:
                errors.append("Не используется async with для lock")

        # Проверка lock per client
        if reqs.get("lock_per_client"):
            # Ищем словарь локов
            if not re.search(r'_locks.*=.*{}|Dict\[.*Lock', code):
                errors.append("Отсутствует per-client lock (словарь локов)")

        # Проверка validation
        if reqs.get("has_validation"):
            validation_patterns = [
                r'if.*amount.*>.*0',
                r'if.*amount.*<=.*0',
                r'require.*amount',
                r'assert.*amount'
            ]
            if not any(re.search(p, code) for p in validation_patterns):
                errors.append("Отсутствует валидация amount")

        # Проверка error handling
        if reqs.get("has_error_handling"):
            if "try" not in code or "catch" not in code:
                errors.append("Отсутствует обработка ошибок (try-catch)")

        return errors

    # ══════════════════════════════════════════════════════════════════════
    # ФУНКЦИОНАЛЬНЫЕ ТЕСТЫ С МОКИРОВАНИЕМ
    # ══════════════════════════════════════════════════════════════════════

    def _run_functional_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск функциональных тестов с автоматическим мокированием."""
        lang = task.language

        if lang == "python":
            return self._run_python_test(code, task)
        elif lang == "kotlin":
            return self._run_kotlin_test(code, task)
        elif lang in ("javascript", "typescript"):
            return self._run_js_test(code, task)

        return {"success": True, "warning": f"No runner for {lang}"}

    def _run_python_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск Python с автоматическим мокированием зависимостей."""
        # Подготовка моков
        mock_setup = ""
        if task.external_dependencies:
            mock_setup = "import sys\nfrom unittest.mock import MagicMock\n"
            for dep in task.external_dependencies:
                mock_setup += f"sys.modules['{dep}'] = MagicMock()\n"
            mock_setup += "\n"

        full_code = f"{mock_setup}{code}\n\n# === TESTS ===\n{task.test_code}"

        try:
            namespace = {}
            exec(compile(full_code, "<test>", "exec"), namespace)
            return {"success": True}
        except AssertionError as e:
            return {"success": False, "error": f"Assertion failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Runtime error: {e}"}

    def _run_kotlin_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск Kotlin тестов."""
        if not task.test_code:
            return {"success": True}

        full_code = f"{code}\n\n{task.test_code}"
        result = self.execute_kotlin_code(full_code)

        if result.get("success"):
            return {"success": True}
        return {"success": False, "error": result.get("error", "Unknown error")}

    def _run_js_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск JS/TS тестов."""
        if not task.test_code:
            return {"success": True}

        full_code = f"{code}\n\n{task.test_code}"
        suffix = ".ts" if task.language == "typescript" else ".js"

        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(full_code)
            tmp_path = f.name

        try:
            if task.language == "typescript":
                # Компиляция TypeScript
                compile_result = subprocess.run(
                    ["npx", "tsc", "--noEmit", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if compile_result.returncode != 0:
                    return {"success": False, "error": f"TS compilation error: {compile_result.stderr[:500]}"}

                # Запуск через ts-node
                cmd = ["npx", "ts-node", tmp_path]
            else:
                cmd = ["node", tmp_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return {"success": False, "error": result.stderr[:500]}

            return {"success": True}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"success": False, "error": "Node/TS runtime not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ══════════════════════════════════════════════════════════════════════
    # ИЗВЛЕЧЕНИЕ КОДА (УЛУЧШЕННОЕ)
    # ══════════════════════════════════════════════════════════════════════

    def _extract_code(self, raw: str, lang: str) -> str:
        """Извлечение кода с многоступенчатой стратегией."""

        # 1. Удаляем think блоки
        cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL | re.IGNORECASE)

        # 2. Ищем markdown блоки (приоритетные паттерны)
        patterns = [
            rf'```{lang}\s*\n(.*?)```',           # ```python
            rf'```{lang[:2]}\s*\n(.*?)```',       # ```py
            r'```\w*\s*\n(.*?)```',               # ```code
            r'```\s*\n(.*?)```',                  # ```
        ]

        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                if len(code) > 50:  # Минимальная длина
                    return self._sanitize_code(code)

        # 3. Fallback: весь текст после очистки
        fallback = self._sanitize_code(cleaned.strip())
        if len(fallback) > 50:
            return fallback

        return ""
