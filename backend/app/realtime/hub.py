"""In-process fan-out of live events to connected WebSockets.

Services queue events on the session (see app.db.uow). They are published only
after the transaction commits, so a client never sees XP that was rolled back.
One process holds every connection. Running several API replicas would put a
broker (Redis pub/sub) behind the same publish() call.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any

log = logging.getLogger(__name__)

Event = dict[str, Any]


class Hub:
    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[Event]]] = defaultdict(set)

    def subscribe(self, user_id: int) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=100)
        self._subscribers[user_id].add(queue)
        return queue

    def unsubscribe(self, user_id: int, queue: asyncio.Queue[Event]) -> None:
        subs = self._subscribers.get(user_id)
        if subs is not None:
            subs.discard(queue)
            if not subs:
                del self._subscribers[user_id]

    def publish(self, user_id: int, event: Event) -> None:
        for queue in list(self._subscribers.get(user_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # a stalled client loses events rather than blocking everyone
                log.warning("dropping realtime event for user %s: queue full", user_id)

    def connected(self, user_id: int) -> bool:
        return bool(self._subscribers.get(user_id))


hub = Hub()
