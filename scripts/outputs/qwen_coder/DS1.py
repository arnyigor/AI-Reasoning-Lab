import time
from collections import OrderedDict

class LRUCacheTTL:
    def __init__(self, capacity: int, ttl_seconds: int):
        if capacity <= 0 or ttl_seconds <= 0:
            raise ValueError("capacity и ttl_seconds должны быть больше нуля")
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()

    def _purge_expired(self, now: float):
        """Удаляет просроченные записи из кэша."""
        expired_keys = []
        for key, item in self.cache.items():
            if now >= item['expires_at']:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

    def put(self, key, value, now: float):
        self._purge_expired(now)
        # Если ключ уже существует — обновляем его
        if key in self.cache:
            self.cache.move_to_end(key)  # Обновляем порядок (LRU)
        else:
            # Проверяем вместимость и удаляем LRU если нужно
            if len(self.cache) >= self.capacity:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

        self.cache[key] = {
            'value': value,
            'expires_at': now + self.ttl_seconds
        }

    def get(self, key, now: float):
        self._purge_expired(now)
        if key not in self.cache:
            return None

        item = self.cache[key]
        self.cache.move_to_end(key)  # Обновляем порядок (LRU)
        return item['value']

def ds1_check():
    # Создаём кэш с capacity=2 и ttl=3 секунды
    cache = LRUCacheTTL(capacity=2, ttl_seconds=3)

    now = 0.0

    # Проверка 1: put a@t=0, get a@t=1 == value
    cache.put("a", "value_a", now)
    result = cache.get("a", now + 1)
    if result != "value_a":
        return False

    # Проверка 2: get a@t=ttl == None (expired when now >= expires)
    result = cache.get("a", now + 3)  # ttl = 3 => ключ просрочен
    if result is not None:
        return False

    # Проверка 3: LRU eviction: capacity=2, добавить 3 ключа, выкинуть LRU.
    cache.put("b", "value_b", now)
    cache.put("c", "value_c", now)
    cache.put("d", "value_d", now)  # При этом кэш имеет вместимость 2

    # После добавления "d" ключ "b" должен быть вытеснен (LRU), так как он был использован первым
    result_b = cache.get("b", now)
    if result_b is not None:
        return False

    result_c = cache.get("c", now)
    if result_c != "value_c":
        return False

    result_d = cache.get("d", now)
    if result_d != "value_d":
        return False

    return True
