from typing import List, Tuple

# Константы состояний
CREATED = "CREATED"
STARTED = "STARTED"
RESUMED = "RESUMED"
PAUSED = "PAUSED"
STOPPED = "STOPPED"
DESTROYED = "DESTROYED"

ALL_STATES = {CREATED, STARTED, RESUMED, PAUSED, STOPPED, DESTROYED}

# Таблица переходов
TRANSITIONS = {
    (None, 'onCreate'): CREATED,
    (CREATED, 'onStart'): STARTED,
    (STARTED, 'onResume'): RESUMED,
    (RESUMED, 'onPause'): PAUSED,
    (PAUSED, 'onStop'): STOPPED,
    (STOPPED, 'onDestroy'): DESTROYED,
    (PAUSED, 'onDestroy'): DESTROYED,
    (STARTED, 'onStop'): STOPPED,
    (STARTED, 'onDestroy'): DESTROYED,
    (CREATED, 'onStart'): STARTED,
    (CREATED, 'onDestroy'): DESTROYED,
    (RESUMED, 'onStop'): STOPPED,
    (STOPPED, 'onStart'): STARTED,
    (PAUSED, 'onStart'): STARTED,
}

# Специальное событие
ROTATE = "rotate"

def reduce_lifecycle(events: List[str]) -> Tuple[str, bool]:
    current_state = None
    can_access_ui = False

    # Развертываем rotate в последовательность событий
    expanded_events = []
    for event in events:
        if event == ROTATE:
            expanded_events.extend(['onPause', 'onStop', 'onDestroy', 'onCreate', 'onStart', 'onResume'])
        else:
            expanded_events.append(event)

    # Обрабатываем события по порядку
    for event in expanded_events:
        if event not in TRANSITIONS.get((current_state, None), set()):
            # Проверка на корректность перехода
            next_state = TRANSITIONS.get((current_state, event))
            if next_state is None:
                raise ValueError(f"Invalid lifecycle transition from {current_state} on {event}")
        else:
            # Если событие не в таблице, но допустимо (например, повторное событие)
            pass

        # Используем переход
        next_state = TRANSITIONS.get((current_state, event))
        if next_state is None:
            raise ValueError(f"Invalid lifecycle transition from {current_state} on {event}")

        current_state = next_state
        can_access_ui = (current_state == RESUMED)

    return (current_state, can_access_ui)
