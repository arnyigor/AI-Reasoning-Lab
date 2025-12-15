# --- СЮДА ВСТАВИТЬ КОД МОДЕЛИ ---
class TransactionalKV:
    """
    In‑memory key/value store supporting arbitrarily nested transactions.
    """
    # Marker used to represent a deleted key inside a transaction layer
    _DELETED = object()

    def __init__(self):
        # layers[0] is the committed (root) data, each following element
        # represents an open transaction.  The top of the stack is the current
        # transaction context.
        self._layers: list[dict[str, object]] = [{}]

    # ------------------------------------------------------------------
    # Basic key/value operations – they always operate on the current layer
    # (the topmost dictionary).  Reads walk the layers from top to bottom,
    # honouring deletions and overriding values.
    # ------------------------------------------------------------------

    def set(self, key: str, value: object) -> None:
        """Store *value* under *key* in the active transaction."""
        self._layers[-1][key] = value

    def get(self, key: str) -> object | None:
        """
        Retrieve the value for *key*.  Search from the current layer downwards
        until a non‑deletion entry is found.  If the key is deleted or not
        present, return `None`.
        """
        for layer in reversed(self._layers):
            if key in layer:
                val = layer[key]
                return None if val is self._DELETED else val
        return None

    def delete(self, key: str) -> None:
        """Mark *key* as deleted in the current transaction."""
        self._layers[-1][key] = self._DELETED

    # ------------------------------------------------------------------
    # Transaction control – layers are pushed and popped from the stack.
    # ------------------------------------------------------------------

    def begin_transaction(self) -> None:
        """Start a new (nested) transaction by adding an empty layer."""
        self._layers.append({})

    def commit_transaction(self) -> None:
        """
        Merge changes made in the current (topmost) transaction into its
        parent.  Deletions are propagated correctly:

          * If the parent is another transaction (i.e., not the root),
            we store the `_DELETED` marker so that subsequent reads see
            the deletion.

          * If the parent is the root, we actually remove the key from the
            underlying dictionary.

        Raises ValueError if there is no active transaction to commit.
        """
        if len(self._layers) == 1:
            raise ValueError("No active transaction to commit.")

        # Remove the top layer and obtain its contents
        child_layer = self._layers.pop()
        parent_layer = self._layers[-1]          # now the new top

        is_parent_root = len(self._layers) == 1

        for key, val in child_layer.items():
            if val is self._DELETED:
                if is_parent_root:
                    # Truly delete from the root store
                    parent_layer.pop(key, None)
                else:
                    # Propagate deletion marker to the next transaction level
                    parent_layer[key] = self._DELETED
            else:
                parent_layer[key] = val

    def rollback_transaction(self) -> None:
        """
        Discard all changes made in the current transaction.
        Raises ValueError if there is no active transaction to roll back.
        """
        if len(self._layers) == 1:
            raise ValueError("No active transaction to roll back.")

        self._layers.pop()


# --- ВАЛИДАТОР ---
import unittest

class TestAIReasoningLab_Module3(unittest.TestCase):
    def setUp(self):
        self.db = TransactionalKV()

    def test_basic_ops(self):
        self.db.set("key1", "value1")
        self.assertEqual(self.db.get("key1"), "value1")
        self.db.set("key1", "value2")
        self.assertEqual(self.db.get("key1"), "value2")
        self.db.delete("key1")
        self.assertIsNone(self.db.get("key1"))

    def test_single_transaction_commit(self):
        self.db.set("a", 1)
        self.db.begin_transaction()
        self.db.set("a", 2)
        self.db.set("b", 3)
        self.assertEqual(self.db.get("a"), 2)
        self.assertEqual(self.db.get("b"), 3)
        self.db.commit_transaction()
        self.assertEqual(self.db.get("a"), 2)
        self.assertEqual(self.db.get("b"), 3)

    def test_single_transaction_rollback(self):
        self.db.set("a", 1)
        self.db.begin_transaction()
        self.db.set("a", 2)
        self.db.delete("a") # теперь None
        self.assertIsNone(self.db.get("a"))
        self.db.rollback_transaction()
        self.assertEqual(self.db.get("a"), 1) # Вернулось 1

    def test_nested_transactions(self):
        self.db.set("x", 100)
        self.db.begin_transaction() # L1
        self.db.set("x", 200)

        self.db.begin_transaction() # L2
        self.db.set("x", 300)
        self.assertEqual(self.db.get("x"), 300)
        self.db.rollback_transaction() # Откат L2 -> 200

        self.assertEqual(self.db.get("x"), 200)

        self.db.begin_transaction() # L2 снова
        self.db.delete("x")
        self.assertIsNone(self.db.get("x"))
        self.db.commit_transaction() # Применяем удаление к L1

        self.assertIsNone(self.db.get("x")) # В L1 теперь удалено
        self.db.rollback_transaction() # Откат L1 -> 100

        self.assertEqual(self.db.get("x"), 100)

    def test_commit_deletion_propagation(self):
        """Проверка, что удаление корректно всплывает при коммите"""
        self.db.set("d", "alive")
        self.db.begin_transaction()
        self.db.delete("d")
        self.assertIsNone(self.db.get("d"))
        self.db.begin_transaction()
        self.assertIsNone(self.db.get("d")) # И во вложенной тоже нет
        self.db.set("d", "zombie")
        self.db.commit_transaction() # d=zombie в уровень 1
        self.assertEqual(self.db.get("d"), "zombie")
        self.db.delete("d")
        self.db.commit_transaction() # d удален в корне
        self.assertIsNone(self.db.get("d"))

    def test_no_transaction_error(self):
        with self.assertRaises(Exception):
            self.db.commit_transaction()
        with self.assertRaises(Exception):
            self.db.rollback_transaction()

if __name__ == '__main__':
    print("\n🚀 ЗАПУСК МОДУЛЯ 3: DATA STRUCTURES (TRANSACTIONS)")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
