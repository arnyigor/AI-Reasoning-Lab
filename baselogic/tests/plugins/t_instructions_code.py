import logging
import os
import random
import re
import subprocess
import sys
import tempfile
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

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
    user_request: str

    # Язык промпта
    prompt_language: str = "ru"  # "ru" или "en"

    # Валидация
    expected_changes: List[str] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)
    structural_requirements: Dict[str, Any] = field(default_factory=dict)

    # Функциональные тесты
    test_code: str = ""
    expected_output: Optional[str] = None

    # Внешние зависимости (для мокирования)
    external_dependencies: List[str] = field(default_factory=list)

    # Режим тестирования: execute, structure_only, compile_only
    test_mode: str = "execute"


class CombatCodeAgentTestGenerator(AbstractTestGenerator):
    """
    Combat-level тест для code agent v4.

    Исправления v4:
    - Гибкие паттерны для type/interface в TypeScript
    - Исправлены regex для validation в Kotlin
    - Совместимость с Python 3.10+ (Self → строковые аннотации)
    - Улучшенные структурные проверки
    """

    def __init__(self, test_id: str = "t_instructions_code"):
        super().__init__(test_id)
        self.tasks = self._init_combat_tasks()

    def _init_combat_tasks(self) -> List[CodeTask]:
        """Боевые задачи из реальной практики."""
        return [
            # ══════════════════════════════════════════════════════════════
            # 1. KOTLIN: Добавить обработку ошибок (RU)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_add_error_handling",
                language="kotlin",
                mode="feature_add",
                prompt_language="ru",
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
                    "User?",
                    "null"
                ],
                structural_requirements={
                    "must_contain_all": ["try", "catch"],
                    "must_contain_any": ["Log.e", "log.e", "Logger"],
                },
                test_mode="structure_only"
            ),

            # ══════════════════════════════════════════════════════════════
            # 2. KOTLIN: Error Handling (EN)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_error_handling_en",
                language="kotlin",
                mode="feature_add",
                prompt_language="en",
                description="Add error handling to suspend functions",
                original_code='''
class ProductRepository(private val api: ProductApi) {
    
    suspend fun getProduct(productId: Long): Product {
        val response = api.fetchProduct(productId)
        return response.toProduct()
    }
    
    suspend fun deleteProduct(productId: Long): Boolean {
        val response = api.deleteProduct(productId)
        return response.isSuccessful
    }
}
'''.strip(),
                user_request="""
Add error handling to both methods:
1. Wrap in try-catch blocks
2. Log errors using Log.e with tag "ProductRepository"
3. In getProduct, return null on error (change return type to Product?)
4. In deleteProduct, return false on error
5. Catch Exception type
""",
                expected_changes=[
                    "try",
                    "catch",
                    "Log.e",
                    "Product?",
                    "null",
                    "Exception"
                ],
                forbidden_patterns=[
                    ": Product {"
                ],
                structural_requirements={
                    "must_contain_all": ["try", "catch"],
                },
                test_mode="structure_only"
            ),

            # ══════════════════════════════════════════════════════════════
            # 3. PYTHON: Dataclass → Pydantic (RU)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_extract_config",
                language="python",
                mode="refactor",
                prompt_language="ru",
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
                structural_requirements={
                    "classes": ["RedisConfig", "CacheService"],
                    "dataclass_frozen": True,
                    "cache_service_accepts_config": True
                },
                external_dependencies=["redis"],
                test_code='''
import sys
from unittest.mock import MagicMock
sys.modules['redis'] = MagicMock()

import dataclasses

# Проверяем что RedisConfig - dataclass
assert dataclasses.is_dataclass(RedisConfig), "RedisConfig должен быть dataclass"

# Проверяем frozen
cfg = RedisConfig(host="localhost", port=6379, db=0, password=None)
try:
    cfg.host = "other"
    raise AssertionError("RedisConfig должен быть frozen")
except dataclasses.FrozenInstanceError:
    pass

# Проверяем from_env
assert hasattr(RedisConfig, 'from_env'), "Отсутствует метод from_env"

# Проверяем что CacheService принимает config
import inspect
sig = inspect.signature(CacheService.__init__)
params = list(sig.parameters.keys())
assert any(p in params for p in ['config', 'redis_config', 'cfg']), f"CacheService должен принимать config. Params: {params}"

print("ALL_STRUCTURE_TESTS_PASSED")
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 4. PYTHON: Async Context Manager (EN) - ИСПРАВЛЕН
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_async_context_manager",
                language="python",
                mode="feature_add",
                prompt_language="en",
                description="Convert class to async context manager",
                original_code='''
class DatabaseConnection:
    def __init__(self, url: str):
        self.url = url
        self.connection = None
    
    async def connect(self):
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
                # Исправлено: указание на строковые аннотации для совместимости
                user_request="""
Convert this class to an async context manager:
1. Add __aenter__ and __aexit__ methods
2. __aenter__ should call connect() and return self
3. __aexit__ should call disconnect() even if an error occurred
4. Use proper type hints (use string annotation 'DatabaseConnection' for compatibility)
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

async def test_context_manager():
    async with DatabaseConnection("postgresql://localhost") as db:
        result = await db.execute("SELECT 1")
        assert "Executed" in result, "execute() should work inside context"
    
    assert db.connection is None, "Connection should be closed after context exit"
    print("ASYNC_CONTEXT_MANAGER_OK")

asyncio.run(test_context_manager())
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 5. PYTHON: Fix Race Condition (EN)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_fix_race_condition",
                language="python",
                mode="bug_fix",
                prompt_language="en",
                description="Fix race condition in async code",
                original_code='''
import asyncio
from typing import Dict

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: Dict[str, list] = {}
    
    async def is_allowed(self, client_id: str) -> bool:
        now = asyncio.get_event_loop().time()
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
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
This code has a race condition when is_allowed is called concurrently.
Fix it:
1. Add asyncio.Lock to protect shared state
2. Use per-client locks (not a global lock)
3. Use 'async with' to acquire the lock
4. Store locks in a dictionary attribute
""",
                expected_changes=[
                    "asyncio.Lock",
                    "async with",
                ],
                structural_requirements={
                    "has_lock_dict": True,
                    "uses_async_with": True
                },
                test_code='''
import asyncio

async def stress_test():
    limiter = RateLimiter(max_requests=5, window_seconds=1)
    
    async def hammer(client_id: str, n: int):
        results = await asyncio.gather(*[
            limiter.is_allowed(client_id) for _ in range(n)
        ])
        return sum(results)
    
    allowed = await hammer("test_client", 100)
    
    assert allowed == 5, f"Race condition detected! Allowed {allowed} instead of 5"
    print("RACE_CONDITION_FIXED")

asyncio.run(stress_test())
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 6. TYPESCRIPT: Add Types (EN) - ИСПРАВЛЕН
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="ts_add_types",
                language="typescript",
                mode="feature_add",
                prompt_language="en",
                description="Add strict typing to legacy JavaScript code",
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
Add full TypeScript typing:
1. Remove @ts-nocheck
2. Create types for: Order, OrderItem, User, ProcessOptions, ProcessedOrder, ValidationResult
3. Type all function parameters and return types
4. Use strict types (no 'any')
""",
                # ИСПРАВЛЕНО: Убран "interface ProcessedOrder" - принимаем и type
                expected_changes=[
                    "Order",
                    "OrderItem",
                    "User",
                    "ProcessedOrder",
                    "ValidationResult",
                ],
                forbidden_patterns=[
                    "@ts-nocheck",
                    ": any",
                    "as any"
                ],
                structural_requirements={
                    "min_type_definitions": 5,  # interface или type
                    "no_ts_nocheck": True
                },
                test_mode="structure_only"
            ),

            # ══════════════════════════════════════════════════════════════
            # 7. KOTLIN: Callback to Flow (EN)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_callback_to_flow",
                language="kotlin",
                mode="refactor",
                prompt_language="en",
                description="Migrate callback API to Kotlin Flow",
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
Rewrite using Kotlin Flow:
1. Remove the LocationCallback interface
2. Create a method locationUpdates() that returns Flow<LatLng>
3. Use callbackFlow to wrap the callback-based API
4. Add awaitClose for proper cleanup
5. Create data class LatLng(val lat: Double, val lng: Double)
""",
                expected_changes=[
                    "Flow<LatLng>",
                    "callbackFlow",
                    "awaitClose",
                    "data class LatLng",
                ],
                forbidden_patterns=[
                    "interface LocationCallback",
                    "var callback:",
                ],
                structural_requirements={
                    "has_flow_return": True,
                    "has_data_class": "LatLng"
                },
                test_mode="structure_only"
            ),

            # ══════════════════════════════════════════════════════════════
            # 8. JAVASCRIPT: Promisify Callbacks (EN)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="js_promisify_callbacks",
                language="javascript",
                mode="refactor",
                prompt_language="en",
                description="Convert callback-based functions to Promises",
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
Rewrite these functions using Promises:
1. Rename to fetchUserDataAsync and saveUserDataAsync
2. Remove the callback parameter
3. Return a Promise
4. Use resolve/reject instead of callback(err, data)
5. Add JSDoc comments with type annotations
""",
                expected_changes=[
                    "fetchUserDataAsync",
                    "saveUserDataAsync",
                    "new Promise",
                    "resolve",
                    "reject"
                ],
                forbidden_patterns=[
                    ", callback)",
                    "callback("
                ],
                structural_requirements={
                    "returns_promise": True,
                    "has_jsdoc": True
                },
                test_code='''
async function test() {
    const user = await fetchUserDataAsync(1);
    if (user.id !== 1) throw new Error("Wrong user ID");
    
    try {
        await fetchUserDataAsync(-1);
        throw new Error("Should reject for negative ID");
    } catch (err) {
        if (!err.message.includes("Invalid")) throw err;
    }
    
    const result = await saveUserDataAsync({ id: 1, name: "Test" });
    if (!result.success) throw new Error("Save should succeed");
    
    console.log("PROMISIFY_OK");
}

test().catch(err => { console.error(err); process.exit(1); });
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 9. KOTLIN: Code Review Fixes (EN) - ИСПРАВЛЕН
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_code_review_fixes",
                language="kotlin",
                mode="agent_edit",
                prompt_language="en",
                description="Apply code review fixes",
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
Apply these code review comments:
1. Change amount type from Double to BigDecimal (financial precision!)
2. Add validation: amount must be > 0
3. Wrap gateway.charge in try-catch (it can throw exceptions)
4. Log the transactionId in success case
5. Make the function suspend (gateway.charge should be suspend)
""",
                expected_changes=[
                    "BigDecimal",
                    "suspend fun",
                    "try",
                    "catch",
                ],
                forbidden_patterns=[
                    "amount: Double",
                ],
                structural_requirements={
                    "suspend_function": True,
                    "has_amount_validation": True,  # ИСПРАВЛЕНО: специальная проверка
                    "has_try_catch": True
                },
                test_mode="structure_only"
            ),

            # ══════════════════════════════════════════════════════════════
            # 10. PYTHON: Add Retry Logic (EN)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_add_retry",
                language="python",
                mode="feature_add",
                prompt_language="en",
                description="Add retry logic with exponential backoff",
                original_code='''
import httpx
from typing import Any

class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def get(self, endpoint: str) -> dict[str, Any]:
        response = await self.client.get(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()
    
    async def post(self, endpoint: str, data: dict) -> dict[str, Any]:
        response = await self.client.post(f"{self.base_url}{endpoint}", json=data)
        response.raise_for_status()
        return response.json()
'''.strip(),
                user_request="""
Add retry logic with exponential backoff:
1. Create a decorator or helper method for retry logic
2. Retry on httpx.HTTPStatusError with 5xx status codes
3. Retry on httpx.ConnectError
4. Use exponential backoff: start at 1s, multiply by 2, max 3 retries
5. Add max_retries parameter to __init__ with default value 3
6. Apply retry to both get() and post() methods
""",
                expected_changes=[
                    "max_retries",
                    "retry",
                ],
                structural_requirements={
                    "has_retry_logic": True,
                    "has_max_retries_param": True
                },
                external_dependencies=["httpx"],
                test_code='''
import sys
from unittest.mock import MagicMock
sys.modules['httpx'] = MagicMock()

import inspect

# Проверяем наличие max_retries в __init__
sig = inspect.signature(ApiClient.__init__)
params = list(sig.parameters.keys())
assert 'max_retries' in params, f"ApiClient должен принимать max_retries. Params: {params}"

print("RETRY_STRUCTURE_OK")
''',
                test_mode="execute"
            ),

            # ══════════════════════════════════════════════════════════════
            # 11. KOTLIN: Sealed Class Migration (EN)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="kotlin_sealed_class",
                language="kotlin",
                mode="refactor",
                prompt_language="en",
                description="Convert enum to sealed class hierarchy",
                original_code='''
enum class NetworkResult {
    SUCCESS,
    ERROR,
    LOADING
}

class Repository {
    fun handleResult(result: NetworkResult, data: Any?, error: String?) {
        when (result) {
            NetworkResult.SUCCESS -> println("Data: $data")
            NetworkResult.ERROR -> println("Error: $error")
            NetworkResult.LOADING -> println("Loading...")
        }
    }
}
'''.strip(),
                user_request="""
Refactor to use sealed class:
1. Convert NetworkResult enum to a sealed class
2. Success should hold data of generic type T
3. Error should hold an exception and optional message
4. Loading should be an object (singleton)
5. Update handleResult to use when expression with smart casts
6. Make Repository generic with type parameter T
""",
                expected_changes=[
                    "sealed class NetworkResult",
                    "Success",
                    "Error",
                    "Loading",
                ],
                forbidden_patterns=[
                    "enum class NetworkResult",
                ],
                structural_requirements={
                    "has_sealed_class": True,
                    "has_generics": True
                },
                test_mode="structure_only"
            ),

            # ══════════════════════════════════════════════════════════════
            # 12. PYTHON: Pydantic Model (EN)
            # ══════════════════════════════════════════════════════════════
            CodeTask(
                task_id="python_pydantic_model",
                language="python",
                mode="refactor",
                prompt_language="en",
                description="Convert dataclass to Pydantic model with validation",
                original_code='''
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    id: int
    email: str
    name: str
    age: Optional[int] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
'''.strip(),
                user_request="""
Convert to Pydantic v2 model with validation:
1. Use pydantic.BaseModel instead of dataclass
2. Add email validation using EmailStr
3. Add age validation: must be >= 0 and <= 150 if provided
4. Use Field() for default values and validation
5. Add model_config with str_strip_whitespace = True
6. created_at should default to current time using default_factory
""",
                expected_changes=[
                    "BaseModel",
                    "EmailStr",
                    "Field(",
                    "model_config",
                    "default_factory",
                ],
                forbidden_patterns=[
                    "@dataclass",
                    "__post_init__",
                ],
                structural_requirements={
                    "extends_basemodel": True,
                    "has_field_validation": True
                },
                test_mode="structure_only"
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
        """Генерация промпта на нужном языке."""
        if task.prompt_language == "en":
            return self._build_prompt_en(task)
        else:
            return self._build_prompt_ru(task)

    def _build_prompt_en(self, task: CodeTask) -> str:
        """English prompt template."""
        return f"""You are an AI code assistant. The user provides code and asks for modifications.

**Your task:**
1. Carefully read the original code
2. Apply ALL requested changes
3. Return the COMPLETE updated code (not a diff, not fragments)
4. The code must compile/work correctly

---

**Original code ({task.language}):**

```{task.language}
{task.original_code}
```

---

**User request:**

{task.user_request}

---

**Response requirements:**
- Output ONLY the updated code in a markdown code block
- No explanations before or after the code
- Preserve the original formatting and style where possible
"""

    def _build_prompt_ru(self, task: CodeTask) -> str:
        """Russian prompt template."""
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
    # ВЕРИФИКАЦИЯ
    # ══════════════════════════════════════════════════════════════════════

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        task: CodeTask = expected_output["task"]

        # Извлекаем код
        code = self._extract_code(llm_output, task.language)
        if not code:
            return {
                "is_correct": False,
                "details": {
                    "level": "extraction",
                    "task_id": task.task_id,
                    "error": "Code not found in response",
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
                    "task_id": task.task_id,
                    "error": syntax_check["error"],
                    "code_preview": code[:500]
                }
            }

        # Структурная верификация
        errors = []
        warnings = []

        # Проверяем expected_changes
        for change in task.expected_changes:
            if not self._flexible_search(code, change):
                errors.append(f"Expected change not found: '{change}'")

        # Проверяем forbidden_patterns
        for pattern in task.forbidden_patterns:
            if self._flexible_search(code, pattern):
                errors.append(f"Forbidden pattern found: '{pattern}'")

        # Структурные требования
        struct_result = self._verify_structure(code, task)
        errors.extend(struct_result["errors"])
        warnings.extend(struct_result.get("warnings", []))

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

        # Функциональные тесты
        if task.test_mode == "execute" and task.test_code:
            func_result = self._run_functional_test(code, task)
            if not func_result["success"]:
                return {
                    "is_correct": False,
                    "details": {
                        "level": "execution",
                        "task_id": task.task_id,
                        "mode": task.mode,
                        "language": task.language,
                        "errors": [f"Functional test failed: {func_result['error']}"],
                        "warnings": warnings,
                        "structure_ok": True,
                        "code_preview": code[:300]
                    }
                }

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
        """Проверка синтаксиса."""
        try:
            if language == "python":
                compile(code, "<test>", "exec")
            elif language in ("kotlin", "javascript", "typescript"):
                if code.count('{') != code.count('}'):
                    return {"valid": False, "error": "Unbalanced braces"}
                if code.count('(') != code.count(')'):
                    return {"valid": False, "error": "Unbalanced parentheses"}
            return {"valid": True}
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {e}"}

    def _flexible_search(self, code: str, pattern: str) -> bool:
        """Гибкий поиск с учетом вариаций."""
        if pattern in code:
            return True

        normalized_code = re.sub(r'\s+', ' ', code)
        normalized_pattern = re.sub(r'\s+', ' ', pattern)
        if normalized_pattern in normalized_code:
            return True

        try:
            regex_pattern = re.sub(r'\s+', r'\\s*', re.escape(pattern))
            if re.search(regex_pattern, code, re.IGNORECASE):
                return True
        except re.error:
            pass

        return False

    def _verify_structure(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Проверка структурных требований."""
        errors = []
        warnings = []
        reqs = task.structural_requirements

        # Проверка классов
        for cls in reqs.get("classes", []):
            if not re.search(rf'\bclass\s+{cls}\b', code):
                errors.append(f"Class not found: {cls}")

        # must_contain_all
        for item in reqs.get("must_contain_all", []):
            if not self._flexible_search(code, item):
                errors.append(f"Required element not found: {item}")

        # must_contain_any
        any_items = reqs.get("must_contain_any", [])
        if any_items:
            if not any(self._flexible_search(code, item) for item in any_items):
                errors.append(f"None of required elements found: {any_items}")

        # Data class в Kotlin
        if "has_data_class" in reqs:
            cls_name = reqs["has_data_class"]
            if not re.search(rf'data\s+class\s+{cls_name}\b', code):
                errors.append(f"Data class not found: {cls_name}")

        # Sealed class
        if reqs.get("has_sealed_class"):
            if not re.search(r'sealed\s+class', code):
                errors.append("Sealed class not found")

        # Generics
        if reqs.get("has_generics"):
            if not re.search(r'<\s*\w+\s*>', code):
                errors.append("Generic type parameter not found")

        # Suspend function
        if reqs.get("suspend_function"):
            if "suspend fun" not in code:
                errors.append("Function should be suspend")

        # Frozen dataclass
        if reqs.get("dataclass_frozen"):
            if not re.search(r'@dataclass\s*\(\s*frozen\s*=\s*True', code):
                errors.append("Dataclass should be frozen=True")

        # CacheService accepts config
        if reqs.get("cache_service_accepts_config"):
            init_match = re.search(
                r'class\s+CacheService.*?def\s+__init__\s*\(\s*self\s*,\s*(\w+)',
                code, re.DOTALL
            )
            if init_match:
                param = init_match.group(1)
                if param not in ["config", "redis_config", "cfg"]:
                    warnings.append(f"CacheService.__init__ parameter '{param}'")
            else:
                errors.append("CacheService.__init__ should accept config parameter")

        # Async context manager
        if reqs.get("has_aenter"):
            if not re.search(r'async\s+def\s+__aenter__', code):
                errors.append("Missing async def __aenter__")

        if reqs.get("has_aexit"):
            if not re.search(r'async\s+def\s+__aexit__', code):
                errors.append("Missing async def __aexit__")

        # Lock dictionary
        if reqs.get("has_lock_dict"):
            patterns = [
                r'self\._?locks\s*[:\[=]',
                r'Dict\[.*Lock\]',
                r'dict\[.*Lock\]',
                r'\.setdefault\([^,]+,\s*asyncio\.Lock',
            ]
            if not any(re.search(p, code) for p in patterns):
                errors.append("Per-client lock dictionary not found")

        # Uses async with
        if reqs.get("uses_async_with"):
            if "async with" not in code:
                errors.append("'async with' not used for lock")

        # ИСПРАВЛЕНО: Amount validation для Kotlin с compareTo
        if reqs.get("has_amount_validation"):
            validation_patterns = [
                r'amount\.compareTo\s*\([^)]*\)\s*[<>]=?\s*0',
                r'if\s*\(\s*amount\s*[<>]=?',
                r'amount\s*[<>]=?\s*(?:0|BigDecimal)',
                r'require\s*\{?\s*amount',
                r'check\s*\{?\s*amount',
                r'throw.*[Ii]llegal.*amount',
                r'amount.*<=.*ZERO',
                r'amount.*>.*ZERO',
            ]
            if not any(re.search(p, code, re.IGNORECASE) for p in validation_patterns):
                errors.append("Amount validation not found")

        # Has try-catch
        if reqs.get("has_try_catch"):
            if "try" not in code or "catch" not in code:
                errors.append("Try-catch block not found")

        # Flow return type
        if reqs.get("has_flow_return"):
            if not re.search(r'Flow\s*<', code):
                errors.append("Flow<> return type not found")

        # Returns Promise
        if reqs.get("returns_promise"):
            if "new Promise" not in code and "Promise(" not in code:
                errors.append("Should return new Promise")

        # Has JSDoc
        if reqs.get("has_jsdoc"):
            if not re.search(r'/\*\*[\s\S]*?\*/', code):
                warnings.append("JSDoc comments not found")

        # ИСПРАВЛЕНО: min_type_definitions - принимает и interface и type
        min_types = reqs.get("min_type_definitions", 0)
        if min_types > 0:
            interface_count = len(re.findall(r'\binterface\s+\w+', code))
            type_count = len(re.findall(r'\btype\s+\w+\s*=', code))
            total = interface_count + type_count
            if total < min_types:
                errors.append(f"Expected at least {min_types} type definitions, found {total}")

        # No @ts-nocheck
        if reqs.get("no_ts_nocheck"):
            if "@ts-nocheck" in code:
                errors.append("@ts-nocheck should be removed")

        # Retry logic
        if reqs.get("has_retry_logic"):
            retry_patterns = ["retry", "retries", "attempt", "max_retries"]
            if not any(p in code.lower() for p in retry_patterns):
                errors.append("Retry logic not found")

        # max_retries parameter
        if reqs.get("has_max_retries_param"):
            if not re.search(r'max_retries\s*[=:]', code):
                errors.append("max_retries parameter not found")

        # Extends BaseModel
        if reqs.get("extends_basemodel"):
            if not re.search(r'class\s+\w+\s*\(\s*BaseModel\s*\)', code):
                errors.append("Class should extend BaseModel")

        # Field validation
        if reqs.get("has_field_validation"):
            if "Field(" not in code:
                errors.append("Field() validation not found")

        return {"errors": errors, "warnings": warnings}

    # ══════════════════════════════════════════════════════════════════════
    # ФУНКЦИОНАЛЬНЫЕ ТЕСТЫ
    # ══════════════════════════════════════════════════════════════════════

    def _run_functional_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск функциональных тестов."""
        lang = task.language

        if lang == "python":
            return self._run_python_test(code, task)
        elif lang == "kotlin":
            return self._run_kotlin_test(code, task)
        elif lang in ("javascript", "typescript"):
            return self._run_js_test(code, task)

        return {"success": True, "warning": f"No runner for {lang}"}

    def _run_python_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск Python с мокированием."""
        mock_setup = ""
        if task.external_dependencies:
            mock_setup = "import sys\nfrom unittest.mock import MagicMock, AsyncMock\n"
            for dep in task.external_dependencies:
                mock_setup += f"sys.modules['{dep}'] = MagicMock()\n"
            mock_setup += "\n"

        test_code = task.test_code.replace("{CODE}", code)
        full_code = f"{mock_setup}{code}\n\n# === TESTS ===\n{test_code}"

        try:
            namespace = {"__name__": "__main__"}
            exec(compile(full_code, "<test>", "exec"), namespace)
            return {"success": True}
        except AssertionError as e:
            return {"success": False, "error": f"Assertion failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Runtime error: {e}"}

    def _run_kotlin_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск Kotlin."""
        if not task.test_code:
            return {"success": True}

        full_code = f"{code}\n\n{task.test_code}"
        result = self.execute_kotlin_code(full_code)

        if result.get("success"):
            return {"success": True}
        return {"success": False, "error": result.get("error", "Unknown error")}

    def _run_js_test(self, code: str, task: CodeTask) -> Dict[str, Any]:
        """Запуск JavaScript."""
        if not task.test_code:
            return {"success": True}

        full_code = f"{code}\n\n{task.test_code}"
        suffix = ".mjs"

        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
            f.write(full_code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["node", tmp_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {"success": False, "error": result.stderr[:500] or result.stdout[:500]}
            return {"success": True}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}
        except FileNotFoundError:
            return {"success": False, "error": "Node.js not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ══════════════════════════════════════════════════════════════════════
    # ИЗВЛЕЧЕНИЕ КОДА
    # ══════════════════════════════════════════════════════════════════════

    def _extract_code(self, raw: str, lang: str) -> str:
        """Извлечение кода из ответа LLM."""
        cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL | re.IGNORECASE)

        lang_aliases = {
            "kotlin": ["kotlin", "kt"],
            "python": ["python", "py"],
            "javascript": ["javascript", "js"],
            "typescript": ["typescript", "ts"],
        }

        aliases = lang_aliases.get(lang, [lang])

        for alias in aliases:
            pattern = rf'```{alias}\s*\n(.*?)```'
            match = re.search(pattern, cleaned, flags=re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                if len(code) > 30:
                    return self._sanitize_code(code)

        match = re.search(r'```\w*\s*\n(.*?)```', cleaned, flags=re.DOTALL)
        if match:
            code = match.group(1).strip()
            if len(code) > 30:
                return self._sanitize_code(code)

        return ""
